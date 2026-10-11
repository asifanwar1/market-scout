import logging
import os
import socket
import threading
import time
import uuid
from collections.abc import Callable, Sequence
from contextlib import closing

from sqlalchemy.orm import Session, sessionmaker

from app.core.database import SessionLocal, WriteSessionLocal
from app.features.jobs import service as jobs_service
from app.features.jobs.handler import JobHandler
from app.features.jobs.models import JobKind

POLL_SECONDS = 1.0
ERROR_BACKOFF_SECONDS = 5.0
MAINTENANCE_SECONDS = 10.0
SCHEDULER_SECONDS = 15.0
PRUNE_SECONDS = 3600.0
FINISH_ATTEMPTS = 3
FINISH_RETRY_SECONDS = 2.0
STOP_TIMEOUT_SECONDS = 5.0
CRASH_MESSAGE = "Stopped by an unexpected error (see the server log)"
LANE_ERROR_MESSAGE = (
    "The %s job lane hit an error and will retry. If it repeats, the database may be out of date: run `alembic upgrade head`"
)


logger = logging.getLogger(__name__)


class JobRunner:
    def __init__(self, read_factory: sessionmaker[Session], write_factory: sessionmaker[Session]) -> None:
        self._read_factory = read_factory
        self._write_factory = write_factory
        self._handlers: dict[JobKind, JobHandler] = {}
        self._tickers: Sequence[Callable[[], None]] = ()
        self._lanes: dict[JobKind, threading.Thread] = {}
        self._maintenance: threading.Thread | None = None
        self._scheduler: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._held: set[int] = set()
        self._lock = threading.Lock()
        self._owner = ""
        self._last_prune = 0.0

    @property
    def owner(self) -> str:
        return self._owner

    @property
    def is_running(self) -> bool:
        return any(thread.is_alive() for thread in self._lanes.values())

    def lanes_alive(self) -> dict[str, bool]:
        return {kind.value: thread.is_alive() for kind, thread in self._lanes.items()}

    def start(self, handlers: dict[JobKind, JobHandler], tickers: Sequence[Callable[[], None]] = ()) -> None:
        if self.is_running:
            return
        self._handlers = dict(handlers)
        self._tickers = tuple(tickers)
        self._owner = f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex[:8]}"
        self._stop_event.clear()
        self._held = set()
        self._last_prune = 0.0
        self._sweep()
        for kind in self._handlers:
            self._lanes[kind] = self._spawn_lane(kind)
        self._maintenance = threading.Thread(target=self._maintenance_loop, name="job-maintenance", daemon=True)
        self._maintenance.start()
        self._scheduler = threading.Thread(target=self._scheduler_loop, name="job-scheduler", daemon=True)
        self._scheduler.start()

    def stop(self, timeout: float = STOP_TIMEOUT_SECONDS) -> None:
        self._stop_event.set()
        threads = [*self._lanes.values(), self._maintenance, self._scheduler]
        for thread in threads:
            if thread is not None:
                thread.join(timeout)
        with self._lock:
            held = set(self._held)
        if held:
            self._release(held)
        self._lanes = {}
        self._maintenance = None
        self._scheduler = None

    def process_one(self, kind: JobKind) -> bool:
        job = self._claim(kind)
        if job is None:
            return False
        self._execute(kind, job)
        return True

    def run_maintenance_once(self) -> None:
        self._beat()
        self._sweep()

    def _spawn_lane(self, kind: JobKind) -> threading.Thread:
        thread = threading.Thread(target=self._lane_loop, args=(kind,), name=f"job-{kind.value}", daemon=True)
        thread.start()
        return thread

    def _lane_loop(self, kind: JobKind) -> None:
        while not self._stop_event.is_set():
            try:
                worked = self.process_one(kind)
            except Exception:
                logger.exception(LANE_ERROR_MESSAGE, kind.value)
                self._stop_event.wait(ERROR_BACKOFF_SECONDS)
                continue
            if not worked:
                self._stop_event.wait(POLL_SECONDS)

    def _claim(self, kind: JobKind) -> jobs_service.ClaimedJob | None:
        with closing(self._read_factory()) as db:
            if not jobs_service.has_due(db, kind):
                return None
        with closing(self._write_factory()) as db:
            return jobs_service.claim_next(db, kind, self._owner)

    def _execute(self, kind: JobKind, job: jobs_service.ClaimedJob) -> None:
        with self._lock:
            self._held.add(job.id)
        error = None
        try:
            self._handlers[kind].execute(job.ref_id)
        except Exception:
            logger.exception("%s %s crashed", kind.value, job.ref_id)
            error = CRASH_MESSAGE
        finally:
            self._finish(job, error)
            with self._lock:
                self._held.discard(job.id)

    def _finish(self, job: jobs_service.ClaimedJob, error: str | None) -> None:
        for attempt in range(FINISH_ATTEMPTS):
            try:
                with closing(self._write_factory()) as db:
                    jobs_service.finish(db, job.id, self._owner, error)
                return
            except Exception:
                logger.exception("Could not record the end of job %s (attempt %s)", job.id, attempt + 1)
                time.sleep(FINISH_RETRY_SECONDS)

    def _release(self, held: set[int]) -> None:
        try:
            with closing(self._write_factory()) as db:
                jobs_service.release_leases(db, self._owner, held)
        except Exception:
            logger.exception("Could not hand back the jobs still running")

    def _maintenance_loop(self) -> None:
        while not self._stop_event.wait(MAINTENANCE_SECONDS):
            self.run_maintenance_once()
            self._revive_lanes()
            self._prune_if_due()

    def _beat(self) -> None:
        with self._lock:
            held = set(self._held)
        try:
            with closing(self._write_factory()) as db:
                jobs_service.extend_leases(db, self._owner, held)
        except Exception:
            logger.exception("Could not renew the leases of the jobs running")

    def _sweep(self) -> None:
        with self._lock:
            held = set(self._held)
        try:
            with closing(self._write_factory()) as db:
                jobs_service.reclaim_expired(db, self._handlers, self._owner, held)
            with closing(self._write_factory()) as db:
                jobs_service.adopt_orphans(db, self._handlers)
        except Exception:
            logger.exception("Checking for interrupted jobs failed")

    def _revive_lanes(self) -> None:
        for kind, thread in list(self._lanes.items()):
            if not thread.is_alive() and not self._stop_event.is_set():
                logger.error("The %s job lane had stopped; starting it again", kind.value)
                self._lanes[kind] = self._spawn_lane(kind)

    def _prune_if_due(self) -> None:
        if time.monotonic() - self._last_prune < PRUNE_SECONDS:
            return
        self._last_prune = time.monotonic()
        try:
            with closing(self._write_factory()) as db:
                jobs_service.prune(db)
        except Exception:
            logger.exception("Clearing old job records failed")

    def _scheduler_loop(self) -> None:
        while not self._stop_event.wait(SCHEDULER_SECONDS):
            for ticker in self._tickers:
                try:
                    ticker()
                except Exception:
                    logger.exception("A scheduled task failed")


job_runner = JobRunner(SessionLocal, WriteSessionLocal)
