import threading

import pytest

from app.config import settings
from app.core.scouting.enrichment.website import EnrichmentError, WebsiteContacts
from app.core.scouting.normalize import PhoneInfo
from app.core.scouting.sources.base import SourceAuthError, SourceError
from app.core.scouting.types import RawBusiness, SearchResult
from app.features.businesses import ingest as businesses_ingest
from app.features.businesses.models import Business, ContactPoint
from app.features.geographies.models import Geography
from app.features.profiles.models import Profile
from app.features.runs import service
from app.features.runs.models import Run, RunTask
from app.features.runs.worker import RunWorker
from app.features.sources import service as sources_service
from app.features.sources.schemas import SourceUpdate
from scripts.seed import seed_geographies, seed_solar_profile
from scripts.seed_data.pakistan import REGIONS

# ---- fixtures / fakes -----------------------------------------------------------

@pytest.fixture()
def world(db_session):
    seed_geographies(db_session)
    seed_solar_profile(db_session)
    profile = db_session.query(Profile).filter_by(slug="solar-inverters-batteries").one()
    return profile


def city(db, slug: str) -> Geography:
    return db.query(Geography).filter_by(slug=slug).one()


def raw(n: int, source: str = "osm", **overrides) -> RawBusiness:
    data = dict(
        source_key=source, external_id=f"{source}/{n}", name=f"Solar Shop {n}",
        latitude=31.50 + n * 0.01, longitude=74.30 + n * 0.01,
        phones=[f"0300 {n:07d}"], emails=[], categories=[],
    )
    data.update(overrides)
    return RawBusiness(**data)


class FakeSource:
    """Stands in for OSM / Places. ``businesses`` is a list, or a function of the query."""

    def __init__(self, key="osm", businesses=(), error=None, requests_per_search=1, on_search=None):
        self.key = key
        self.businesses = businesses
        self.error = error
        self.requests_per_search = requests_per_search
        self.on_search = on_search
        self.calls = []

    def search(self, query, max_requests=None):
        self.calls.append(query)
        if self.on_search:
            self.on_search(query)
        if self.error:
            raise self.error
        found = self.businesses(query) if callable(self.businesses) else list(self.businesses)
        requests = self.requests_per_search if max_requests is None else min(self.requests_per_search, max_requests)
        return SearchResult(found, requests_made=requests, truncated=requests < self.requests_per_search)

    def test_connection(self):
        return True, "ok"


class FakeEnricher:
    def __init__(self, results=None, error=None):
        self.results = results or {}
        self.error = error
        self.urls = []
        self._lock = threading.Lock()

    def enrich(self, url):
        with self._lock:
            self.urls.append(url)
        if self.error:
            raise self.error
        return self.results.get(url, WebsiteContacts())


def builder(**sources):
    return lambda db, keys: {key: sources[key] for key in keys}


def enable_places(db):
    sources_service.update_source(db, "google_places", SourceUpdate(api_key="test-key-12345", is_enabled=True))


def payload(profile, cities, **overrides):
    data = {
        "profile_id": profile.id,
        "geography_ids": [c.id for c in cities],
        "source_keys": ["osm"],
        "segment_slugs": ["dealer"],
        "enrich_websites": False,
    }
    data.update(overrides)
    return data


def make_run(client, admin_user, auth_headers, body):
    response = client.post("/api/v1/runs/", headers=auth_headers(admin_user), json=body)
    assert response.status_code == 201, response.text
    return response.json()


def osm_dealer_terms(profile) -> int:
    return sum(1 for t in profile.search_terms if t.segment_slug == "dealer" and t.osm_filter)


def dealer_terms(profile) -> int:
    return sum(1 for t in profile.search_terms if t.segment_slug == "dealer")


# ---- permissions ----------------------------------------------------------------------

def test_runs_are_admin_only(client, world, db_session, sales_user, auth_headers):
    headers = auth_headers(sales_user)
    lahore = city(db_session, "lahore")
    body = payload(world, [lahore])
    assert client.get("/api/v1/runs/", headers=headers).status_code == 403
    assert client.post("/api/v1/runs/", headers=headers, json=body).status_code == 403
    assert client.post("/api/v1/runs/estimate", headers=headers, json=body).status_code == 403
    assert client.get("/api/v1/runs/1", headers=headers).status_code == 403
    assert client.post("/api/v1/runs/1/cancel", headers=headers).status_code == 403
    assert client.get("/api/v1/runs/").status_code == 401


# ---- estimate / create ----------------------------------------------------------------------

