import os
from collections.abc import AsyncGenerator
from functools import lru_cache

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import BaseAppSettings, Settings, TestingSettings
from database.session import AsyncSessionLocal
from security.interfaces import JWTAuthManagerInterface
from security.token_manager import JWTAuthManager


@lru_cache
def get_settings() -> BaseAppSettings:
    """Return application settings based on the current environment."""
    environment = os.getenv("ENVIRONMENT", "developing")
    if environment == "testing":
        return TestingSettings()
    return Settings()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a DB session and closes it after the request."""
    async with AsyncSessionLocal() as session:
        yield session


def get_jwt_auth_manager(
    settings: Settings = Depends(get_settings),
) -> JWTAuthManagerInterface:
    """FastAPI dependency that builds a JWTAuthManager from current settings."""
    return JWTAuthManager(
        secret_key_access=settings.SECRET_KEY_ACCESS,
        secret_key_refresh=settings.SECRET_KEY_REFRESH,
        algorithm=settings.JWT_SIGNING_ALGORITHM,
    )
