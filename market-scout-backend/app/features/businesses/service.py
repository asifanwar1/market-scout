import re
from collections.abc import Iterator
from dataclasses import dataclass

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, defer, joinedload, selectinload

from app.core.constants import EMAIL_SEPARATOR, FIRST_PAGE
from app.core.exceptions import BadRequestException, NotFoundException
from app.features.ai import service as ai_service
from app.features.ai.models import AnalysisStatus, LeadAiResult
from app.features.businesses.models import (
    Business,
    BusinessClassification,
    ContactKind,
    ContactPoint,
    LeadStatus,
    SourceRecord,
)
from app.features.businesses.schemas import BulkBusinessDelete, BulkBusinessUpdate, BusinessSort, BusinessUpdate, SortDirection
from app.features.compliance import service as compliance_service
from app.features.geographies import service as geographies_service
from app.features.geographies.models import Geography
from app.features.pipeline import service as pipeline_service
from app.features.profiles.models import ProfileSegment
from app.features.users.models import User

MIN_PHONE_SEARCH_DIGITS = 4
EXPORT_BATCH_SIZE = 500


DEFAULT_LIMIT = 25


_PHONE_KINDS = (ContactKind.PHONE.value, ContactKind.WHATSAPP.value)


@dataclass
class BusinessFilters:
    profile_id: int | None = None
    segment: str | None = None
    geography_id: int | None = None
    has_phone: bool | None = None
    whatsapp_likely: bool | None = None
    has_email: bool | None = None
    has_website: bool | None = None
    status: LeadStatus | None = None
    assigned_to_id: int | None = None
    unassigned: bool = False
    source: str | None = None
    min_score: int | None = None
    min_ai_fit: int | None = None
    search: str | None = None


def visible_businesses(db: Session, filters: BusinessFilters):
    query = db.query(Business).filter(compliance_service.not_blocked_filter())
    return _apply_filters(db, query, filters)


def _apply_filters(db: Session, query, f: BusinessFilters):
    if f.segment and f.profile_id is None:
        raise BadRequestException("Choose a profile to filter by segment")
    if f.unassigned and f.assigned_to_id is not None:
        raise BadRequestException("Filter by assignee or by unassigned, not both")

    if f.profile_id is not None:
        classified = [BusinessClassification.profile_id == f.profile_id]
        if f.segment:
            segment_ids = select(ProfileSegment.id).where(
                ProfileSegment.profile_id == f.profile_id, ProfileSegment.slug == f.segment
            )
            classified.append(BusinessClassification.segment_id.in_(segment_ids))
        query = query.filter(Business.classifications.any(and_(*classified)))

    if f.min_score is not None:
        score_conditions = [BusinessClassification.score >= f.min_score]
        if f.profile_id is not None:
            score_conditions.append(BusinessClassification.profile_id == f.profile_id)
        query = query.filter(Business.classifications.any(and_(*score_conditions)))

    if f.min_ai_fit is not None:
        fitted = select(LeadAiResult.business_id).where(
            LeadAiResult.status == AnalysisStatus.OK.value, LeadAiResult.fit_score >= f.min_ai_fit
        )
        if f.profile_id is not None:
            fitted = fitted.where(LeadAiResult.profile_id == f.profile_id)
        query = query.filter(Business.id.in_(fitted))

    if f.geography_id is not None:
        query = query.filter(Business.geography_id.in_(geographies_service.get_city_ids(db, f.geography_id)))

    query = _tri_state(query, f.has_phone, Business.contact_points.any(ContactPoint.kind.in_(_PHONE_KINDS)))
    query = _tri_state(
        query, f.whatsapp_likely,
        Business.contact_points.any(
            or_(ContactPoint.whatsapp_likely.is_(True), ContactPoint.kind == ContactKind.WHATSAPP.value)
        ),
    )
    query = _tri_state(query, f.has_email, Business.contact_points.any(ContactPoint.kind == ContactKind.EMAIL.value))
    query = _tri_state(query, f.has_website, Business.website.isnot(None))

    if f.status is not None:
        query = query.filter(Business.lead_status == f.status.value)
    if f.assigned_to_id is not None:
        query = query.filter(Business.assigned_to_id == f.assigned_to_id)
    if f.unassigned:
        query = query.filter(Business.assigned_to_id.is_(None))
    if f.source:
        query = query.filter(Business.source_records.any(SourceRecord.source_key == f.source))
    if f.search and f.search.strip():
        query = query.filter(_search_condition(f.search.strip()))
    return query


