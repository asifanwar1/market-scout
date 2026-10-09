from cryptography.fernet import Fernet
from dotenv import load_dotenv
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

SECRET_KEY_MIN_LENGTH = 32
LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")


load_dotenv()


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./market_scout.db"
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    CORS_ORIGINS: str = "http://localhost:5173"
    LOG_LEVEL: str = "INFO"

    ENCRYPTION_KEY: str = ""

    SCOUT_CONTACT_EMAIL: str = ""
    OVERPASS_URL: str = "https://overpass-api.de/api/interpreter"
    OVERPASS_MIN_INTERVAL_SECONDS: float = 5.0
    GOOGLE_PLACES_API_KEY: str = ""
    PLACES_COST_PER_REQUEST_USD: float = 0.035
    DEAL_CURRENCY: str = "USD"
    HERE_API_KEY: str = ""
    HERE_COST_PER_REQUEST_USD: float = 0.0
    TOMTOM_API_KEY: str = ""
    TOMTOM_COST_PER_REQUEST_USD: float = 0.0
    RUN_WORKER_ENABLED: bool = True
    RUN_MAX_TASKS: int = 2000
    RUN_TASK_CACHE_DAYS: int = 7
    ENRICHMENT_CONCURRENCY: int = 4

    OVERTURE_DB_PATH: str = "./data/overture.sqlite"
    OVERTURE_MIN_CONFIDENCE: float = 0.3

    FOURSQUARE_DB_PATH: str = "./data/foursquare.sqlite"

    IMPORTS_DIR: str = "./imports"
    IMPORT_MAX_MB: int = 10
    IMPORT_MAX_ROWS: int = 50000
    IMPORT_BATCH_PAUSE_SECONDS: float = 0.15

    GOOGLE_SERVICE_ACCOUNT_JSON: str = ""
    SHEETS_API_URL: str = "https://sheets.googleapis.com/v4"
    GOOGLE_TOKEN_URL: str = "https://oauth2.googleapis.com/token"
    SHEETS_AUTO_SYNC_DELAY_SECONDS: float = 20.0

    @field_validator("SECRET_KEY")
    @classmethod
    def _secret_key_must_be_strong(cls, value: str) -> str:
        if len(value) < SECRET_KEY_MIN_LENGTH:
            raise ValueError(
                f"SECRET_KEY must be at least {SECRET_KEY_MIN_LENGTH} characters. Generate one with: "
                'python -c "import secrets; print(secrets.token_urlsafe(48))"'
            )
        return value

    @field_validator("LOG_LEVEL")
    @classmethod
    def _log_level_must_be_known(cls, value: str) -> str:
        level = value.strip().upper()
        if level not in LOG_LEVELS:
            raise ValueError(f"LOG_LEVEL must be one of {', '.join(LOG_LEVELS)}")
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
