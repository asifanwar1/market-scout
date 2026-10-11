import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.routing import APIRoute
from pydantic import ValidationError

from app.core.config import Settings
from app.core.dependencies import get_db
from app.features.api_keys.dependencies import get_api_key
from app.features.auth.dependencies import get_current_admin_user, get_current_user
from app.main import app

BACKEND_DIR = Path(__file__).resolve().parent.parent

PUBLIC = {
    ("POST", "/api/v1/auth/login"),
    ("POST", "/api/v1/auth/token"),
    ("POST", "/api/v1/auth/refresh"),
    ("GET", "/"),
    ("GET", "/health"),
}

ADMIN_ONLY = {
    ("GET", "/api/v1/users/"),
    ("POST", "/api/v1/users/"),
    ("GET", "/api/v1/users/{user_id}"),
    ("PUT", "/api/v1/users/{user_id}"),
    ("POST", "/api/v1/geographies/"),
    ("PUT", "/api/v1/geographies/{geography_id}"),
    ("DELETE", "/api/v1/geographies/{geography_id}"),
    ("POST", "/api/v1/profiles/"),
    ("PUT", "/api/v1/profiles/{profile_id}"),
    ("DELETE", "/api/v1/profiles/{profile_id}"),
    ("DELETE", "/api/v1/businesses/{business_id}"),
    ("POST", "/api/v1/businesses/bulk-delete"),
    ("GET", "/api/v1/sources/"),
    ("GET", "/api/v1/sources/{key}"),
    ("PUT", "/api/v1/sources/{key}"),
    ("POST", "/api/v1/sources/{key}/test"),
    ("GET", "/api/v1/runs/"),
    ("POST", "/api/v1/runs/"),
    ("POST", "/api/v1/runs/estimate"),
    ("GET", "/api/v1/runs/{run_id}"),
    ("GET", "/api/v1/runs/{run_id}/tasks"),
    ("POST", "/api/v1/runs/{run_id}/cancel"),
    ("POST", "/api/v1/runs/{run_id}/resume"),
    ("DELETE", "/api/v1/compliance/do-not-contact/{entry_id}"),
    ("GET", "/api/v1/sheets/"),
    ("PUT", "/api/v1/sheets/"),
    ("POST", "/api/v1/sheets/test"),
    ("POST", "/api/v1/sheets/sync"),
    ("GET", "/api/v1/ai/settings"),
    ("PUT", "/api/v1/ai/settings"),
    ("POST", "/api/v1/ai/settings/test"),
    ("GET", "/api/v1/jobs/status"),
    ("GET", "/api/v1/alerts/settings"),
    ("PUT", "/api/v1/alerts/settings"),
    ("POST", "/api/v1/outreach/templates"),
    ("GET", "/api/v1/api-keys/"),
    ("POST", "/api/v1/api-keys/"),
    ("DELETE", "/api/v1/api-keys/{key_id}"),
    ("GET", "/api/v1/webhooks/config"),
    ("GET", "/api/v1/webhooks/"),
    ("POST", "/api/v1/webhooks/"),
    ("PATCH", "/api/v1/webhooks/{hook_id}"),
    ("DELETE", "/api/v1/webhooks/{hook_id}"),
    ("POST", "/api/v1/webhooks/{hook_id}/rotate-secret"),
    ("POST", "/api/v1/webhooks/{hook_id}/test"),
    ("GET", "/api/v1/webhooks/{hook_id}/deliveries"),
    ("POST", "/api/v1/webhooks/deliveries/{delivery_id}/retry"),
    ("PATCH", "/api/v1/outreach/templates/{template_id}"),
    ("DELETE", "/api/v1/outreach/templates/{template_id}"),
    ("GET", "/api/v1/quality/settings"),
    ("PUT", "/api/v1/quality/settings"),
    ("GET", "/api/v1/quality/duplicates"),
    ("POST", "/api/v1/quality/duplicates/scan"),
    ("POST", "/api/v1/quality/duplicates/{candidate_id}/merge"),
    ("POST", "/api/v1/quality/duplicates/{candidate_id}/dismiss"),
    ("GET", "/api/v1/quality/scoring"),
    ("POST", "/api/v1/quality/scoring/apply"),
    ("POST", "/api/v1/quality/scoring/revert"),
    ("GET", "/api/v1/schedules/"),
    ("POST", "/api/v1/schedules/"),
    ("GET", "/api/v1/schedules/{schedule_id}"),
    ("PUT", "/api/v1/schedules/{schedule_id}"),
    ("DELETE", "/api/v1/schedules/{schedule_id}"),
    ("POST", "/api/v1/schedules/{schedule_id}/run-now"),
    ("POST", "/api/v1/imports/preview"),
    ("POST", "/api/v1/imports/"),
    ("GET", "/api/v1/imports/"),
    ("GET", "/api/v1/imports/{import_id}"),
    ("POST", "/api/v1/imports/{import_id}/cancel"),
}


def _dependency_calls(dependant) -> set:
    calls = set()
    for child in dependant.dependencies:
        calls.add(child.call)
        calls |= _dependency_calls(child)
    return calls


