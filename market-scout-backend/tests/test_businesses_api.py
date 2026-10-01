from datetime import UTC, datetime, timedelta

import pytest

from app.features.businesses.models import Business
from app.features.geographies.models import Geography

BASE = "/api/v1/businesses"


def ids(response) -> list[int]:
    return [item["id"] for item in response.json()["data"]]


@pytest.fixture()
def leads(make_business):
    """Six leads with deliberately different attributes."""
    now = datetime.now(UTC)
    return {
        "noor": make_business(
            "Al Noor Solar Dealer", phones=["0300 4438424", "042 3577 1769"], emails=["info@alnoor.pk"],
            website="https://alnoor.pk", address="12 Mall Road", review_count=20, rating=4.6,
            categories=["shop=electrical"], now=now - timedelta(days=3),
        ),
        "bilal": make_business(
            "Bilal Wholesale Traders", hint="wholesaler", phones=["0301 1112223"], source="google_places",
            now=now - timedelta(days=2),
        ),
        "zahid": make_business("Zahid Battery House", hint="retailer", phones=["042 3577 9999"], now=now - timedelta(days=1)),
        "ghost": make_business("Ghost Energy", hint="installer", now=now),                   # no contact details at all
        "karachi": make_business("Karachi Inverter Center", city="karachi", hint="retailer", phones=["0333 7654321"]),
        "quetta": make_business("Quetta Solar Works", city="quetta", hint="installer", emails=["hello@quettasolar.pk"]),
    }


# ---- access -------------------------------------------------------------------------------

def test_endpoints_require_a_login(client, leads):
    assert client.get(f"{BASE}/").status_code == 401
    assert client.get(f"{BASE}/{leads['noor'].id}").status_code == 401
    assert client.patch(f"{BASE}/{leads['noor'].id}", json={"notes": "x"}).status_code == 401
    assert client.post(f"{BASE}/bulk-update", json={"business_ids": [1], "lead_status": "contacted"}).status_code == 401
    assert client.get(f"{BASE}/assignees").status_code == 401
    assert client.post(f"{BASE}/{leads['noor'].id}/do-not-contact", json={}).status_code == 401


# ---- list --------------------------------------------------------------------------------------

def test_list_shows_the_row_fields_a_salesperson_needs(client, leads, seeded_profile, sales_user, admin_user, auth_headers):
    client.patch(f"{BASE}/{leads['noor'].id}", headers=auth_headers(admin_user), json={"assigned_to_id": sales_user.id})

    body = client.get(f"{BASE}/?profile_id={seeded_profile.id}", headers=auth_headers(sales_user)).json()
    noor = next(item for item in body["data"] if item["id"] == leads["noor"].id)

    assert body["count"] == 6
    assert noor["name"] == "Al Noor Solar Dealer" and noor["address"] == "12 Mall Road"
    assert (noor["city"], noor["province"]) == ("Lahore", "Punjab")
    assert (noor["segment_slug"], noor["segment_name"]) == ("dealer", "Dealer")
    assert noor["profile_id"] == seeded_profile.id and noor["score"] == 100      # everything present + name match
    assert noor["primary_phone"] == "+923004438424"                             # the WhatsApp-capable mobile, not the landline
    assert noor["whatsapp_likely"] is True and noor["email"] == "info@alnoor.pk"
    assert noor["website"] == "https://alnoor.pk" and noor["rating"] == 4.6 and noor["review_count"] == 20
    assert noor["lead_status"] == "new" and noor["sources"] == ["osm"]
    assert noor["assigned_to"] == {"id": sales_user.id, "full_name": "Sales User"}

    ghost = next(item for item in body["data"] if item["id"] == leads["ghost"].id)
    assert ghost["primary_phone"] is None and ghost["whatsapp_likely"] is False and ghost["email"] is None
    assert ghost["assigned_to"] is None and ghost["province"] == "Punjab"
    bilal = next(item for item in body["data"] if item["id"] == leads["bilal"].id)
    assert bilal["sources"] == ["google_places"] and bilal["segment_slug"] == "wholesaler"


