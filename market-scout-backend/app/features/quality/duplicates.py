from collections import defaultdict
from datetime import UTC, datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.constants import FIRST_PAGE
from app.core.exceptions import BadRequestException, ConflictException, NotFoundException
from app.core.scouting.dedupe import BusinessKeys, is_same_business, near_miss
from app.features.ai.models import AiUsage, LeadAiResult
from app.features.alerts.models import Alert
from app.features.businesses import ingest as businesses_ingest
from app.features.businesses.models import (
    Business,
    BusinessClassification,
    ContactKind,
    ContactPoint,
    LeadStatus,
    SourceRecord,
)
from app.features.compliance.models import DoNotContact
from app.features.geographies.models import Geography
from app.features.insights.models import BusinessSnapshot
from app.features.outreach.models import OutreachMessage
from app.features.pipeline import service as pipeline_service
from app.features.pipeline.models import ActivityKind, LeadActivity, LeadOutcome, LeadTask
from app.features.profiles.models import Profile
from app.features.quality.models import DuplicateCandidate, DuplicateConfidence, DuplicateStatus
from app.features.users.models import User

DEFAULT_LIMIT = 10
GRID_DEGREES = 0.003
MAX_SHARERS_PER_PHONE = 5
PHONE_KINDS = (ContactKind.PHONE.value, ContactKind.WHATSAPP.value)
PROGRESS_ORDER = [
    LeadStatus.NEW.value,
    LeadStatus.CONTACTED.value,
    LeadStatus.INTERESTED.value,
    LeadStatus.MEETING.value,
    LeadStatus.QUOTED.value,
    LeadStatus.CUSTOMER.value,
]
MERGED_SUMMARY = 'Merged with "{name}" (a duplicate)'
NOTES_JOINER = "\n\n"
NOT_FOUND_MESSAGE = "That pair was not found"
ALREADY_DECIDED_MESSAGE = "This pair has already been decided"
WRONG_LEAD_MESSAGE = "Choose one of the two leads in this pair to keep"
GONE_MESSAGE = "One of these leads no longer exists"



def _now() -> datetime:
    return datetime.now(UTC)


def _side(business: Business, phones: list[str], emails: list[str], city: str | None, assignee: str | None) -> dict:
    score = max((c.score for c in business.classifications), default=None)
    return {
        "id": business.id,
        "name": business.name,
        "address": business.address,
        "city": city,
        "website": business.website,
        "phones": phones,
        "emails": emails,
        "score": score,
        "lead_status": business.lead_status,
        "sources": sorted({record.source_key for record in business.source_records}),
        "rating": business.rating,
        "review_count": business.review_count,
        "assigned_to": assignee,
    }


def _describe(db: Session, business_ids: set[int]) -> dict[int, dict]:
    businesses = db.query(Business).filter(Business.id.in_(business_ids)).all()
    contacts: dict[int, tuple[list[str], list[str]]] = defaultdict(lambda: ([], []))
    for business_id, kind, value in db.query(ContactPoint.business_id, ContactPoint.kind, ContactPoint.value).filter(
        ContactPoint.business_id.in_(business_ids)
    ):
        if kind in PHONE_KINDS:
            contacts[business_id][0].append(value)
        elif kind == ContactKind.EMAIL.value:
            contacts[business_id][1].append(value)
    cities = dict(db.query(Geography.id, Geography.name).filter(Geography.id.in_({b.geography_id for b in businesses if b.geography_id})))
    people = dict(db.query(User.id, User.full_name).filter(User.id.in_({b.assigned_to_id for b in businesses if b.assigned_to_id})))
    return {
        business.id: _side(
            business,
            contacts[business.id][0],
            contacts[business.id][1],
            cities.get(business.geography_id),
            people.get(business.assigned_to_id),
        )
        for business in businesses
    }


def get_duplicates(
    db: Session, status: DuplicateStatus = DuplicateStatus.PENDING, page: int = FIRST_PAGE, limit: int = DEFAULT_LIMIT
) -> dict:
    query = db.query(DuplicateCandidate).filter(DuplicateCandidate.status == status.value)
    total = query.count()
    rows = (
        query.order_by(
            (DuplicateCandidate.confidence == DuplicateConfidence.LIKELY.value).desc(),
            DuplicateCandidate.similarity.desc(),
            DuplicateCandidate.id,
        )
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )
    ids = {row.business_a_id for row in rows} | {row.business_b_id for row in rows}
    sides = _describe(db, ids) if ids else {}
    data = [
        {
            "id": row.id, "reason": row.reason, "similarity": row.similarity, "confidence": row.confidence,
            "status": row.status, "created_at": row.created_at, "a": sides[row.business_a_id], "b": sides[row.business_b_id],
        }
        for row in rows
        if row.business_a_id in sides and row.business_b_id in sides
    ]
    return {"data": data, "count": total}


