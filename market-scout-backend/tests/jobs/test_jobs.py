import threading
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from app.core.database import Base, build_engine, make_sessionmakers
from app.features.jobs import runner as runner_module
from app.features.jobs import service
from app.features.jobs.handler import JobHandler
from app.features.jobs.models import Job, JobKind
from app.features.jobs.runner import CRASH_MESSAGE, JobRunner


def naive_utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


OWNER = "test-owner"
OTHER = "someone-else"
WAIT_SECONDS = 10


class Domain:
    def __init__(self):
        self.executed = []
        self.recovered = []
        self.recover_result = True
        self.recover_error = None
        self.queued = []
        self.running = []
        self.on_execute = None

    def handler(self):
        def execute(ref_id):
            self.executed.append(ref_id)
            if self.on_execute:
                self.on_execute(ref_id)

        def recover(db, ref_id, retries_left):
            self.recovered.append((ref_id, retries_left))
            if self.recover_error:
                raise self.recover_error
            return self.recover_result and retries_left

        return JobHandler(execute=execute, recover=recover, queued_ids=lambda db: list(self.queued), running_ids=lambda db: list(self.running))


@pytest.fixture()
def domain():
    return Domain()


@pytest.fixture()
def handlers(domain):
    return {JobKind.RUN: domain.handler()}


def add_job(db, ref_id=1, **fields):
    values = {"kind": "run", "ref_id": ref_id, "status": "queued", "run_after": datetime.now(UTC) - timedelta(seconds=1)}
    values.update(fields)
    job = Job(**values)
    db.add(job)
    db.commit()
    return job


def test_enqueue_adds_one_active_job_per_item_and_a_new_one_after_it_finished(db_session):
    first = service.enqueue(db_session, JobKind.RUN, 7)
    again = service.enqueue(db_session, JobKind.RUN, 7)
    other = service.enqueue(db_session, JobKind.IMPORT, 7)

    assert again.id == first.id and other.id != first.id and first.status == "queued"

    first.status = "done"
    db_session.flush()
    assert service.enqueue(db_session, JobKind.RUN, 7).id != first.id


def test_claiming_takes_the_oldest_due_job_and_marks_it_running_with_a_lease(db_session):
    later = add_job(db_session, 2, run_after=datetime.now(UTC) - timedelta(seconds=1))
    earlier = add_job(db_session, 1, run_after=datetime.now(UTC) - timedelta(minutes=5))
    add_job(db_session, 3, run_after=datetime.now(UTC) + timedelta(hours=1))
    add_job(db_session, 4, kind="import")

    claimed = service.claim_next(db_session, JobKind.RUN, OWNER)

    assert (claimed.id, claimed.ref_id, claimed.attempts) == (earlier.id, 1, 1)
    db_session.refresh(earlier)
    assert earlier.status == "running" and earlier.claimed_by == OWNER and earlier.started_at is not None
    assert earlier.lease_expires_at is not None
    assert service.claim_next(db_session, JobKind.RUN, OWNER).id == later.id
    assert service.claim_next(db_session, JobKind.RUN, OWNER) is None


def test_has_due_ignores_future_and_running_jobs(db_session):
    assert service.has_due(db_session, JobKind.RUN) is False
    add_job(db_session, 1, run_after=datetime.now(UTC) + timedelta(hours=1))
    add_job(db_session, 2, status="running")
    assert service.has_due(db_session, JobKind.RUN) is False
    add_job(db_session, 3)
    assert service.has_due(db_session, JobKind.RUN) is True


def test_finishing_records_the_outcome_only_for_the_job_owner(db_session):
    mine = add_job(db_session, 1, status="running", claimed_by=OWNER)
    theirs = add_job(db_session, 2, status="running", claimed_by=OTHER)
    broken = add_job(db_session, 3, status="running", claimed_by=OWNER)

    assert service.finish(db_session, mine.id, OWNER) is True
    assert service.finish(db_session, theirs.id, OWNER) is False
    assert service.finish(db_session, broken.id, OWNER, "x" * 900) is True

    for job in (mine, theirs, broken):
        db_session.refresh(job)
    assert mine.status == "done" and mine.finished_at is not None and mine.lease_expires_at is None
    assert theirs.status == "running"
    assert broken.status == "failed" and len(broken.error) == service.ERROR_MAX_LENGTH