def test_default_order_is_best_score_first_when_a_profile_is_chosen_else_newest(client, leads, seeded_profile, sales_user, auth_headers):
    headers = auth_headers(sales_user)
    by_score = client.get(f"{BASE}/?profile_id={seeded_profile.id}", headers=headers)
    scores = [item["score"] for item in by_score.json()["data"]]
    assert scores == sorted(scores, reverse=True) and ids(by_score)[0] == leads["noor"].id

    # Created in this order, but noor/bilal/zahid/ghost were given explicit first-seen times.
    newest = client.get(f"{BASE}/", headers=headers)
    assert ids(newest) == [leads[k].id for k in ("quetta", "karachi", "ghost", "zahid", "bilal", "noor")]


def test_sorting_options(client, leads, seeded_profile, sales_user, auth_headers):
    headers = auth_headers(sales_user)
    by_name = [i["name"] for i in client.get(f"{BASE}/?sort=name", headers=headers).json()["data"]]
    assert by_name == sorted(by_name, key=str.lower)
    by_name_desc = [i["name"] for i in client.get(f"{BASE}/?sort=name&direction=desc", headers=headers).json()["data"]]
    assert by_name_desc == by_name[::-1]

    oldest_seen_first = ids(client.get(f"{BASE}/?sort=last_seen&direction=asc", headers=headers))
    assert oldest_seen_first.index(leads["noor"].id) < oldest_seen_first.index(leads["bilal"].id) < oldest_seen_first.index(leads["zahid"].id)

    lowest_score_first = client.get(f"{BASE}/?profile_id={seeded_profile.id}&sort=score&direction=asc", headers=headers)
    scores = [i["score"] for i in lowest_score_first.json()["data"]]
    assert scores == sorted(scores)
    assert client.get(f"{BASE}/?sort=nonsense", headers=headers).status_code == 422


def test_pagination(client, leads, sales_user, auth_headers):
    headers = auth_headers(sales_user)
    first = client.get(f"{BASE}/?limit=4&sort=name", headers=headers).json()
    second = client.get(f"{BASE}/?limit=4&page=2&sort=name", headers=headers).json()
    assert first["count"] == second["count"] == 6 and len(first["data"]) == 4 and len(second["data"]) == 2
    assert not {i["id"] for i in first["data"]} & {i["id"] for i in second["data"]}
    assert client.get(f"{BASE}/?limit=101", headers=headers).status_code == 422


# ---- filters -----------------------------------------------------------------------------------------

@pytest.mark.parametrize(
    "query, expected",
    [
        ("has_phone=true", {"noor", "bilal", "zahid", "karachi"}),
        ("has_phone=false", {"ghost", "quetta"}),
        ("whatsapp_likely=true", {"noor", "bilal", "karachi"}),            # mobiles only; zahid has a landline
        ("whatsapp_likely=false", {"zahid", "ghost", "quetta"}),
        ("has_email=true", {"noor", "quetta"}),
        ("has_email=false", {"bilal", "zahid", "ghost", "karachi"}),
        ("has_website=true", {"noor"}),
        ("has_website=false", {"bilal", "zahid", "ghost", "karachi", "quetta"}),
        ("source=google_places", {"bilal"}),
        ("source=osm", {"noor", "zahid", "ghost", "karachi", "quetta"}),
        ("min_score=80", {"noor"}),
        ("status=new", {"noor", "bilal", "zahid", "ghost", "karachi", "quetta"}),
        ("status=customer", set()),
    ],
)
def test_simple_filters(client, leads, sales_user, auth_headers, query, expected):
    response = client.get(f"{BASE}/?{query}", headers=auth_headers(sales_user))
    assert response.status_code == 200
    assert set(ids(response)) == {leads[key].id for key in expected}
    assert response.json()["count"] == len(expected)