def _pending(db: Session, candidate_id: int) -> DuplicateCandidate:
    candidate = db.get(DuplicateCandidate, candidate_id)
    if candidate is None:
        raise NotFoundException(NOT_FOUND_MESSAGE)
    if candidate.status != DuplicateStatus.PENDING.value:
        raise ConflictException(ALREADY_DECIDED_MESSAGE)
    return candidate


def dismiss(db: Session, candidate_id: int, user_id: int) -> None:
    candidate = _pending(db, candidate_id)
    candidate.status = DuplicateStatus.DISMISSED.value
    candidate.decided_by_id = user_id
    candidate.decided_at = _now()
    db.commit()


def merge_pair(db: Session, candidate_id: int, keep_id: int, user_id: int) -> dict:
    candidate = _pending(db, candidate_id)
    if keep_id not in (candidate.business_a_id, candidate.business_b_id):
        raise BadRequestException(WRONG_LEAD_MESSAGE)
    remove_id = candidate.business_b_id if keep_id == candidate.business_a_id else candidate.business_a_id
    keep, remove = db.get(Business, keep_id), db.get(Business, remove_id)
    if keep is None or remove is None:
        raise NotFoundException(GONE_MESSAGE)
    merge_businesses(db, keep, remove, user_id)
    db.commit()
    return {"kept_id": keep_id, "removed_id": remove_id}


def _move_unique(db: Session, model, keep_id: int, remove_id: int, key) -> None:
    held = {key(row) for row in db.query(model).filter(model.business_id == keep_id)}
    for row in db.query(model).filter(model.business_id == remove_id).all():
        if key(row) in held:
            db.delete(row)
        else:
            row.business_id = keep_id
    db.flush()


def merge_businesses(db: Session, keep: Business, remove: Business, actor_id: int | None) -> None:
    keep_id, remove_id = keep.id, remove.id
    removed_name = remove.name

    _move_unique(db, ContactPoint, keep_id, remove_id, lambda row: (row.kind, row.value))
    _move_unique(db, BusinessSnapshot, keep_id, remove_id, lambda row: row.run_id if row.run_id is not None else ("none", row.id))
    _move_unique(db, LeadAiResult, keep_id, remove_id, lambda row: row.profile_id)
    keeper_classes = {row.profile_id: row for row in db.query(BusinessClassification).filter(BusinessClassification.business_id == keep_id)}
    for row in db.query(BusinessClassification).filter(BusinessClassification.business_id == remove_id).all():
        existing = keeper_classes.get(row.profile_id)
        if existing is None:
            row.business_id = keep_id
        else:
            if existing.segment_id is None:
                existing.segment_id = row.segment_id
            db.delete(row)
    db.flush()

    carried_outcome = False
    if db.query(LeadOutcome.id).filter(LeadOutcome.business_id == keep_id).first() is None:
        carried_outcome = db.query(LeadOutcome).filter(LeadOutcome.business_id == remove_id).update(
            {LeadOutcome.business_id: keep_id}, synchronize_session=False
        ) > 0
    db.query(LeadOutcome).filter(LeadOutcome.business_id == remove_id).delete(synchronize_session=False)

    for model in (SourceRecord, LeadActivity, LeadTask, DoNotContact, AiUsage, OutreachMessage):
        db.query(model).filter(model.business_id == remove_id).update({model.business_id: keep_id}, synchronize_session=False)
    db.query(Alert).filter(Alert.business_id == remove_id).delete(synchronize_session=False)

    _merge_fields(keep, remove, carried_outcome)
    pipeline_service.add_system_activity(db, keep_id, ActivityKind.MERGED, actor_id, summary=MERGED_SUMMARY.format(name=removed_name))
    db.flush()

    db.expire(remove)
    db.query(Business).filter(Business.id == remove_id).delete(synchronize_session=False)
    db.expire(keep)
    _rescore(db, keep)


