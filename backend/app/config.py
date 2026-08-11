"""Environment-backed application settings."""

from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Load application configuration from environment variables or the root .env file."""

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str
    qdrant_url: str
    qdrant_api_key: SecretStr
    redis_url: str | None = None
    upstash_redis_rest_url: str | None = None
    upstash_redis_rest_token: SecretStr | None = None
    groq_api_key: SecretStr
    langsmith_api_key: SecretStr | None = None
    langsmith_tracing: bool = False
    secret_key: SecretStr | None = None

    @property
    def async_database_url(self) -> str:
        """Return DATABASE_URL normalized for SQLAlchemy's asyncpg driver."""
        if self.database_url.startswith("postgresql+asyncpg://"):
            return self.database_url
        if self.database_url.startswith("postgresql://"):
            return self.database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        raise ValueError("DATABASE_URL must use a PostgreSQL URL")


@lru_cache
def get_settings() -> Settings:
    """Return the cached settings instance; validation errors fail startup closed."""
    return Settings()
