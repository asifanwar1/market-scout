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
# Pin every setting the tests rely on, so a developer's own .env (another port, a real key, tuned
# limits) can never change the results. Environment variables beat .env.
for name, value in {
    "GOOGLE_PLACES_API_KEY": "",
    "SCOUT_CONTACT_EMAIL": "",
    "GOOGLE_SERVICE_ACCOUNT_JSON": "",
    "ENCRYPTION_KEY": "",
    "CORS_ORIGINS": "http://localhost:5173",
    "LOG_LEVEL": "INFO",
    "ACCESS_TOKEN_EXPIRE_MINUTES": "30",
    "REFRESH_TOKEN_EXPIRE_DAYS": "7",
    "OVERPASS_URL": "https://overpass-api.de/api/interpreter",
    "OVERPASS_MIN_INTERVAL_SECONDS": "5",
    "PLACES_COST_PER_REQUEST_USD": "0.035",
    "RUN_MAX_TASKS": "2000",
    "RUN_TASK_CACHE_DAYS": "7",
    "ENRICHMENT_CONCURRENCY": "4",
    "SHEETS_API_URL": "https://sheets.googleapis.com/v4",
    "GOOGLE_TOKEN_URL": "https://oauth2.googleapis.com/token",
}.items():
    os.environ[name] = value
# No timers left running after a test; the debounce is tested with its own scheduler.
os.environ["SHEETS_AUTO_SYNC_DELAY_SECONDS"] = "-1"

from datetime import UTC

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
def seeded_profile(db_session):
    """Pakistan's cities and the solar profile, loaded the way `python -m scripts.seed` does."""
    from app.features.profiles.models import Profile
    from scripts.seed import seed_geographies, seed_solar_profile

    seed_geographies(db_session)
    seed_solar_profile(db_session)
    return db_session.query(Profile).filter_by(slug="solar-inverters-batteries").one()


@pytest.fixture()
def make_business(db_session, seeded_profile):
    """Build a stored lead by pushing a raw record through the real ingest path."""
    import itertools
    from datetime import datetime

    from app.core.scouting.types import RawBusiness
    from app.features.businesses.ingest import IngestContext, ingest_business
    from app.features.geographies.models import Geography
    from app.features.runs.service import _profile_scoring

    counter = itertools.count(1)
    scoring = _profile_scoring(seeded_profile)

    def _make(
        name: str = "Solar Shop",
        *,
        city: str = "lahore",
        hint: str | None = "dealer",
        phones=(),
        emails=(),
        website: str | None = None,
        address: str | None = None,
        rating: float | None = None,
        review_count: int | None = None,
        source: str = "osm",
        categories=(),
        now: datetime | None = None,
    ):
        n = next(counter)
        place = db_session.query(Geography).filter_by(slug=city).one()
        raw = RawBusiness(
            source_key=source,
            external_id=f"{source}/{n}",
            name=name,
            address=address,
            # ~1 km apart, so two test businesses are never mistaken for the same place.
            latitude=place.latitude + n * 0.01,
            longitude=place.longitude + n * 0.01,
            phones=list(phones),
            emails=list(emails),
            website=website,
            categories=list(categories),
            rating=rating,
            review_count=review_count,
        )
        context = IngestContext(
            run_id=None,
            geography_id=place.id,
            hint_segment_slug=hint,
            now=now or datetime.now(UTC),
            profile=scoring,
        )
        outcome = ingest_business(db_session, raw, context)
        db_session.commit()
        return outcome.business

    return _make


@pytest.fixture()
def admin_user(make_user):
    return make_user("admin@example.com", role=UserRole.ADMIN, full_name="Admin User")


@pytest.fixture()
def sales_user(make_user):
    return make_user("sales@example.com", role=UserRole.SALES, full_name="Sales User")
