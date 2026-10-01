from datetime import UTC, datetime, timedelta

import pytest

from app.features.businesses.models import ContactKind, ContactPoint, SourceRecord
from app.features.geographies.models import Geography
from app.features.insights.models import BusinessSnapshot
from app.features.runs.models import Run, RunTask, TaskStatus

BASE = "/api/v1/insights"


def days_ago(days: float) -> datetime:
    return datetime.now(UTC) - timedelta(days=days)


@pytest.fixture()
def headers(sales_user, auth_headers):
    return auth_headers(sales_user)


@pytest.fixture()
def make_run(db_session, seeded_profile):
    def _make() -> Run:
        run = Run(profile_id=seeded_profile.id, profile_name=seeded_profile.name, source_keys=["osm"], status="completed")
        db_session.add(run)
        db_session.commit()
        return run

    return _make


@pytest.fixture()
def leads(make_business):
    return {
        "noor": make_business("Al Noor Solar Dealer", hint="dealer", phones=["0300 4438424"], emails=["info@alnoor.pk"],
                              website="https://alnoor.pk", now=days_ago(3)),
        "bilal": make_business("Bilal Wholesale Traders", hint="wholesaler", phones=["0301 1112223"], now=days_ago(20)),
        "zahid": make_business("Zahid Battery House", hint="dealer", phones=["042 3577 9999"], now=days_ago(60)),
        "karachi": make_business("Karachi Inverter Center", city="karachi", hint="retailer", phones=["0333 7654321"], now=days_ago(1)),
        "quetta": make_business("Quetta Solar Works", city="quetta", hint="installer", emails=["hello@quettasolar.pk"], now=days_ago(200)),
    }


def city_row(body, name):
    return next(city for city in body["cities"] if city["city"] == name)


# ---- access ----------------------------------------------------------------------------------------

def test_insights_need_a_login(client):
    for path in ("overview", "coverage?profile_id=1", "gaps?profile_id=1", "timeline", "sources", "movers"):
        assert client.get(f"{BASE}/{path}").status_code == 401, path


def test_sales_can_view_insights(client, leads, headers, seeded_profile):
    for path in ("overview", f"coverage?profile_id={seeded_profile.id}", "timeline", "sources", "movers"):
        assert client.get(f"{BASE}/{path}", headers=headers).status_code == 200, path


# ---- overview -------------------------------------------------------------------------------------------

def test_overview_counts(client, leads, headers, admin_user, auth_headers):
    client.patch(f"/api/v1/businesses/{leads['noor'].id}", headers=auth_headers(admin_user), json={"lead_status": "contacted"})

    body = client.get(f"{BASE}/overview", headers=headers).json()

    assert body["total"] == 5
    assert body["with_phone"] == 4          # quetta has only an email
    assert body["whatsapp_likely"] == 3     # three mobile numbers; zahid's is a landline
    assert body["with_email"] == 2
    assert body["with_website"] == 1
    assert body["new_last_7_days"] == 2     # noor (3 days ago) and karachi (1 day ago)
    assert body["new_last_30_days"] == 3    # + bilal
    assert body["by_status"] == {"new": 4, "contacted": 1}


def test_overview_can_be_limited_to_a_profile(client, leads, headers, seeded_profile):
    assert client.get(f"{BASE}/overview?profile_id={seeded_profile.id}", headers=headers).json()["total"] == 5
    assert client.get(f"{BASE}/overview?profile_id=99999", headers=headers).json()["total"] == 0


def test_someone_on_do_not_contact_is_in_no_number(client, leads, headers, admin_user, auth_headers, seeded_profile):
    client.post(f"/api/v1/businesses/{leads['noor'].id}/do-not-contact", headers=auth_headers(admin_user), json={})

    overview = client.get(f"{BASE}/overview", headers=headers).json()
    coverage = client.get(f"{BASE}/coverage?profile_id={seeded_profile.id}", headers=headers).json()

    assert overview["total"] == 4 and overview["with_website"] == 0
    assert sum(city["total"] for city in coverage["cities"]) == 4


