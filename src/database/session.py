from typing import Annotated, AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from config.settings import Settings

settings = Settings()

engine: AsyncEngine = create_async_engine(
    settings.database_url, echo=False, future=True
)

AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a DB session and closes it after the request."""
    async with AsyncSessionLocal() as session:
        yield session


DataBase = Annotated[AsyncSession, Depends(get_db)]
