import os
import secrets
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseAppSettings(BaseSettings):
    """Settings shared by every environment (local, docker, tests)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    BASE_DIR: Path = Path(__file__).parent.parent


class Settings(BaseAppSettings):
    """Settings for local development, Docker, and production."""

    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "online_cinema")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "postgres")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "postgres")
    POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", 5432))

    SECRET_KEY_ACCESS: str = os.getenv("SECRET_KEY_ACCESS", secrets.token_urlsafe(32))
    SECRET_KEY_REFRESH: str = os.getenv("SECRET_KEY_REFRESH", secrets.token_urlsafe(32))
    JWT_SIGNING_ALGORITHM: str = os.getenv("JWT_SIGNING_ALGORITHM", "HS256")

    @property
    def database_url(self) -> str:
        """Async SQLAlchemy connection string (asyncpg driver)."""
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


class TestingSettings(BaseAppSettings):
    """Settings for pytest — no dependency on real .env or Postgres."""

    SECRET_KEY_ACCESS: str = "test-secret-key-access"
    SECRET_KEY_REFRESH: str = "test-secret-key-refresh"
    JWT_SIGNING_ALGORITHM: str = "HS256"

    @property
    def database_url(self) -> str:
        """In-memory SQLite for fast, isolated test runs."""
        return "sqlite+aiosqlite:///:memory:"
