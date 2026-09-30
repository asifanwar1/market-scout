import atexit
import os
import shutil
import tempfile

# Point the app at a throwaway SQLite file *before* importing it. A file (not
# ":memory:") because the background worker uses connections from other threads.
_TEST_DB_DIR = tempfile.mkdtemp(prefix="market-scout-tests-")
atexit.register(shutil.rmtree, _TEST_DB_DIR, ignore_errors=True)
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB_DIR}/test.db"
os.environ["SECRET_KEY"] = "test-secret-key-not-for-production"
# Tests drive runs directly; a live background thread would race them.
os.environ["RUN_WORKER_ENABLED"] = "false"
# Never pick up a real key or contact address from a developer's .env.
os.environ["GOOGLE_PLACES_API_KEY"] = ""
os.environ["SCOUT_CONTACT_EMAIL"] = ""

import pytest
from fastapi.testclient import TestClient

from app.core.limiter import limiter
from app.core.security import create_access_token, hash_password
from app.database import Base, SessionLocal, engine
from app.dependencies import get_db
from app.features.users.models import User, UserRole
from app.main import app


DEFAULT_PASSWORD = "Str0ng!Passw0rd"


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    limiter.reset()
    yield


@pytest.fixture(scope="session", autouse=True)
def _prepare_schema():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture()
def db_session():
    # Each test runs inside an outer transaction; the session's commits only release
    # a SAVEPOINT, so rolling back the outer transaction undoes everything.
    connection = engine.connect()
    outer_transaction = connection.begin()
    session = SessionLocal(bind=connection, join_transaction_mode="create_savepoint")

    yield session

    session.close()
    outer_transaction.rollback()
    connection.close()


@pytest.fixture()
def client(db_session):
    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def make_user(db_session):
    def _make(
        email: str,
        password: str = DEFAULT_PASSWORD,
        role: UserRole = UserRole.SALES,
        full_name: str = "Test User",
        is_active: bool = True,
    ) -> User:
        user = User(
            email=email,
            full_name=full_name,
            hashed_password=hash_password(password),
            role=role.value,
            is_active=is_active,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user

    return _make


@pytest.fixture()
def auth_headers():
    def _headers(user: User) -> dict[str, str]:
        token = create_access_token({"sub": str(user.id), "tv": user.token_version})
        return {"Authorization": f"Bearer {token}"}

    return _headers


@pytest.fixture()
def admin_user(make_user):
    return make_user("admin@example.com", role=UserRole.ADMIN, full_name="Admin User")


@pytest.fixture()
def sales_user(make_user):
    return make_user("sales@example.com", role=UserRole.SALES, full_name="Sales User")
