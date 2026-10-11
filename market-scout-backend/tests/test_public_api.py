import pytest
from fastapi.routing import APIRoute

from app.features.businesses.models import Business, ContactPoint, SourceRecord
from app.features.pipeline.models import LeadActivity
from app.main import app

BASE = "/api/v1/public"
KEYS = "/api/v1/api-keys"


@pytest.fixture()
def admin(admin_user, auth_headers):
    return auth_headers(admin_user)


@pytest.fixture()
def reader(client, admin):
    token = client.post(f"{KEYS}/", headers=admin, json={"name": "Reader"}).json()["token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def writer(client, admin, seeded_profile):
    token = client.post(f"{KEYS}/", headers=admin, json={"name": "Writer", "can_write": True}).json()["token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def lead(make_business):
    return make_business("Al Noor Solar", phones=["0300 4438424"], emails=["info@alnoor.pk"])


def test_the_public_routes_are_exactly_the_intended_ones():
    found = set()
    for route in app.routes:
        if isinstance(route, APIRoute) and route.path.startswith(BASE):
            found |= {(method, route.path) for method in route.methods - {"HEAD", "OPTIONS"}}

    assert found == {
        ("GET", f"{BASE}/me"),
        ("GET", f"{BASE}/leads"),
        ("GET", f"{BASE}/leads/{{lead_id}}"),
        ("GET", f"{BASE}/leads/{{lead_id}}/activities"),
        ("POST", f"{BASE}/leads"),
        ("PATCH", f"{BASE}/leads/{{lead_id}}"),
        ("POST", f"{BASE}/leads/{{lead_id}}/activities"),
    }


def test_a_read_key_lists_and_filters_leads(client, reader, make_business):
    make_business("Al Noor Solar", phones=["0300 4438424"])
    make_business("Bright Panels", phones=["0301 1112223"], emails=["hi@bright.pk"])

    everything = client.get(f"{BASE}/leads", headers=reader).json()
    with_email = client.get(f"{BASE}/leads", headers=reader, params={"has_email": True}).json()
    searched = client.get(f"{BASE}/leads", headers=reader, params={"search": "Bright"}).json()

    assert everything["count"] == 2
    assert [item["name"] for item in with_email["data"]] == ["Bright Panels"]
    assert searched["count"] == 1


def test_the_list_is_paged_and_limits_are_checked(client, reader, make_business):
    for index in range(3):
        make_business(f"Shop {index}", phones=[f"030{index} 1112223"])

    page = client.get(f"{BASE}/leads", headers=reader, params={"limit": 2, "page": 2}).json()

    assert page["count"] == 3 and len(page["data"]) == 1
    assert client.get(f"{BASE}/leads", headers=reader, params={"limit": 0}).status_code == 422
    assert client.get(f"{BASE}/leads", headers=reader, params={"limit": 101}).status_code == 422


def test_one_lead_comes_back_in_full(client, reader, lead):
    data = client.get(f"{BASE}/leads/{lead.id}", headers=reader).json()

    assert data["name"] == "Al Noor Solar" and data["lead_status"] == "new"
    assert {c["value"] for c in data["contacts"]} == {"+923004438424", "info@alnoor.pk"}
    assert client.get(f"{BASE}/leads/999999", headers=reader).status_code == 404


def test_a_lead_on_the_do_not_contact_list_is_invisible(client, reader, lead, admin):
    client.post(f"/api/v1/businesses/{lead.id}/do-not-contact", headers=admin, json={})

    assert client.get(f"{BASE}/leads/{lead.id}", headers=reader).status_code == 404
    assert client.get(f"{BASE}/leads", headers=reader).json()["count"] == 0
    assert client.get(f"{BASE}/leads/{lead.id}/activities", headers=reader).status_code == 404


def test_the_history_of_a_lead_can_be_read(client, reader, writer, lead):
    client.post(f"{BASE}/leads/{lead.id}/activities", headers=writer, json={"kind": "call", "summary": "Spoke to the owner"})

    data = client.get(f"{BASE}/leads/{lead.id}/activities", headers=reader).json()

    assert data["count"] == 1 and data["data"][0]["summary"] == "Spoke to the owner" and data["data"][0]["created_by"] is None


def test_a_write_key_changes_status_notes_and_the_contact_person(client, writer, lead, db_session):
    response = client.patch(
        f"{BASE}/leads/{lead.id}", headers=writer, json={"lead_status": "interested", "notes": " Wants a quote ", "contact_name": "Mr Khan"}
    )

    assert response.status_code == 200
    data = response.json()
    assert (data["lead_status"], data["notes"], data["contact_name"]) == ("interested", "Wants a quote", "Mr Khan")
    kinds = [a.kind for a in db_session.query(LeadActivity).filter_by(business_id=lead.id)]
    assert kinds == ["status_change"]


def test_a_write_key_can_close_a_deal_with_its_value(client, writer, lead):
    response = client.patch(
        f"{BASE}/leads/{lead.id}", headers=writer, json={"lead_status": "customer", "outcome": {"value": 1500, "product": "Billing"}}
    )

    assert response.status_code == 200
    assert response.json()["outcome"]["value"] == 1500 and response.json()["outcome"]["kind"] == "won"


def test_a_key_cannot_assign_leads_or_send_unknown_fields(client, writer, lead, sales_user):
    assert client.patch(f"{BASE}/leads/{lead.id}", headers=writer, json={"assigned_to_id": sales_user.id}).status_code == 422
    assert client.patch(f"{BASE}/leads/{lead.id}", headers=writer, json={"anything": 1}).status_code == 422
    assert client.patch(f"{BASE}/leads/{lead.id}", headers=writer, json={"lead_status": "bogus"}).status_code == 422
    assert client.patch(f"{BASE}/leads/999999", headers=writer, json={"notes": "x"}).status_code == 404


def test_a_key_adds_a_note_to_the_history(client, writer, lead, db_session):
    response = client.post(f"{BASE}/leads/{lead.id}/activities", headers=writer, json={"kind": "note", "summary": "Imported from billing"})

    assert response.status_code == 201
    assert db_session.query(LeadActivity).filter_by(business_id=lead.id, kind="note").one().created_by_id is None
    assert client.post(f"{BASE}/leads/{lead.id}/activities", headers=writer, json={"kind": "note", "summary": " "}).status_code == 422
    assert client.post(f"{BASE}/leads/{lead.id}/activities", headers=writer, json={"kind": "status_change", "summary": "x"}).status_code == 422


def test_a_key_adds_a_new_lead(client, writer, reader, db_session):
    response = client.post(
        f"{BASE}/leads", headers=writer,
        json={"name": "Zed Energy", "phones": ["0302 7778889"], "emails": ["hello@zed.pk"], "website": "https://zed.pk", "city_id": None},
    )

    assert response.status_code == 201 and response.json()["created"] is True
    lead_id = response.json()["id"]
    detail = client.get(f"{BASE}/leads/{lead_id}", headers=reader).json()
    assert detail["name"] == "Zed Energy" and detail["website"] == "https://zed.pk"
    assert {c["value"] for c in detail["contacts"]} == {"+923027778889", "hello@zed.pk"}
    assert db_session.query(SourceRecord).filter_by(business_id=lead_id).one().source_key == "api"


def test_the_same_business_sent_twice_is_merged_not_duplicated(client, writer):
    body = {"name": "Zed Energy", "phones": ["0302 7778889"]}

    first = client.post(f"{BASE}/leads", headers=writer, json=body).json()
    second = client.post(f"{BASE}/leads", headers=writer, json={**body, "emails": ["hello@zed.pk"]}).json()

    assert first["created"] is True and second["created"] is False and first["id"] == second["id"]


def test_a_new_lead_can_be_put_in_a_city_and_a_profile(client, writer, seeded_profile, db_session):
    from app.features.geographies.models import Geography

    city = db_session.query(Geography).filter_by(slug="lahore").one()

    response = client.post(
        f"{BASE}/leads", headers=writer,
        json={"name": "Lahore Panels", "phones": ["0303 1112223"], "city_id": city.id, "profile_id": seeded_profile.id},
    )

    assert response.status_code == 201
    assert db_session.get(Business, response.json()["id"]).geography_id == city.id


def test_a_new_lead_must_be_valid(client, writer, db_session):
    from app.features.geographies.models import Geography

    province = Geography(name="Test Province", slug="test-province", level="province")
    db_session.add(province)
    db_session.commit()

    assert client.post(f"{BASE}/leads", headers=writer, json={"name": "No Contact"}).status_code == 400
    assert client.post(f"{BASE}/leads", headers=writer, json={"name": " ", "phones": ["0300 1"]}).status_code == 422
    assert client.post(f"{BASE}/leads", headers=writer, json={"name": "Okay Co", "phones": ["0300 1112223"], "profile_id": 999}).status_code == 400
    assert client.post(f"{BASE}/leads", headers=writer, json={"name": "Okay Co", "phones": ["0300 1112223"], "city_id": 999999}).status_code == 400
    assert client.post(f"{BASE}/leads", headers=writer, json={"name": "Okay Co", "phones": ["0300 1112223"], "city_id": province.id}).status_code == 400
    assert client.post(f"{BASE}/leads", headers=writer, json={"name": "Okay Co", "phones": ["0300 1112223"], "segment_slug": "nope"}).status_code == 400
    assert client.post(f"{BASE}/leads", headers=writer, json={"name": "Okay Co", "phones": ["0300 1112223"], "extra": 1}).status_code == 422


def test_a_blocked_contact_cannot_be_added_back(client, writer, lead, admin):
    client.post(f"/api/v1/businesses/{lead.id}/do-not-contact", headers=admin, json={})

    response = client.post(f"{BASE}/leads", headers=writer, json={"name": "Another Name", "phones": ["0300 4438424"]})

    assert response.status_code == 409 and "do-not-contact" in response.json()["detail"]
    assert client.get("/api/v1/businesses/", headers=admin).json()["count"] == 0


def test_the_public_api_is_rate_limited_per_key(client, reader):
    statuses = [client.get(f"{BASE}/me", headers=reader).status_code for _ in range(125)]

    assert statuses[:120] == [200] * 120
    assert 429 in statuses[120:]


def test_one_keys_limit_does_not_affect_another(client, admin, reader):
    for _ in range(125):
        client.get(f"{BASE}/me", headers=reader)
    other = client.post(f"{KEYS}/", headers=admin, json={"name": "Other"}).json()["token"]

    assert client.get(f"{BASE}/me", headers={"Authorization": f"Bearer {other}"}).status_code == 200


def test_contacts_added_through_the_api_are_normal_contacts(client, writer, db_session):
    created = client.post(f"{BASE}/leads", headers=writer, json={"name": "Phone Only Co", "phones": ["03001112223", "0300 1112223"]}).json()

    phones = db_session.query(ContactPoint).filter_by(business_id=created["id"], kind="phone").all()

    assert [c.value for c in phones] == ["+923001112223"]