def _merge_fields(keep: Business, remove: Business, carried_outcome: bool) -> None:
    for field in ("address", "latitude", "longitude", "geography_id"):
        if getattr(keep, field) is None and getattr(remove, field) is not None:
            setattr(keep, field, getattr(remove, field))
    if not keep.website and remove.website:
        keep.website, keep.website_domain = remove.website, remove.website_domain
        keep.website_status, keep.website_check_note, keep.website_checked_at = (
            remove.website_status, remove.website_check_note, remove.website_checked_at,
        )
    if (remove.review_count or 0) > (keep.review_count or 0):
        keep.rating, keep.review_count = remove.rating, remove.review_count
    keep.categories = list(dict.fromkeys([*(keep.categories or []), *(remove.categories or [])]))
    keep.first_seen_at = min(keep.first_seen_at, remove.first_seen_at, key=_comparable)
    keep.last_seen_at = max(keep.last_seen_at, remove.last_seen_at, key=_comparable)
    if keep.assigned_to_id is None:
        keep.assigned_to_id = remove.assigned_to_id
    if not keep.contact_name:
        keep.contact_name = remove.contact_name
    if remove.notes and remove.notes != keep.notes:
        keep.notes = NOTES_JOINER.join(part for part in (keep.notes, remove.notes) if part)

    if carried_outcome:
        keep.lead_status = remove.lead_status
    elif _progress(remove.lead_status) > _progress(keep.lead_status) and keep.lead_status != LeadStatus.NOT_INTERESTED.value:
        keep.lead_status = remove.lead_status


def _progress(status: str) -> int:
    return PROGRESS_ORDER.index(status) if status in PROGRESS_ORDER else -1


def _comparable(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _rescore(db: Session, business: Business) -> None:
    profile_ids = [row[0] for row in db.query(BusinessClassification.profile_id).filter(BusinessClassification.business_id == business.id)]
    for profile in db.query(Profile).filter(Profile.id.in_(profile_ids)).all():
        businesses_ingest.rescore_business(db, business, businesses_ingest.build_profile_scoring(profile))


def scan(db: Session, progress=None) -> dict[str, int]:
    rows = db.query(Business.id, Business.normalized_name, Business.website_domain, Business.latitude, Business.longitude).all()
    phones: dict[int, set[str]] = defaultdict(set)
    for business_id, value in db.query(ContactPoint.business_id, ContactPoint.value).filter(ContactPoint.kind.in_(PHONE_KINDS)):
        phones[business_id].add(value)
    keys = {
        row.id: BusinessKeys(row.normalized_name, frozenset(phones[row.id]), row.website_domain, row.latitude, row.longitude)
        for row in rows
    }

    by_phone: dict[str, list[int]] = defaultdict(list)
    for business_id, values in phones.items():
        for value in values:
            by_phone[value].append(business_id)
    grid: dict[tuple[int, int], list[int]] = defaultdict(list)
    for row in rows:
        if row.latitude is not None and row.longitude is not None:
            grid[(int(row.latitude // GRID_DEGREES), int(row.longitude // GRID_DEGREES))].append(row.id)
    by_domain: dict[str, list[int]] = defaultdict(list)
    for row in rows:
        if row.website_domain:
            by_domain[row.website_domain].append(row.id)

    pairs: set[tuple[int, int]] = set()
    for group in (*by_domain.values(), *(ids for ids in by_phone.values() if len(ids) <= MAX_SHARERS_PER_PHONE)):
        for index, first in enumerate(group):
            pairs.update((min(first, other), max(first, other)) for other in group[index + 1:])
    for (row, column), members in grid.items():
        neighbours = [other for dr in (-1, 0, 1) for dc in (-1, 0, 1) for other in grid.get((row + dr, column + dc), [])]
        for first in members:
            pairs.update((min(first, other), max(first, other)) for other in neighbours if other != first)

    known = {(first, second) for first, second in db.query(DuplicateCandidate.business_a_id, DuplicateCandidate.business_b_id)}
    found = added = 0
    for first, second in sorted(pairs - known):
        decision = is_same_business(keys[first], keys[second])
        if decision.is_match:
            confidence, reason, similarity = DuplicateConfidence.LIKELY.value, decision.reason, 100
        else:
            miss = near_miss(keys[first], keys[second])
            if miss is None:
                continue
            confidence, reason, similarity = DuplicateConfidence.POSSIBLE.value, miss.reason, miss.similarity
        found += 1
        db.add(DuplicateCandidate(business_a_id=first, business_b_id=second, reason=reason, similarity=similarity, confidence=confidence))
        added += 1
        if added % 500 == 0:
            db.commit()
    db.commit()
    return {"businesses": len(rows), "pairs_found": found}


def pending_count(db: Session) -> int:
    return db.query(func.count(DuplicateCandidate.id)).filter(DuplicateCandidate.status == DuplicateStatus.PENDING.value).scalar() or 0