def _tri_state(query, wanted: bool | None, condition):
    if wanted is None:
        return query
    return query.filter(condition if wanted else ~condition)


def _search_condition(term: str):
    like = f"%{term}%"
    conditions = [Business.name.ilike(like), Business.address.ilike(like)]

    digits = re.sub(r"\D", "", term)
    if len(digits) >= MIN_PHONE_SEARCH_DIGITS:
        local = digits.removeprefix("0092").removeprefix("92").lstrip("0") or digits
        conditions.append(
            Business.contact_points.any(
                and_(ContactPoint.kind.in_(_PHONE_KINDS), ContactPoint.value.like(f"%{local}%"))
            )
        )
    if EMAIL_SEPARATOR in term:
        conditions.append(
            Business.contact_points.any(
                and_(ContactPoint.kind == ContactKind.EMAIL.value, ContactPoint.value.ilike(like))
            )
        )
    return or_(*conditions)


def _score_subquery(profile_id: int | None):
    stmt = select(func.coalesce(func.max(BusinessClassification.score), -1)).where(
        BusinessClassification.business_id == Business.id
    )
    if profile_id is not None:
        stmt = stmt.where(BusinessClassification.profile_id == profile_id)
    return stmt.correlate(Business).scalar_subquery()


def _ai_fit_subquery(profile_id: int | None):
    stmt = select(func.coalesce(func.max(LeadAiResult.fit_score), -1)).where(
        LeadAiResult.business_id == Business.id, LeadAiResult.status == AnalysisStatus.OK.value
    )
    if profile_id is not None:
        stmt = stmt.where(LeadAiResult.profile_id == profile_id)
    return stmt.correlate(Business).scalar_subquery()


def _order_clauses(sort: BusinessSort | None, direction: SortDirection | None, profile_id: int | None) -> list:
    sort = sort or (BusinessSort.SCORE if profile_id is not None else BusinessSort.NEWEST)
    column = {
        BusinessSort.SCORE: _score_subquery(profile_id),
        BusinessSort.AI_FIT: _ai_fit_subquery(profile_id),
        BusinessSort.NEWEST: Business.first_seen_at,
        BusinessSort.LAST_SEEN: Business.last_seen_at,
        BusinessSort.NAME: func.lower(Business.name),
    }[sort]
    descending = (direction or (SortDirection.ASC if sort == BusinessSort.NAME else SortDirection.DESC)) == SortDirection.DESC
    return [column.desc() if descending else column.asc(), Business.id.desc() if descending else Business.id.asc()]


def get_businesses(
    db: Session,
    filters: BusinessFilters,
    page: int = FIRST_PAGE,
    limit: int = DEFAULT_LIMIT,
    sort: BusinessSort | None = None,
    direction: SortDirection | None = None,
) -> dict:
    query = visible_businesses(db, filters)
    total_count = query.count()

    businesses = (
        query.order_by(*_order_clauses(sort, direction, filters.profile_id))
        .options(
            selectinload(Business.contact_points),
            selectinload(Business.classifications),
            joinedload(Business.geography).joinedload(Geography.parent),
        )
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )
    lookups = _load_lookups(db, businesses)
    fits = ai_service.fit_scores(db, [b.id for b in businesses], filters.profile_id)
    return {"data": [_to_list_item(b, filters.profile_id, lookups, fits.get(b.id)) for b in businesses], "count": total_count}


def iter_business_batches(
    db: Session,
    filters: BusinessFilters,
    sort: BusinessSort | None = None,
    direction: SortDirection | None = None,
    batch_size: int = EXPORT_BATCH_SIZE,
) -> Iterator[tuple[list[Business], "_Lookups"]]:
    ids = [
        row[0]
        for row in visible_businesses(db, filters)
        .with_entities(Business.id)
        .order_by(*_order_clauses(sort, direction, filters.profile_id))
        .all()
    ]
    for start in range(0, len(ids), batch_size):
        chunk = ids[start:start + batch_size]
        by_id = {
            business.id: business
            for business in db.query(Business)
            .filter(Business.id.in_(chunk))
            .options(
                selectinload(Business.contact_points),
                selectinload(Business.classifications),
                joinedload(Business.geography).joinedload(Geography.parent),
            )
            .all()
        }
        businesses = [by_id[business_id] for business_id in chunk if business_id in by_id]
        yield businesses, _load_lookups(db, businesses)


@dataclass
class _Lookups:
    users: dict[int, str]
    segments: dict[int, tuple[str, str]]
    sources: dict[int, list[str]]