def test_segment_filter_needs_and_respects_the_profile(client, leads, seeded_profile, sales_user, auth_headers):
    headers = auth_headers(sales_user)
    retailers = client.get(f"{BASE}/?profile_id={seeded_profile.id}&segment=retailer", headers=headers)
    assert set(ids(retailers)) == {leads["zahid"].id, leads["karachi"].id}
    assert client.get(f"{BASE}/?segment=retailer", headers=headers).status_code == 400
    assert client.get(f"{BASE}/?profile_id=9999", headers=headers).json()["count"] == 0
    assert client.get(f"{BASE}/?profile_id={seeded_profile.id}&segment=nope", headers=headers).json()["count"] == 0


def test_geography_filter_accepts_a_city_a_province_or_the_country(client, leads, db_session, sales_user, auth_headers):
    headers = auth_headers(sales_user)

    def by(slug):
        geography_id = db_session.query(Geography).filter_by(slug=slug).one().id
        return set(ids(client.get(f"{BASE}/?geography_id={geography_id}", headers=headers)))

    assert by("karachi") == {leads["karachi"].id}
    assert by("punjab") == {leads[k].id for k in ("noor", "bilal", "zahid", "ghost")}
    assert by("sindh") == {leads["karachi"].id}
    assert by("balochistan") == {leads["quetta"].id}
    assert by("pakistan") == {lead.id for lead in leads.values()}
    assert client.get(f"{BASE}/?geography_id=99999", headers=headers).status_code == 404


def test_assignment_filters(client, leads, sales_user, admin_user, auth_headers):
    headers = auth_headers(sales_user)
    client.post(f"{BASE}/bulk-update", headers=headers, json={"business_ids": [leads["noor"].id, leads["zahid"].id], "assigned_to_id": sales_user.id})

    mine = client.get(f"{BASE}/?assigned_to_id={sales_user.id}", headers=headers)
    assert set(ids(mine)) == {leads["noor"].id, leads["zahid"].id}
    unassigned = client.get(f"{BASE}/?unassigned=true", headers=headers)
    assert unassigned.json()["count"] == 4 and leads["noor"].id not in ids(unassigned)
    assert client.get(f"{BASE}/?unassigned=true&assigned_to_id={sales_user.id}", headers=headers).status_code == 400


@pytest.mark.parametrize(
    "term, expected",
    [
        ("noor", {"noor"}),
        ("BATTERY", {"zahid"}),                       # case-insensitive
        ("mall road", {"noor"}),                      # address
        ("0300 4438424", {"noor"}),                   # phone as written locally
        ("03004438424", {"noor"}),
        ("300-443", {"noor"}),                        # partial
        ("+92 300 4438424", {"noor"}),                # international form
        ("3577", {"noor", "zahid"}),                  # two shops share this landline prefix
        ("info@alnoor", {"noor"}),                    # email
        ("hello@quettasolar.pk", {"quetta"}),
        ("no such thing", set()),
        ("   ", {"noor", "bilal", "zahid", "ghost", "karachi", "quetta"}),   # blank search means no search
    ],
)
def test_search_finds_names_addresses_phones_and_emails(client, leads, sales_user, auth_headers, term, expected):
    response = client.get(f"{BASE}/", headers=auth_headers(sales_user), params={"search": term})
    assert set(ids(response)) == {leads[key].id for key in expected}


def test_filters_combine(client, leads, seeded_profile, sales_user, auth_headers):
    response = client.get(
        f"{BASE}/?profile_id={seeded_profile.id}&has_phone=true&whatsapp_likely=true&min_score=50&search=solar",
        headers=auth_headers(sales_user),
    )
    assert set(ids(response)) == {leads["noor"].id}


# ---- detail ----------------------------------------------------------------------------------------------

