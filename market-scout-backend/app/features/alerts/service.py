import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.constants import FIRST_PAGE
from app.features.alerts.models import Alert, AlertKind, AlertRead
from app.features.alerts.schemas import AlertSettings, AlertSettingsUpdate, MarkReadRequest
from app.features.businesses.models import (
    Business,
    BusinessClassification,
    ContactKind,
    ContactPoint,
    SourceRecord,
)
from app.features.compliance import service as compliance_service
from app.features.geographies.models import Geography
from app.features.insights.models import BusinessSnapshot
from app.features.runs.models import Run, RunStatus
from app.features.sheets.models import AppSetting
from app.features.webhooks import events as webhook_events
from app.features.webhooks import service as webhooks_service
from app.features.webhooks.models import WebhookEvent

SETTINGS_KEY = "alerts"
DEFAULT_LIMIT = 25
RETENTION_DAYS = 90
PERCENT = 100
REACHABLE_KINDS = (ContactKind.PHONE.value, ContactKind.EMAIL.value, ContactKind.WHATSAPP.value)
REACHABLE_KEY = "reachable"
NEW_LEAD_KEY = "new"
NEW_LEAD_MESSAGE = "New lead{where}: {name} (score {score})"
GROWING_MESSAGE = "{name} gained {change} reviews ({previous} to {now}){where}"
REACHABLE_MESSAGE = "{name} can now be contacted: it gained {gained}{where}"
WHERE_TEMPLATE = " in {city}"
NOT_STARTED_STATUSES = (RunStatus.QUEUED.value,)


logger = logging.getLogger(__name__)


@dataclass
class Candidate:
    kind: AlertKind
    business_id: int
    priority: int
    dedupe_key: str
    message: str
    detail: dict = field(default_factory=dict)


def _now() -> datetime:
    return datetime.now(UTC)


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def get_settings(db: Session) -> dict:
    row = db.get(AppSetting, SETTINGS_KEY)
    return AlertSettings(**(row.value if row is not None else {})).model_dump()


def update_settings(db: Session, update_in: AlertSettingsUpdate) -> dict:
    merged = {**get_settings(db), **update_in.model_dump(exclude_none=True)}
    value = AlertSettings(**merged).model_dump()
    row = db.get(AppSetting, SETTINGS_KEY)
    if row is None:
        db.add(AppSetting(key=SETTINGS_KEY, value=value))
    else:
        row.value = value
    db.commit()
    return value


def _where(city: str | None) -> str:
    return WHERE_TEMPLATE.format(city=city) if city else ""


def _places(db: Session, business_ids: list[int]) -> dict[int, tuple[str, str | None, int | None]]:
    if not business_ids:
        return {}
    rows = (
        db.query(Business.id, Business.name, Geography.name, Business.assigned_to_id)
        .outerjoin(Geography, Geography.id == Business.geography_id)
        .filter(Business.id.in_(business_ids), compliance_service.not_blocked_filter())
        .all()
    )
    return {business_id: (name, city, assignee) for business_id, name, city, assignee in rows}


def _scores(db: Session, profile_id: int, business_ids: list[int]) -> dict[int, int]:
    if not business_ids:
        return {}
    rows = db.query(BusinessClassification.business_id, BusinessClassification.score).filter(
        BusinessClassification.profile_id == profile_id, BusinessClassification.business_id.in_(business_ids)
    )
    return dict(rows.all())


def _touched_by(db: Session, run: Run) -> list[int]:
    return [row[0] for row in db.query(SourceRecord.business_id).filter(SourceRecord.run_id == run.id).distinct().all()]


def _new_leads(db: Session, run: Run, config: dict, touched: list[int]) -> list[Candidate]:
    created = [
        row[0]
        for row in db.query(Business.id).filter(Business.id.in_(touched), Business.first_seen_at >= run.started_at).all()
    ]
    scores = _scores(db, run.profile_id, created)
    places = _places(db, [business_id for business_id, score in scores.items() if score >= config["new_lead_min_score"]])
    return [
        Candidate(
            AlertKind.NEW_LEAD,
            business_id,
            scores[business_id],
            NEW_LEAD_KEY,
            NEW_LEAD_MESSAGE.format(where=_where(city), name=name, score=scores[business_id]),
            {"score": scores[business_id]},
        )
        for business_id, (name, city, _) in places.items()
    ]