def test_only_the_owners_leases_are_extended_or_released(db_session):
    soon = datetime.now(UTC) + timedelta(seconds=1)
    mine = add_job(db_session, 1, status="running", claimed_by=OWNER, lease_expires_at=soon)
    theirs = add_job(db_session, 2, status="running", claimed_by=OTHER, lease_expires_at=soon)

    assert service.extend_leases(db_session, OWNER, {mine.id, theirs.id}) == 1
    assert service.extend_leases(db_session, OWNER, set()) == 0
    db_session.refresh(mine)
    db_session.refresh(theirs)
    assert mine.lease_expires_at > theirs.lease_expires_at

    assert service.release_leases(db_session, OWNER, {mine.id, theirs.id}) == 1
    db_session.refresh(mine)
    assert mine.lease_expires_at < naive_utc_now()


def expired(db, ref_id, **fields):
    return add_job(db, ref_id, status="running", claimed_by=OTHER, attempts=1, lease_expires_at=datetime.now(UTC) - timedelta(seconds=5), **fields)


def test_an_interrupted_job_with_tries_left_is_queued_again_after_a_short_wait(db_session, handlers, domain):
    job = expired(db_session, 5)

    assert service.reclaim_expired(db_session, handlers, OWNER, set()) == 1

    db_session.refresh(job)
    assert domain.recovered == [(5, True)]
    assert job.status == "queued" and job.claimed_by is None and job.lease_expires_at is None
    assert job.error == service.INTERRUPTED_MESSAGE
    assert service.has_due(db_session, JobKind.RUN) is False
    assert service.has_due(db_session, JobKind.RUN, datetime.now(UTC) + timedelta(seconds=service.RETRY_DELAY_SECONDS + 1)) is True


def test_a_job_that_keeps_getting_interrupted_is_given_up_on(db_session, handlers, domain):
    job = expired(db_session, 5)
    job.attempts = service.MAX_ATTEMPTS
    db_session.commit()

    service.reclaim_expired(db_session, handlers, OWNER, set())

    db_session.refresh(job)
    assert domain.recovered == [(5, False)]
    assert job.status == "failed" and "3 times" in job.error and job.finished_at is not None


def test_a_job_that_cannot_be_resumed_is_failed(db_session, handlers, domain):
    domain.recover_result = False
    job = expired(db_session, 5)

    service.reclaim_expired(db_session, handlers, OWNER, set())

    db_session.refresh(job)
    assert job.status == "failed" and job.error == service.NOT_RESUMABLE_MESSAGE


def test_a_failing_recovery_fails_the_job_instead_of_looping(db_session, handlers, domain):
    domain.recover_error = RuntimeError("boom")
    job = expired(db_session, 5)

    assert service.reclaim_expired(db_session, handlers, OWNER, set()) == 1

    db_session.refresh(job)
    assert job.status == "failed"


def test_jobs_still_running_here_or_with_time_left_are_not_reclaimed(db_session, handlers, domain):
    held = expired(db_session, 1)
    alive = add_job(
        db_session, 2, status="running", claimed_by=OTHER, lease_expires_at=datetime.now(UTC) + timedelta(seconds=20)
    )

    assert service.reclaim_expired(db_session, handlers, OWNER, {held.id}) == 0

    db_session.refresh(held)
    db_session.refresh(alive)
    assert held.status == "running" and alive.status == "running" and domain.recovered == []


