from datetime import UTC, datetime, timedelta

import pytest

from app.features.api_keys import service
from app.features.api_keys.models import ApiKey

BASE = "/api/v1/api-keys"
PUBLIC = "/api/v1/public"


@pytest.fixture()
def admin(admin_user, auth_headers):
    return auth_headers(admin_user)


@pytest.fixture()
def sales(sales_user, auth_headers):
    return auth_headers(sales_user)


def make_key(client, admin, name="Billing app", can_write=False):
    return client.post(f"{BASE}/", headers=admin, json={"name": name, "can_write": can_write})


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def test_a_new_key_shows_its_secret_once_and_the_list_never_does(client, admin, db_session):
    created = make_key(client, admin)

    assert created.status_code == 201
    data = created.json()
    assert data["token"].startswith("ms_") and len(data["token"]) > 30
    assert data["prefix"] == data["token"][:11] and data["can_write"] is False and data["last_used_at"] is None

    listed = client.get(f"{BASE}/", headers=admin).json()
    assert listed["count"] == 1 and "token" not in listed["data"][0]
    stored = db_session.query(ApiKey).one()
    assert data["token"] not in (stored.key_hash, stored.prefix, stored.name)
    assert stored.key_hash == service.hash_token(data["token"])


def test_only_an_admin_manages_keys(client, sales, admin):
    assert make_key(client, sales).status_code == 403
    assert client.get(f"{BASE}/", headers=sales).status_code == 403
    key_id = make_key(client, admin).json()["id"]
    assert client.delete(f"{BASE}/{key_id}", headers=sales).status_code == 403


def test_a_key_needs_a_real_name(client, admin):
    assert make_key(client, admin, name=" ").status_code == 422
    assert make_key(client, admin, name="x").status_code == 422
    assert client.post(f"{BASE}/", headers=admin, json={"name": "Okay", "extra": 1}).status_code == 422


def test_a_key_opens_the_public_api_in_either_header(client, admin):
    token = make_key(client, admin, name="Zapier").json()["token"]

    by_bearer = client.get(f"{PUBLIC}/me", headers=bearer(token))
    by_header = client.get(f"{PUBLIC}/me", headers={"X-API-Key": token})

    assert by_bearer.json() == {"name": "Zapier", "can_write": False}
    assert by_header.status_code == 200


def test_requests_without_a_valid_key_are_refused(client, admin):
    token = make_key(client, admin).json()["token"]

    assert client.get(f"{PUBLIC}/me").status_code == 401
    assert client.get(f"{PUBLIC}/me", headers=bearer("ms_nope")).status_code == 401
    assert client.get(f"{PUBLIC}/me", headers=bearer(token[:-1] + "x")).status_code == 401
    assert client.get(f"{PUBLIC}/me", headers=bearer("not-a-key-format")).status_code == 401
    assert client.get(f"{PUBLIC}/me", headers={"X-API-Key": ""}).status_code == 401


def test_a_login_token_is_not_an_api_key_and_a_key_is_not_a_login(client, admin, admin_user):
    token = make_key(client, admin).json()["token"]

    assert client.get(f"{PUBLIC}/me", headers=admin).status_code == 401
    assert client.get("/api/v1/businesses/", headers=bearer(token)).status_code == 401
    assert client.get(f"{BASE}/", headers=bearer(token)).status_code == 401


def test_a_revoked_key_stops_working_at_once_and_stays_listed(client, admin):
    created = make_key(client, admin).json()
    assert client.get(f"{PUBLIC}/me", headers=bearer(created["token"])).status_code == 200

    revoked = client.delete(f"{BASE}/{created['id']}", headers=admin)

    assert revoked.status_code == 200 and revoked.json()["revoked_at"] is not None
    assert client.get(f"{PUBLIC}/me", headers=bearer(created["token"])).status_code == 401
    assert client.get(f"{BASE}/", headers=admin).json()["count"] == 1
    assert client.delete(f"{BASE}/{created['id']}", headers=admin).status_code == 200
    assert client.delete(f"{BASE}/999", headers=admin).status_code == 404


def test_revoked_keys_are_listed_after_active_ones(client, admin):
    first = make_key(client, admin, name="First").json()
    make_key(client, admin, name="Second")
    client.delete(f"{BASE}/{first['id']}", headers=admin)

    names = [item["name"] for item in client.get(f"{BASE}/", headers=admin).json()["data"]]

    assert names == ["Second", "First"]


def test_using_a_key_records_when_but_not_on_every_request(client, admin, db_session):
    created = make_key(client, admin).json()

    client.get(f"{PUBLIC}/me", headers=bearer(created["token"]))
    first = db_session.get(ApiKey, created["id"]).last_used_at
    client.get(f"{PUBLIC}/me", headers=bearer(created["token"]))
    second = db_session.get(ApiKey, created["id"]).last_used_at

    assert first is not None and second == first


def test_a_stale_last_used_time_is_refreshed(client, admin, db_session):
    created = make_key(client, admin).json()
    key = db_session.get(ApiKey, created["id"])
    key.last_used_at = datetime.now(UTC) - timedelta(minutes=5)
    db_session.commit()
    before = key.last_used_at

    client.get(f"{PUBLIC}/me", headers=bearer(created["token"]))

    assert db_session.get(ApiKey, created["id"]).last_used_at > before


def test_a_read_only_key_cannot_use_the_write_routes(client, admin):
    token = make_key(client, admin).json()["token"]

    for method, path, body in (
        ("POST", "/leads", {"name": "Zed Solar", "phones": ["0300 1112223"]}),
        ("PATCH", "/leads/1", {"notes": "x"}),
        ("POST", "/leads/1/activities", {"kind": "note", "summary": "x"}),
    ):
        response = client.request(method, f"{PUBLIC}{path}", headers=bearer(token), json=body)
        assert response.status_code == 403, (method, path)
        assert response.json()["detail"] == "This API key is read-only"
