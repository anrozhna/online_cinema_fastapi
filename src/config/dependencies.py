from collections.abc import AsyncGenerator
from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import Settings
from database.session import AsyncSessionLocal


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings (reads .env only once per process)."""
    return Settings()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a DB session and closes it after the request."""
    async with AsyncSessionLocal() as session:
        yield session