def test_waiting_and_stranded_work_without_a_job_gets_one(db_session, handlers, domain):
    domain.queued = [10, 11]
    domain.running = [20, 21]
    add_job(db_session, 10)
    add_job(db_session, 21, status="running", claimed_by=OTHER)

    adopted = service.adopt_orphans(db_session, handlers)

    assert adopted == 2
    assert domain.recovered == [(20, True)]
    refs = sorted((job.ref_id, job.status) for job in db_session.query(Job))
    assert refs == [(10, "queued"), (11, "queued"), (20, "queued"), (21, "running")]


def test_stranded_work_that_cannot_be_resumed_gets_no_job(db_session, handlers, domain):
    domain.running = [20]
    domain.recover_result = False

    assert service.adopt_orphans(db_session, handlers) == 0
    assert db_session.query(Job).count() == 0


def test_finished_job_records_are_cleared_after_the_retention_period(db_session):
    old = datetime.now(UTC) - timedelta(days=service.RETENTION_DAYS + 1)
    add_job(db_session, 1, status="done", finished_at=old)
    add_job(db_session, 2, status="failed", finished_at=old)
    keep_recent = add_job(db_session, 3, status="done", finished_at=datetime.now(UTC))
    keep_active = add_job(db_session, 4, status="queued")

    assert service.prune(db_session) == 2

    assert {job.id for job in db_session.query(Job)} == {keep_recent.id, keep_active.id}


def test_status_counts_active_jobs_and_lists_recent_failures(db_session):
    add_job(db_session, 1, run_after=datetime.now(UTC) - timedelta(seconds=90))
    add_job(db_session, 2, status="running", claimed_by=OTHER)
    add_job(db_session, 3, kind="import")
    add_job(db_session, 4, status="failed", error="no", finished_at=datetime.now(UTC))

    status = service.get_status(db_session)

    counts = {queue["kind"]: (queue["queued"], queue["running"]) for queue in status["queues"]}
    assert counts == {"run": (1, 1), "import": (1, 0), "ai_batch": (0, 0), "quality": (0, 0), "webhook": (0, 0)}
    assert status["oldest_waiting_seconds"] >= 89
    assert [failure.ref_id for failure in status["recent_failures"]] == [4]


@pytest.fixture()
def real_db(tmp_path):
    engine = build_engine(f"sqlite:///{tmp_path / 'jobs.db'}")
    Base.metadata.create_all(engine)
    read, write, _ = make_sessionmakers(engine)
    yield SimpleNamespace(read=read, write=write)
    engine.dispose()


@pytest.fixture()
def fast(monkeypatch):
    monkeypatch.setattr(runner_module, "POLL_SECONDS", 0.05)
    monkeypatch.setattr(runner_module, "ERROR_BACKOFF_SECONDS", 0.05)
    monkeypatch.setattr(runner_module, "MAINTENANCE_SECONDS", 0.1)
    monkeypatch.setattr(runner_module, "SCHEDULER_SECONDS", 0.1)
    monkeypatch.setattr(runner_module, "FINISH_RETRY_SECONDS", 0.01)


def make_runner(real_db, handlers):
    runner = JobRunner(real_db.read, real_db.write)
    runner._handlers = dict(handlers)
    runner._owner = OWNER
    return runner


def queue(real_db, *ref_ids, kind=JobKind.RUN):
    with real_db.write() as db:
        for ref_id in ref_ids:
            service.enqueue(db, kind, ref_id)
        db.commit()


def job_state(real_db, ref_id):
    with real_db.read() as db:
        job = db.query(Job).filter(Job.ref_id == ref_id).first()
        return job.status, job.error, job.attempts


def wait_for(condition, seconds=WAIT_SECONDS):
    done = threading.Event()

    def poll():
        while not done.is_set():
            if condition():
                done.set()
                return
            done.wait(0.02)

    thread = threading.Thread(target=poll, daemon=True)
    thread.start()
    done.wait(seconds)
    done.set()
    thread.join()
    return condition()


