def test_health_check(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_unknown_route_returns_404(client):
    assert client.get("/api/v1/does-not-exist").status_code == 404


def test_protected_route_requires_auth(client):
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.get("/api/v1/users/").status_code == 401