def test_estimate_counts_searches_per_source_and_prices_the_paid_one(client, admin_user, auth_headers, world, db_session):
    enable_places(db_session)
    cities = [city(db_session, "lahore"), city(db_session, "karachi")]

    response = client.post(
        "/api/v1/runs/estimate", headers=auth_headers(admin_user),
        json=payload(world, cities, source_keys=["osm", "google_places"], max_paid_requests=10),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    by_source = {s["source_key"]: s for s in body["by_source"]}
    # OSM can only search terms that carry an OSM filter; Places can search every term.
    assert by_source["osm"]["tasks"] == 2 * osm_dealer_terms(world)
    assert by_source["google_places"]["tasks"] == 2 * dealer_terms(world)
    assert by_source["osm"]["max_requests"] is None and by_source["osm"]["estimated_cost_usd"] is None
    assert by_source["google_places"]["max_requests"] == 10          # capped below tasks x 3 pages
    assert body["paid_requests_max"] == 10
    assert body["estimated_cost_usd"] == round(10 * settings.PLACES_COST_PER_REQUEST_USD, 2)
    assert body["tasks_total"] == body["tasks_to_run"] == by_source["osm"]["tasks"] + by_source["google_places"]["tasks"]
    assert body["allowed"] is True and body["cities"] == 2 and body["estimated_minutes"] >= 1
    assert any("cap" in warning for warning in body["warnings"])


def test_estimate_warns_when_a_paid_source_has_no_cap(client, admin_user, auth_headers, world, db_session):
    enable_places(db_session)
    body = client.post(
        "/api/v1/runs/estimate", headers=auth_headers(admin_user),
        json=payload(world, [city(db_session, "lahore")], source_keys=["google_places"]),
    ).json()
    assert body["paid_requests_max"] == dealer_terms(world) * 3
    assert any("No request cap" in warning for warning in body["warnings"])


def test_create_run_builds_a_queued_run_with_one_task_per_search(client, admin_user, auth_headers, world, db_session):
    lahore = city(db_session, "lahore")
    run = make_run(client, admin_user, auth_headers, payload(world, [lahore]))

    assert run["status"] == "queued" and run["profile_name"] == world.name
    assert run["tasks_total"] == osm_dealer_terms(world) and run["progress_percent"] == 0
    assert run["created_by_id"] == admin_user.id

    tasks = client.get(f"/api/v1/runs/{run['id']}/tasks", headers=auth_headers(admin_user)).json()
    assert tasks["count"] == run["tasks_total"]
    assert {t["status"] for t in tasks["data"]} == {"pending"}
    assert {t["geography_name"] for t in tasks["data"]} == {"Lahore"}
    assert all(t["source_key"] == "osm" and t["segment_slug"] == "dealer" for t in tasks["data"])


def test_a_province_expands_to_its_cities(client, admin_user, auth_headers, world, db_session):
    punjab = db_session.query(Geography).filter_by(slug="punjab").one()
    run = make_run(client, admin_user, auth_headers, payload(world, [punjab]))
    assert run["tasks_total"] == len(REGIONS["Punjab"]) * osm_dealer_terms(world)


@pytest.mark.parametrize(
    "change, status",
    [
        ({"source_keys": ["nope"]}, 400),
        ({"source_keys": ["website_enrichment"]}, 400),          # not a discovery source
        ({"source_keys": ["google_places"]}, 400),               # switched off, no key
        ({"segment_slugs": ["nonexistent"]}, 400),
        ({"profile_id": 9999}, 404),
        ({"geography_ids": [9999]}, 404),
        ({"geography_ids": []}, 422),
        ({"source_keys": []}, 422),
        ({"max_paid_requests": 0}, 422),
    ],
)
def test_create_run_rejects_bad_requests(client, admin_user, auth_headers, world, db_session, change, status):
    body = payload(world, [city(db_session, "lahore")], **change)
    response = client.post("/api/v1/runs/", headers=auth_headers(admin_user), json=body)
    assert response.status_code == status, response.text


def test_create_run_rejects_inactive_profile_country_without_cities_and_oversized_runs(
    client, admin_user, auth_headers, world, db_session, monkeypatch
):
    headers = auth_headers(admin_user)
    lahore = city(db_session, "lahore")

    monkeypatch.setattr(settings, "RUN_MAX_TASKS", 1)
    too_big = client.post("/api/v1/runs/", headers=headers, json=payload(world, [lahore]))
    assert too_big.status_code == 400 and "limit" in too_big.json()["detail"]
    estimate = client.post("/api/v1/runs/estimate", headers=headers, json=payload(world, [lahore])).json()
    assert estimate["allowed"] is False and estimate["warnings"]
    monkeypatch.undo()

    empty_province = client.post(
        "/api/v1/geographies/", headers=headers, json={"name": "Empty", "level": "province", "parent_id": db_session.query(Geography).filter_by(slug="pakistan").one().id}
    ).json()
    assert client.post("/api/v1/runs/", headers=headers, json=payload(world, [], geography_ids=[empty_province["id"]])).status_code == 400

    world.is_active = False
    db_session.commit()
    assert client.post("/api/v1/runs/", headers=headers, json=payload(world, [lahore])).status_code == 400


def test_source_without_matching_terms_is_refused(client, admin_user, auth_headers, world, db_session):
    # Only Roman-Urdu terms remain, and OpenStreetMap can't search those.
    lahore = city(db_session, "lahore")
    body = payload(world, [lahore], segment_slugs=["dealer"])
    for term in world.search_terms:
        if term.segment_slug == "dealer" and term.language == "en":
            term.is_active = False
    db_session.commit()
    response = client.post("/api/v1/runs/", headers=auth_headers(admin_user), json=body)
    assert response.status_code == 400 and "Nothing to search" in response.json()["detail"]


# ---- executing --------------------------------------------------------------------------------

def test_execute_run_stores_deduplicated_businesses_and_reports_stats(client, admin_user, auth_headers, world, db_session):
    lahore = city(db_session, "lahore")
    run = make_run(client, admin_user, auth_headers, payload(world, [lahore]))
    # Every search returns the same two shops; the second search of each pair must merge, not duplicate.
    source = FakeSource("osm", [raw(1, emails=["a@shop1.pk"], website="shop1.pk"), raw(2)])

    finished = service.execute_run(db_session, run["id"], source_builder=builder(osm=source))

    n_tasks = osm_dealer_terms(world)
    assert finished.status == "completed" and finished.error is None
    assert (finished.tasks_done, finished.tasks_failed, finished.tasks_skipped) == (n_tasks, 0, 0)
    assert finished.progress_percent == 100 and finished.started_at and finished.finished_at
    assert db_session.query(Business).count() == 2

    stats = finished.stats["osm"]
    assert stats["found"] == 2 * n_tasks
    assert (stats["new"], stats["merged"]) == (2, 2 * n_tasks - 2)
    assert stats["with_phone"] == 2 * n_tasks and stats["with_website"] == n_tasks and stats["with_email"] == n_tasks
    assert stats["tasks_done"] == n_tasks and stats["requests"] == n_tasks
    assert finished.paid_requests_used == 0

    first_query = source.calls[0]
    assert first_query.area.name == "Lahore" and first_query.area.radius_km == lahore.radius_km
    assert first_query.osm_filter is not None
    tasks = db_session.query(RunTask).filter_by(run_id=finished.id).order_by(RunTask.id).all()
    assert all(t.status == "done" and t.results_count == 2 and t.finished_at for t in tasks)
    assert sum(t.new_count for t in tasks) == 2


def test_repeating_a_run_skips_recent_searches_unless_refreshed(client, admin_user, auth_headers, world, db_session):
    lahore = city(db_session, "lahore")
    source = FakeSource("osm", [raw(1)])
    first = make_run(client, admin_user, auth_headers, payload(world, [lahore]))
    service.execute_run(db_session, first["id"], source_builder=builder(osm=source))
    calls_after_first = len(source.calls)

    repeat = make_run(client, admin_user, auth_headers, payload(world, [lahore]))
    assert repeat["tasks_skipped"] == repeat["tasks_total"] > 0
    finished = service.execute_run(db_session, repeat["id"], source_builder=builder(osm=source))
    assert len(source.calls) == calls_after_first                       # nothing was searched again
    assert finished.status == "completed" and finished.progress_percent == 100
    assert {t.error for t in db_session.query(RunTask).filter_by(run_id=finished.id)} == {"Searched recently; skipped"}

    estimate = client.post("/api/v1/runs/estimate", headers=auth_headers(admin_user), json=payload(world, [lahore])).json()
    assert estimate["tasks_to_run"] == 0 and estimate["tasks_skipped"] == estimate["tasks_total"]
    assert f"{estimate['tasks_skipped']} searches were completed recently" in estimate["warnings"][0]

    refreshed = make_run(client, admin_user, auth_headers, payload(world, [lahore], refresh=True))
    assert refreshed["tasks_skipped"] == 0
    done = service.execute_run(db_session, refreshed["id"], source_builder=builder(osm=source))
    assert len(source.calls) > calls_after_first
    assert db_session.query(Business).count() == 1                     # re-finding it created no duplicate
    assert done.stats["osm"]["new"] == 0


def test_estimate_wording_for_exactly_one_recent_search(client, admin_user, auth_headers, world, db_session):
    lahore = city(db_session, "lahore")
    body = payload(world, [lahore], segment_slugs=["contractor"])      # one OpenStreetMap search
    run = make_run(client, admin_user, auth_headers, body)
    service.execute_run(db_session, run["id"], source_builder=builder(osm=FakeSource("osm", [raw(1)])))

    estimate = client.post("/api/v1/runs/estimate", headers=auth_headers(admin_user), json=body).json()

    assert estimate["tasks_total"] == estimate["tasks_skipped"] == 1
    assert estimate["warnings"][0].startswith("1 search was completed recently")


def test_failed_searches_are_isolated_and_retried_next_time(client, admin_user, auth_headers, world, db_session):
    lahore = city(db_session, "lahore")
    run = make_run(client, admin_user, auth_headers, payload(world, [lahore]))
    seen = []

    def flaky(query):
        seen.append(query.text)
        if len(seen) == 1:
            raise SourceError("Overpass gave up: timed out")
        return [raw(len(seen))]

    source = FakeSource("osm", flaky)
    finished = service.execute_run(db_session, run["id"], source_builder=builder(osm=source))

    assert finished.status == "completed"                                # partial success is still a completed run
    assert (finished.tasks_done, finished.tasks_failed) == (osm_dealer_terms(world) - 1, 1)
    failed = db_session.query(RunTask).filter_by(run_id=finished.id, status="failed").one()
    assert "timed out" in failed.error
    assert finished.stats["osm"]["tasks_failed"] == 1

    # A failed search is not cached: the next run tries it again.
    rerun = make_run(client, admin_user, auth_headers, payload(world, [lahore]))
    assert rerun["tasks_skipped"] == osm_dealer_terms(world) - 1


def test_run_fails_when_every_search_fails(client, admin_user, auth_headers, world, db_session):
    run = make_run(client, admin_user, auth_headers, payload(world, [city(db_session, "lahore")]))
    source = FakeSource("osm", error=SourceError("Rate limited (HTTP 429)"))

    finished = service.execute_run(db_session, run["id"], source_builder=builder(osm=source))

    assert finished.status == "failed" and "429" in finished.error
    assert finished.tasks_done == 0 and finished.tasks_failed == osm_dealer_terms(world)


def test_unexpected_errors_fail_one_task_not_the_run(client, admin_user, auth_headers, world, db_session):
    run = make_run(client, admin_user, auth_headers, payload(world, [city(db_session, "lahore")]))
    calls = []

    def sometimes_explodes(query):
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("boom")
        return [raw(1)]

    finished = service.execute_run(db_session, run["id"], source_builder=builder(osm=FakeSource("osm", sometimes_explodes)))

    assert finished.status == "completed" and finished.tasks_failed == 1
    failed = db_session.query(RunTask).filter_by(run_id=finished.id, status="failed").one()
    assert "Unexpected error" in failed.error and "boom" not in failed.error      # no internals leaked to the UI
    assert db_session.query(Business).count() == 1


def test_one_malformed_listing_does_not_lose_the_others(client, admin_user, auth_headers, world, db_session, monkeypatch):
    run = make_run(client, admin_user, auth_headers, payload(world, [city(db_session, "lahore")]))
    real_ingest = businesses_ingest.ingest_business

    def picky(db, raw_business, ctx):
        if raw_business.external_id == "osm/2":
            raise ValueError("bad listing")
        return real_ingest(db, raw_business, ctx)

    monkeypatch.setattr(businesses_ingest, "ingest_business", picky)
    finished = service.execute_run(db_session, run["id"], source_builder=builder(osm=FakeSource("osm", [raw(1), raw(2), raw(3)])))

    assert finished.status == "completed" and finished.tasks_failed == 0
    assert {b.name for b in db_session.query(Business)} == {"Solar Shop 1", "Solar Shop 3"}
    assert finished.stats["osm"]["errors"] == osm_dealer_terms(world)


def test_rejected_key_stops_asking_that_source_but_other_sources_continue(client, admin_user, auth_headers, world, db_session):
    enable_places(db_session)
    run = make_run(client, admin_user, auth_headers, payload(world, [city(db_session, "lahore")], source_keys=["osm", "google_places"]))
    places = FakeSource("google_places", error=SourceAuthError("API key not valid"))
    osm = FakeSource("osm", [raw(1)])

    finished = service.execute_run(db_session, run["id"], source_builder=builder(osm=osm, google_places=places))

    assert len(places.calls) == 1                                        # only the first search hit the bad key
    assert len(osm.calls) == osm_dealer_terms(world)
    assert finished.status == "completed"
    assert "API key not valid" in finished.error and "Google Places" in finished.error
    places_tasks = db_session.query(RunTask).filter_by(run_id=finished.id, source_key="google_places").all()
    assert sorted(t.status for t in places_tasks) == ["failed"] + ["skipped"] * (dealer_terms(world) - 1)
    assert finished.tasks_failed == 1 and finished.tasks_skipped == dealer_terms(world) - 1


def test_request_cap_stops_paid_searches_and_counts_billable_requests(client, admin_user, auth_headers, world, db_session, monkeypatch):
    monkeypatch.setattr(settings, "PLACES_COST_PER_REQUEST_USD", 0.5)
    enable_places(db_session)
    run = make_run(client, admin_user, auth_headers, payload(
        world, [city(db_session, "lahore"), city(db_session, "karachi")],
        source_keys=["google_places"], max_paid_requests=4,
    ))
    places = FakeSource("google_places", [raw(1, source="google_places")], requests_per_search=3)

    finished = service.execute_run(db_session, run["id"], source_builder=builder(google_places=places))

    # search 1 uses 3 of the 4 allowed requests, search 2 is cut to the 1 that's left, the rest never run.
    assert finished.paid_requests_used == 4 and finished.estimated_cost_usd == 2.0
    assert len(places.calls) == 2
    statuses = [t.status for t in db_session.query(RunTask).filter_by(run_id=finished.id).order_by(RunTask.id)]
    assert statuses[:2] == ["done", "done"] and set(statuses[2:]) == {"skipped"}
    assert db_session.query(RunTask).filter_by(run_id=finished.id, status="skipped").first().error == "Request cap reached"
    assert db_session.query(RunTask).filter_by(run_id=finished.id).order_by(RunTask.id).all()[1].error == "Stopped early: request cap reached"
    assert finished.stats["google_places"]["requests"] == 4


def test_free_sources_never_count_against_the_cap(client, admin_user, auth_headers, world, db_session):
    run = make_run(client, admin_user, auth_headers, payload(world, [city(db_session, "lahore")], max_paid_requests=1))
    finished = service.execute_run(db_session, run["id"], source_builder=builder(osm=FakeSource("osm", [raw(1)], requests_per_search=5)))
    assert finished.paid_requests_used == 0 and finished.tasks_done == osm_dealer_terms(world)


def test_both_sources_merge_into_one_lead(client, admin_user, auth_headers, world, db_session):
    enable_places(db_session)
    run = make_run(client, admin_user, auth_headers, payload(
        world, [city(db_session, "lahore")], source_keys=["osm", "google_places"], segment_slugs=["dealer"],
    ))
    osm = FakeSource("osm", [raw(1, name="Al Noor Solar", phones=["0300 4438424"], latitude=31.5204, longitude=74.3587)])
    places = FakeSource("google_places", [raw(
        7, source="google_places", name="Al-Noor Solar", phones=["+92 300 4438424"], website="https://alnoor.pk",
        latitude=31.5205, longitude=74.3588, rating=4.7, review_count=30,
    )])

    finished = service.execute_run(db_session, run["id"], source_builder=builder(osm=osm, google_places=places))

    assert db_session.query(Business).count() == 1
    business = db_session.query(Business).one()
    assert business.website == "https://alnoor.pk" and business.review_count == 30
    # Quality per source is what lets the admin decide whether the paid one is worth it.
    assert finished.stats["osm"]["with_website"] == 0
    assert finished.stats["google_places"]["with_website"] == dealer_terms(world)
    # OpenStreetMap ran first and created the lead; every Places result was that same business.
    assert finished.stats["osm"]["new"] == 1
    assert (finished.stats["google_places"]["new"], finished.stats["google_places"]["merged"]) == (0, dealer_terms(world))


# ---- cancel / resume / recovery ------------------------------------------------------------------

def test_cancelling_a_queued_run(client, admin_user, auth_headers, world, db_session):
    headers = auth_headers(admin_user)
    run = make_run(client, admin_user, auth_headers, payload(world, [city(db_session, "lahore")]))

    response = client.post(f"/api/v1/runs/{run['id']}/cancel", headers=headers)

    assert response.status_code == 200 and response.json()["status"] == "cancelled"
    assert response.json()["tasks_skipped"] == run["tasks_total"]
    source = FakeSource("osm", [raw(1)])
    service.execute_run(db_session, run["id"], source_builder=builder(osm=source))     # the worker still dequeues it
    assert source.calls == []
    assert client.post(f"/api/v1/runs/{run['id']}/cancel", headers=headers).status_code == 409


def test_cancelling_a_running_run_stops_between_searches(client, admin_user, auth_headers, world, db_session):
    headers = auth_headers(admin_user)
    run = make_run(client, admin_user, auth_headers, payload(world, [city(db_session, "lahore")]))

    def cancel_after_first_search(query):
        if not getattr(cancel_after_first_search, "done", False):
            cancel_after_first_search.done = True
            assert client.post(f"/api/v1/runs/{run['id']}/cancel", headers=headers).json()["status"] == "cancelling"

    source = FakeSource("osm", [raw(1)], on_search=cancel_after_first_search)
    finished = service.execute_run(db_session, run["id"], source_builder=builder(osm=source))

    assert finished.status == "cancelled" and len(source.calls) == 1
    assert finished.tasks_done == 1 and finished.tasks_skipped == run["tasks_total"] - 1
    assert db_session.query(RunTask).filter_by(run_id=finished.id, status="pending").count() == 0
    assert db_session.query(Business).count() == 1                     # what was found before cancelling is kept


def test_interrupted_run_is_recovered_and_can_be_resumed(client, admin_user, auth_headers, world, db_session):
    headers = auth_headers(admin_user)
    lahore = city(db_session, "lahore")
    interrupted = make_run(client, admin_user, auth_headers, payload(world, [lahore]))
    waiting = make_run(client, admin_user, auth_headers, payload(world, [lahore], source_keys=["osm"], segment_slugs=["contractor"]))

    # Simulate a crash: the first run was mid-flight with one search finished and one in progress.
    tasks = db_session.query(RunTask).filter_by(run_id=interrupted["id"]).order_by(RunTask.id).all()
    tasks[0].status, tasks[1].status = "done", "running"
    db_session.query(Run).filter(Run.id == interrupted["id"]).update({"status": "running", "tasks_done": 1})
    db_session.commit()

    still_queued = service.recover_interrupted_runs(db_session)

    assert still_queued == [waiting["id"]]
    run = db_session.get(Run, interrupted["id"])
    assert run.status == "failed" and "restart" in run.error
    assert [t.status for t in db_session.query(RunTask).filter_by(run_id=run.id).order_by(RunTask.id)][:2] == ["done", "pending"]

    resumed = client.post(f"/api/v1/runs/{interrupted['id']}/resume", headers=headers)
    assert resumed.status_code == 200 and resumed.json()["status"] == "queued" and resumed.json()["error"] is None

    source = FakeSource("osm", [raw(1)])
    finished = service.execute_run(db_session, interrupted["id"], source_builder=builder(osm=source))
    assert finished.status == "completed"
    assert len(source.calls) == osm_dealer_terms(world) - 1            # the finished search was not repeated


def test_only_interrupted_runs_with_work_left_can_be_resumed(client, admin_user, auth_headers, world, db_session):
    headers = auth_headers(admin_user)
    run = make_run(client, admin_user, auth_headers, payload(world, [city(db_session, "lahore")]))
    assert client.post(f"/api/v1/runs/{run['id']}/resume", headers=headers).status_code == 409     # still queued
    service.execute_run(db_session, run["id"], source_builder=builder(osm=FakeSource("osm", [raw(1)])))
    assert client.post(f"/api/v1/runs/{run['id']}/resume", headers=headers).status_code == 409     # completed
    assert client.post("/api/v1/runs/9999/resume", headers=headers).status_code == 404


def test_execute_run_ignores_runs_that_are_not_queued(client, admin_user, auth_headers, world, db_session):
    run = make_run(client, admin_user, auth_headers, payload(world, [city(db_session, "lahore")]))
    source = FakeSource("osm", [raw(1)])
    service.execute_run(db_session, run["id"], source_builder=builder(osm=source))
    calls = len(source.calls)

    again = service.execute_run(db_session, run["id"], source_builder=builder(osm=source))
    assert len(source.calls) == calls and again.status == "completed"
    assert service.execute_run(db_session, 9999) is None


def test_history_survives_deleting_the_profile_and_locations(client, admin_user, auth_headers, world, db_session):
    headers = auth_headers(admin_user)
    lahore = city(db_session, "lahore")
    profile_id, profile_name, lahore_id = world.id, world.name, lahore.id      # the objects are gone after the deletes
    run = make_run(client, admin_user, auth_headers, payload(world, [lahore]))
    service.execute_run(db_session, run["id"], source_builder=builder(osm=FakeSource("osm", [raw(1)])))

    assert client.delete(f"/api/v1/profiles/{profile_id}", headers=headers).status_code == 204
    assert client.delete(f"/api/v1/geographies/{lahore_id}", headers=headers).status_code == 204

    body = client.get(f"/api/v1/runs/{run['id']}", headers=headers).json()
    assert body["profile_id"] is None and body["profile_name"] == profile_name and body["status"] == "completed"
    tasks = client.get(f"/api/v1/runs/{run['id']}/tasks", headers=headers).json()["data"]
    assert {t["geography_name"] for t in tasks} == {"Lahore"} and all(t["geography_id"] is None for t in tasks)
    # The business found stays too, just no longer tied to a deleted city.
    assert db_session.query(Business).one().geography_id is None


def test_run_whose_profile_disappeared_fails_cleanly(client, admin_user, auth_headers, world, db_session):
    run = make_run(client, admin_user, auth_headers, payload(world, [city(db_session, "lahore")]))
    client.delete(f"/api/v1/profiles/{world.id}", headers=auth_headers(admin_user))
    finished = service.execute_run(db_session, run["id"], source_builder=builder(osm=FakeSource("osm", [raw(1)])))
    assert finished.status == "failed" and "profile" in finished.error


def test_run_fails_cleanly_if_a_source_lost_its_key_after_queueing(client, admin_user, auth_headers, world, db_session):
    run = make_run(client, admin_user, auth_headers, payload(world, [city(db_session, "lahore")]))

    def broken_builder(db, keys):
        raise ValueError("Google Places needs an API key")

    finished = service.execute_run(db_session, run["id"], source_builder=broken_builder)
    assert finished.status == "failed" and "API key" in finished.error


# ---- listing --------------------------------------------------------------------------------------

def test_list_runs_and_tasks_with_filters_and_pagination(client, admin_user, auth_headers, world, db_session):
    headers = auth_headers(admin_user)
    lahore = city(db_session, "lahore")
    first = make_run(client, admin_user, auth_headers, payload(world, [lahore]))
    second = make_run(client, admin_user, auth_headers, payload(world, [lahore], segment_slugs=["contractor"]))
    client.post(f"/api/v1/runs/{first['id']}/cancel", headers=headers)

    listing = client.get("/api/v1/runs/", headers=headers).json()
    assert listing["count"] == 2 and [r["id"] for r in listing["data"]] == [second["id"], first["id"]]      # newest first
    assert [r["id"] for r in client.get("/api/v1/runs/?status=cancelled", headers=headers).json()["data"]] == [first["id"]]
    assert client.get("/api/v1/runs/?limit=1&page=2", headers=headers).json()["data"][0]["id"] == first["id"]

    skipped = client.get(f"/api/v1/runs/{first['id']}/tasks?status=skipped&limit=1", headers=headers).json()
    assert skipped["count"] == first["tasks_total"] and len(skipped["data"]) == 1
    assert client.get("/api/v1/runs/9999", headers=headers).status_code == 404
    assert client.get("/api/v1/runs/9999/tasks", headers=headers).status_code == 404


# ---- website enrichment -----------------------------------------------------------------------------

def enrichment_run(client, admin_user, auth_headers, world, db_session, **overrides):
    return make_run(client, admin_user, auth_headers, payload(
        world, [city(db_session, "lahore")], segment_slugs=["contractor"], enrich_websites=True, **overrides,
    ))


def test_enrichment_adds_contacts_from_websites_and_is_not_repeated(client, admin_user, auth_headers, world, db_session):
    run = enrichment_run(client, admin_user, auth_headers, world, db_session)
    source = FakeSource("osm", [
        raw(1, name="Noor Electrical Contractors", phones=["042 3577 1769"], website="https://noor.pk"),
        raw(2, name="Bilal Engineering", website="https://bilal.pk"),
        raw(3, name="No Website Traders"),
    ])
    enricher = FakeEnricher({
        "https://noor.pk": WebsiteContacts(
            emails=["sales@noor.pk"], phones=[PhoneInfo("+923004438424", True)], whatsapp=["+923014962026"],
            facebook="https://facebook.com/noor",
        ),
        "https://bilal.pk": WebsiteContacts(blocked_by_robots=True),
    })

    finished = service.execute_run(db_session, run["id"], source_builder=builder(osm=source), enricher_factory=lambda: enricher)

    assert sorted(enricher.urls) == ["https://bilal.pk", "https://noor.pk"]
    assert (finished.enrich_total, finished.enrich_done, finished.status) == (2, 2, "completed")
    stats = finished.stats["website_enrichment"]
    assert stats == {"visited": 2, "with_email": 1, "with_whatsapp": 1, "with_social": 1, "blocked_by_robots": 1, "failed": 0}

    noor = db_session.query(Business).filter_by(name="Noor Electrical Contractors").one()
    kinds = {(c.kind, c.value, c.source_key) for c in db_session.query(ContactPoint).filter_by(business_id=noor.id)}
    assert ("email", "sales@noor.pk", "website_enrichment") in kinds
    assert ("whatsapp", "+923014962026", "website_enrichment") in kinds
    assert ("phone", "+924235771769", "osm") in kinds
    assert noor.enriched_at is not None

    # A later run finds the same shops but doesn't fetch their sites again.
    again = make_run(client, admin_user, auth_headers, payload(
        world, [city(db_session, "lahore")], segment_slugs=["contractor"], enrich_websites=True, refresh=True,
    ))
    second_enricher = FakeEnricher()
    done = service.execute_run(db_session, again["id"], source_builder=builder(osm=source), enricher_factory=lambda: second_enricher)
    assert second_enricher.urls == [] and done.enrich_total == 0


def test_enrichment_failures_are_counted_but_do_not_fail_the_run(client, admin_user, auth_headers, world, db_session):
    run = enrichment_run(client, admin_user, auth_headers, world, db_session)
    source = FakeSource("osm", [raw(1, website="https://dead.pk"), raw(2, website="https://also-dead.pk")])

    finished = service.execute_run(
        db_session, run["id"], source_builder=builder(osm=source),
        enricher_factory=lambda: FakeEnricher(error=EnrichmentError("HTTP 404")),
    )

    assert finished.status == "completed" and finished.enrich_done == 2
    assert finished.stats["website_enrichment"]["failed"] == 2
    # Stamped anyway so dead sites aren't hammered on every run.
    assert all(b.enriched_at is not None for b in db_session.query(Business))


def test_enrichment_is_skipped_when_off_for_the_run_or_switched_off_globally(client, admin_user, auth_headers, world, db_session):
    source = FakeSource("osm", [raw(1, website="https://noor.pk")])

    off_for_run = make_run(client, admin_user, auth_headers, payload(world, [city(db_session, "lahore")], segment_slugs=["contractor"], enrich_websites=False))
    enricher = FakeEnricher()
    finished = service.execute_run(db_session, off_for_run["id"], source_builder=builder(osm=source), enricher_factory=lambda: enricher)
    assert enricher.urls == [] and "website_enrichment" not in finished.stats

    sources_service.update_source(db_session, "website_enrichment", SourceUpdate(is_enabled=False))
    off_globally = enrichment_run(client, admin_user, auth_headers, world, db_session, refresh=True)
    enricher = FakeEnricher()
    service.execute_run(db_session, off_globally["id"], source_builder=builder(osm=source), enricher_factory=lambda: enricher)
    assert enricher.urls == []


def test_cancelling_during_enrichment_stops_processing(client, admin_user, auth_headers, world, db_session, monkeypatch):
    run = enrichment_run(client, admin_user, auth_headers, world, db_session)
    source = FakeSource("osm", [raw(n, website=f"https://shop{n}.pk") for n in range(1, 9)])
    real_as_completed = service.as_completed

    def cancel_after_first_result(futures):
        # The generator body runs on the main thread, so the shared session is touched safely.
        for index, future in enumerate(real_as_completed(futures)):
            if index == 1:
                db_session.query(Run).filter(Run.id == run["id"]).update({"status": "cancelling"})
            yield future

    monkeypatch.setattr(service, "as_completed", cancel_after_first_result)
    finished = service.execute_run(
        db_session, run["id"], source_builder=builder(osm=source), enricher_factory=lambda: FakeEnricher(),
    )

    assert finished.status == "cancelled"
    assert finished.enrich_total == 8 and finished.enrich_done == 1


# ---- worker -----------------------------------------------------------------------------------------

def test_worker_runs_queued_ids_in_order_on_its_own_thread_and_survives_errors():
    done = threading.Event()
    seen, threads = [], set()

    def executor(run_id):
        seen.append(run_id)
        threads.add(threading.current_thread().name)
        if run_id == 1:
            raise RuntimeError("crash")
        if run_id == 3:
            done.set()

    worker = RunWorker()
    worker.start(executor)
    try:
        for run_id in (1, 2, 3):
            worker.enqueue(run_id)
        assert done.wait(5)
    finally:
        worker.stop()

    assert seen == [1, 2, 3]                                   # a crash on 1 didn't stop 2 and 3
    assert threads == {"run-worker"} and not worker.is_running


def test_worker_start_is_idempotent_and_stoppable():
    worker = RunWorker()
    worker.start(lambda run_id: None)
    thread = worker._thread
    worker.start(lambda run_id: None)
    assert worker._thread is thread and worker.is_running
    worker.stop()
    assert not worker.is_running