def test_detail_shows_contacts_with_provenance_classification_and_sources(client, leads, seeded_profile, sales_user, auth_headers):
    body = client.get(f"{BASE}/{leads['noor'].id}", headers=auth_headers(sales_user)).json()

    assert body["name"] == "Al Noor Solar Dealer" and body["website"] == "https://alnoor.pk"
    assert (body["city"], body["province"]) == ("Lahore", "Punjab")
    assert body["categories"] == ["shop=electrical"] and body["notes"] is None
    assert body["classifications"] == [
        {"profile_id": seeded_profile.id, "segment_slug": "dealer", "segment_name": "Dealer", "score": 100}
    ]
    contacts = {(c["kind"], c["value"]): c for c in body["contacts"]}
    assert set(contacts) == {("phone", "+923004438424"), ("phone", "+924235771769"), ("email", "info@alnoor.pk")}
    mobile = contacts[("phone", "+923004438424")]
    assert (mobile["is_mobile"], mobile["whatsapp_likely"], mobile["source_key"]) == (True, True, "osm")
    assert mobile["created_at"] is not None
    assert [(s["source_key"], s["external_id"]) for s in body["sources"]] == [("osm", "osm/1")]
    assert "raw_payload" not in body["sources"][0]
    assert body["first_seen_at"] and body["last_seen_at"] and body["latitude"] is not None


def test_detail_of_a_missing_business_is_404(client, sales_user, auth_headers):
    assert client.get(f"{BASE}/9999", headers=auth_headers(sales_user)).status_code == 404


# ---- editing -------------------------------------------------------------------------------------------------

def test_a_salesperson_updates_status_notes_and_assignee(client, leads, sales_user, admin_user, auth_headers):
    headers = auth_headers(sales_user)
    url = f"{BASE}/{leads['noor'].id}"

    response = client.patch(url, headers=headers, json={"lead_status": "contacted", "notes": "  Called; wants a quote.  ", "assigned_to_id": admin_user.id})

    assert response.status_code == 200
    body = response.json()
    assert (body["lead_status"], body["notes"]) == ("contacted", "Called; wants a quote.")
    assert body["assigned_to"] == {"id": admin_user.id, "full_name": "Admin User"}
    assert body["updated_at"] is not None

    # Partial updates leave the other fields alone.
    only_status = client.patch(url, headers=headers, json={"lead_status": "interested"}).json()
    assert only_status["lead_status"] == "interested" and only_status["notes"] == "Called; wants a quote."
    assert only_status["assigned_to"]["id"] == admin_user.id

    unassigned = client.patch(url, headers=headers, json={"assigned_to_id": None}).json()
    assert unassigned["assigned_to"] is None
    cleared = client.patch(url, headers=headers, json={"notes": "   "}).json()
    assert cleared["notes"] is None and cleared["lead_status"] == "interested"


def test_update_validation(client, leads, sales_user, make_user, auth_headers):
    headers = auth_headers(sales_user)
    url = f"{BASE}/{leads['noor'].id}"
    inactive = make_user("gone@example.com", is_active=False)

    assert client.patch(url, headers=headers, json={"lead_status": "won"}).status_code == 422
    assert client.patch(url, headers=headers, json={"lead_status": None}).status_code == 400
    assert client.patch(url, headers=headers, json={"assigned_to_id": 9999}).status_code == 400
    assert client.patch(url, headers=headers, json={"assigned_to_id": inactive.id}).status_code == 400
    assert client.patch(url, headers=headers, json={"notes": "x" * 5001}).status_code == 422
    assert client.patch(f"{BASE}/9999", headers=headers, json={"notes": "x"}).status_code == 404
    # Read-only fields can't be smuggled in.
    client.patch(url, headers=headers, json={"name": "Hacked", "website": "https://evil.example"})
    assert client.get(url, headers=headers).json()["name"] == "Al Noor Solar Dealer"


# ---- bulk -------------------------------------------------------------------------------------------------------

