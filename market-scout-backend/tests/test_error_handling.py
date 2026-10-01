from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app.features.profiles import service as profiles_service
from app.main import app

ORIGIN = "http://localhost:5173"


def boom(*args, **kwargs):
    raise RuntimeError("something internal, with details that must not leak")


def test_a_500_still_carries_cors_headers_so_the_browser_can_read_it(client, admin_user, auth_headers, monkeypatch):
    monkeypatch.setattr(profiles_service, "get_profiles", boom)
    with TestClient(app, raise_server_exceptions=False) as real_server:
        response = real_server.get("/api/v1/profiles/", headers={**auth_headers(admin_user), "Origin": ORIGIN})

    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error"}
    assert response.headers["access-control-allow-origin"] == ORIGIN
    assert response.headers["access-control-allow-credentials"] == "true"


def test_a_500_does_not_grant_cors_to_unknown_origins(client, admin_user, auth_headers, monkeypatch):
    monkeypatch.setattr(profiles_service, "get_profiles", boom)
    with TestClient(app, raise_server_exceptions=False) as real_server:
        response = real_server.get("/api/v1/profiles/", headers={**auth_headers(admin_user), "Origin": "https://evil.example"})

    assert response.status_code == 500
    assert "access-control-allow-origin" not in response.headers


def test_an_unexpected_database_conflict_is_a_409_not_a_500(client, admin_user, auth_headers, monkeypatch):
    def conflict(*args, **kwargs):
        raise IntegrityError("INSERT ...", {}, Exception("UNIQUE constraint failed"))

    monkeypatch.setattr(profiles_service, "get_profiles", conflict)
    response = client.get("/api/v1/profiles/", headers={**auth_headers(admin_user), "Origin": ORIGIN})

    assert response.status_code == 409
    assert "conflicts with existing data" in response.json()["detail"]
    assert "UNIQUE" not in response.text
    assert response.headers["access-control-allow-origin"] == ORIGIN
