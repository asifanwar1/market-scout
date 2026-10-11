import logging
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.constants import FIRST_PAGE
from app.core.database import WorkerSessionLocal
from app.core.exceptions import BadRequestException, ConflictException, NotFoundException
from app.core.scouting.sources.registry import ENRICHMENT_KEY, get_source_info
from app.features.geographies.models import Geography
from app.features.profiles.models import Profile
from app.features.runs import service as runs_service
from app.features.runs.models import ACTIVE_RUN_STATUSES, Run, RunStatus
from app.features.runs.schemas import RunCreate
from app.features.schedules.models import FREQUENCY_DAYS, Schedule
from app.features.schedules.schemas import ScheduleCreate, ScheduleUpdate

DEFAULT_LIMIT = 20
MAX_CONSECUTIVE_FAILURES = 3
UNEXPECTED_ERROR_MESSAGE = "Unexpected error (see the server log)"
PAID_NEEDS_CAP_MESSAGE = "A repeating search that uses a paid source needs a spending cap on billable requests"
PREVIOUS_RUN_FAILED_MESSAGE = "The previous run failed: {reason}"
PAUSED_SUFFIX = " Paused after {count} failures in a row; fix the cause and switch it back on."
STILL_RUNNING_MESSAGE = "The previous run is still going, so this one was skipped"
ALREADY_RUNNING_MESSAGE = "A run from this schedule is still going"
NO_REASON_MESSAGE = "no reason was recorded"
NOT_FOUND_MESSAGE = "Schedule not found"


logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(UTC)


def _interval(frequency: str) -> timedelta:
    return timedelta(days=FREQUENCY_DAYS[frequency])


def _run_create(schedule: Schedule) -> RunCreate:
    return RunCreate(
        profile_id=schedule.profile_id,
        geography_ids=list(schedule.geography_ids),
        source_keys=list(schedule.source_keys),
        segment_slugs=list(schedule.segment_slugs) if schedule.segment_slugs is not None else None,
        enrich_websites=schedule.enrich_websites,
        refresh=True,
        max_paid_requests=schedule.max_paid_requests,
    )


def _validate(db: Session, fields: dict) -> Profile:
    run_in = RunCreate(
        profile_id=fields["profile_id"],
        geography_ids=fields["geography_ids"],
        source_keys=fields["source_keys"],
        segment_slugs=fields["segment_slugs"],
        enrich_websites=fields["enrich_websites"],
        refresh=True,
        max_paid_requests=fields["max_paid_requests"],
    )
    profile, _, _ = runs_service.check_plan(db, run_in)
    uses_paid = any(get_source_info(key).is_paid for key in run_in.source_keys)
    if uses_paid and run_in.max_paid_requests is None:
        raise BadRequestException(PAID_NEEDS_CAP_MESSAGE)
    return profile


def _latest_runs(db: Session, schedule_ids: list[int]) -> dict[int, Run]:
    if not schedule_ids:
        return {}
    newest = [
        row[0]
        for row in db.query(func.max(Run.id)).filter(Run.schedule_id.in_(schedule_ids)).group_by(Run.schedule_id).all()
    ]
    return {run.schedule_id: run for run in db.query(Run).filter(Run.id.in_(newest)).all()}


def _new_leads(run: Run) -> int:
    return sum(values.get("new", 0) for key, values in (run.stats or {}).items() if key != ENRICHMENT_KEY)