def test_bulk_update_assigns_and_sets_status(client, leads, sales_user, auth_headers, db_session):
    headers = auth_headers(sales_user)
    chosen = [leads["noor"].id, leads["zahid"].id, leads["ghost"].id]

    response = client.post(f"{BASE}/bulk-update", headers=headers, json={"business_ids": chosen, "lead_status": "contacted", "assigned_to_id": sales_user.id})
    assert response.status_code == 200 and response.json() == {"updated": 3}

    db_session.expire_all()
    assert {b.lead_status for b in db_session.query(Business).filter(Business.id.in_(chosen))} == {"contacted"}
    assert db_session.query(Business).filter(Business.id == leads["bilal"].id).one().lead_status == "new"

    # null un-assigns; other fields untouched.
    client.post(f"{BASE}/bulk-update", headers=headers, json={"business_ids": chosen, "assigned_to_id": None})
    db_session.expire_all()
    rows = db_session.query(Business).filter(Business.id.in_(chosen)).all()
    assert {b.assigned_to_id for b in rows} == {None} and {b.lead_status for b in rows} == {"contacted"}


def test_bulk_update_ignores_unknown_ids_and_validates_input(client, leads, sales_user, auth_headers):
    headers = auth_headers(sales_user)
    ok = client.post(f"{BASE}/bulk-update", headers=headers, json={"business_ids": [leads["noor"].id, leads["noor"].id, 9999], "lead_status": "quoted"})
    assert ok.json() == {"updated": 1}

    assert client.post(f"{BASE}/bulk-update", headers=headers, json={"business_ids": [leads["noor"].id]}).status_code == 422       # nothing to change
    assert client.post(f"{BASE}/bulk-update", headers=headers, json={"business_ids": [], "lead_status": "quoted"}).status_code == 422
    assert client.post(f"{BASE}/bulk-update", headers=headers, json={"business_ids": list(range(501)), "lead_status": "quoted"}).status_code == 422
    assert client.post(f"{BASE}/bulk-update", headers=headers, json={"business_ids": [1], "lead_status": None}).status_code == 400
    assert client.post(f"{BASE}/bulk-update", headers=headers, json={"business_ids": [1], "assigned_to_id": 9999}).status_code == 400
    assert client.post(f"{BASE}/bulk-update", headers=headers, json={"business_ids": [1], "notes": "x"}).status_code == 422


def test_assignees_are_the_active_users_for_any_role(client, sales_user, admin_user, make_user, auth_headers):
    make_user("gone@example.com", full_name="Former Rep", is_active=False)
    response = client.get(f"{BASE}/assignees", headers=auth_headers(sales_user))
    assert response.status_code == 200
    assert {u["full_name"] for u in response.json()} == {"Admin User", "Sales User"}


# ---- do-not-contact hides people everywhere --------------------------------------------------------------------------

def test_a_blocked_business_disappears_from_every_leads_endpoint(client, leads, sales_user, auth_headers):
    headers = auth_headers(sales_user)
    blocked = leads["noor"]

    assert client.post(f"{BASE}/{blocked.id}/do-not-contact", headers=headers, json={"reason": "asked us to stop"}).status_code == 201

    everything = client.get(f"{BASE}/", headers=headers)
    assert blocked.id not in ids(everything) and everything.json()["count"] == 5     # others are NOT hidden by the NULL columns
    assert client.get(f"{BASE}/?search=noor", headers=headers).json()["count"] == 0
    assert client.get(f"{BASE}/?has_email=true", headers=headers).json()["count"] == 1
    assert client.get(f"{BASE}/{blocked.id}", headers=headers).status_code == 404
    assert client.patch(f"{BASE}/{blocked.id}", headers=headers, json={"notes": "x"}).status_code == 404
    assert client.post(f"{BASE}/bulk-update", headers=headers, json={"business_ids": [blocked.id], "lead_status": "contacted"}).json() == {"updated": 0}


def test_blocking_a_phone_or_email_hides_whoever_owns_it(client, leads, sales_user, auth_headers):
    headers = auth_headers(sales_user)
    client.post("/api/v1/compliance/do-not-contact", headers=headers, json={"phone": "0301 1112223"})
    client.post("/api/v1/compliance/do-not-contact", headers=headers, json={"email": "Hello@QuettaSolar.pk"})

    remaining = set(ids(client.get(f"{BASE}/", headers=headers)))
    assert remaining == {leads[k].id for k in ("noor", "zahid", "ghost", "karachi")}
