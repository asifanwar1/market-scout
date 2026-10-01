import logging
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.scouting.classify import LeadSignals, SegmentRule, classify, score_lead
from app.core.scouting.dedupe import BusinessKeys, is_same_business
from app.core.scouting.normalize import (
    PhoneInfo,
    extract_phones_from_many,
    normalize_email,
    normalize_name,
    normalize_website,
)
from app.core.scouting.types import RawBusiness
from app.features.businesses.models import (
    Business,
    BusinessClassification,
    ContactKind,
    ContactPoint,
    SourceRecord,
)
from app.features.compliance import service as compliance_service
from app.features.insights.models import BusinessSnapshot

_GEO_PREFILTER_DEGREES = 0.003
_PHONE_KINDS = (ContactKind.PHONE.value, ContactKind.WHATSAPP.value)
_MATCH_PRIORITY = {"website": 0, "phone": 1, "location": 2}
_MAX_CATEGORIES = 20


@dataclass(frozen=True)
class ProfileScoring:
    profile_id: int
    segment_ids: dict[str, int]
    segment_rules: list[SegmentRule]
    weights: dict[str, int]


@dataclass(frozen=True)
class IngestContext:
    run_id: int | None
    geography_id: int | None
    hint_segment_slug: str | None
    now: datetime
    profile: ProfileScoring


@dataclass(frozen=True)
class IngestOutcome:
    business: Business | None
    created: bool
    phone_count: int
    has_website: bool
    has_email: bool
    blocked: bool = False


logger = logging.getLogger(__name__)

STAT_FIELDS = ("found", "new", "merged", "blocked", "with_phone", "with_website", "with_email", "errors")


def build_profile_scoring(profile) -> ProfileScoring:
    from app.features.profiles.schemas import ScoringConfig

    weights = {**ScoringConfig().model_dump(), **(profile.scoring_config or {})}
    return ProfileScoring(
        profile_id=profile.id,
        segment_ids={segment.slug: segment.id for segment in profile.segments},
        segment_rules=[
            SegmentRule(segment.slug, tuple((segment.match_rules or {}).get("name_patterns", [])))
            for segment in profile.segments
        ],
        weights=weights,
    )


def ingest_records(db: Session, items: Iterable[tuple[RawBusiness, IngestContext]]) -> dict[str, int]:
    counts = dict.fromkeys(STAT_FIELDS, 0)
    for raw, context in items:
        try:
            with db.begin_nested():
                outcome = ingest_business(db, raw, context)
        except Exception:
            logger.exception("Could not store %s/%s", raw.source_key, raw.external_id)
            counts["errors"] += 1
            continue

        if outcome.blocked:
            counts["blocked"] += 1
            continue

        counts["found"] += 1
        counts["new" if outcome.created else "merged"] += 1
        counts["with_phone"] += outcome.phone_count > 0
        counts["with_website"] += outcome.has_website
        counts["with_email"] += outcome.has_email
    return counts


def ingest_business(db: Session, raw: RawBusiness, ctx: IngestContext) -> IngestOutcome:
    phones = extract_phones_from_many(raw.phones)
    site = normalize_website(raw.website)
    emails = list(dict.fromkeys(e for e in (normalize_email(x) for x in raw.emails) if e))
    all_phones = frozenset(phone.e164 for phone in phones)
    keys = BusinessKeys(
        normalized_name=normalize_name(raw.name),
        phones=all_phones - frozenset(raw.unreliable_phones),
        domain=site.domain,
        latitude=raw.latitude,
        longitude=raw.longitude,
    )

    record = (
        db.query(SourceRecord)
        .filter(SourceRecord.source_key == raw.source_key, SourceRecord.external_id == raw.external_id)
        .first()
    )
    business = record.business if record else _find_match(db, keys)

    blocked = business is not None and compliance_service.is_business_blocked(db, business.id)
    if blocked or compliance_service.identifiers_blocked(db, all_phones, emails):
        return IngestOutcome(business=None, created=False, phone_count=0, has_website=False, has_email=False, blocked=True)

    created = business is None
    if business is None:
        business = Business(
            name=raw.name.strip(),
            normalized_name=keys.normalized_name,
            geography_id=ctx.geography_id,
            first_seen_at=ctx.now,
            last_seen_at=ctx.now,
            categories=[],
        )
        db.add(business)
        db.flush()

    _merge_fields(business, raw, site.url, site.domain, ctx)
    _record_snapshot(db, business, ctx)
    _store_source_record(db, business, record, raw, ctx)
    _add_contact_points(db, business, raw.source_key, phones, emails, site.social_platform, site.social_url)
    db.flush()
    classify_business(db, business, ctx.profile, ctx.hint_segment_slug)

    return IngestOutcome(
        business=business,
        created=created,
        phone_count=len(phones),
        has_website=site.url is not None,
        has_email=bool(emails),
    )


