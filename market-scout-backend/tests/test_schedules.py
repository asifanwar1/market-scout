from datetime import UTC, datetime, timedelta

import pytest

from app.core.config import settings
from app.features.jobs.models import Job
from app.features.profiles.models import Profile
from app.features.runs.models import Run
from app.features.schedules import service
from app.features.schedules.models import Schedule
from tests.test_runs import city, enable_paid, payload

BASE = "/api/v1/schedules"


@pytest.fixture()
def world(db_session, seeded_profile):
    return db_session.query(Profile).filter_by(slug="solar-inverters-batteries").one()


@pytest.fixture()
def admin(admin_user, auth_headers):
    return auth_headers(admin_user)


def body(world, db_session, **overrides):
    data = payload(world, [city(db_session, "lahore")], name="Weekly Lahore dealers", frequency="weekly")
    data.pop("refresh", None)
    data.update(overrides)
    return data


def create(client, admin, world, db_session, **overrides):
    response = client.post(f"{BASE}/", headers=admin, json=body(world, db_session, **overrides))
    assert response.status_code == 201, response.text
    return response.json()


def naive(value):
    return value.replace(tzinfo=None)


def make_due(db_session, schedule_id, **fields):
    db_session.query(Schedule).filter(Schedule.id == schedule_id).update(
        {"next_run_at": datetime.now(UTC) - timedelta(minutes=1), **fields}
    )
    db_session.commit()


def runs_of(db_session, schedule_id):
    return db_session.query(Run).filter(Run.schedule_id == schedule_id).order_by(Run.id).all()


def test_schedules_are_admin_only(client, world, db_session, sales_user, auth_headers):
    headers = auth_headers(sales_user)

    assert client.get(f"{BASE}/", headers=headers).status_code == 403
    assert client.post(f"{BASE}/", headers=headers, json=body(world, db_session)).status_code == 403
    assert client.get(f"{BASE}/1", headers=headers).status_code == 403
    assert client.put(f"{BASE}/1", headers=headers, json={"name": "xx"}).status_code == 403
    assert client.delete(f"{BASE}/1", headers=headers).status_code == 403
    assert client.post(f"{BASE}/1/run-now", headers=headers).status_code == 403
    assert client.get(f"{BASE}/").status_code == 401


def test_creating_a_schedule_sets_the_first_run_one_cycle_away(client, admin, world, db_session):
    for frequency, days in (("daily", 1), ("weekly", 7), ("monthly", 30)):
        created = create(client, admin, world, db_session, frequency=frequency)
        wait = naive(datetime.fromisoformat(created["next_run_at"])) - datetime.now(UTC).replace(tzinfo=None)
        assert timedelta(days=days) - timedelta(minutes=1) < wait <= timedelta(days=days)

    assert created["is_active"] is True and created["last_run"] is None and created["cities"] == ["Lahore"]
    assert created["profile_name"] == world.name and created["consecutive_failures"] == 0


def test_a_schedule_is_checked_like_a_run_when_it_is_saved(client, admin, world, db_session):
    def rejected(status=400, **overrides):
        response = client.post(f"{BASE}/", headers=admin, json=body(world, db_session, **overrides))
        assert response.status_code == status, response.text
        return response.json()["detail"]

    assert "not found" in rejected(404, profile_id=99999).lower()
    assert "not found" in rejected(404, geography_ids=[99999]).lower()
    assert "not a source" in rejected(source_keys=["nope"])
    assert "Unknown segment" in rejected(segment_slugs=["nope"])
    world.is_active = False
    db_session.commit()
    assert "switched off" in rejected()


def test_a_schedule_with_a_paid_source_needs_a_spending_cap(client, admin, world, db_session):
    enable_paid(db_session, "google_places")

    detail = client.post(f"{BASE}/", headers=admin, json=body(world, db_session, source_keys=["osm", "google_places"])).json()["detail"]
    assert detail == service.PAID_NEEDS_CAP_MESSAGE

    capped = create(client, admin, world, db_session, source_keys=["osm", "google_places"], max_paid_requests=40)
    assert capped["max_paid_requests"] == 40


def test_a_schedule_that_covers_too_many_searches_is_refused(client, admin, world, db_session, monkeypatch):
    monkeypatch.setattr(settings, "RUN_MAX_TASKS", 1)

    response = client.post(f"{BASE}/", headers=admin, json=body(world, db_session))

    assert response.status_code == 400 and "limit for one run" in response.json()["detail"]