def _view(db: Session, schedule: Schedule, latest: Run | None) -> dict:
    names = dict(db.query(Geography.id, Geography.name).filter(Geography.id.in_(schedule.geography_ids)).all())
    last_run = None
    if latest is not None:
        last_run = {
            "id": latest.id,
            "status": latest.status,
            "new_leads": _new_leads(latest),
            "started_at": latest.started_at,
            "finished_at": latest.finished_at,
        }
    return {
        "id": schedule.id,
        "name": schedule.name,
        "profile_id": schedule.profile_id,
        "profile_name": schedule.profile_name,
        "is_active": schedule.is_active,
        "frequency": schedule.frequency,
        "geography_ids": list(schedule.geography_ids),
        "cities": [names[geography_id] for geography_id in schedule.geography_ids if geography_id in names],
        "source_keys": list(schedule.source_keys),
        "segment_slugs": list(schedule.segment_slugs) if schedule.segment_slugs is not None else None,
        "enrich_websites": schedule.enrich_websites,
        "max_paid_requests": schedule.max_paid_requests,
        "next_run_at": schedule.next_run_at,
        "last_run_at": schedule.last_run_at,
        "last_run": last_run,
        "consecutive_failures": schedule.consecutive_failures,
        "last_error": schedule.last_error,
        "created_at": schedule.created_at,
    }


def get_schedule_by_id(db: Session, schedule_id: int) -> Schedule:
    schedule = db.get(Schedule, schedule_id)
    if schedule is None:
        raise NotFoundException(NOT_FOUND_MESSAGE)
    return schedule


def get_schedule_view(db: Session, schedule_id: int) -> dict:
    schedule = get_schedule_by_id(db, schedule_id)
    return _view(db, schedule, _latest_runs(db, [schedule.id]).get(schedule.id))


def get_schedules(db: Session, page: int = FIRST_PAGE, limit: int = DEFAULT_LIMIT) -> dict:
    query = db.query(Schedule)
    total = query.count()
    schedules = query.order_by(Schedule.id.desc()).offset((page - 1) * limit).limit(limit).all()
    latest = _latest_runs(db, [schedule.id for schedule in schedules])
    return {"data": [_view(db, schedule, latest.get(schedule.id)) for schedule in schedules], "count": total}


def create_schedule(db: Session, schedule_in: ScheduleCreate, created_by_id: int) -> dict:
    fields = schedule_in.model_dump(exclude={"name", "frequency"})
    profile = _validate(db, fields)
    schedule = Schedule(
        name=schedule_in.name,
        frequency=schedule_in.frequency.value,
        profile_name=profile.name,
        created_by_id=created_by_id,
        is_active=True,
        next_run_at=_now() + _interval(schedule_in.frequency.value),
        consecutive_failures=0,
        **fields,
    )
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    return _view(db, schedule, None)


def update_schedule(db: Session, schedule_id: int, update_in: ScheduleUpdate) -> dict:
    schedule = get_schedule_by_id(db, schedule_id)
    changes = update_in.model_dump(exclude_unset=True)
    for required in ("name", "frequency", "is_active", "profile_id", "geography_ids", "source_keys", "enrich_websites"):
        if required in changes and changes[required] is None:
            raise BadRequestException(f"{required} cannot be empty")

    definition = {
        "profile_id": schedule.profile_id,
        "geography_ids": list(schedule.geography_ids),
        "source_keys": list(schedule.source_keys),
        "segment_slugs": schedule.segment_slugs,
        "enrich_websites": schedule.enrich_websites,
        "max_paid_requests": schedule.max_paid_requests,
    }
    definition.update({key: changes[key] for key in definition if key in changes})
    if any(key in changes for key in definition):
        profile = _validate(db, definition)
        schedule.profile_name = profile.name
        for key, value in definition.items():
            setattr(schedule, key, value)

    if "name" in changes:
        schedule.name = changes["name"]
    if "frequency" in changes:
        frequency = changes["frequency"].value
        if frequency != schedule.frequency:
            schedule.frequency = frequency
            schedule.next_run_at = _now() + _interval(frequency)
    if "is_active" in changes and changes["is_active"] != schedule.is_active:
        schedule.is_active = changes["is_active"]
        if schedule.is_active:
            schedule.next_run_at = _now() + _interval(schedule.frequency)
            schedule.consecutive_failures = 0
            schedule.last_error = None

    db.commit()
    return get_schedule_view(db, schedule_id)