def add_enrichment_contacts(
    db: Session,
    business: Business,
    *,
    emails: list[str],
    phones: list[PhoneInfo],
    whatsapp: list[str],
    facebook: str | None,
    instagram: str | None,
    source_key: str,
) -> int:
    added = _add_contact_points(
        db, business, source_key, phones, emails, None, None,
        whatsapp=whatsapp, facebook=facebook, instagram=instagram,
    )
    db.flush()
    return added


def classify_business(db: Session, business: Business, profile: ProfileScoring, hint_slug: str | None) -> None:
    result = classify(business.name, hint_slug, profile.segment_rules)
    segment_id = profile.segment_ids.get(result.segment_slug) if result.segment_slug else None

    classification = (
        db.query(BusinessClassification)
        .filter(BusinessClassification.business_id == business.id, BusinessClassification.profile_id == profile.profile_id)
        .first()
    )
    if classification is None:
        classification = BusinessClassification(business_id=business.id, profile_id=profile.profile_id, score=0)
        db.add(classification)

    if classification.segment_id is None or result.name_matched:
        classification.segment_id = segment_id or classification.segment_id

    signals = _contact_signals(db, business)
    classification.score = score_lead(signals, result.name_matched, profile.weights)
    db.flush()


def rescore_business(db: Session, business: Business, profile: ProfileScoring) -> None:
    slug_by_id = {segment_id: slug for slug, segment_id in profile.segment_ids.items()}
    existing = (
        db.query(BusinessClassification.segment_id)
        .filter(BusinessClassification.business_id == business.id, BusinessClassification.profile_id == profile.profile_id)
        .first()
    )
    hint = slug_by_id.get(existing[0]) if existing else None
    classify_business(db, business, profile, hint)


def _find_match(db: Session, keys: BusinessKeys) -> Business | None:
    candidate_ids: set[int] = set()

    if keys.phones:
        rows = (
            db.query(ContactPoint.business_id)
            .filter(ContactPoint.kind.in_(_PHONE_KINDS), ContactPoint.value.in_(keys.phones))
            .all()
        )
        candidate_ids.update(row[0] for row in rows)
    if keys.domain:
        candidate_ids.update(row[0] for row in db.query(Business.id).filter(Business.website_domain == keys.domain))
    if keys.latitude is not None and keys.longitude is not None:
        box = _GEO_PREFILTER_DEGREES
        rows = db.query(Business.id).filter(
            Business.latitude.between(keys.latitude - box, keys.latitude + box),
            Business.longitude.between(keys.longitude - box, keys.longitude + box),
        )
        candidate_ids.update(row[0] for row in rows)

    if not candidate_ids:
        return None

    phones_by_business: dict[int, set[str]] = defaultdict(set)
    for business_id, value in (
        db.query(ContactPoint.business_id, ContactPoint.value)
        .filter(ContactPoint.business_id.in_(candidate_ids), ContactPoint.kind.in_(_PHONE_KINDS))
    ):
        phones_by_business[business_id].add(value)

    best: tuple[Business, str] | None = None
    for candidate in db.query(Business).filter(Business.id.in_(candidate_ids)).all():
        decision = is_same_business(
            keys,
            BusinessKeys(
                candidate.normalized_name,
                frozenset(phones_by_business[candidate.id]),
                candidate.website_domain,
                candidate.latitude,
                candidate.longitude,
            ),
        )
        if decision.is_match and (best is None or _MATCH_PRIORITY[decision.reason] < _MATCH_PRIORITY[best[1]]):
            best = (candidate, decision.reason)
    return best[0] if best else None