def test_overview_of_an_empty_database(client, headers):
    body = client.get(f"{BASE}/overview", headers=headers).json()
    assert body["total"] == 0 and body["by_status"] == {}


# ---- coverage ------------------------------------------------------------------------------------------------

def test_coverage_is_a_city_by_segment_matrix(client, leads, headers, seeded_profile):
    body = client.get(f"{BASE}/coverage?profile_id={seeded_profile.id}", headers=headers).json()

    assert {s["slug"] for s in body["segments"]} == {"importer", "wholesaler", "dealer", "retailer", "installer", "contractor"}
    lahore = city_row(body, "Lahore")
    assert lahore["province"] == "Punjab" and lahore["total"] == 3
    assert lahore["counts"] == {"dealer": 2, "wholesaler": 1}
    assert city_row(body, "Karachi")["counts"] == {"retailer": 1}
    assert city_row(body, "Quetta")["counts"] == {"installer": 1}


def test_coverage_lists_every_target_city_even_with_no_leads(client, leads, headers, seeded_profile, db_session):
    body = client.get(f"{BASE}/coverage?profile_id={seeded_profile.id}", headers=headers).json()
    assert len(body["cities"]) == db_session.query(Geography).filter_by(level="city").count()
    assert city_row(body, "Multan")["total"] == 0 and city_row(body, "Multan")["counts"] == {}


def test_coverage_adds_up_to_the_overview_total(client, leads, headers, seeded_profile):
    coverage = client.get(f"{BASE}/coverage?profile_id={seeded_profile.id}", headers=headers).json()
    overview = client.get(f"{BASE}/overview?profile_id={seeded_profile.id}", headers=headers).json()
    assert sum(c["total"] for c in coverage["cities"]) + coverage["unplaced"] == overview["total"]


def test_leads_with_no_city_are_counted_as_unplaced(client, leads, headers, seeded_profile, db_session):
    leads["noor"].geography_id = None
    db_session.commit()
    body = client.get(f"{BASE}/coverage?profile_id={seeded_profile.id}", headers=headers).json()
    assert body["unplaced"] == 1


def test_coverage_needs_a_real_profile(client, headers):
    assert client.get(f"{BASE}/coverage", headers=headers).status_code == 422
    assert client.get(f"{BASE}/coverage?profile_id=99999", headers=headers).status_code == 404


# ---- gaps --------------------------------------------------------------------------------------------------------

def add_search(db_session, run, city_name, status=TaskStatus.DONE.value, finished=None):
    city = db_session.query(Geography).filter_by(name=city_name).one()
    db_session.add(RunTask(
        run_id=run.id, source_key="osm", geography_id=city.id, geography_name=city.name, term_text="solar", term_language="en",
        segment_slug="dealer", status=status, finished_at=finished or datetime.now(UTC),
    ))
    db_session.commit()


def test_gaps_separate_places_never_searched_from_places_searched_with_little_found(
    client, leads, headers, seeded_profile, db_session, make_run
):
    run = make_run()
    add_search(db_session, run, "Karachi")
    add_search(db_session, run, "Quetta", status=TaskStatus.FAILED.value)   # a failed search doesn't count as looking

    body = client.get(f"{BASE}/gaps?profile_id={seeded_profile.id}&threshold=2", headers=headers).json()
    by_city = {gap["city"]: gap for gap in body["data"]}

    assert "Lahore" not in by_city                                   # 3 leads, above the threshold
    assert by_city["Karachi"]["reason"] == "few_found" and by_city["Karachi"]["searches_done"] == 1
    assert by_city["Karachi"]["last_searched_at"] is not None
    assert by_city["Quetta"]["reason"] == "never_searched"
    assert by_city["Multan"]["reason"] == "never_searched" and by_city["Multan"]["total"] == 0
    assert body["count"] == len(body["data"]) and body["threshold"] == 2


