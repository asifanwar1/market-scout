"""SQLite lets many readers and one writer at a time. These tests use a real database file and real
competing connections (the rest of the suite shares one connection), to keep the background run and
everything else that writes from colliding."""
import threading
import time
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.core.security import hash_password
from app.database import WRITE_INTENT, Base, build_engine, make_sessionmakers
from app.features.businesses import service as businesses_service
from app.features.businesses.models import Business
from app.features.businesses.schemas import BusinessUpdate
from app.features.geographies.models import Geography
from app.features.profiles.models import Profile
from app.features.runs import service as runs_service
from app.features.runs.models import Run, RunStatus, TaskStatus
from app.features.runs.schemas import RunCreate
from app.features.sheets.models import AppSetting
from app.features.users.models import User, UserRole
from scripts.seed import seed_geographies, seed_solar_profile
from tests.test_runs import FakeSource, builder, raw


@pytest.fixture()
def real_db(tmp_path):
    """A throwaway database file with its own engine, profile and admin."""
    engine = build_engine(f"sqlite:///{tmp_path / 'concurrent.db'}")
    Base.metadata.create_all(engine)
    read, write, worker = make_sessionmakers(engine)
    with write() as db:
        seed_geographies(db)
        seed_solar_profile(db)
        db.add(User(email="a@example.com", full_name="A", hashed_password=hash_password("Str0ng!Passw0rd"), role=UserRole.ADMIN.value))
        db.commit()
    yield SimpleNamespace(engine=engine, read=read, write=write, worker=worker)
    engine.dispose()


def queue_run(real, segments=("dealer",), cities=("lahore",)) -> int:
    with real.write() as db:
        profile = db.query(Profile).one()
        ids = [db.query(Geography).filter_by(slug=slug).one().id for slug in cities]
        admin = db.query(User).one()
        run = runs_service.create_run(
            db,
            RunCreate(profile_id=profile.id, geography_ids=ids, source_keys=["osm"], segment_slugs=list(segments), enrich_websites=False),
            admin.id,
        )
        return run.id


def another_connection_commits(real, n: int = 1) -> None:
    """What the API or a sheet sync does at any moment: a write that commits while the run is busy."""
    for _ in range(n):
        with real.write() as other:
            setting = other.get(AppSetting, "noise")
            if setting is None:
                other.add(AppSetting(key="noise", value={"n": 1}))
            else:
                setting.value = {"n": setting.value["n"] + 1}
            other.commit()


# ---- the bug this guards against ---------------------------------------------------------------------

def test_a_run_survives_other_writes_committing_while_it_waits_on_the_network(real_db):
    """A search is a network call; the API, a sheet sync or a person editing a lead commits in that
    gap. The run must carry on (before this was fixed: "database is locked", the search failed)."""
    run_id = queue_run(real_db)
    source = FakeSource("osm", [raw(n) for n in range(1, 6)], on_search=lambda _query: another_connection_commits(real_db))

    with real_db.worker() as db:
        runs_service.execute_run(db, run_id, source_builder=builder(osm=source))

    with real_db.read() as db:
        run = db.get(Run, run_id)
        assert run.status == RunStatus.COMPLETED.value, run.error
        assert run.tasks_failed == 0 and run.tasks_done == run.tasks_total > 0
        assert db.query(Business).count() == 5
        assert all(task.status == TaskStatus.DONE.value for task in run.tasks)
        assert db.get(AppSetting, "noise").value["n"] == run.tasks_total  # every competing write also landed


def test_no_transaction_is_held_open_while_a_search_waits_on_the_network(real_db):
    """If the worker held a write lock across the network call, every edit in the app would freeze
    behind a slow search. Prove another writer can get in *during* the search."""
    run_id = queue_run(real_db)
    waited = []

    def during_search(_query):
        started = datetime.now(UTC)
        another_connection_commits(real_db)  # would block until the 15 s timeout if the worker held the lock
        waited.append((datetime.now(UTC) - started).total_seconds())

    source = FakeSource("osm", [raw(1)], on_search=during_search)
    with real_db.worker() as db:
        runs_service.execute_run(db, run_id, source_builder=builder(osm=source))

    assert waited and max(waited) < 2, f"a competing write waited {max(waited):.1f}s during a search"


def test_editing_leads_while_a_run_is_ingesting_never_fails(real_db):
    """The real collision: a person edits leads (read, then write) while the worker ingests."""
    run_id = queue_run(real_db)
    errors: list[Exception] = []
    stop = threading.Event()
    edits = []

    def edit_leads():
        counter = 0
        while not stop.is_set():
            try:
                with real_db.write() as api_db:  # how a PATCH request is served
                    lead = api_db.query(Business).first()
                    if lead is None:
                        time.sleep(0.01)
                        continue
                    businesses_service.update_business(api_db, lead.id, BusinessUpdate(notes=f"edit {counter}"))
                    counter += 1
                    edits.append(counter)
            except Exception as exc:  # any failure here is the bug
                errors.append(exc)
                return

    editor = threading.Thread(target=edit_leads)
    editor.start()
    try:
        source = FakeSource("osm", lambda q: [raw(n) for n in range(1, 25)], on_search=lambda _q: another_connection_commits(real_db, 3))
        with real_db.worker() as db:
            runs_service.execute_run(db, run_id, source_builder=builder(osm=source))
    finally:
        stop.set()
        editor.join(timeout=30)

    assert not errors, f"an edit failed while the run was writing: {errors[0]!r}"
    with real_db.read() as db:
        run = db.get(Run, run_id)
        assert run.status == RunStatus.COMPLETED.value, run.error
        assert run.tasks_failed == 0


# ---- the session types -------------------------------------------------------------------------------------------

def test_write_sessions_lock_up_front_and_read_sessions_do_not(real_db):
    with real_db.read() as reader, real_db.write() as writer:
        assert WRITE_INTENT not in reader.get_bind().get_execution_options()
        assert writer.get_bind().get_execution_options().get(WRITE_INTENT) is True

        # A reader is never blocked by an open writer (WAL), which is what keeps the screens snappy.
        writer.add(AppSetting(key="held", value={}))
        writer.flush()
        assert reader.query(User).count() == 1

        # A second writer can't start until the first is done (here it gives up after 0.2 s), rather than
        # starting on a snapshot that goes stale and failing later.
        second = real_db.engine.execution_options(**{WRITE_INTENT: True}).connect()
        try:
            second.connection.driver_connection.execute("PRAGMA busy_timeout=200")
            with pytest.raises(Exception, match="locked"):
                second.begin()
        finally:
            second.close()
        writer.rollback()


def test_the_worker_session_keeps_loaded_objects_after_a_commit(real_db):
    """Otherwise reading an attribute after a commit would silently open a transaction (and take the
    write lock) right before the network call."""
    run_id = queue_run(real_db)
    with real_db.worker() as db:
        run = db.get(Run, run_id)
        run.status = RunStatus.RUNNING.value
        db.commit()
        assert not db.in_transaction()
        assert run.status == RunStatus.RUNNING.value  # no refresh happened
        assert not db.in_transaction()


def test_requests_that_change_data_get_a_write_session_and_reads_do_not():
    from app.dependencies import get_db

    def session_for(method: str):
        generator = get_db(SimpleNamespace(method=method))
        db = next(generator)
        intent = db.get_bind().get_execution_options().get(WRITE_INTENT)
        generator.close()
        return intent

    assert [session_for(m) for m in ("GET", "HEAD", "OPTIONS")] == [None, None, None]
    assert [session_for(m) for m in ("POST", "PUT", "PATCH", "DELETE")] == [True, True, True, True]
