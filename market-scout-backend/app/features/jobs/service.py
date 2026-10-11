import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.features.jobs.handler import JobHandler
from app.features.jobs.models import ACTIVE_JOB_STATUSES, Job, JobKind, JobStatus

LEASE_SECONDS = 30
MAX_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 5
RETENTION_DAYS = 30
ERROR_MAX_LENGTH = 500
RECENT_FAILURES_LIMIT = 10
RECLAIM_PREFIX = "reclaim:"
INTERRUPTED_MESSAGE = "Interrupted (the server stopped or lost contact); started again"
GAVE_UP_MESSAGE = "Interrupted {attempts} times; not started again"
NOT_RESUMABLE_MESSAGE = "Interrupted and could not be resumed"


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ClaimedJob:
    id: int
    kind: str
    ref_id: int
    attempts: int


def _now() -> datetime:
    return datetime.now(UTC)


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def enqueue(db: Session, kind: JobKind, ref_id: int) -> Job:
    existing = (
        db.query(Job).filter(Job.kind == kind.value, Job.ref_id == ref_id, Job.status.in_(ACTIVE_JOB_STATUSES)).first()
    )
    if existing is not None:
        return existing
    job = Job(kind=kind.value, ref_id=ref_id, status=JobStatus.QUEUED.value, run_after=_now())
    db.add(job)
    db.flush()
    return job


def has_due(db: Session, kind: JobKind, now: datetime | None = None) -> bool:
    now = now or _now()
    due = db.query(Job.id).filter(Job.kind == kind.value, Job.status == JobStatus.QUEUED.value, Job.run_after <= now).first()
    db.rollback()
    return due is not None


def claim_next(db: Session, kind: JobKind, owner: str, now: datetime | None = None) -> ClaimedJob | None:
    now = now or _now()
    candidate = (
        db.query(Job.id, Job.ref_id, Job.attempts)
        .filter(Job.kind == kind.value, Job.status == JobStatus.QUEUED.value, Job.run_after <= now)
        .order_by(Job.run_after, Job.id)
        .first()
    )
    if candidate is None:
        db.rollback()
        return None

    claimed = (
        db.query(Job)
        .filter(Job.id == candidate.id, Job.status == JobStatus.QUEUED.value)
        .update(
            {
                Job.status: JobStatus.RUNNING.value,
                Job.claimed_by: owner,
                Job.lease_expires_at: now + timedelta(seconds=LEASE_SECONDS),
                Job.started_at: now,
                Job.attempts: Job.attempts + 1,
            },
            synchronize_session=False,
        )
    )
    db.commit()
    if not claimed:
        return None
    return ClaimedJob(id=candidate.id, kind=kind.value, ref_id=candidate.ref_id, attempts=candidate.attempts + 1)


def extend_leases(db: Session, owner: str, job_ids: set[int], now: datetime | None = None) -> int:
    if not job_ids:
        return 0
    now = now or _now()
    extended = (
        db.query(Job)
        .filter(Job.id.in_(job_ids), Job.claimed_by == owner, Job.status == JobStatus.RUNNING.value)
        .update({Job.lease_expires_at: now + timedelta(seconds=LEASE_SECONDS)}, synchronize_session=False)
    )
    db.commit()
    return extended


def release_leases(db: Session, owner: str, job_ids: set[int], now: datetime | None = None) -> int:
    if not job_ids:
        return 0
    now = now or _now()
    released = (
        db.query(Job)
        .filter(Job.id.in_(job_ids), Job.claimed_by == owner, Job.status == JobStatus.RUNNING.value)
        .update({Job.lease_expires_at: now - timedelta(seconds=1)}, synchronize_session=False)
    )
    db.commit()
    return released


def finish(db: Session, job_id: int, owner: str, error: str | None = None, now: datetime | None = None) -> bool:
    now = now or _now()
    values = {
        Job.status: JobStatus.FAILED.value if error else JobStatus.DONE.value,
        Job.finished_at: now,
        Job.lease_expires_at: None,
    }
    if error:
        values[Job.error] = error[:ERROR_MAX_LENGTH]
    finished = (
        db.query(Job)
        .filter(Job.id == job_id, Job.claimed_by == owner, Job.status == JobStatus.RUNNING.value)
        .update(values, synchronize_session=False)
    )
    db.commit()
    return bool(finished)