def _load_lookups(db: Session, businesses: list[Business], with_sources: bool = True) -> _Lookups:
    business_ids = [b.id for b in businesses]
    user_ids = {b.assigned_to_id for b in businesses if b.assigned_to_id is not None}
    segment_ids = {c.segment_id for b in businesses for c in b.classifications if c.segment_id is not None}

    users = dict(db.query(User.id, User.full_name).filter(User.id.in_(user_ids)).all()) if user_ids else {}
    segments = (
        {sid: (slug, name) for sid, slug, name in db.query(ProfileSegment.id, ProfileSegment.slug, ProfileSegment.name)
         .filter(ProfileSegment.id.in_(segment_ids))}
        if segment_ids else {}
    )
    sources: dict[int, list[str]] = {}
    if with_sources and business_ids:
        rows = db.query(SourceRecord.business_id, SourceRecord.source_key).filter(SourceRecord.business_id.in_(business_ids)).distinct()
        for business_id, source_key in rows:
            sources.setdefault(business_id, []).append(source_key)
    return _Lookups(users, segments, {k: sorted(v) for k, v in sources.items()})


def _assigned(business: Business, lookups: _Lookups) -> dict | None:
    if business.assigned_to_id is None:
        return None
    return {"id": business.assigned_to_id, "full_name": lookups.users.get(business.assigned_to_id, "Unknown user")}


def _place(business: Business) -> tuple[str | None, str | None]:
    city = business.geography
    province = city.parent if city is not None else None
    return (city.name if city else None, province.name if province else None)


def _to_list_item(business: Business, profile_id: int | None, lookups: _Lookups, ai_fit: int | None = None) -> dict:
    classifications = business.classifications
    if profile_id is not None:
        classifications = [c for c in classifications if c.profile_id == profile_id]
    chosen = max(classifications, key=lambda c: c.score, default=None)
    segment = lookups.segments.get(chosen.segment_id) if chosen and chosen.segment_id else None

    phones = sorted((c for c in business.contact_points if c.kind in _PHONE_KINDS), key=lambda c: (not c.whatsapp_likely, c.id))
    emails = sorted((c for c in business.contact_points if c.kind == ContactKind.EMAIL.value), key=lambda c: c.id)
    city, province = _place(business)

    return {
        "id": business.id,
        "name": business.name,
        "address": business.address,
        "city": city,
        "province": province,
        "profile_id": chosen.profile_id if chosen else None,
        "segment_slug": segment[0] if segment else None,
        "segment_name": segment[1] if segment else None,
        "score": chosen.score if chosen else None,
        "ai_fit": ai_fit,
        "lead_status": business.lead_status,
        "assigned_to": _assigned(business, lookups),
        "primary_phone": phones[0].value if phones else None,
        "whatsapp_likely": any(c.whatsapp_likely or c.kind == ContactKind.WHATSAPP.value for c in business.contact_points),
        "email": emails[0].value if emails else None,
        "website": business.website,
        "rating": business.rating,
        "review_count": business.review_count,
        "sources": lookups.sources.get(business.id, []),
        "first_seen_at": business.first_seen_at,
        "last_seen_at": business.last_seen_at,
    }


def get_business_by_id(db: Session, business_id: int) -> Business:
    business = (
        db.query(Business)
        .filter(Business.id == business_id, compliance_service.not_blocked_filter())
        .options(
            selectinload(Business.contact_points),
            selectinload(Business.classifications),
            selectinload(Business.source_records).options(defer(SourceRecord.raw_payload)),
            joinedload(Business.geography).joinedload(Geography.parent),
        )
        .first()
    )
    if business is None:
        raise NotFoundException("Business not found")
    return business


