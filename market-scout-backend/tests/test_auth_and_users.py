from app.core.security import create_refresh_token
from tests.conftest import DEFAULT_PASSWORD


def _login(client, email: str, password: str = DEFAULT_PASSWORD):
    return client.post("/api/v1/auth/login", json={"email": email, "password": password})


def test_login_success_returns_tokens(client, sales_user):
    response = _login(client, sales_user.email)
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"] and body["refresh_token"]


def test_login_is_case_insensitive_on_email(client, sales_user):
    assert _login(client, sales_user.email.upper()).status_code == 200


def test_login_wrong_password_and_unknown_email_look_identical(client, sales_user):
    wrong_password = _login(client, sales_user.email, "Wr0ng!Password")
    unknown_email = _login(client, "nobody@example.com")
    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()


def test_inactive_user_cannot_log_in(client, make_user):
    user = make_user("inactive@example.com", is_active=False)
    assert _login(client, user.email).status_code == 401


def test_me_returns_current_user(client, sales_user, auth_headers):
    response = client.get("/api/v1/auth/me", headers=auth_headers(sales_user))
    assert response.status_code == 200
    assert response.json()["email"] == sales_user.email
    assert response.json()["role"] == "sales"
    assert "hashed_password" not in response.json()


def test_refresh_issues_new_tokens(client, sales_user):
    tokens = _login(client, sales_user.email).json()
    response = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert response.status_code == 200
    assert response.json()["access_token"]


def test_access_token_cannot_be_used_to_refresh(client, sales_user):
    tokens = _login(client, sales_user.email).json()
    response = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["access_token"]})
    assert response.status_code == 401


def test_refresh_token_cannot_be_used_as_access_token(client, sales_user):
    refresh = create_refresh_token({"sub": str(sales_user.id), "tv": sales_user.token_version})
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {refresh}"})
    assert response.status_code == 401


def test_garbage_token_is_rejected(client):
    response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not-a-token"})
    assert response.status_code == 401


def test_logout_all_invalidates_existing_tokens(client, sales_user):
    tokens = _login(client, sales_user.email).json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    assert client.post("/api/v1/auth/logout-all", headers=headers).status_code == 200

    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401
    refresh = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refresh.status_code == 401


def test_change_password_success_returns_working_tokens(client, sales_user, auth_headers):
    new_password = "N3w!Passw0rd"
    response = client.post(
        "/api/v1/auth/change-password",
        headers=auth_headers(sales_user),
        json={"current_password": DEFAULT_PASSWORD, "new_password": new_password},
    )
    assert response.status_code == 200
    new_headers = {"Authorization": f"Bearer {response.json()['access_token']}"}
    assert client.get("/api/v1/auth/me", headers=new_headers).status_code == 200
    assert _login(client, sales_user.email, new_password).status_code == 200
    assert _login(client, sales_user.email, DEFAULT_PASSWORD).status_code == 401


def test_change_password_requires_correct_current_password(client, sales_user, auth_headers):
    response = client.post(
        "/api/v1/auth/change-password",
        headers=auth_headers(sales_user),
        json={"current_password": "Wr0ng!Password", "new_password": "N3w!Passw0rd"},
    )
    assert response.status_code == 400


def test_change_password_enforces_strength(client, sales_user, auth_headers):
    response = client.post(
        "/api/v1/auth/change-password",
        headers=auth_headers(sales_user),
        json={"current_password": DEFAULT_PASSWORD, "new_password": "weakpassword"},
    )
    assert response.status_code == 422


def test_login_is_rate_limited(client, sales_user):
    statuses = [_login(client, sales_user.email, "Wr0ng!Password").status_code for _ in range(12)]
    assert statuses[:10] == [401] * 10
    assert 429 in statuses[10:]


def test_sales_cannot_access_user_management(client, sales_user, auth_headers):
    headers = auth_headers(sales_user)
    assert client.get("/api/v1/users/", headers=headers).status_code == 403
    assert client.post(
        "/api/v1/users/",
        headers=headers,
        json={"email": "x@example.com", "full_name": "X Person", "password": DEFAULT_PASSWORD},
    ).status_code == 403


def test_admin_creates_lists_and_filters_users(client, admin_user, sales_user, auth_headers):
    headers = auth_headers(admin_user)
    created = client.post(
        "/api/v1/users/",
        headers=headers,
        json={"email": "New.Rep@Example.com", "full_name": "New Rep", "password": DEFAULT_PASSWORD},
    )
    assert created.status_code == 201
    assert created.json()["email"] == "new.rep@example.com"
    assert created.json()["role"] == "sales"

    listing = client.get("/api/v1/users/", headers=headers).json()
    assert listing["count"] == 3

    only_admins = client.get("/api/v1/users/?role=admin", headers=headers).json()
    assert [u["email"] for u in only_admins["data"]] == [admin_user.email]

    searched = client.get("/api/v1/users/?search=new.rep", headers=headers).json()
    assert searched["count"] == 1


def test_create_user_rejects_duplicate_email_and_weak_password(client, admin_user, sales_user, auth_headers):
    headers = auth_headers(admin_user)
    duplicate = client.post(
        "/api/v1/users/",
        headers=headers,
        json={"email": sales_user.email, "full_name": "Dup User", "password": DEFAULT_PASSWORD},
    )
    assert duplicate.status_code == 409

    weak = client.post(
        "/api/v1/users/",
        headers=headers,
        json={"email": "weak@example.com", "full_name": "Weak User", "password": "password"},
    )
    assert weak.status_code == 422


def test_admin_update_user_role_deactivation_and_session_revocation(client, admin_user, sales_user, auth_headers):
    sales_headers = auth_headers(sales_user)
    assert client.get("/api/v1/auth/me", headers=sales_headers).status_code == 200

    response = client.put(
        f"/api/v1/users/{sales_user.id}",
        headers=auth_headers(admin_user),
        json={"is_active": False},
    )
    assert response.status_code == 200
    assert response.json()["is_active"] is False
    assert client.get("/api/v1/auth/me", headers=sales_headers).status_code == 401


def test_admin_can_reset_another_users_password(client, admin_user, sales_user, auth_headers):
    response = client.put(
        f"/api/v1/users/{sales_user.id}",
        headers=auth_headers(admin_user),
        json={"password": "Reset!Passw0rd"},
    )
    assert response.status_code == 200
    assert _login(client, sales_user.email, "Reset!Passw0rd").status_code == 200


def test_admin_cannot_deactivate_or_demote_self(client, admin_user, auth_headers):
    headers = auth_headers(admin_user)
    deactivate = client.put(f"/api/v1/users/{admin_user.id}", headers=headers, json={"is_active": False})
    demote = client.put(f"/api/v1/users/{admin_user.id}", headers=headers, json={"role": "sales"})
    assert deactivate.status_code == 400
    assert demote.status_code == 400


def test_get_missing_user_returns_404(client, admin_user, auth_headers):
    response = client.get("/api/v1/users/9999", headers=auth_headers(admin_user))
    assert response.status_code == 404
