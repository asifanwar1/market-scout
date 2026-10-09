from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from typing import NamedTuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.constants import PRICE_DIGITS
from app.core.exceptions import BadRequestException, NotFoundException
from app.core.scouting.sources.base import KIND_DISCOVERY
from app.core.scouting.sources.registry import CATALOG, is_import_key, source_label
from app.features.businesses import service as businesses_service
from app.features.businesses.models import (
    Business,
    BusinessClassification,
    ContactKind,
    ContactPoint,
    LeadStatus,
    SourceRecord,
)
from app.features.businesses.service import BusinessFilters
from app.features.geographies.models import Geography, GeographyLevel
from app.features.insights.models import BusinessSnapshot
from app.features.insights.schemas import Bucket, ConversionGroup
from app.features.pipeline.models import ActivityKind, LeadActivity, LeadOutcome
from app.features.profiles.models import Profile, ProfileSegment
from app.features.runs.models import Run, RunTask, TaskStatus

MIN_SNAPSHOTS_TO_COMPARE = 2


class Mover(NamedTuple):
    business_id: int
    previous: BusinessSnapshot
    latest: BusinessSnapshot
    change: int


NEW_SHORT_DAYS = 7
NEW_LONG_DAYS = 30
GAP_FEW_FOUND = "few_found"
GAP_NEVER_SEARCHED = "never_searched"
DAYS_PER_WEEK = 7
LAST_DAY_IN_EVERY_MONTH = 28
DAYS_PAST_MONTH_END = 4
COST_PER_LEAD_DIGITS = 3


UNCLASSIFIED = "unclassified"
UNKNOWN_CITY = "unknown"
UNKNOWN_CITY_NAME = "Unknown city"
UNCLASSIFIED_NAME = "Unclassified"
SEGMENT_NEEDS_PROFILE_MESSAGE = "Choose a profile to group by segment"
STAGE_ORDER = (
    LeadStatus.NEW.value,
    LeadStatus.CONTACTED.value,
    LeadStatus.INTERESTED.value,
    LeadStatus.MEETING.value,
    LeadStatus.QUOTED.value,
    LeadStatus.CUSTOMER.value,
)
STAGE_RANK = {status: rank for rank, status in enumerate(STAGE_ORDER)}
UNKNOWN_RANK = -1
WON_STATUS = LeadStatus.CUSTOMER.value
LOST_STATUS = LeadStatus.NOT_INTERESTED.value
WIN_RATE_DIGITS = 3
_PHONE_KINDS = (ContactKind.PHONE.value, ContactKind.WHATSAPP.value)


def _now() -> datetime:
    return datetime.now(UTC)


def _require_profile(db: Session, profile_id: int) -> Profile:
    profile = db.get(Profile, profile_id)
    if profile is None:
        raise NotFoundException("Profile not found")
    return profile


def _visible(db: Session, profile_id: int | None):
    return businesses_service.visible_businesses(db, BusinessFilters(profile_id=profile_id))


def _visible_ids(db: Session, profile_id: int | None):
    return _visible(db, profile_id).with_entities(Business.id).scalar_subquery()


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def get_overview(db: Session, profile_id: int | None) -> dict:
    def count(**filters) -> int:
        return businesses_service.visible_businesses(db, BusinessFilters(profile_id=profile_id, **filters)).count()

    now = _now()

    def new_since(days: int) -> int:
        return _visible(db, profile_id).filter(Business.first_seen_at >= now - timedelta(days=days)).count()

    statuses = (
        _visible(db, profile_id)
        .with_entities(Business.lead_status, func.count(Business.id))
        .group_by(Business.lead_status)
        .all()
    )
    return {
        "total": count(),
        "with_phone": count(has_phone=True),
        "whatsapp_likely": count(whatsapp_likely=True),
        "with_email": count(has_email=True),
        "with_website": count(has_website=True),
        "new_last_7_days": new_since(NEW_SHORT_DAYS),
        "new_last_30_days": new_since(NEW_LONG_DAYS),
        "by_status": {status: total for status, total in statuses},
    }