def _routes() -> list[tuple[str, str, str]]:
    found = []
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        calls = _dependency_calls(route.dependant)
        access = (
            "admin" if get_current_admin_user in calls
            else "user" if get_current_user in calls
            else "api_key" if get_api_key in calls
            else "public"
        )
        for method in sorted(route.methods - {"HEAD", "OPTIONS"}):
            found.append((method, route.path, access))
    return found


ROUTES = _routes()


def _fill(path: str, value) -> str:
    return re.sub(r"\{[^}]+\}", str(value), path)


def test_the_public_and_admin_routes_are_exactly_the_intended_ones():
    public = {(m, p) for m, p, a in ROUTES if a == "public"}
    admin = {(m, p) for m, p, a in ROUTES if a == "admin"}
    assert public == PUBLIC, f"public routes changed: {public ^ PUBLIC}"
    assert admin == ADMIN_ONLY, f"admin-only routes changed: {admin ^ ADMIN_ONLY}"


@pytest.mark.parametrize("method, path", sorted((m, p) for m, p, a in ROUTES if a != "public"))
def test_every_non_public_route_refuses_a_request_with_no_login(client, method, path):
    response = client.request(method, _fill(path, 1), json={} if method in ("POST", "PUT", "PATCH") else None)
    assert response.status_code == 401, f"{method} {path} answered {response.status_code} without a login"


@pytest.mark.parametrize("method, path", sorted((m, p) for m, p, a in ROUTES if a != "public"))
def test_a_refresh_token_is_not_accepted_as_a_login(client, sales_user, method, path):
    from app.core.security import create_refresh_token

    token = create_refresh_token({"sub": str(sales_user.id), "tv": sales_user.token_version})
    response = client.request(method, _fill(path, 1), headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


@pytest.mark.parametrize("method, path", sorted(ADMIN_ONLY))
def test_sales_cannot_reach_any_admin_route(client, sales_user, auth_headers, method, path):
    response = client.request(
        method, _fill(path, 1), headers=auth_headers(sales_user), json={} if method in ("POST", "PUT", "PATCH") else None
    )
    assert response.status_code == 403, f"{method} {path} let a sales user in ({response.status_code})"


def test_a_deactivated_user_is_locked_out_immediately(client, make_user, auth_headers):
    user = make_user("gone@example.com", is_active=False)
    assert client.get("/api/v1/businesses/", headers=auth_headers(user)).status_code == 401


_DESTRUCTIVE = {("POST", "/api/v1/auth/logout-all")}
_BODIES = [None, {}, {"unexpected": [1, 2, 3]}, [], "text", {"name": None, "id": "abc", "email": 5}]


@pytest.mark.parametrize("method, path", sorted((m, p) for m, p, a in ROUTES if (m, p) not in _DESTRUCTIVE and a != "public"))
def test_no_route_crashes_on_unknown_ids_or_garbage_bodies(client, admin_user, auth_headers, method, path):
    headers = auth_headers(admin_user)
    for id_value in (999999, "not-a-number", "x" * 300):
        for body in _BODIES if method in ("POST", "PUT", "PATCH") else [None]:
            response = client.request(method, _fill(path, id_value), headers=headers, json=body)
            assert response.status_code < 500, f"{method} {path} id={id_value!r} body={body!r} -> {response.status_code}"


@pytest.mark.parametrize("query", [
    "page=0", "page=-1", "page=abc", "limit=0", "limit=100000", "limit=abc", "sort=nonsense", "direction=sideways",
    "profile_id=abc", "geography_id=-5", "min_score=1000", "status=unknown", "search=" + "x" * 500, "days=0", "threshold=0",
])
def test_bad_query_parameters_are_rejected_politely(client, admin_user, auth_headers, query):
    headers = auth_headers(admin_user)
    for path in ("/api/v1/businesses/", "/api/v1/exports/leads.csv", "/api/v1/exports/leads.xlsx", "/api/v1/insights/gaps", "/api/v1/insights/timeline",
                 "/api/v1/runs/", "/api/v1/users/", "/api/v1/compliance/do-not-contact"):
        response = client.get(f"{path}?{query}", headers=headers)
        assert response.status_code < 500, f"GET {path}?{query} -> {response.status_code}"


def test_login_with_garbage_is_a_client_error_not_a_crash(client):
    for body in ({}, {"email": "nobody@example.com"}, {"email": "not-an-email", "password": "x"}, {"email": None, "password": None}):
        assert client.post("/api/v1/auth/login", json=body).status_code in (400, 401, 422)


@pytest.mark.parametrize("token", ["", "abc", "a.b.c", "Bearer", "x" * 5000])
def test_malformed_tokens_are_unauthorized(client, token):
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_security_headers_do_not_leak_the_server_stack_on_errors(client):
    response = client.get("/api/v1/auth/me")
    assert "traceback" not in response.text.lower()
    assert response.json() == {"detail": "Unauthorized"}


def test_health_reports_ok_when_the_database_answers(client):
    assert client.get("/health").json() == {"status": "ok", "database": "ok", "workers": "disabled"}


def test_health_reports_unavailable_when_the_database_is_down(client):
    class BrokenSession:
        def execute(self, *_args, **_kwargs):
            raise RuntimeError("connection refused: postgres://user:secret@db/app")

    app.dependency_overrides[get_db] = lambda: BrokenSession()
    try:
        response = client.get("/health")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 503
    assert response.json() == {"status": "unavailable", "database": "down"}
    assert "secret" not in response.text


GOOD_KEY = "k" * 40


def settings_with(**values) -> Settings:
    return Settings(_env_file=None, **{"SECRET_KEY": GOOD_KEY, **values})


def test_a_short_secret_key_is_refused_at_start_up():
    with pytest.raises(ValidationError, match="at least 32 characters"):
        settings_with(SECRET_KEY="short")
    assert settings_with().SECRET_KEY == GOOD_KEY


def test_a_missing_secret_key_is_refused(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_a_malformed_encryption_key_is_refused_now_not_when_someone_saves_a_key():
    with pytest.raises(ValidationError, match="ENCRYPTION_KEY is not a valid key"):
        settings_with(ENCRYPTION_KEY="definitely-not-a-fernet-key")
    from cryptography.fernet import Fernet

    assert settings_with(ENCRYPTION_KEY=Fernet.generate_key().decode()).ENCRYPTION_KEY
    assert settings_with(ENCRYPTION_KEY="").ENCRYPTION_KEY == ""


def test_log_level_is_checked_and_normalised():
    assert settings_with(LOG_LEVEL="debug").LOG_LEVEL == "DEBUG"
    with pytest.raises(ValidationError):
        settings_with(LOG_LEVEL="chatty")


def test_env_example_lists_every_setting_and_nothing_else():
    text = (BACKEND_DIR / ".env.example").read_text(encoding="utf-8")
    documented = set(re.findall(r"^([A-Z][A-Z0-9_]*)=", text, flags=re.MULTILINE))
    assert documented == set(Settings.model_fields), (
        f"missing from .env.example: {set(Settings.model_fields) - documented}; "
        f"not a setting: {documented - set(Settings.model_fields)}"
    )


def test_env_example_values_match_the_defaults_in_the_code():
    from pydantic import TypeAdapter

    text = (BACKEND_DIR / ".env.example").read_text(encoding="utf-8")
    example = dict(re.findall(r"^([A-Z][A-Z0-9_]*)=(.*)$", text, flags=re.MULTILINE))
    for name, field in Settings.model_fields.items():
        if field.is_required() or not example.get(name, "").strip():
            continue
        assert TypeAdapter(field.annotation).validate_python(example[name].strip()) == field.default, (
            f"{name}: .env.example says {example[name]!r} but the code defaults to {field.default!r}"
        )


def _alembic(*args: str, db_url: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "DATABASE_URL": db_url}
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args], cwd=BACKEND_DIR, env=env, capture_output=True, text=True, timeout=120
    )