def reclaim_expired(
    db: Session, handlers: dict[JobKind, JobHandler], owner: str, held_ids: set[int], now: datetime | None = None
) -> int:
    now = now or _now()
    expired = [
        row[0]
        for row in db.query(Job.id).filter(Job.status == JobStatus.RUNNING.value, Job.lease_expires_at < now).all()
    ]
    db.rollback()
    reclaimed = 0

    for job_id in expired:
        if job_id in held_ids:
            continue
        taken = (
            db.query(Job)
            .filter(Job.id == job_id, Job.status == JobStatus.RUNNING.value, Job.lease_expires_at < now)
            .update(
                {Job.claimed_by: RECLAIM_PREFIX + owner, Job.lease_expires_at: now + timedelta(seconds=LEASE_SECONDS)},
                synchronize_session=False,
            )
        )
        db.commit()
        if not taken:
            continue

        job = db.get(Job, job_id)
        handler = handlers.get(JobKind(job.kind))
        retries_left = job.attempts < MAX_ATTEMPTS
        resumed = False
        if handler is not None:
            try:
                resumed = handler.recover(db, job.ref_id, retries_left)
            except Exception:
                logger.exception("Could not recover %s %s after it was interrupted", job.kind, job.ref_id)
                db.rollback()

        job = db.get(Job, job_id, populate_existing=True)
        job.claimed_by = None
        job.lease_expires_at = None
        if resumed:
            job.status = JobStatus.QUEUED.value
            job.run_after = now + timedelta(seconds=RETRY_DELAY_SECONDS)
            job.error = INTERRUPTED_MESSAGE
        else:
            job.status = JobStatus.FAILED.value
            job.finished_at = now
            job.error = GAVE_UP_MESSAGE.format(attempts=job.attempts) if not retries_left else NOT_RESUMABLE_MESSAGE
        db.commit()
        reclaimed += 1
        logger.warning("%s %s was interrupted: %s", job.kind, job.ref_id, job.error)

    return reclaimed


def adopt_orphans(db: Session, handlers: dict[JobKind, JobHandler]) -> int:
    adopted = 0
    for kind, handler in handlers.items():
        queued = handler.queued_ids(db)
        running = handler.running_ids(db)
        covered = {
            row[0]
            for row in db.query(Job.ref_id).filter(Job.kind == kind.value, Job.status.in_(ACTIVE_JOB_STATUSES)).all()
        }
        for ref_id in queued:
            if ref_id not in covered:
                enqueue(db, kind, ref_id)
                covered.add(ref_id)
                adopted += 1
        for ref_id in running:
            if ref_id not in covered and handler.recover(db, ref_id, True):
                enqueue(db, kind, ref_id)
                covered.add(ref_id)
                adopted += 1
        db.commit()
    return adopted


def prune(db: Session, now: datetime | None = None) -> int:
    cutoff = (now or _now()) - timedelta(days=RETENTION_DAYS)
    removed = (
        db.query(Job)
        .filter(Job.status.in_((JobStatus.DONE.value, JobStatus.FAILED.value)), Job.finished_at < cutoff)
        .delete(synchronize_session=False)
    )
    db.commit()
    return removed


def get_status(db: Session) -> dict:
    now = _now()
    counts = {
        (kind, status): count
        for kind, status, count in db.query(Job.kind, Job.status, func.count(Job.id))
        .filter(Job.status.in_(ACTIVE_JOB_STATUSES))
        .group_by(Job.kind, Job.status)
        .all()
    }
    oldest = (
        db.query(func.min(Job.run_after)).filter(Job.status == JobStatus.QUEUED.value, Job.run_after <= now).scalar()
    )
    failures = db.query(Job).filter(Job.status == JobStatus.FAILED.value).order_by(Job.id.desc()).limit(RECENT_FAILURES_LIMIT).all()
    return {
        "queues": [
            {
                "kind": kind.value,
                "queued": counts.get((kind.value, JobStatus.QUEUED.value), 0),
                "running": counts.get((kind.value, JobStatus.RUNNING.value), 0),
            }
            for kind in JobKind
        ],
        "oldest_waiting_seconds": int((now - _as_utc(oldest)).total_seconds()) if oldest is not None else None,
        "recent_failures": failures,
    }
