import threading
import time
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.core.config import settings
from app.core.database import WRITE_INTENT, Base, build_engine, make_sessionmakers
from app.core.security import hash_password
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
    for _ in range(n):
        with real.write() as other:
            setting = other.get(AppSetting, "noise")
            if setting is None:
                other.add(AppSetting(key="noise", value={"n": 1}))
            else:
                setting.value = {"n": setting.value["n"] + 1}
            other.commit()


def test_a_run_survives_other_writes_committing_while_it_waits_on_the_network(real_db):
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
        assert db.get(AppSetting, "noise").value["n"] == run.tasks_total


def test_no_transaction_is_held_open_while_a_search_waits_on_the_network(real_db):
    run_id = queue_run(real_db)
    waited = []

    def during_search(_query):
        started = datetime.now(UTC)
        another_connection_commits(real_db)
        waited.append((datetime.now(UTC) - started).total_seconds())

    source = FakeSource("osm", [raw(1)], on_search=during_search)
    with real_db.worker() as db:
        runs_service.execute_run(db, run_id, source_builder=builder(osm=source))

    assert waited and max(waited) < 2, f"a competing write waited {max(waited):.1f}s during a search"


def test_editing_leads_while_a_run_is_ingesting_never_fails(real_db):
    run_id = queue_run(real_db)
    errors: list[Exception] = []
    stop = threading.Event()
    edits = []

    def edit_leads():
        counter = 0
        while not stop.is_set():
            try:
                with real_db.write() as api_db:
                    lead = api_db.query(Business).first()
                    if lead is None:
                        time.sleep(0.01)
                        continue
                    businesses_service.update_business(api_db, lead.id, BusinessUpdate(notes=f"edit {counter}"))
                    counter += 1
                    edits.append(counter)
            except Exception as exc:
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


def test_write_sessions_lock_up_front_and_read_sessions_do_not(real_db):
    with real_db.read() as reader, real_db.write() as writer:
        assert WRITE_INTENT not in reader.get_bind().get_execution_options()
        assert writer.get_bind().get_execution_options().get(WRITE_INTENT) is True

        writer.add(AppSetting(key="held", value={}))
        writer.flush()
        assert reader.query(User).count() == 1

        second = real_db.engine.execution_options(**{WRITE_INTENT: True}).connect()
        try:
            second.connection.driver_connection.execute("PRAGMA busy_timeout=200")
            with pytest.raises(Exception, match="locked"):
                second.begin()
        finally:
            second.close()
        writer.rollback()


def test_the_worker_session_keeps_loaded_objects_after_a_commit(real_db):
    run_id = queue_run(real_db)
    with real_db.worker() as db:
        run = db.get(Run, run_id)
        run.status = RunStatus.RUNNING.value
        db.commit()
        assert not db.in_transaction()
        assert run.status == RunStatus.RUNNING.value
        assert not db.in_transaction()


def test_requests_that_change_data_get_a_write_session_and_reads_do_not():
    from app.core.dependencies import get_db

    def session_for(method: str):
        generator = get_db(SimpleNamespace(method=method))
        db = next(generator)
        intent = db.get_bind().get_execution_options().get(WRITE_INTENT)
        generator.close()
        return intent

    assert [session_for(m) for m in ("GET", "HEAD", "OPTIONS")] == [None, None, None]
    assert [session_for(m) for m in ("POST", "PUT", "PATCH", "DELETE")] == [True, True, True, True]


def test_an_import_and_people_editing_leads_do_not_collide(real_db, monkeypatch):
    from app.features.imports import service as imports_service
    from app.features.imports.models import Import, ImportStatus
    from app.features.imports.schemas import ColumnMapping, ImportOptions

    monkeypatch.setattr(imports_service, "BATCH_SIZE", 15)
    rows = "\n".join(f"Solar Shop {n},0300 {n:07d},Lahore" for n in range(1, 241))
    content = f"Company,Phone,City\n{rows}\n".encode()

    with real_db.write() as db:
        profile = db.query(Profile).one()
        admin = db.query(User).one()
        options = ImportOptions(label="Concurrent list", profile_id=profile.id, mapping=ColumnMapping(name="Company", phones=["Phone"], city="City"))
        import_id = imports_service.create_import(db, "list.csv", content, options, admin.id).id

    errors: list[Exception] = []
    stop = threading.Event()

    def edit_leads():
        counter = 0
        while not stop.is_set():
            try:
                with real_db.write() as api_db:
                    lead = api_db.query(Business).first()
                    if lead is None:
                        time.sleep(0.005)
                        continue
                    businesses_service.update_business(api_db, lead.id, BusinessUpdate(notes=f"edit {counter}"))
                    counter += 1
            except Exception as exc:
                errors.append(exc)
                return

    editor = threading.Thread(target=edit_leads)
    editor.start()
    try:
        with real_db.worker() as db:
            imports_service.execute_import(db, import_id)
    finally:
        stop.set()
        editor.join(timeout=30)

    assert not errors, f"an edit failed during the import: {errors[0]!r}"
    with real_db.read() as db:
        record = db.get(Import, import_id)
        assert record.status == ImportStatus.COMPLETED.value, record.error
        assert record.stats["new"] == 240 and record.stats["errors"] == 0
        assert db.query(Business).count() == 240


def test_a_long_import_leaves_room_for_other_saves(real_db, monkeypatch):
    from app.features.imports import service as imports_service
    from app.features.imports.schemas import ColumnMapping, ImportOptions

    monkeypatch.setattr(settings, "IMPORT_BATCH_PAUSE_SECONDS", 0.15)
    rows = "\n".join(f"Volt Traders {n},03{n % 5}{10_000_000 + n},Lahore" for n in range(1, 1501))
    content = f"Company,Phone,City\n{rows}\n".encode()
    with real_db.write() as db:
        profile, admin = db.query(Profile).one(), db.query(User).one()
        options = ImportOptions(label="Long list", profile_id=profile.id, mapping=ColumnMapping(name="Company", phones=["Phone"], city="City"))
        import_id = imports_service.create_import(db, "list.csv", content, options, admin.id).id

    waits: list[float] = []
    stop = threading.Event()

    def other_saves():
        while not stop.is_set():
            started = time.monotonic()
            with real_db.write() as db:
                setting = db.get(AppSetting, "noise")
                if setting is None:
                    db.add(AppSetting(key="noise", value={"n": 1}))
                else:
                    setting.value = {"n": setting.value["n"] + 1}
                db.commit()
            waits.append(time.monotonic() - started)
            time.sleep(0.1)

    saver = threading.Thread(target=other_saves)
    saver.start()
    try:
        with real_db.worker() as db:
            imports_service.execute_import(db, import_id)
    finally:
        stop.set()
        saver.join(timeout=60)

    assert len(waits) >= 5, "other saves barely got a turn while the import ran"
    assert max(waits) < 4, f"a save waited {max(waits):.1f}s behind the import"
