from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict


load_dotenv()


class Settings(BaseSettings):
    # Core
    DATABASE_URL: str = "sqlite:///./market_scout.db"
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    CORS_ORIGINS: str = "http://localhost:5173"

    # Encrypts API keys saved from the UI. Leave empty to derive one from SECRET_KEY
    # (then rotating SECRET_KEY means re-entering saved keys).
    ENCRYPTION_KEY: str = ""

    # Scouting
    # Identifies us to the free public services we call (their usage policies ask for it).
    SCOUT_CONTACT_EMAIL: str = ""
    OVERPASS_URL: str = "https://overpass-api.de/api/interpreter"
    OVERPASS_MIN_INTERVAL_SECONDS: float = 5.0
    # Optional fallback if no Places key is saved from the UI.
    GOOGLE_PLACES_API_KEY: str = ""
    # An estimate for the run-cost preview only -- check Google's current pricing.
    PLACES_COST_PER_REQUEST_USD: float = 0.035
    RUN_WORKER_ENABLED: bool = True
    RUN_MAX_TASKS: int = 2000
    # A search finished within this many days is skipped when a run repeats it.
    RUN_TASK_CACHE_DAYS: int = 7
    ENRICHMENT_CONCURRENCY: int = 4

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def is_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