def test_gaps_list_unsearched_cities_first_then_the_emptiest(client, leads, headers, seeded_profile, db_session, make_run):
    add_search(db_session, make_run(), "Multan")
    body = client.get(f"{BASE}/gaps?profile_id={seeded_profile.id}&threshold=5", headers=headers).json()

    reasons = [gap["reason"] for gap in body["data"]]
    assert reasons == sorted(reasons, key=lambda r: r != "never_searched")
    unsearched = [g for g in body["data"] if g["reason"] == "never_searched"]
    assert [g["total"] for g in unsearched] == sorted(g["total"] for g in unsearched)
    assert body["data"][-1]["city"] == "Multan"                      # searched, found nothing: after the unsearched ones


def test_gaps_name_the_segments_with_nothing(client, leads, headers, seeded_profile):
    body = client.get(f"{BASE}/gaps?profile_id={seeded_profile.id}&threshold=5", headers=headers).json()
    karachi = next(gap for gap in body["data"] if gap["city"] == "Karachi")
    assert "Retailer" not in karachi["missing_segments"]
    assert "Dealer" in karachi["missing_segments"] and "Installer" in karachi["missing_segments"]


def test_gaps_threshold_is_validated(client, headers, seeded_profile):
    assert client.get(f"{BASE}/gaps?profile_id={seeded_profile.id}&threshold=0", headers=headers).status_code == 422


# ---- timeline ----------------------------------------------------------------------------------------------------

def test_timeline_by_week_counts_new_leads_and_keeps_a_running_total(client, leads, headers):
    body = client.get(f"{BASE}/timeline?days=90&bucket=week", headers=headers).json()
    points = body["data"]

    assert body["bucket"] == "week"
    assert sum(p["new"] for p in points) == 4                        # quetta (200 days ago) is before the chart starts
    assert points[0]["total"] >= 1                                   # ...but is already in the running total
    assert points[-1]["total"] == 5
    assert [p["total"] for p in points] == sorted(p["total"] for p in points)
    periods = [p["period"] for p in points]
    assert periods == sorted(set(periods))                           # no gaps or repeats, oldest first


def test_timeline_fills_quiet_periods_with_zero(client, leads, headers):
    points = client.get(f"{BASE}/timeline?days=90&bucket=week", headers=headers).json()["data"]
    assert any(p["new"] == 0 for p in points)
    assert len(points) >= 12


def test_timeline_buckets(client, leads, headers):
    daily = client.get(f"{BASE}/timeline?days=30&bucket=day", headers=headers).json()["data"]
    monthly = client.get(f"{BASE}/timeline?days=200&bucket=month", headers=headers).json()["data"]
    assert len(daily) in (31, 32)
    assert all(p["period"].endswith("-01") for p in monthly)
    assert monthly[-1]["total"] == 5


def test_timeline_input_is_validated(client, headers):
    assert client.get(f"{BASE}/timeline?days=1", headers=headers).status_code == 422
    assert client.get(f"{BASE}/timeline?bucket=year", headers=headers).status_code == 422


# ---- sources -----------------------------------------------------------------------------------------------------------

@pytest.fixture()
def two_sources(make_business, db_session):
    osm_only = make_business("Osm Only Traders", phones=["0300 1111111"], source="osm", website="https://osmonly.pk")
    places_only = make_business("Places Only Traders", phones=["0301 2222222"], emails=["a@places.pk"], source="google_places")
    both = make_business("Shared Solar", phones=["0302 3333333"], source="osm")
    db_session.add(SourceRecord(business_id=both.id, source_key="google_places", external_id="gp/shared", fetched_at=datetime.now(UTC)))
    db_session.add(ContactPoint(business_id=osm_only.id, kind=ContactKind.EMAIL.value, value="hi@osmonly.pk", source_key="website_enrichment"))
    db_session.commit()
    return {"osm_only": osm_only, "places_only": places_only, "both": both}


def by_key(body):
    return {row["key"]: row for row in body["data"]}


def test_source_quality_compares_what_each_source_delivered(client, two_sources, headers):
    rows = by_key(client.get(f"{BASE}/sources", headers=headers).json())

    assert rows["osm"]["found"] == 2 and rows["osm"]["exclusive"] == 1        # "Shared Solar" was found by both
    assert rows["google_places"]["found"] == 2 and rows["google_places"]["exclusive"] == 1
    assert rows["osm"]["with_phone"] == 2 and rows["osm"]["with_whatsapp"] == 2
    assert rows["google_places"]["with_phone"] == 1 and rows["google_places"]["with_email"] == 1
    assert rows["osm"]["with_website"] == 1 and rows["google_places"]["with_website"] == 0


