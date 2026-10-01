from cryptography.fernet import Fernet
from dotenv import load_dotenv
from pydantic import field_validator
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
    LOG_LEVEL: str = "INFO"

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

    # Google Sheets live mirror
    # Optional fallback if no service-account key is saved from the UI: the key file's whole JSON.
    GOOGLE_SERVICE_ACCOUNT_JSON: str = ""
    SHEETS_API_URL: str = "https://sheets.googleapis.com/v4"
    GOOGLE_TOKEN_URL: str = "https://oauth2.googleapis.com/token"
    # After leads change (a run, an edit, a do-not-contact) the sheet is refreshed once this many
    # seconds have passed, so a burst of edits costs one update. Negative turns it off.
    SHEETS_AUTO_SYNC_DELAY_SECONDS: float = 20.0

    @field_validator("SECRET_KEY")
    @classmethod
    def _secret_key_must_be_strong(cls, value: str) -> str:
        # It signs every login token; a guessable one lets anyone sign in as anybody.
        if len(value) < 32:
            raise ValueError(
                "SECRET_KEY must be at least 32 characters. Generate one with: "
                'python -c "import secrets; print(secrets.token_urlsafe(48))"'
            )
        return value

    @field_validator("LOG_LEVEL")
    @classmethod
    def _log_level_must_be_known(cls, value: str) -> str:
        level = value.strip().upper()
        if level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError("LOG_LEVEL must be one of DEBUG, INFO, WARNING, ERROR, CRITICAL")
        return level

    @field_validator("ENCRYPTION_KEY")
    @classmethod
    def _encryption_key_must_be_a_fernet_key(cls, value: str) -> str:
        if value:
            try:
                Fernet(value.encode("utf-8"))
            except ValueError:
                raise ValueError(
                    "ENCRYPTION_KEY is not a valid key. Generate one with: "
                    'python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
                ) from None
        return value

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def is_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
