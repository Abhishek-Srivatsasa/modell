from functools import lru_cache
from typing import List

from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = "development"

    database_url: str = "postgresql+asyncpg://pratyaksha:pratyaksha@db:5432/pratyaksha"
    sync_database_url: str = "postgresql://pratyaksha:pratyaksha@db:5432/pratyaksha"
    redis_url: str = "redis://redis:6379/0"

    minio_endpoint: str = "http://minio:9000"
    minio_access_key: str = "changeme"
    minio_secret_key: str = "changeme_secret"

    milvus_host: str = "milvus"

    jwt_secret_key: str = "supersecretjwtkey"
    jwt_algorithm: str = "HS256"

    use_mock_models: bool = True

    cors_origins: List[str] = []

    n8n_webhook_url: AnyHttpUrl | None = None

    @field_validator("cors_origins", mode="before")
    @classmethod
    def assemble_cors_origins(cls, value: str | List[str]) -> List[str]:
        """Parse CORS origins from a comma-separated string or list."""
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        if isinstance(value, list):
            return value
        return []


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings instance."""
    return Settings()

