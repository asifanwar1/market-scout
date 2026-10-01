"""Market intelligence computed from what runs have already stored: coverage, gaps, growth,
source quality and movement. Everything starts from ``visible_businesses`` so anyone on the
do-not-contact list is left out of every number, exactly as in the leads list."""
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.core.exceptions import NotFoundException
from app.core.scouting.sources.registry import CATALOG, KIND_DISCOVERY
from app.features.businesses import service as businesses_service
from app.features.businesses.models import (
    Business,
    BusinessClassification,
    ContactKind,
    ContactPoint,
    SourceRecord,
)
from app.features.businesses.service import BusinessFilters
from app.features.geographies.models import Geography, GeographyLevel
from app.features.insights.models import BusinessSnapshot
from app.features.insights.schemas import Bucket
from app.features.profiles.models import Profile
from app.features.runs.models import Run, RunTask, TaskStatus

UNCLASSIFIED = "unclassified"
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
    """The ids the numbers are about, as a subquery to filter other tables by."""
    return _visible(db, profile_id).with_entities(Business.id).scalar_subquery()


def _aware(value: datetime) -> datetime:
    # SQLite hands back naive datetimes; they are stored as UTC.
    return value if value.tzinfo else value.replace(tzinfo=UTC)


# ---- overview ---------------------------------------------------------------------------------

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
        "new_last_7_days": new_since(7),
        "new_last_30_days": new_since(30),
        "by_status": {status: total for status, total in statuses},
    }


# ---- coverage and gaps -----------------------------------------------------------------------------

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

    # Only searches that finished for this profile count as "we looked here".
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
            "reason": "few_found" if done else "never_searched",
            "searches_done": done,
            "last_searched_at": last,
            "missing_segments": [name for slug, name in segment_names.items() if not city["counts"].get(slug)],
        })
    # Places never looked at first, then the emptiest.
    gaps.sort(key=lambda gap: (gap["reason"] != "never_searched", gap["total"], gap["city"]))
    return {"threshold": threshold, "data": gaps, "count": len(gaps)}


# ---- growth over time --------------------------------------------------------------------------------

def _bucket_start(day: date, bucket: Bucket) -> date:
    if bucket == Bucket.WEEK:
        return day - timedelta(days=day.weekday())
    if bucket == Bucket.MONTH:
        return day.replace(day=1)
    return day


def _next_bucket(start: date, bucket: Bucket) -> date:
    if bucket == Bucket.WEEK:
        return start + timedelta(days=7)
    if bucket == Bucket.MONTH:
        return (start.replace(day=28) + timedelta(days=4)).replace(day=1)
    return start + timedelta(days=1)


def get_timeline(db: Session, profile_id: int | None, days: int, bucket: Bucket) -> dict:
    today = _now().date()
    first = _bucket_start(today - timedelta(days=days), bucket)

    seen = [
        _aware(row[0]).date()
        for row in _visible(db, profile_id).with_entities(Business.first_seen_at).all()
    ]
    total = sum(1 for day in seen if _bucket_start(day, bucket) < first)  # already known before the chart starts
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


# ---- source quality ----------------------------------------------------------------------------------------

def get_sources(db: Session, profile_id: int | None) -> dict:
    """How useful each source has been. Read into memory as (source, business) pairs: simple and
    plenty fast for tens of thousands of leads; revisit with SQL aggregates if it grows far beyond."""
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
        # A discovery source "found" what it reported; website reading "found" what it added contacts to.
        found = {b for k, b in (reported if is_discovery else contributed) if k == info.key}
        used = int(requests.get(info.key, 0))
        if not found and not used:
            continue
        cost = round(used * settings.PLACES_COST_PER_REQUEST_USD, 2) if info.is_paid else None
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
            "cost_per_lead_usd": round(cost / len(found), 3) if cost is not None and found else None,
        })
    return {"data": data, "count": len(data)}


# ---- movement ---------------------------------------------------------------------------------------------------------

def get_movers(db: Session, profile_id: int | None, days: int, limit: int) -> dict:
    """Businesses whose review count grew most since the search before their latest one, among
    those seen in the last ``days`` days: a rough sign of who is getting busier. Comparing with the
    previous search (rather than a fixed window) means it works however far apart the runs are."""
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
        previous, latest = (history[-2], history[-1]) if len(history) >= 2 else (None, history[-1])
        if previous is None or _aware(latest.seen_at) < since:
            continue  # seen once, or not seen recently
        change = latest.review_count - previous.review_count
        if change > 0:
            movers.append((business_id, previous, latest, change))
    movers.sort(key=lambda mover: (-mover[3], mover[0]))
    movers = movers[:limit]

    places = {}
    if movers:
        for business_id, name, city in (
            db.query(Business.id, Business.name, Geography.name)
            .outerjoin(Geography, Geography.id == Business.geography_id)
            .filter(Business.id.in_([mover[0] for mover in movers]))
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