def _growing(db: Session, run: Run, config: dict) -> list[Candidate]:
    latest_rows = (
        db.query(BusinessSnapshot)
        .filter(BusinessSnapshot.run_id == run.id, BusinessSnapshot.review_count.isnot(None))
        .all()
    )
    latest = {snapshot.business_id: snapshot for snapshot in latest_rows}
    if not latest:
        return []

    history: dict[int, list[BusinessSnapshot]] = defaultdict(list)
    older = (
        db.query(BusinessSnapshot)
        .filter(BusinessSnapshot.business_id.in_(list(latest)), BusinessSnapshot.review_count.isnot(None))
        .order_by(BusinessSnapshot.business_id, BusinessSnapshot.seen_at, BusinessSnapshot.id)
        .all()
    )
    for snapshot in older:
        if snapshot.run_id != run.id:
            history[snapshot.business_id].append(snapshot)

    grown: dict[int, tuple[int, int]] = {}
    for business_id, snapshot in latest.items():
        before = [item for item in history.get(business_id, []) if _aware(item.seen_at) < _aware(snapshot.seen_at)]
        if not before:
            continue
        previous = before[-1].review_count
        change = snapshot.review_count - previous
        percent = PERCENT * change / previous if previous else float("inf")
        if change >= config["growing_min_new_reviews"] and percent >= config["growing_min_percent"]:
            grown[business_id] = (previous, snapshot.review_count)

    scores = _scores(db, run.profile_id, list(grown))
    places = _places(db, [business_id for business_id in grown if business_id in scores])
    return [
        Candidate(
            AlertKind.GROWING,
            business_id,
            grown[business_id][1] - grown[business_id][0],
            str(grown[business_id][1]),
            GROWING_MESSAGE.format(
                name=name, change=grown[business_id][1] - grown[business_id][0], previous=grown[business_id][0],
                now=grown[business_id][1], where=_where(city),
            ),
            {"previous": grown[business_id][0], "now": grown[business_id][1]},
        )
        for business_id, (name, city, _) in places.items()
    ]


def _reachable(db: Session, run: Run, touched: list[int]) -> list[Candidate]:
    existing = [
        row[0]
        for row in db.query(Business.id).filter(Business.id.in_(touched), Business.first_seen_at < run.started_at).all()
    ]
    if not existing:
        return []
    contacts = (
        db.query(ContactPoint.business_id, ContactPoint.kind, ContactPoint.created_at)
        .filter(ContactPoint.business_id.in_(existing), ContactPoint.kind.in_(REACHABLE_KINDS))
        .all()
    )
    started = _aware(run.started_at)
    had_before = {business_id for business_id, _, created in contacts if _aware(created) < started}
    gained: dict[int, set[str]] = defaultdict(set)
    for business_id, kind, created in contacts:
        if _aware(created) >= started and business_id not in had_before:
            gained[business_id].add(kind)

    scores = _scores(db, run.profile_id, list(gained))
    places = _places(db, [business_id for business_id in gained if business_id in scores])
    return [
        Candidate(
            AlertKind.REACHABLE,
            business_id,
            scores[business_id],
            REACHABLE_KEY,
            REACHABLE_MESSAGE.format(name=name, gained=" and ".join(sorted(gained[business_id])), where=_where(city)),
            {"gained": sorted(gained[business_id])},
        )
        for business_id, (name, city, _) in places.items()
    ]


def _store(db: Session, run: Run, candidates: list[Candidate], limit: int) -> int:
    chosen = sorted(candidates, key=lambda item: (-item.priority, item.business_id))[:limit]
    assignees: dict[int, int | None] = {}
    if chosen:
        rows = db.query(Business.id, Business.assigned_to_id).filter(Business.id.in_([item.business_id for item in chosen]))
        assignees = dict(rows.all())
    created = 0
    for item in chosen:
        exists = (
            db.query(Alert.id)
            .filter(Alert.kind == item.kind.value, Alert.business_id == item.business_id, Alert.dedupe_key == item.dedupe_key)
            .first()
        )
        if exists is not None:
            continue
        db.add(
            Alert(
                kind=item.kind.value,
                business_id=item.business_id,
                profile_id=run.profile_id,
                run_id=run.id,
                user_id=assignees.get(item.business_id),
                dedupe_key=item.dedupe_key,
                message=item.message,
                detail=item.detail,
            )
        )
        business = db.get(Business, item.business_id)
        if business is not None:
            webhooks_service.emit(
                db,
                WebhookEvent.ALERT_RAISED,
                lambda item=item, business=business: {
                    "alert": {"kind": item.kind.value, "message": item.message, "detail": item.detail},
                    "lead": webhook_events.lead_snapshot(db, business),
                },
            )
        created += 1
    db.commit()
    return created