def _merge_fields(business: Business, raw: RawBusiness, website_url: str | None, domain: str | None, ctx: IngestContext) -> None:
    business.last_seen_at = ctx.now
    if not business.address and raw.address:
        business.address = raw.address
    if business.latitude is None and raw.latitude is not None and raw.longitude is not None:
        business.latitude, business.longitude = raw.latitude, raw.longitude
    if not business.website and website_url:
        business.website, business.website_domain = website_url, domain
    if business.geography_id is None:
        business.geography_id = ctx.geography_id
    if raw.review_count is not None and raw.review_count >= (business.review_count or 0):
        business.rating, business.review_count = raw.rating, raw.review_count
    if raw.categories:
        merged = list(dict.fromkeys([*(business.categories or []), *raw.categories]))
        business.categories = merged[:_MAX_CATEGORIES]


def _record_snapshot(db: Session, business: Business, ctx: IngestContext) -> None:
    if ctx.run_id is None or (business.rating is None and business.review_count is None):
        return
    snapshot = (
        db.query(BusinessSnapshot)
        .filter(BusinessSnapshot.business_id == business.id, BusinessSnapshot.run_id == ctx.run_id)
        .first()
    )
    if snapshot is None:
        snapshot = BusinessSnapshot(business_id=business.id, run_id=ctx.run_id)
        db.add(snapshot)
    snapshot.seen_at = ctx.now
    snapshot.rating = business.rating
    snapshot.review_count = business.review_count


def _store_source_record(db: Session, business: Business, record: SourceRecord | None, raw: RawBusiness, ctx: IngestContext) -> None:
    if record is None:
        db.add(
            SourceRecord(
                business_id=business.id,
                run_id=ctx.run_id,
                source_key=raw.source_key,
                external_id=raw.external_id,
                raw_payload=raw.raw,
                fetched_at=ctx.now,
            )
        )
        return
    record.run_id = ctx.run_id
    record.raw_payload = raw.raw
    record.fetched_at = ctx.now


def _add_contact_points(
    db: Session,
    business: Business,
    source_key: str,
    phones: list[PhoneInfo],
    emails: list[str],
    social_platform: str | None,
    social_url: str | None,
    *,
    whatsapp: list[str] | None = None,
    facebook: str | None = None,
    instagram: str | None = None,
) -> int:
    existing = {
        (row.kind, row.value)
        for row in db.query(ContactPoint.kind, ContactPoint.value).filter(ContactPoint.business_id == business.id)
    }
    wanted: list[ContactPoint] = []

    def want(kind: ContactKind, value: str, is_mobile: bool = False, whatsapp_likely: bool = False) -> None:
        if (kind.value, value) not in existing:
            existing.add((kind.value, value))
            wanted.append(
                ContactPoint(
                    business_id=business.id, kind=kind.value, value=value,
                    is_mobile=is_mobile, whatsapp_likely=whatsapp_likely, source_key=source_key,
                )
            )

    for phone in phones:
        want(ContactKind.PHONE, phone.e164, is_mobile=phone.is_mobile, whatsapp_likely=phone.is_mobile)
    for number in whatsapp or []:
        want(ContactKind.WHATSAPP, number, is_mobile=True, whatsapp_likely=True)
    for email in emails:
        want(ContactKind.EMAIL, email)
    if social_platform and social_url:
        want(ContactKind(social_platform), social_url)
    if facebook:
        want(ContactKind.FACEBOOK, facebook)
    if instagram:
        want(ContactKind.INSTAGRAM, instagram)

    db.add_all(wanted)
    return len(wanted)


def _contact_signals(db: Session, business: Business) -> LeadSignals:
    rows = db.query(ContactPoint.kind, ContactPoint.whatsapp_likely).filter(ContactPoint.business_id == business.id).all()
    return LeadSignals(
        has_phone=any(kind in _PHONE_KINDS for kind, _ in rows),
        has_whatsapp_likely=any(likely or kind == ContactKind.WHATSAPP.value for kind, likely in rows),
        has_website=bool(business.website),
        has_email=any(kind == ContactKind.EMAIL.value for kind, _ in rows),
        review_count=business.review_count,
    )