def delete_schedule(db: Session, schedule_id: int) -> None:
    schedule = get_schedule_by_id(db, schedule_id)
    db.delete(schedule)
    db.commit()


def _active_run(db: Session, schedule_id: int) -> Run | None:
    return (
        db.query(Run).filter(Run.schedule_id == schedule_id, Run.status.in_(ACTIVE_RUN_STATUSES)).order_by(Run.id.desc()).first()
    )


def run_now(db: Session, schedule_id: int) -> Run:
    schedule = get_schedule_by_id(db, schedule_id)
    if _active_run(db, schedule.id) is not None:
        raise ConflictException(ALREADY_RUNNING_MESSAGE)
    run = runs_service.create_run(db, _run_create(schedule), schedule.created_by_id, schedule.id, schedule.name)
    schedule.last_run_at = _now()
    db.commit()
    db.refresh(run)
    return run


def _record_failure(db: Session, schedule_id: int, reason: str) -> None:
    schedule = db.get(Schedule, schedule_id, populate_existing=True)
    if schedule is None:
        return
    schedule.consecutive_failures += 1
    schedule.last_error = reason
    if schedule.consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
        schedule.is_active = False
        schedule.last_error = reason + PAUSED_SUFFIX.format(count=schedule.consecutive_failures)
    db.commit()


def _start(db: Session, schedule_id: int, now: datetime) -> bool:
    schedule = db.get(Schedule, schedule_id, populate_existing=True)
    if schedule is None or not schedule.is_active:
        return False

    previous = _latest_runs(db, [schedule.id]).get(schedule.id)
    if previous is not None and previous.status in ACTIVE_RUN_STATUSES:
        schedule.last_error = STILL_RUNNING_MESSAGE
        db.commit()
        return False
    if previous is not None and previous.status == RunStatus.FAILED.value:
        _record_failure(db, schedule.id, PREVIOUS_RUN_FAILED_MESSAGE.format(reason=previous.error or NO_REASON_MESSAGE))
        schedule = db.get(Schedule, schedule_id, populate_existing=True)
        if not schedule.is_active:
            return False

    try:
        runs_service.create_run(db, _run_create(schedule), schedule.created_by_id, schedule.id, schedule.name)
    except HTTPException as exc:
        db.rollback()
        _record_failure(db, schedule_id, str(exc.detail))
        return False
    except Exception:
        logger.exception("Schedule %s could not start its run", schedule_id)
        db.rollback()
        _record_failure(db, schedule_id, UNEXPECTED_ERROR_MESSAGE)
        return False

    schedule = db.get(Schedule, schedule_id, populate_existing=True)
    schedule.last_run_at = now
    schedule.last_error = None
    if previous is not None and previous.status == RunStatus.COMPLETED.value:
        schedule.consecutive_failures = 0
    db.commit()
    return True


def fire_due(db: Session, now: datetime | None = None) -> int:
    now = now or _now()
    due = [
        row[0]
        for row in db.query(Schedule.id)
        .filter(Schedule.is_active.is_(True), Schedule.next_run_at <= now)
        .order_by(Schedule.next_run_at, Schedule.id)
        .all()
    ]
    db.rollback()
    started = 0
    for schedule_id in due:
        schedule = db.get(Schedule, schedule_id, populate_existing=True)
        if schedule is None:
            continue
        claimed = (
            db.query(Schedule)
            .filter(Schedule.id == schedule_id, Schedule.is_active.is_(True), Schedule.next_run_at == schedule.next_run_at)
            .update({Schedule.next_run_at: now + _interval(schedule.frequency)}, synchronize_session=False)
        )
        db.commit()
        if claimed and _start(db, schedule_id, now):
            started += 1
    return started


def fire_due_schedules() -> None:
    db = WorkerSessionLocal()
    try:
        fire_due(db)
    finally:
        db.close()
