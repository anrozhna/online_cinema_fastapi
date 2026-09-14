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
    LOGIN_TIME_DAYS: int = 7

    PATH_TO_EMAIL_TEMPLATES_DIR: str = str(BASE_DIR / "notifications" / "templates")
    ACTIVATION_EMAIL_TEMPLATE_NAME: str = "activation_request.html"
    ACTIVATION_COMPLETE_EMAIL_TEMPLATE_NAME: str = "activation_complete.html"
    PASSWORD_RESET_TEMPLATE_NAME: str = "password_reset_request.html"
    PASSWORD_RESET_COMPLETE_TEMPLATE_NAME: str = "password_reset_complete.html"

    EMAIL_HOST: str = os.getenv("EMAIL_HOST", "host")
    EMAIL_PORT: int = int(os.getenv("EMAIL_PORT", 25))
    EMAIL_HOST_USER: str = os.getenv("EMAIL_HOST_USER", "testuser")
    EMAIL_HOST_PASSWORD: str = os.getenv("EMAIL_HOST_PASSWORD", "test_password")
    EMAIL_USE_TLS: bool = os.getenv("EMAIL_USE_TLS", "False").lower() == "true"
    MAILHOG_API_PORT: int = int(os.getenv("MAILHOG_API_PORT", 8025))

    SITE_URL: str = os.getenv("SITE_URL", "http://127.0.0.1:8000")


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

    REDIS_HOST: str = os.getenv("REDIS_HOST", "redis")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", 6379))

    S3_STORAGE_HOST: str = os.getenv("S3_STORAGE_HOST", "minio")
    S3_STORAGE_PORT: int = int(os.getenv("S3_STORAGE_PORT", 9000))
    S3_BUCKET_NAME: str = os.getenv("S3_BUCKET_NAME", "online-cinema-storage")
    MINIO_ROOT_USER: str = os.getenv("MINIO_ROOT_USER", "minioadmin")
    MINIO_ROOT_PASSWORD: str = os.getenv("MINIO_ROOT_PASSWORD", "minioadmin123")

    @property
    def s3_endpoint_url(self) -> str:
        """S3-compatible endpoint (MinIO locally, real AWS S3 URL in production)."""
        return f"http://{self.S3_STORAGE_HOST}:{self.S3_STORAGE_PORT}"

    @property
    def redis_url(self) -> str:
        """Connection string used as both Celery broker and result backend."""
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

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

    @property
    def redis_url(self) -> str:
        """Not backed by a real Redis in tests; celery tasks should be mocked."""
        return "redis://localhost:6379/0"