def test_processing_a_job_runs_its_handler_and_marks_it_done(real_db, handlers, domain):
    runner = make_runner(real_db, handlers)
    queue(real_db, 41)

    assert runner.process_one(JobKind.RUN) is True
    assert runner.process_one(JobKind.RUN) is False

    assert domain.executed == [41]
    assert job_state(real_db, 41)[0] == "done"


def test_a_handler_that_crashes_fails_its_job_without_stopping_the_runner(real_db, handlers, domain):
    def crash(ref_id):
        if ref_id == 1:
            raise RuntimeError("boom")

    domain.on_execute = crash
    runner = make_runner(real_db, handlers)
    queue(real_db, 1, 2)

    runner.process_one(JobKind.RUN)
    runner.process_one(JobKind.RUN)

    assert job_state(real_db, 1)[:2] == ("failed", CRASH_MESSAGE)
    assert job_state(real_db, 2)[0] == "done"
    assert domain.executed == [1, 2]


def test_lane_threads_run_queued_jobs_in_order_on_their_own_thread_and_stop_cleanly(real_db, handlers, domain, fast):
    threads = set()
    domain.on_execute = lambda ref_id: threads.add(threading.current_thread().name)
    runner = JobRunner(real_db.read, real_db.write)
    queue(real_db, 1, 2, 3)

    runner.start(handlers)
    try:
        assert wait_for(lambda: domain.executed == [1, 2, 3])
        assert runner.is_running and runner.lanes_alive() == {"run": True}
        queue(real_db, 4)
        assert wait_for(lambda: domain.executed == [1, 2, 3, 4])
    finally:
        runner.stop()

    assert threads == {"job-run"} and not runner.is_running


def test_starting_twice_does_not_start_a_second_set_of_threads(real_db, handlers, fast):
    runner = JobRunner(real_db.read, real_db.write)
    runner.start(handlers)
    try:
        lane = runner._lanes[JobKind.RUN]
        runner.start(handlers)
        assert runner._lanes[JobKind.RUN] is lane
    finally:
        runner.stop()


def test_a_database_error_while_looking_for_work_does_not_kill_the_lane(real_db, handlers, domain, fast, monkeypatch):
    real_claim = service.claim_next
    failures = {"left": 2}

    def flaky(db, kind, owner, now=None):
        if failures["left"]:
            failures["left"] -= 1
            raise RuntimeError("database is locked")
        return real_claim(db, kind, owner, now)

    monkeypatch.setattr(service, "claim_next", flaky)
    queue(real_db, 9)
    runner = JobRunner(real_db.read, real_db.write)
    runner.start(handlers)
    try:
        assert wait_for(lambda: domain.executed == [9])
        assert runner.lanes_alive() == {"run": True}
    finally:
        runner.stop()


def test_a_stopped_lane_is_started_again_by_maintenance(real_db, handlers, fast):
    runner = JobRunner(real_db.read, real_db.write)
    runner.start(handlers)
    try:
        dead = threading.Thread(target=lambda: None)
        dead.start()
        dead.join()
        runner._lanes[JobKind.RUN] = dead
        assert runner.lanes_alive() == {"run": False}

        assert wait_for(lambda: runner.lanes_alive() == {"run": True})
    finally:
        runner.stop()


def test_a_job_left_running_by_a_stopped_process_is_picked_up_and_run_again(real_db, handlers, domain):
    with real_db.write() as db:
        add_job(db, 77, status="running", claimed_by=OTHER, attempts=1, lease_expires_at=datetime.now(UTC) - timedelta(seconds=5))
    runner = make_runner(real_db, handlers)

    runner.run_maintenance_once()

    assert domain.recovered == [(77, True)]
    assert job_state(real_db, 77)[0] == "queued"
    with real_db.write() as db:
        db.query(Job).update({Job.run_after: datetime.now(UTC) - timedelta(seconds=1)})
        db.commit()
    runner.process_one(JobKind.RUN)
    assert domain.executed == [77] and job_state(real_db, 77)[0] == "done"