def test_migrations_build_exactly_the_schema_the_models_describe(tmp_path):
    url = f"sqlite:///{tmp_path / 'migrated.db'}"

    upgrade = _alembic("upgrade", "head", db_url=url)
    assert upgrade.returncode == 0, upgrade.stderr[-800:]

    check = _alembic("check", db_url=url)
    assert check.returncode == 0, f"models and migrations disagree:\n{(check.stdout + check.stderr)[-1200:]}"


def test_migrations_can_be_undone_and_redone(tmp_path):
    url = f"sqlite:///{tmp_path / 'roundtrip.db'}"
    assert _alembic("upgrade", "head", db_url=url).returncode == 0

    down = _alembic("downgrade", "base", db_url=url)
    assert down.returncode == 0, down.stderr[-800:]
    up = _alembic("upgrade", "head", db_url=url)
    assert up.returncode == 0, up.stderr[-800:]


def test_every_third_party_package_the_app_imports_is_in_requirements_txt():
    import ast
    import importlib.metadata as metadata

    def listed(filename: str) -> set[str]:
        return {
            re.split(r"[=<>\[ ]", line.strip(), maxsplit=1)[0].lower().replace("_", "-")
            for line in (BACKEND_DIR / filename).read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith(("#", "-"))
        }

    runtime, development = listed("requirements.txt"), listed("requirements-dev.txt")
    distributions = metadata.packages_distributions()

    def missing_from(folder: str, allowed: set[str]) -> list[str]:
        modules: set[str] = set()
        for source in (BACKEND_DIR / folder).rglob("*.py"):
            for node in ast.walk(ast.parse(source.read_text(encoding="utf-8"))):
                if isinstance(node, ast.Import):
                    modules.update(alias.name.split(".")[0] for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                    modules.add(node.module.split(".")[0])
        third_party = {m for m in modules if m not in sys.stdlib_module_names and m not in {"app", "scripts"}}
        return sorted(
            module for module in third_party
            if not any(dist.lower().replace("_", "-") in allowed for dist in distributions.get(module, [module]))
        )

    assert not missing_from("app", runtime), f"the app imports packages missing from requirements.txt: {missing_from('app', runtime)}"
    assert not missing_from("scripts", runtime | development), "a script imports a package that is in neither requirements file"