def get_business_detail(db: Session, business_id: int) -> dict:
    business = get_business_by_id(db, business_id)
    lookups = _load_lookups(db, [business], with_sources=False)
    city, province = _place(business)
    top = max(business.classifications, key=lambda c: c.score, default=None)
    top_profile_id = top.profile_id if top else None

    return {
        "id": business.id,
        "name": business.name,
        "address": business.address,
        "city_id": business.geography_id,
        "city": city,
        "province": province,
        "latitude": business.latitude,
        "longitude": business.longitude,
        "website": business.website,
        "website_status": business.website_status,
        "website_check_note": business.website_check_note,
        "website_checked_at": business.website_checked_at,
        "rating": business.rating,
        "review_count": business.review_count,
        "categories": business.categories or [],
        "lead_status": business.lead_status,
        "assigned_to": _assigned(business, lookups),
        "notes": business.notes,
        "contact_name": business.contact_name,
        "outcome": pipeline_service.get_outcome(db, business.id),
        "ai": ai_service.get_result_view(db, business.id, top_profile_id),
        "classifications": [
            {
                "profile_id": c.profile_id,
                "segment_slug": lookups.segments[c.segment_id][0] if c.segment_id in lookups.segments else None,
                "segment_name": lookups.segments[c.segment_id][1] if c.segment_id in lookups.segments else None,
                "score": c.score,
            }
            for c in sorted(business.classifications, key=lambda c: -c.score)
        ],
        "contacts": sorted(business.contact_points, key=lambda c: (c.kind, c.id)),
        "sources": sorted(business.source_records, key=lambda r: r.id),
        "first_seen_at": business.first_seen_at,
        "last_seen_at": business.last_seen_at,
        "enriched_at": business.enriched_at,
        "updated_at": business.updated_at,
    }


def _require_assignable_user(db: Session, user_id: int) -> None:
    if not db.query(User.id).filter(User.id == user_id, User.is_active.is_(True)).first():
        raise BadRequestException("That user doesn't exist or is inactive")


def _user_name(db: Session, user_id: int | None) -> str | None:
    if user_id is None:
        return None
    return db.query(User.full_name).filter(User.id == user_id).scalar()


def update_business(db: Session, business_id: int, update_in: BusinessUpdate, actor_id: int | None = None) -> dict:
    business = get_business_by_id(db, business_id)
    data = update_in.model_dump(exclude_unset=True, exclude={"outcome"})

    if "lead_status" in data and data["lead_status"] is None:
        raise BadRequestException("lead_status can't be empty")
    if data.get("assigned_to_id") is not None:
        _require_assignable_user(db, data["assigned_to_id"])

    if "lead_status" in data or update_in.outcome is not None:
        new_status = data["lead_status"].value if "lead_status" in data else business.lead_status
        pipeline_service.apply_status_change(db, business, new_status, actor_id, update_in.outcome)
    if "assigned_to_id" in data:
        before = _user_name(db, business.assigned_to_id)
        business.assigned_to_id = data["assigned_to_id"]
        pipeline_service.record_assignment(db, business.id, before, _user_name(db, data["assigned_to_id"]), actor_id)
    if "notes" in data:
        business.notes = (data["notes"] or "").strip() or None
    if "contact_name" in data:
        business.contact_name = (data["contact_name"] or "").strip() or None
    db.commit()
    return get_business_detail(db, business_id)


def delete_business(db: Session, business_id: int) -> None:
    business = get_business_by_id(db, business_id)
    db.delete(business)
    db.commit()


def bulk_delete_businesses(db: Session, delete_in: BulkBusinessDelete) -> int:
    businesses = (
        db.query(Business)
        .filter(Business.id.in_(set(delete_in.business_ids)), compliance_service.not_blocked_filter())
        .all()
    )
    for business in businesses:
        db.delete(business)
    db.commit()
    return len(businesses)


def bulk_update_businesses(db: Session, update_in: BulkBusinessUpdate, actor_id: int | None = None) -> int:
    data = update_in.model_dump(exclude_unset=True, exclude={"business_ids"})
    if "lead_status" in data and data["lead_status"] is None:
        raise BadRequestException("lead_status can't be empty")
    if data.get("assigned_to_id") is not None:
        _require_assignable_user(db, data["assigned_to_id"])

    businesses = (
        db.query(Business)
        .filter(Business.id.in_(set(update_in.business_ids)), compliance_service.not_blocked_filter())
        .all()
    )
    names: dict[int | None, str | None] = {None: None}
    if "assigned_to_id" in data:
        wanted = {data["assigned_to_id"], *(business.assigned_to_id for business in businesses)}
        names.update({user_id: _user_name(db, user_id) for user_id in wanted if user_id is not None})

    for business in businesses:
        if "lead_status" in data:
            pipeline_service.apply_status_change(db, business, data["lead_status"].value, actor_id)
        if "assigned_to_id" in data:
            before = names.get(business.assigned_to_id)
            business.assigned_to_id = data["assigned_to_id"]
            pipeline_service.record_assignment(db, business.id, before, names.get(data["assigned_to_id"]), actor_id)
    db.commit()
    return len(businesses)


def get_assignable_users(db: Session) -> list[dict]:
    users = db.query(User.id, User.full_name).filter(User.is_active.is_(True)).order_by(User.full_name, User.id).all()
    return [{"id": user_id, "full_name": full_name} for user_id, full_name in users]