def test_a_job_this_process_is_still_running_is_never_reclaimed_even_if_its_lease_lapsed(real_db, handlers, domain):
    runner = make_runner(real_db, handlers)
    seen = {}

    def during(ref_id):
        with real_db.write() as db:
            db.query(Job).update({Job.lease_expires_at: datetime.now(UTC) - timedelta(minutes=5)})
            db.commit()
        runner.run_maintenance_once()
        seen["state"] = job_state(real_db, ref_id)[0]

    domain.on_execute = during
    queue(real_db, 5)

    runner.process_one(JobKind.RUN)

    assert seen["state"] == "running" and domain.recovered == [] and job_state(real_db, 5)[0] == "done"


def test_the_heartbeat_keeps_the_lease_of_a_running_job_fresh(real_db, handlers, domain):
    runner = make_runner(real_db, handlers)
    seen = {}

    def during(ref_id):
        with real_db.write() as db:
            db.query(Job).update({Job.lease_expires_at: datetime.now(UTC) + timedelta(seconds=1)})
            db.commit()
        runner._beat()
        with real_db.read() as db:
            seen["lease"] = db.query(Job.lease_expires_at).scalar()

    domain.on_execute = during
    queue(real_db, 5)

    runner.process_one(JobKind.RUN)

    assert seen["lease"] > naive_utc_now() + timedelta(seconds=service.LEASE_SECONDS - 5)


def test_stopping_hands_back_jobs_still_running_so_the_next_start_resumes_them_at_once(real_db, handlers, domain, fast):
    started, release = threading.Event(), threading.Event()

    def block(ref_id):
        started.set()
        release.wait(WAIT_SECONDS)

    domain.on_execute = block
    runner = JobRunner(real_db.read, real_db.write)
    queue(real_db, 8)
    runner.start(handlers)
    try:
        assert started.wait(WAIT_SECONDS)
        runner.stop(timeout=0.2)
        with real_db.read() as db:
            job = db.query(Job).one()
            assert job.status == "running" and job.lease_expires_at < naive_utc_now()
    finally:
        release.set()


def test_starting_picks_up_waiting_work_that_has_no_job_yet(real_db, handlers, domain, fast):
    domain.queued = [31]
    runner = JobRunner(real_db.read, real_db.write)
    runner.start(handlers)
    try:
        assert wait_for(lambda: domain.executed == [31])
    finally:
        runner.stop()


def test_schedule_tickers_run_on_their_own_thread_and_a_failing_one_does_not_stop_the_others(real_db, handlers, fast):
    calls = []
    names = set()

    def broken():
        raise RuntimeError("boom")

    def good():
        calls.append(1)
        names.add(threading.current_thread().name)

    runner = JobRunner(real_db.read, real_db.write)
    runner.start(handlers, tickers=[broken, good])
    try:
        assert wait_for(lambda: len(calls) >= 2)
    finally:
        runner.stop()

    assert names == {"job-scheduler"}


def test_job_status_is_for_admins_only_and_reports_the_queues(client, admin_user, sales_user, auth_headers, db_session):
    add_job(db_session, 1)

    assert client.get("/api/v1/jobs/status").status_code == 401
    assert client.get("/api/v1/jobs/status", headers=auth_headers(sales_user)).status_code == 403
    body = client.get("/api/v1/jobs/status", headers=auth_headers(admin_user)).json()

    assert body["workers_enabled"] is False and body["workers_running"] is False
    assert {"kind": "run", "queued": 1, "running": 0} in body["queues"]
    assert body["recent_failures"] == []


def test_health_reports_the_workers_state(client):
    body = client.get("/health").json()

    assert body == {"status": "ok", "database": "ok", "workers": "disabled"}


def test_health_turns_unavailable_when_workers_are_wanted_but_not_running(client, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "RUN_WORKER_ENABLED", True)

    response = client.get("/health")

    assert response.status_code == 503 and response.json()["workers"] == "stopped"
