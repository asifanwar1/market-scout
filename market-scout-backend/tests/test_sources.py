import pytest

from app.core.config import settings
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

    assert set(sources) == {"osm", "overture", "google_places", "website_enrichment"}
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
    assert decrypt_secret(row.encrypted_api_key) == KEY
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
    monkeypatch.setattr(settings, "SCOUT_CONTACT_EMAIL", placeholder)
    assert sources_service.user_agent() == "MarketScout/0.1"


@pytest.fixture()
def overture_file(tmp_path, monkeypatch):
    path = tmp_path / "overture.sqlite"
    monkeypatch.setattr(settings, "OVERTURE_DB_PATH", str(path))
    return path


def make_overture_file(path):
    from app.core.scouting import overture_store

    overture_store.write_store(
        path,
        [{"id": "g1", "name": "Noor Solar", "categories": ["solar_installation"], "confidence": 0.9, "latitude": 31.5, "longitude": 74.3}],
        release="2026-09-23.1",
    )


def test_overture_is_unavailable_until_its_data_is_downloaded(client, admin_user, auth_headers, overture_file, db_session):
    overture = by_key(client, auth_headers(admin_user))["overture"]

    assert overture["is_enabled"] is True and overture["requires_dataset"] is True
    assert overture["dataset_ready"] is False and overture["is_available"] is False
    assert "scripts.download_overture" in overture["dataset_note"]
    assert "overture" not in sources_service.get_available_discovery_keys(db_session)


def test_overture_becomes_available_once_the_data_is_there(client, admin_user, auth_headers, overture_file, db_session):
    make_overture_file(overture_file)

    overture = by_key(client, auth_headers(admin_user))["overture"]

    assert overture["dataset_ready"] is True and overture["is_available"] is True
    assert "2026-09-23.1" in overture["dataset_note"] and "1 places" in overture["dataset_note"]
    assert "overture" in sources_service.get_available_discovery_keys(db_session)


def test_switching_overture_off_makes_it_unavailable_even_with_the_data(client, admin_user, auth_headers, overture_file):
    make_overture_file(overture_file)
    headers = auth_headers(admin_user)

    off = client.put("/api/v1/sources/overture", headers=headers, json={"is_enabled": False}).json()

    assert off["dataset_ready"] is True and off["is_available"] is False


def test_other_sources_do_not_depend_on_a_download(client, admin_user, auth_headers, overture_file):
    sources = by_key(client, auth_headers(admin_user))

    assert sources["osm"]["requires_dataset"] is False and sources["osm"]["dataset_ready"] is True
    assert sources["osm"]["dataset_note"] is None


def test_overture_connection_test_says_what_is_missing_or_how_much_is_there(client, admin_user, auth_headers, overture_file):
    headers = auth_headers(admin_user)

    missing = client.post("/api/v1/sources/overture/test", headers=headers).json()
    assert missing["ok"] is False and "not been downloaded" in missing["message"]

    make_overture_file(overture_file)
    found = client.post("/api/v1/sources/overture/test", headers=headers).json()
    assert found["ok"] is True and "2026-09-23.1" in found["message"]


def test_build_sources_makes_an_overture_source_that_uses_the_configured_file(db_session, overture_file, monkeypatch):
    from app.core.scouting.sources.overture import OvertureSource

    monkeypatch.setattr(settings, "OVERTURE_MIN_CONFIDENCE", 0.55)
    built = sources_service.build_sources(db_session, ["overture"])["overture"]

    assert isinstance(built, OvertureSource)
    assert built._path == str(overture_file) and built._min_confidence == 0.55
