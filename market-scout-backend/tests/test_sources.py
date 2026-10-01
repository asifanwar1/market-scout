
import pytest

from app.config import settings
from app.core.crypto import decrypt_secret
from app.features.sources import service as sources_service
from app.features.sources.models import DataSource

KEY = "AIzaSy-test-key-1234"


def by_key(client, headers):
    listing = client.get("/api/v1/sources/", headers=headers).json()
    return {source["key"]: source for source in listing["data"]}


def test_only_admins_can_see_or_change_sources(client, sales_user, auth_headers):
    headers = auth_headers(sales_user)
    assert client.get("/api/v1/sources/", headers=headers).status_code == 403
    assert client.put("/api/v1/sources/osm", headers=headers, json={"is_enabled": False}).status_code == 403
    assert client.post("/api/v1/sources/osm/test", headers=headers).status_code == 403
    assert client.get("/api/v1/sources/").status_code == 401


def test_default_state_is_free_sources_on_and_paid_source_off(client, admin_user, auth_headers):
    sources = by_key(client, auth_headers(admin_user))

    assert set(sources) == {"osm", "google_places", "website_enrichment"}
    assert sources["osm"]["is_enabled"] and sources["osm"]["is_available"]
    assert sources["website_enrichment"]["is_available"] and sources["website_enrichment"]["kind"] == "enrichment"
    places = sources["google_places"]
    assert places["is_enabled"] is False and places["has_key"] is False
    assert places["requires_api_key"] and places["is_paid"] and places["is_available"] is False


def test_cannot_enable_a_key_source_without_a_key(client, admin_user, auth_headers):
    response = client.put("/api/v1/sources/google_places", headers=auth_headers(admin_user), json={"is_enabled": True})
    assert response.status_code == 400
    assert "API key" in response.json()["detail"]
    assert by_key(client, auth_headers(admin_user))["google_places"]["is_enabled"] is False