def test_the_list_shows_newest_first_with_each_schedules_latest_run(client, admin, world, db_session):
    first = create(client, admin, world, db_session, name="First one")
    second = create(client, admin, world, db_session, name="Second one")
    make_due(db_session, first["id"])
    service.fire_due(db_session)

    listed = client.get(f"{BASE}/", headers=admin).json()

    assert listed["count"] == 2 and [item["name"] for item in listed["data"]] == ["Second one", "First one"]
    assert listed["data"][0]["last_run"] is None
    assert listed["data"][1]["last_run"]["status"] == "queued" and listed["data"][1]["last_run"]["new_leads"] == 0
    assert client.get(f"{BASE}/{second['id']}", headers=admin).json()["name"] == "Second one"
    assert client.get(f"{BASE}/99999", headers=admin).status_code == 404


def test_a_due_schedule_starts_a_refreshing_run_and_waits_a_cycle(client, admin, world, db_session):
    created = create(client, admin, world, db_session, enrich_websites=False)
    make_due(db_session, created["id"])

    assert service.fire_due(db_session) == 1

    [run] = runs_of(db_session, created["id"])
    assert run.refresh is True and run.status == "queued" and run.schedule_name == "Weekly Lahore dealers"
    assert run.source_keys == ["osm"] and run.enrich_websites is False
    assert db_session.query(Job).filter_by(kind="run", ref_id=run.id, status="queued").count() == 1
    schedule = db_session.get(Schedule, created["id"])
    assert schedule.last_run_at is not None and schedule.last_error is None
    assert naive(schedule.next_run_at) > datetime.now(UTC).replace(tzinfo=None) + timedelta(days=6)

    assert service.fire_due(db_session) == 0
    assert len(runs_of(db_session, created["id"])) == 1


def test_schedules_that_are_not_due_or_switched_off_do_not_start(client, admin, world, db_session):
    waiting = create(client, admin, world, db_session)
    off = create(client, admin, world, db_session, name="Switched off")
    make_due(db_session, off["id"], is_active=False)

    assert service.fire_due(db_session) == 0
    assert runs_of(db_session, waiting["id"]) == [] and runs_of(db_session, off["id"]) == []


def test_an_overdue_schedule_runs_once_not_once_per_missed_cycle(client, admin, world, db_session):
    created = create(client, admin, world, db_session, frequency="daily")
    make_due(db_session, created["id"], next_run_at=datetime.now(UTC) - timedelta(days=5))

    service.fire_due(db_session)
    service.fire_due(db_session)

    assert len(runs_of(db_session, created["id"])) == 1


def test_a_schedule_does_not_pile_up_runs_while_the_last_one_is_still_going(client, admin, world, db_session):
    created = create(client, admin, world, db_session, frequency="daily")
    make_due(db_session, created["id"])
    service.fire_due(db_session)
    make_due(db_session, created["id"])

    assert service.fire_due(db_session) == 0

    assert len(runs_of(db_session, created["id"])) == 1
    assert db_session.get(Schedule, created["id"]).last_error == service.STILL_RUNNING_MESSAGE


def test_failures_in_a_row_pause_a_schedule_and_a_good_run_clears_the_count(client, admin, world, db_session):
    created = create(client, admin, world, db_session, frequency="daily")
    schedule_id = created["id"]

    def fire_after(status, error=None):
        make_due(db_session, schedule_id)
        service.fire_due(db_session)
        run = runs_of(db_session, schedule_id)[-1]
        run.status, run.error = status, error
        db_session.commit()

    fire_after("failed", "Overpass is down")
    assert db_session.get(Schedule, schedule_id).consecutive_failures == 0

    fire_after("completed")
    assert db_session.get(Schedule, schedule_id).consecutive_failures == 1

    fire_after("failed", "Overpass is down")
    assert db_session.get(Schedule, schedule_id).consecutive_failures == 0

    fire_after("failed", "Overpass is down")
    fire_after("failed", "Overpass is down")
    make_due(db_session, schedule_id)
    service.fire_due(db_session)

    schedule = db_session.get(Schedule, schedule_id)
    assert schedule.consecutive_failures == service.MAX_CONSECUTIVE_FAILURES and schedule.is_active is False
    assert "Overpass is down" in schedule.last_error and "Paused after 3 failures" in schedule.last_error
    assert len(runs_of(db_session, schedule_id)) == 5


def test_a_schedule_whose_search_can_no_longer_run_records_why_and_pauses_after_three_tries(client, admin, world, db_session):
    created = create(client, admin, world, db_session, frequency="daily")
    world.is_active = False
    db_session.commit()

    for _ in range(service.MAX_CONSECUTIVE_FAILURES):
        make_due(db_session, created["id"])
        service.fire_due(db_session)

    schedule = db_session.get(Schedule, created["id"])
    assert schedule.is_active is False and schedule.consecutive_failures == 3
    assert "switched off" in schedule.last_error and runs_of(db_session, created["id"]) == []