def test_website_reading_is_credited_with_the_contacts_it_added(client, two_sources, headers):
    row = by_key(client.get(f"{BASE}/sources", headers=headers).json())["website_enrichment"]
    assert row["kind"] == "enrichment" and row["found"] == 1 and row["with_email"] == 1 and row["exclusive"] is None


def test_paid_source_shows_what_it_cost_and_the_free_one_shows_none(client, two_sources, headers, db_session, make_run):
    run = make_run()
    db_session.add(RunTask(run_id=run.id, source_key="google_places", geography_name="Lahore", term_text="solar", term_language="en",
                           segment_slug="dealer", status="done", requests_made=100))
    db_session.commit()

    rows = by_key(client.get(f"{BASE}/sources", headers=headers).json())

    assert rows["google_places"]["requests"] == 100
    assert rows["google_places"]["estimated_cost_usd"] == 3.5                 # 100 x $0.035
    assert rows["google_places"]["cost_per_lead_usd"] == round(3.5 / 2, 3)
    assert rows["osm"]["estimated_cost_usd"] is None and rows["osm"]["cost_per_lead_usd"] is None


def test_a_source_that_was_never_used_is_left_out(client, make_business, headers):
    make_business("Only Osm", phones=["0300 9999999"], source="osm")
    assert list(by_key(client.get(f"{BASE}/sources", headers=headers).json())) == ["osm"]


def test_source_quality_leaves_out_do_not_contact(client, two_sources, headers, admin_user, auth_headers):
    client.post(f"/api/v1/businesses/{two_sources['places_only'].id}/do-not-contact", headers=auth_headers(admin_user), json={})
    rows = by_key(client.get(f"{BASE}/sources", headers=headers).json())
    assert rows["google_places"]["found"] == 1 and rows["google_places"]["with_email"] == 0


# ---- movers -----------------------------------------------------------------------------------------------------------------

def snapshot(db_session, business, run, days, reviews, rating=4.0):
    db_session.add(BusinessSnapshot(business_id=business.id, run_id=run.id, seen_at=days_ago(days), rating=rating, review_count=reviews))
    db_session.commit()


def test_movers_are_ranked_by_review_growth(client, leads, headers, db_session, make_run):
    first, second = make_run(), make_run()
    snapshot(db_session, leads["noor"], first, 20, 10)
    snapshot(db_session, leads["noor"], second, 2, 40, rating=4.7)
    snapshot(db_session, leads["bilal"], first, 20, 5)
    snapshot(db_session, leads["bilal"], second, 2, 8)

    body = client.get(f"{BASE}/movers?days=30", headers=headers).json()

    assert [m["name"] for m in body["data"]] == ["Al Noor Solar Dealer", "Bilal Wholesale Traders"]
    top = body["data"][0]
    assert (top["review_change"], top["review_count"], top["rating"], top["city"]) == (30, 40, 4.7, "Lahore")


def test_movers_ignore_businesses_that_did_not_grow_or_were_seen_once(client, leads, headers, db_session, make_run):
    first, second = make_run(), make_run()
    snapshot(db_session, leads["noor"], first, 20, 30)
    snapshot(db_session, leads["noor"], second, 2, 30)         # unchanged
    snapshot(db_session, leads["bilal"], first, 20, 50)
    snapshot(db_session, leads["bilal"], second, 2, 40)        # fewer reviews now
    snapshot(db_session, leads["zahid"], second, 2, 99)        # only seen once

    assert client.get(f"{BASE}/movers", headers=headers).json()["data"] == []


def test_movers_compare_with_the_previous_search_however_long_ago_it_was(client, leads, headers, db_session, make_run):
    first, second = make_run(), make_run()
    snapshot(db_session, leads["noor"], first, 90, 1)
    snapshot(db_session, leads["noor"], second, 2, 200)

    row = client.get(f"{BASE}/movers?days=30", headers=headers).json()["data"][0]

    assert row["review_change"] == 199
    assert row["previous_seen_at"] < row["latest_seen_at"]


