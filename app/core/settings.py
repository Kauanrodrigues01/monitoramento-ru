from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ROOT / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    DB_HOST: str = "localhost"
    DB_PORT: str = "5432"
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str
    TEST_DB_NAME: str = "test_db"

    LOG_LEVEL: str = "INFO"
    LOG_ENV: str = "development"  # development | production

    ADMIN_API_KEY: str

    APP_GEO_SECRET: str
    GEO_SIGNATURE_MAX_SKEW_SECONDS: int = 60

    QUEUE_REPORT_COOLDOWN_MINUTES: int = 2

    REDIS_URL: str | None = None

    DEBUG: bool = False


settings = Settings()