def test_an_unexpected_error_while_starting_is_recorded_without_the_detail(client, admin, world, db_session, monkeypatch):
    created = create(client, admin, world, db_session)
    make_due(db_session, created["id"])

    def explode(*_args, **_kwargs):
        raise RuntimeError("secret detail")

    monkeypatch.setattr(service.runs_service, "create_run", explode)

    assert service.fire_due(db_session) == 0

    schedule = db_session.get(Schedule, created["id"])
    assert schedule.last_error == service.UNEXPECTED_ERROR_MESSAGE and schedule.consecutive_failures == 1


def test_run_now_starts_a_run_without_moving_the_schedule(client, admin, world, db_session):
    created = create(client, admin, world, db_session)

    response = client.post(f"{BASE}/{created['id']}/run-now", headers=admin)

    assert response.status_code == 201, response.text
    run = response.json()
    assert run["schedule_id"] == created["id"] and run["schedule_name"] == created["name"] and run["refresh"] is True
    after = client.get(f"{BASE}/{created['id']}", headers=admin).json()
    assert after["next_run_at"] == created["next_run_at"] and after["last_run"]["id"] == run["id"]

    again = client.post(f"{BASE}/{created['id']}/run-now", headers=admin)
    assert again.status_code == 409 and again.json()["detail"] == service.ALREADY_RUNNING_MESSAGE
    assert client.post(f"{BASE}/99999/run-now", headers=admin).status_code == 404


def test_renaming_and_changing_how_often_it_repeats(client, admin, world, db_session):
    created = create(client, admin, world, db_session, frequency="monthly")

    renamed = client.put(f"{BASE}/{created['id']}", headers=admin, json={"name": "  Renamed  "}).json()
    assert renamed["name"] == "Renamed" and renamed["next_run_at"] == created["next_run_at"]

    faster = client.put(f"{BASE}/{created['id']}", headers=admin, json={"frequency": "daily"}).json()
    wait = naive(datetime.fromisoformat(faster["next_run_at"])) - datetime.now(UTC).replace(tzinfo=None)
    assert faster["frequency"] == "daily" and wait <= timedelta(days=1)


def test_changing_what_a_schedule_searches_is_checked_again(client, admin, world, db_session):
    created = create(client, admin, world, db_session)
    karachi = city(db_session, "karachi")

    changed = client.put(
        f"{BASE}/{created['id']}", headers=admin, json={"geography_ids": [karachi.id], "segment_slugs": None, "enrich_websites": True}
    ).json()
    assert changed["cities"] == ["Karachi"] and changed["segment_slugs"] is None and changed["enrich_websites"] is True

    assert client.put(f"{BASE}/{created['id']}", headers=admin, json={"source_keys": ["nope"]}).status_code == 400
    assert client.put(f"{BASE}/{created['id']}", headers=admin, json={"name": None}).status_code == 400
    assert client.put(f"{BASE}/{created['id']}", headers=admin, json={"is_active": None}).status_code == 400
    assert client.get(f"{BASE}/{created['id']}", headers=admin).json()["cities"] == ["Karachi"]


def test_switching_a_paused_schedule_back_on_clears_the_failures_and_waits_a_cycle(client, admin, world, db_session):
    created = create(client, admin, world, db_session)
    make_due(db_session, created["id"], is_active=False, consecutive_failures=3, last_error="boom")

    resumed = client.put(f"{BASE}/{created['id']}", headers=admin, json={"is_active": True}).json()

    assert resumed["is_active"] is True and resumed["consecutive_failures"] == 0 and resumed["last_error"] is None
    assert naive(datetime.fromisoformat(resumed["next_run_at"])) > datetime.now(UTC).replace(tzinfo=None) + timedelta(days=6)

    paused = client.put(f"{BASE}/{created['id']}", headers=admin, json={"is_active": False}).json()
    assert paused["is_active"] is False


def test_deleting_a_schedule_keeps_the_runs_it_made(client, admin, world, db_session):
    created = create(client, admin, world, db_session)
    run_id = client.post(f"{BASE}/{created['id']}/run-now", headers=admin).json()["id"]

    assert client.delete(f"{BASE}/{created['id']}", headers=admin).status_code == 204

    assert client.get(f"{BASE}/{created['id']}", headers=admin).status_code == 404
    run = client.get(f"/api/v1/runs/{run_id}", headers=admin).json()
    assert run["schedule_id"] is None and run["schedule_name"] == created["name"]
    assert client.delete(f"{BASE}/{created['id']}", headers=admin).status_code == 404


def test_the_schedule_check_that_runs_in_the_background_uses_its_own_session(client, admin, world, db_session, monkeypatch):
    seen = []
    monkeypatch.setattr(service, "fire_due", lambda db: seen.append(db) or 0)

    service.fire_due_schedules()

    assert len(seen) == 1
