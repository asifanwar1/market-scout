import pytest

from app.features.businesses.models import Business, SourceRecord

LEADS = "/api/v1/businesses"
INSIGHTS = "/api/v1/insights"


@pytest.fixture()
def admin(admin_user, auth_headers):
    return auth_headers(admin_user)


def move(client, headers, lead, *steps):
    for step in steps:
        status, outcome = step if isinstance(step, tuple) else (step, None)
        body = {"lead_status": status, **({"outcome": outcome} if outcome else {})}
        assert client.patch(f"{LEADS}/{lead.id}", headers=headers, json=body).status_code == 200


@pytest.fixture()
def funnel(client, make_business, admin):
    leads = {
        "fresh": make_business("Fresh Solar", phones=["0300 1000001"]),
        "talking": make_business("Talking Solar", phones=["0300 1000002"], source="google_places"),
        "won_slowly": make_business("Won Slowly", phones=["0300 1000003"], hint="wholesaler"),
        "lost_late": make_business("Lost Late", phones=["0300 1000004"], source="google_places", city="karachi"),
        "won_fast": make_business("Won Fast", phones=["0300 1000005"], city="karachi"),
        "untouched": make_business("Untouched Solar", phones=["0300 1000006"]),
    }
    move(client, admin, leads["talking"], "contacted")
    move(client, admin, leads["won_slowly"], "contacted", "interested", "quoted", ("customer", {"value": 1000, "product": "Quote Pro"}))
    move(client, admin, leads["lost_late"], "contacted", "interested", ("not_interested", {"loss_reason": "price"}))
    move(client, admin, leads["won_fast"], ("customer", {"value": 3000}))
    return leads


def pipeline(client, headers, **params):
    return client.get(f"{INSIGHTS}/pipeline", headers=headers, params=params).json()


def conversion(client, headers, group_by, **params):
    response = client.get(f"{INSIGHTS}/conversion", headers=headers, params={"group_by": group_by, **params})
    assert response.status_code == 200, response.text
    return {row["key"]: row for row in response.json()["data"]}


def test_the_funnel_counts_where_leads_are_and_how_far_they_got(client, funnel, admin):
    body = pipeline(client, admin)
    stages = {stage["status"]: stage for stage in body["stages"]}

    assert body["total"] == 6 and body["won"] == 2 and body["lost"] == 1 and body["open"] == 3
    assert [stage["status"] for stage in body["stages"]] == ["new", "contacted", "interested", "meeting", "quoted", "customer"]
    assert {name: stage["current"] for name, stage in stages.items()} == {
        "new": 2, "contacted": 1, "interested": 0, "meeting": 0, "quoted": 0, "customer": 2,
    }
    assert {name: stage["reached"] for name, stage in stages.items()} == {
        "new": 6, "contacted": 4, "interested": 3, "meeting": 2, "quoted": 2, "customer": 2,
    }


def test_wins_revenue_and_losses_are_summed(client, funnel, admin):
    body = pipeline(client, admin)

    assert body["currency"] == "USD"
    assert body["revenue"] == 4000 and body["average_deal"] == 2000
    assert body["win_rate"] == pytest.approx(0.667, abs=0.001)
    assert body["loss_reasons"] == [{"reason": "price", "count": 1}]


def test_an_empty_pipeline_has_no_rates(client, admin):
    body = pipeline(client, admin)

    assert body["total"] == 0 and body["win_rate"] is None and body["average_deal"] is None and body["revenue"] == 0
    assert all(stage["current"] == stage["reached"] == 0 for stage in body["stages"])


def test_a_lost_lead_with_no_recorded_history_counts_as_lost_but_not_as_contacted(client, make_business, admin, db_session):
    old = make_business("Old Lost")
    db_session.query(Business).filter(Business.id == old.id).update({"lead_status": "not_interested"})
    db_session.commit()

    body = pipeline(client, admin)

    assert body["lost"] == 1 and body["loss_reasons"] == [{"reason": None, "count": 1}]
    assert {s["status"]: s["reached"] for s in body["stages"]}["contacted"] == 0


def test_a_customer_with_no_recorded_history_counts_as_having_gone_through_every_stage(client, make_business, admin, db_session):
    old = make_business("Old Customer")
    db_session.query(Business).filter(Business.id == old.id).update({"lead_status": "customer"})
    db_session.commit()

    body = pipeline(client, admin)

    assert body["won"] == 1 and body["revenue"] == 0 and {s["status"]: s["reached"] for s in body["stages"]}["quoted"] == 1