def evaluate_run(db: Session, run_id: int) -> int:
    run = db.get(Run, run_id)
    if run is None or run.profile_id is None or run.started_at is None or run.status in NOT_STARTED_STATUSES:
        return 0
    config = get_settings(db)
    touched = _touched_by(db, run)

    candidates: list[Candidate] = []
    if config["new_lead_enabled"] and touched:
        candidates += _new_leads(db, run, config, touched)
    if config["growing_enabled"]:
        candidates += _growing(db, run, config)
    if config["reachable_enabled"] and touched:
        candidates += _reachable(db, run, touched)

    created = _store(db, run, candidates, config["max_per_run"])
    prune(db)
    return created


def raise_alerts(db: Session, run_id: int) -> None:
    try:
        evaluate_run(db, run_id)
    except Exception:
        logger.exception("Could not work out alerts for run %s", run_id)
        db.rollback()


def prune(db: Session) -> int:
    cutoff = _now() - timedelta(days=RETENTION_DAYS)
    removed = db.query(Alert).filter(Alert.created_at < cutoff).delete(synchronize_session=False)
    db.commit()
    return removed


def _read_ids(user_id: int):
    return select(AlertRead.alert_id).where(AlertRead.user_id == user_id)


def _visible(db: Session, user_id: int):
    return (
        db.query(Alert)
        .join(Business, Business.id == Alert.business_id)
        .filter(or_(Alert.user_id.is_(None), Alert.user_id == user_id), compliance_service.not_blocked_filter())
    )


def count_unread(db: Session, user_id: int) -> int:
    return _visible(db, user_id).filter(Alert.id.notin_(_read_ids(user_id))).count()


def get_alerts(
    db: Session, user_id: int, page: int = FIRST_PAGE, limit: int = DEFAULT_LIMIT, unread_only: bool = False, kind: AlertKind | None = None
) -> dict:
    query = _visible(db, user_id)
    unread = query.filter(Alert.id.notin_(_read_ids(user_id))).count()
    if kind is not None:
        query = query.filter(Alert.kind == kind.value)
    if unread_only:
        query = query.filter(Alert.id.notin_(_read_ids(user_id)))
    total = query.count()
    alerts = query.order_by(Alert.id.desc()).offset((page - 1) * limit).limit(limit).all()

    read_ids: set[int] = set()
    places: dict[int, tuple[str, str | None]] = {}
    if alerts:
        shown = [alert.id for alert in alerts]
        read_ids = {row[0] for row in db.query(AlertRead.alert_id).filter(AlertRead.user_id == user_id, AlertRead.alert_id.in_(shown))}
        rows = (
            db.query(Business.id, Business.name, Geography.name)
            .outerjoin(Geography, Geography.id == Business.geography_id)
            .filter(Business.id.in_([alert.business_id for alert in alerts]))
        )
        places = {business_id: (name, city) for business_id, name, city in rows}
    data = [
        {
            "id": alert.id,
            "kind": alert.kind,
            "message": alert.message,
            "detail": alert.detail or {},
            "business_id": alert.business_id,
            "business_name": places[alert.business_id][0],
            "city": places[alert.business_id][1],
            "run_id": alert.run_id,
            "is_read": alert.id in read_ids,
            "created_at": alert.created_at,
        }
        for alert in alerts
    ]
    return {"data": data, "count": total, "unread": unread}


def mark_read(db: Session, user_id: int, body: MarkReadRequest) -> int:
    query = _visible(db, user_id).filter(Alert.id.notin_(_read_ids(user_id)))
    if not body.all:
        query = query.filter(Alert.id.in_(body.ids or []))
    ids = [alert.id for alert in query.all()]
    db.add_all(AlertRead(alert_id=alert_id, user_id=user_id) for alert_id in ids)
    db.commit()
    return len(ids)