def get_coverage(db: Session, profile_id: int) -> dict:
    profile = _require_profile(db, profile_id)
    slug_by_id = {s.id: s.slug for s in profile.segments}

    rows = (
        _visible(db, profile_id)
        .join(
            BusinessClassification,
            (BusinessClassification.business_id == Business.id) & (BusinessClassification.profile_id == profile_id),
        )
        .with_entities(Business.geography_id, BusinessClassification.segment_id, func.count(Business.id))
        .group_by(Business.geography_id, BusinessClassification.segment_id)
        .all()
    )
    by_city: dict[int | None, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for geography_id, segment_id, total in rows:
        by_city[geography_id][slug_by_id.get(segment_id, UNCLASSIFIED)] += total

    cities = (
        db.query(Geography)
        .filter(Geography.level == GeographyLevel.CITY.value)
        .order_by(Geography.name, Geography.id)
        .all()
    )
    parents = {g.id: g.name for g in db.query(Geography).filter(Geography.level != GeographyLevel.CITY.value)}
    result = []
    for city in cities:
        counts = dict(by_city.get(city.id, {}))
        result.append({
            "geography_id": city.id,
            "city": city.name,
            "province": parents.get(city.parent_id),
            "total": sum(counts.values()),
            "counts": counts,
        })
    known = {city.id for city in cities}
    unplaced = sum(sum(counts.values()) for geography_id, counts in by_city.items() if geography_id not in known)
    return {
        "segments": [{"slug": s.slug, "name": s.name} for s in profile.segments],
        "cities": result,
        "unplaced": unplaced,
    }


def get_gaps(db: Session, profile_id: int, threshold: int) -> dict:
    coverage = get_coverage(db, profile_id)
    segment_names = {s["slug"]: s["name"] for s in coverage["segments"]}

    searched = {
        geography_id: (done, finished)
        for geography_id, done, finished in (
            db.query(RunTask.geography_id, func.count(RunTask.id), func.max(RunTask.finished_at))
            .join(Run, Run.id == RunTask.run_id)
            .filter(Run.profile_id == profile_id, RunTask.status == TaskStatus.DONE.value)
            .group_by(RunTask.geography_id)
        )
    }

    gaps = []
    for city in coverage["cities"]:
        if city["total"] >= threshold:
            continue
        done, last = searched.get(city["geography_id"], (0, None))
        gaps.append({
            **{key: city[key] for key in ("geography_id", "city", "province", "total")},
            "reason": GAP_FEW_FOUND if done else GAP_NEVER_SEARCHED,
            "searches_done": done,
            "last_searched_at": last,
            "missing_segments": [name for slug, name in segment_names.items() if not city["counts"].get(slug)],
        })
    gaps.sort(key=lambda gap: (gap["reason"] != GAP_NEVER_SEARCHED, gap["total"], gap["city"]))
    return {"threshold": threshold, "data": gaps, "count": len(gaps)}


def _bucket_start(day: date, bucket: Bucket) -> date:
    if bucket == Bucket.WEEK:
        return day - timedelta(days=day.weekday())
    if bucket == Bucket.MONTH:
        return day.replace(day=1)
    return day


def _next_bucket(start: date, bucket: Bucket) -> date:
    if bucket == Bucket.WEEK:
        return start + timedelta(days=DAYS_PER_WEEK)
    if bucket == Bucket.MONTH:
        return (start.replace(day=LAST_DAY_IN_EVERY_MONTH) + timedelta(days=DAYS_PAST_MONTH_END)).replace(day=1)
    return start + timedelta(days=1)


def get_timeline(db: Session, profile_id: int | None, days: int, bucket: Bucket) -> dict:
    today = _now().date()
    first = _bucket_start(today - timedelta(days=days), bucket)

    seen = [
        _aware(row[0]).date()
        for row in _visible(db, profile_id).with_entities(Business.first_seen_at).all()
    ]
    total = sum(1 for day in seen if _bucket_start(day, bucket) < first)
    new_per_bucket: dict[date, int] = defaultdict(int)
    for day in seen:
        start = _bucket_start(day, bucket)
        if start >= first:
            new_per_bucket[start] += 1

    points = []
    cursor, last = first, _bucket_start(today, bucket)
    while cursor <= last:
        total += new_per_bucket.get(cursor, 0)
        points.append({"period": cursor.isoformat(), "new": new_per_bucket.get(cursor, 0), "total": total})
        cursor = _next_bucket(cursor, bucket)
    return {"bucket": bucket, "data": points}


def get_sources(db: Session, profile_id: int | None) -> dict:
    visible = _visible_ids(db, profile_id)

    def pairs(query) -> set[tuple[str, int]]:
        return {(key, business_id) for key, business_id in query}

    def contact_pairs(condition) -> set[tuple[str, int]]:
        return pairs(
            db.query(ContactPoint.source_key, ContactPoint.business_id)
            .filter(ContactPoint.business_id.in_(visible), condition)
        )

    reported = pairs(
        db.query(SourceRecord.source_key, SourceRecord.business_id).filter(SourceRecord.business_id.in_(visible))
    )
    contributed = contact_pairs(ContactPoint.id.isnot(None))
    with_phone = contact_pairs(ContactPoint.kind.in_(_PHONE_KINDS))
    with_email = contact_pairs(ContactPoint.kind == ContactKind.EMAIL.value)
    with_whatsapp = contact_pairs(ContactPoint.whatsapp_likely.is_(True) | (ContactPoint.kind == ContactKind.WHATSAPP.value))
    with_website = {row[0] for row in db.query(Business.id).filter(Business.id.in_(visible), Business.website.isnot(None))}

    requests = dict(
        db.query(RunTask.source_key, func.coalesce(func.sum(RunTask.requests_made), 0)).group_by(RunTask.source_key).all()
    )
    reporters: dict[int, set[str]] = defaultdict(set)
    for key, business_id in reported:
        reporters[business_id].add(key)

    data = []
    for info in CATALOG:
        is_discovery = info.kind == KIND_DISCOVERY
        found = {b for k, b in (reported if is_discovery else contributed) if k == info.key}
        used = int(requests.get(info.key, 0))
        if not found and not used:
            continue
        cost = round(used * info.cost_per_request(settings), PRICE_DIGITS) if info.is_paid else None
        data.append({
            "key": info.key,
            "name": info.name,
            "kind": info.kind,
            "is_paid": info.is_paid,
            "found": len(found),
            "exclusive": sum(1 for b in found if reporters[b] == {info.key}) if is_discovery else None,
            "with_phone": sum(1 for k, _ in with_phone if k == info.key),
            "with_whatsapp": sum(1 for k, _ in with_whatsapp if k == info.key),
            "with_email": sum(1 for k, _ in with_email if k == info.key),
            "with_website": len(found & with_website),
            "requests": used,
            "estimated_cost_usd": cost,
            "cost_per_lead_usd": round(cost / len(found), COST_PER_LEAD_DIGITS) if cost is not None and found else None,
        })

    for key in sorted({k for k, _ in reported if is_import_key(k)}):
        found = {b for k, b in reported if k == key}
        data.append({
            "key": key,
            "name": source_label(key),
            "kind": "import",
            "is_paid": False,
            "found": len(found),
            "exclusive": sum(1 for b in found if reporters[b] == {key}),
            "with_phone": sum(1 for k, _ in with_phone if k == key),
            "with_whatsapp": sum(1 for k, _ in with_whatsapp if k == key),
            "with_email": sum(1 for k, _ in with_email if k == key),
            "with_website": len(found & with_website),
            "requests": 0,
            "estimated_cost_usd": None,
            "cost_per_lead_usd": None,
        })
    return {"data": data, "count": len(data)}


def get_movers(db: Session, profile_id: int | None, days: int, limit: int) -> dict:
    since = _now() - timedelta(days=days)
    visible = _visible_ids(db, profile_id)

    recent = (
        db.query(BusinessSnapshot.business_id)
        .filter(BusinessSnapshot.business_id.in_(visible), BusinessSnapshot.seen_at >= since)
        .distinct()
        .scalar_subquery()
    )
    snapshots = (
        db.query(BusinessSnapshot)
        .filter(BusinessSnapshot.business_id.in_(recent), BusinessSnapshot.review_count.isnot(None))
        .order_by(BusinessSnapshot.business_id, BusinessSnapshot.seen_at, BusinessSnapshot.id)
        .all()
    )
    grouped: dict[int, list[BusinessSnapshot]] = defaultdict(list)
    for snapshot in snapshots:
        grouped[snapshot.business_id].append(snapshot)

    movers = []
    for business_id, history in grouped.items():
        previous, latest = (history[-2], history[-1]) if len(history) >= MIN_SNAPSHOTS_TO_COMPARE else (None, history[-1])
        if previous is None or _aware(latest.seen_at) < since:
            continue
        change = latest.review_count - previous.review_count
        if change > 0:
            movers.append(Mover(business_id, previous, latest, change))
    movers.sort(key=lambda mover: (-mover.change, mover.business_id))
    movers = movers[:limit]

    places = {}
    if movers:
        for business_id, name, city in (
            db.query(Business.id, Business.name, Geography.name)
            .outerjoin(Geography, Geography.id == Business.geography_id)
            .filter(Business.id.in_([mover.business_id for mover in movers]))
        ):
            places[business_id] = (name, city)
    data = [
        {
            "business_id": business_id,
            "name": places[business_id][0],
            "city": places[business_id][1],
            "rating": latest.rating,
            "review_count": latest.review_count,
            "review_change": change,
            "previous_seen_at": previous.seen_at,
            "latest_seen_at": latest.seen_at,
        }
        for business_id, previous, latest, change in movers
    ]
    return {"days": days, "data": data, "count": len(data)}


class _PipelineLead(NamedTuple):
    id: int
    status: str
    geography_id: int | None
    rank: int
    value: float
    loss_reason: str | None


def _pipeline_leads(db: Session, profile_id: int | None) -> list[_PipelineLead]:
    visible = _visible_ids(db, profile_id)
    rows = db.query(Business.id, Business.lead_status, Business.geography_id).filter(Business.id.in_(visible)).all()

    furthest: dict[int, int] = defaultdict(lambda: UNKNOWN_RANK)
    moves = (
        db.query(LeadActivity.business_id, LeadActivity.to_value)
        .filter(LeadActivity.kind == ActivityKind.STATUS_CHANGE.value, LeadActivity.business_id.in_(visible))
        .distinct()
    )
    for business_id, to_status in moves:
        furthest[business_id] = max(furthest[business_id], STAGE_RANK.get(to_status, UNKNOWN_RANK))

    outcomes = {
        business_id: (value, reason)
        for business_id, value, reason in db.query(
            LeadOutcome.business_id, LeadOutcome.value, LeadOutcome.loss_reason
        ).filter(LeadOutcome.business_id.in_(visible))
    }

    leads = []
    for business_id, status, geography_id in rows:
        value, reason = outcomes.get(business_id, (None, None))
        rank = max(furthest[business_id], STAGE_RANK.get(status, UNKNOWN_RANK))
        leads.append(_PipelineLead(business_id, status, geography_id, rank, value or 0.0, reason))
    return leads


def _win_rate(won: int, lost: int) -> float | None:
    return round(won / (won + lost), WIN_RATE_DIGITS) if won + lost else None


def get_pipeline(db: Session, profile_id: int | None) -> dict:
    leads = _pipeline_leads(db, profile_id)
    won = [lead for lead in leads if lead.status == WON_STATUS]
    lost = [lead for lead in leads if lead.status == LOST_STATUS]
    revenue = sum(lead.value for lead in won)

    stages = [
        {
            "status": status,
            "current": sum(1 for lead in leads if lead.status == status),
            "reached": len(leads) if rank == 0 else sum(1 for lead in leads if lead.rank >= rank),
        }
        for status, rank in STAGE_RANK.items()
    ]
    reasons: dict[str | None, int] = defaultdict(int)
    for lead in lost:
        reasons[lead.loss_reason] += 1

    return {
        "currency": settings.DEAL_CURRENCY,
        "total": len(leads),
        "open": len(leads) - len(won) - len(lost),
        "won": len(won),
        "lost": len(lost),
        "win_rate": _win_rate(len(won), len(lost)),
        "revenue": round(revenue, PRICE_DIGITS),
        "average_deal": round(revenue / len(won), PRICE_DIGITS) if won else None,
        "stages": stages,
        "loss_reasons": [
            {"reason": reason, "count": count}
            for reason, count in sorted(reasons.items(), key=lambda item: (-item[1], str(item[0])))
        ],
    }


Members = dict[str, tuple[str, set[int]]]


def _members_by_source(db: Session, visible) -> Members:
    members: dict[str, set[int]] = defaultdict(set)
    for key, business_id in db.query(SourceRecord.source_key, SourceRecord.business_id).filter(
        SourceRecord.business_id.in_(visible)
    ):
        members[key].add(business_id)
    return {key: (source_label(key), ids) for key, ids in members.items()}


def _members_by_segment(db: Session, visible, profile_id: int, leads: list[_PipelineLead]) -> Members:
    names = {
        segment_id: (slug, name)
        for segment_id, slug, name in db.query(ProfileSegment.id, ProfileSegment.slug, ProfileSegment.name)
    }
    classified: set[int] = set()
    members: Members = {}
    for business_id, segment_id in db.query(BusinessClassification.business_id, BusinessClassification.segment_id).filter(
        BusinessClassification.profile_id == profile_id, BusinessClassification.business_id.in_(visible)
    ):
        slug, name = names.get(segment_id, (UNCLASSIFIED, UNCLASSIFIED_NAME))
        classified.add(business_id)
        members.setdefault(slug, (name, set()))[1].add(business_id)
    for lead in leads:
        if lead.id not in classified:
            members.setdefault(UNCLASSIFIED, (UNCLASSIFIED_NAME, set()))[1].add(lead.id)
    return members


def _members_by_city(db: Session, leads: list[_PipelineLead]) -> Members:
    names = {geography_id: name for geography_id, name in db.query(Geography.id, Geography.name)}
    members: Members = {}
    for lead in leads:
        known = lead.geography_id in names
        key = str(lead.geography_id) if known else UNKNOWN_CITY
        members.setdefault(key, (names[lead.geography_id] if known else UNKNOWN_CITY_NAME, set()))[1].add(lead.id)
    return members


def get_conversion(db: Session, profile_id: int | None, group_by: ConversionGroup) -> dict:
    if group_by == ConversionGroup.SEGMENT and profile_id is None:
        raise BadRequestException(SEGMENT_NEEDS_PROFILE_MESSAGE)
    leads = _pipeline_leads(db, profile_id)
    by_id = {lead.id: lead for lead in leads}
    visible = _visible_ids(db, profile_id)

    if group_by == ConversionGroup.SOURCE:
        groups = _members_by_source(db, visible)
    elif group_by == ConversionGroup.SEGMENT:
        groups = _members_by_segment(db, visible, profile_id, leads)
    else:
        groups = _members_by_city(db, leads)

    def reached(members: list[_PipelineLead], status: str) -> int:
        return sum(1 for lead in members if lead.rank >= STAGE_RANK[status])

    rows = []
    for key, (name, ids) in groups.items():
        members = [by_id[business_id] for business_id in ids if business_id in by_id]
        won = [lead for lead in members if lead.status == WON_STATUS]
        lost = [lead for lead in members if lead.status == LOST_STATUS]
        rows.append({
            "key": key,
            "name": name,
            "leads": len(members),
            "contacted": reached(members, LeadStatus.CONTACTED.value),
            "interested": reached(members, LeadStatus.INTERESTED.value),
            "meeting": reached(members, LeadStatus.MEETING.value),
            "quoted": reached(members, LeadStatus.QUOTED.value),
            "won": len(won),
            "lost": len(lost),
            "win_rate": _win_rate(len(won), len(lost)),
            "revenue": round(sum(lead.value for lead in won), PRICE_DIGITS),
        })
    rows.sort(key=lambda row: (-row["leads"], row["name"]))
    return {"group_by": group_by, "data": rows, "count": len(rows)}
