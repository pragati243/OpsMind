"""Environment-backed application settings."""

from functools import lru_cache
from pathlib import Path
import ssl
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

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
    rag_similarity_threshold: float = 0.55
    rag_top_k: int = 5
    qdrant_collection_name: str = "keystone_policy_documents"
    sql_max_row_limit: int = 100
    router_confidence_threshold: float = 0.75

    @property
    def async_database_url(self) -> str:
        """Return DATABASE_URL normalized for SQLAlchemy's asyncpg driver."""
        if self.database_url.startswith("postgresql+asyncpg://"):
            url = self.database_url
        elif self.database_url.startswith("postgresql://"):
            url = self.database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        else:
            raise ValueError("DATABASE_URL must use a PostgreSQL URL")
        parsed = urlsplit(url)
        query = [(key, value) for key, value in parse_qsl(parsed.query) if key not in {"sslmode", "channel_binding"}]
        return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(query), parsed.fragment))

    @property
    def async_database_connect_args(self) -> dict[str, ssl.SSLContext]:
        """Translate PostgreSQL sslmode into asyncpg's SSL context argument."""
        sslmode = dict(parse_qsl(urlsplit(self.database_url).query)).get("sslmode", "").lower()
        if sslmode in {"require", "verify-ca", "verify-full"}:
            return {"ssl": ssl.create_default_context()}
        return {}


@lru_cache
def get_settings() -> Settings:
    """Return the cached settings instance; validation errors fail startup closed."""
    return Settings()