def test_saving_a_key_enables_places_without_exposing_or_storing_it_in_plaintext(client, admin_user, auth_headers, db_session):
    headers = auth_headers(admin_user)
    response = client.put(
        "/api/v1/sources/google_places", headers=headers, json={"api_key": f"  {KEY}  ", "is_enabled": True}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["has_key"] and body["is_enabled"] and body["is_available"]
    assert body["key_source"] == "saved" and body["key_hint"] == "…1234"
    assert KEY not in response.text
    assert KEY not in client.get("/api/v1/sources/", headers=headers).text

    row = db_session.query(DataSource).filter_by(key="google_places").one()
    assert row.encrypted_api_key and KEY not in row.encrypted_api_key
    assert decrypt_secret(row.encrypted_api_key) == KEY      # trimmed
    assert sources_service.resolve_api_key(db_session, "google_places") == KEY


def test_removing_the_key_switches_the_source_off(client, admin_user, auth_headers):
    headers = auth_headers(admin_user)
    client.put("/api/v1/sources/google_places", headers=headers, json={"api_key": KEY, "is_enabled": True})

    response = client.put("/api/v1/sources/google_places", headers=headers, json={"clear_api_key": True})

    assert response.json()["has_key"] is False
    assert response.json()["is_enabled"] is False


def test_rejected_change_leaves_state_untouched(client, admin_user, auth_headers):
    headers = auth_headers(admin_user)
    client.put("/api/v1/sources/google_places", headers=headers, json={"api_key": KEY})

    # A key source can't be enabled while its key is being removed in the same request.
    response = client.put(
        "/api/v1/sources/google_places", headers=headers, json={"is_enabled": True, "clear_api_key": True}
    )

    assert response.status_code == 400
    state = by_key(client, headers)["google_places"]
    assert state["has_key"] is True and state["is_enabled"] is False


def test_key_rules_and_validation(client, admin_user, auth_headers):
    headers = auth_headers(admin_user)
    assert client.put("/api/v1/sources/osm", headers=headers, json={"api_key": KEY}).status_code == 400
    assert client.put("/api/v1/sources/google_places", headers=headers, json={"api_key": "short"}).status_code == 422
    assert client.put("/api/v1/sources/nope", headers=headers, json={"is_enabled": True}).status_code == 404
    assert client.get("/api/v1/sources/nope", headers=headers).status_code == 404


def test_free_sources_can_be_switched_off_and_on(client, admin_user, auth_headers):
    headers = auth_headers(admin_user)
    off = client.put("/api/v1/sources/osm", headers=headers, json={"is_enabled": False}).json()
    assert off["is_enabled"] is False and off["is_available"] is False
    on = client.put("/api/v1/sources/osm", headers=headers, json={"is_enabled": True}).json()
    assert on["is_available"] is True


def test_environment_key_is_used_when_none_is_saved(client, admin_user, auth_headers, monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_PLACES_API_KEY", "env-key-abcd")
    headers = auth_headers(admin_user)

    places = by_key(client, headers)["google_places"]
    assert places["has_key"] and places["key_source"] == "environment" and places["key_hint"] == "…abcd"

    enabled = client.put("/api/v1/sources/google_places", headers=headers, json={"is_enabled": True})
    assert enabled.status_code == 200 and enabled.json()["is_available"] is True

    # A key saved from the UI takes precedence over the environment.
    saved = client.put("/api/v1/sources/google_places", headers=headers, json={"api_key": KEY}).json()
    assert saved["key_source"] == "saved" and saved["key_hint"] == "…1234"


def test_unreadable_saved_key_is_reported_not_crashed_on(client, admin_user, auth_headers, db_session):
    headers = auth_headers(admin_user)
    client.put("/api/v1/sources/google_places", headers=headers, json={"api_key": KEY, "is_enabled": True})
    db_session.query(DataSource).filter_by(key="google_places").one().encrypted_api_key = "not-a-valid-token"
    db_session.commit()

    places = by_key(client, headers)["google_places"]

    assert places["key_needs_reentry"] is True
    assert places["has_key"] is False and places["is_available"] is False


def test_connection_test_uses_the_real_source_object(client, admin_user, auth_headers, monkeypatch):
    headers = auth_headers(admin_user)

    class FakeSource:
        def __init__(self, ok, message):
            self.ok, self.message = ok, message

        def test_connection(self):
            return self.ok, self.message

    built = {}

    def fake_build(db, keys):
        built["keys"] = keys
        return {keys[0]: FakeSource(True, "reachable")}

    monkeypatch.setattr(sources_service, "build_sources", fake_build)

    ok = client.post("/api/v1/sources/osm/test", headers=headers)
    assert ok.json() == {"ok": True, "message": "reachable"} and built["keys"] == ["osm"]

    # A key source with no key never reaches the network.
    no_key = client.post("/api/v1/sources/google_places/test", headers=headers).json()
    assert no_key["ok"] is False and "key" in no_key["message"].lower()

    enrichment = client.post("/api/v1/sources/website_enrichment/test", headers=headers).json()
    assert enrichment["ok"] is True
    assert client.post("/api/v1/sources/nope/test", headers=headers).status_code == 404


def test_build_sources_constructs_real_objects(db_session):
    from app.core.scouting.sources.google_places import GooglePlacesSource
    from app.core.scouting.sources.osm import OsmSource

    sources_service.update_source(
        db_session, "google_places", sources_service.SourceUpdate(api_key=KEY, is_enabled=True)
    )
    built = sources_service.build_sources(db_session, ["osm", "google_places"])

    assert isinstance(built["osm"], OsmSource) and isinstance(built["google_places"], GooglePlacesSource)
    assert sources_service.get_available_discovery_keys(db_session) == ["osm", "google_places"]


def test_user_agent_identifies_the_app_and_optionally_a_contact(monkeypatch):
    monkeypatch.setattr(settings, "SCOUT_CONTACT_EMAIL", "")
    assert sources_service.user_agent() == "MarketScout/0.1"
    monkeypatch.setattr(settings, "SCOUT_CONTACT_EMAIL", "ops@solarco.pk")
    assert sources_service.user_agent() == "MarketScout/0.1 (+mailto:ops@solarco.pk)"


@pytest.mark.parametrize("placeholder", ["you@example.com", "a@EXAMPLE.org", "x@mail.example.net", "me@localhost", "a@b.test", "a@b.invalid"])
def test_a_placeholder_contact_address_is_not_sent(monkeypatch, placeholder):
    # Overpass answers a placeholder address with "406 Not Acceptable"; leaving it out works.
    monkeypatch.setattr(settings, "SCOUT_CONTACT_EMAIL", placeholder)
    assert sources_service.user_agent() == "MarketScout/0.1"