def test_movers_only_include_businesses_seen_recently(client, leads, headers, db_session, make_run):
    first, second = make_run(), make_run()
    snapshot(db_session, leads["noor"], first, 120, 5)
    snapshot(db_session, leads["noor"], second, 90, 50)        # grew, but the last look was long ago

    assert client.get(f"{BASE}/movers?days=30", headers=headers).json()["data"] == []
    assert len(client.get(f"{BASE}/movers?days=120", headers=headers).json()["data"]) == 1


def test_movers_measure_the_latest_change_not_the_total(client, leads, headers, db_session, make_run):
    runs = [make_run(), make_run(), make_run()]
    snapshot(db_session, leads["noor"], runs[0], 60, 10)
    snapshot(db_session, leads["noor"], runs[1], 30, 40)
    snapshot(db_session, leads["noor"], runs[2], 2, 45)

    assert client.get(f"{BASE}/movers", headers=headers).json()["data"][0]["review_change"] == 5


def test_movers_respect_the_limit_and_do_not_contact(client, leads, headers, db_session, make_run, admin_user, auth_headers):
    first, second = make_run(), make_run()
    for index, key in enumerate(("noor", "bilal", "zahid")):
        snapshot(db_session, leads[key], first, 20, 10)
        snapshot(db_session, leads[key], second, 2, 20 + index)

    assert len(client.get(f"{BASE}/movers?limit=2", headers=headers).json()["data"]) == 2

    client.post(f"/api/v1/businesses/{leads['zahid'].id}/do-not-contact", headers=auth_headers(admin_user), json={})
    names = [m["name"] for m in client.get(f"{BASE}/movers", headers=headers).json()["data"]]
    assert "Zahid Battery House" not in names and len(names) == 2


# ---- recording snapshots during a run ---------------------------------------------------------------------------------------

@pytest.fixture()
def ingest(db_session, seeded_profile):
    from app.core.scouting.types import RawBusiness
    from app.features.businesses.ingest import IngestContext, ingest_business
    from app.features.runs.service import _profile_scoring

    scoring = _profile_scoring(seeded_profile)
    lahore = db_session.query(Geography).filter_by(slug="lahore").one()

    def _ingest(run, *, rating=4.5, reviews=12, when=None):
        raw = RawBusiness(source_key="google_places", external_id="gp/1", name="Snapshot Solar", latitude=31.5, longitude=74.3,
                          phones=["0300 5555555"], rating=rating, review_count=reviews)
        context = IngestContext(run_id=run.id if run else None, geography_id=lahore.id, hint_segment_slug="dealer",
                                now=when or datetime.now(UTC), profile=scoring)
        outcome = ingest_business(db_session, raw, context)
        db_session.commit()
        return outcome.business

    return _ingest


def test_each_run_records_one_snapshot_per_business(ingest, db_session, make_run):
    first, second = make_run(), make_run()
    business = ingest(first, reviews=10)
    ingest(first, reviews=11)                      # seen twice in the same run: still one row
    ingest(second, reviews=25)

    rows = db_session.query(BusinessSnapshot).filter_by(business_id=business.id).order_by(BusinessSnapshot.id).all()
    assert [(row.run_id, row.review_count) for row in rows] == [(first.id, 11), (second.id, 25)]


def test_no_snapshot_when_ingesting_outside_a_run(ingest, db_session):
    ingest(None)
    assert db_session.query(BusinessSnapshot).count() == 0


def test_no_snapshot_for_a_business_with_no_rating_or_reviews(ingest, db_session, make_run):
    ingest(make_run(), rating=None, reviews=None)
    assert db_session.query(BusinessSnapshot).count() == 0


def test_snapshots_go_when_the_business_goes(ingest, db_session, make_run):
    business = ingest(make_run())
    assert db_session.query(BusinessSnapshot).count() == 1
    db_session.delete(business)
    db_session.commit()
    assert db_session.query(BusinessSnapshot).count() == 0