def test_reopening_a_won_lead_takes_it_out_of_the_wins_but_keeps_how_far_it_got(client, funnel, admin):
    move(client, admin, funnel["won_slowly"], "interested")

    body = pipeline(client, admin)

    assert body["won"] == 1 and body["revenue"] == 3000
    assert {s["status"]: s["reached"] for s in body["stages"]}["quoted"] == 2


def test_do_not_contact_leads_are_left_out_of_the_pipeline(client, funnel, admin):
    client.post(f"{LEADS}/{funnel['won_fast'].id}/do-not-contact", headers=admin, json={})

    body = pipeline(client, admin)

    assert body["total"] == 5 and body["won"] == 1 and body["revenue"] == 1000


def test_the_pipeline_can_be_limited_to_a_profile(client, funnel, admin, seeded_profile):
    assert pipeline(client, admin, profile_id=seeded_profile.id)["total"] == 6
    assert pipeline(client, admin, profile_id=999999)["total"] == 0


def test_conversion_by_source_credits_every_source_that_reported_a_lead(client, funnel, admin):
    rows = conversion(client, admin, "source")

    assert rows["osm"]["leads"] == 4 and rows["osm"]["won"] == 2 and rows["osm"]["revenue"] == 4000
    assert rows["google_places"]["leads"] == 2 and rows["google_places"]["lost"] == 1 and rows["google_places"]["won"] == 0
    assert rows["google_places"]["name"] == "Google Places API"
    assert (rows["osm"]["contacted"], rows["osm"]["interested"], rows["osm"]["meeting"], rows["osm"]["quoted"]) == (2, 2, 2, 2)
    assert rows["osm"]["win_rate"] == 1.0 and rows["google_places"]["win_rate"] == 0.0


def test_a_lead_found_by_two_sources_counts_for_both(client, funnel, admin, db_session):
    from datetime import UTC, datetime

    db_session.add(SourceRecord(business_id=funnel["won_fast"].id, source_key="google_places", external_id="gp/extra", fetched_at=datetime.now(UTC)))
    db_session.commit()

    rows = conversion(client, admin, "source")

    assert rows["google_places"]["leads"] == 3 and rows["google_places"]["won"] == 1 and rows["google_places"]["revenue"] == 3000


def test_conversion_by_city(client, funnel, admin):
    rows = conversion(client, admin, "city")
    by_name = {row["name"]: row for row in rows.values()}

    assert by_name["Lahore"]["leads"] == 4 and by_name["Lahore"]["won"] == 1 and by_name["Lahore"]["revenue"] == 1000
    assert by_name["Karachi"]["leads"] == 2 and by_name["Karachi"]["won"] == 1 and by_name["Karachi"]["lost"] == 1
    assert by_name["Karachi"]["win_rate"] == 0.5


def test_conversion_by_segment_needs_a_profile(client, funnel, admin, seeded_profile):
    response = client.get(f"{INSIGHTS}/conversion", headers=admin, params={"group_by": "segment"})
    assert response.status_code == 400 and "profile" in response.json()["detail"]

    rows = conversion(client, admin, "segment", profile_id=seeded_profile.id)

    assert rows["wholesaler"]["leads"] == 1 and rows["wholesaler"]["won"] == 1 and rows["wholesaler"]["revenue"] == 1000
    assert rows["dealer"]["leads"] == 5 and sum(row["leads"] for row in rows.values()) == 6


def test_rows_are_sorted_with_the_biggest_group_first(client, funnel, admin):
    body = client.get(f"{INSIGHTS}/conversion", headers=admin, params={"group_by": "source"}).json()

    assert [row["key"] for row in body["data"]] == ["osm", "google_places"] and body["count"] == 2


def test_an_unknown_grouping_is_rejected(client, admin):
    assert client.get(f"{INSIGHTS}/conversion", headers=admin, params={"group_by": "color"}).status_code == 422


def test_sales_can_read_the_reports(client, funnel, sales_user, auth_headers):
    headers = auth_headers(sales_user)

    assert client.get(f"{INSIGHTS}/pipeline", headers=headers).status_code == 200
    assert client.get(f"{INSIGHTS}/conversion", headers=headers).status_code == 200
