import os

from database.models.movies import Certification, Director, Genre, Movie, Star

os.environ.setdefault("ENVIRONMENT", "testing")

from collections.abc import AsyncGenerator
from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from config.dependencies import get_current_user, get_s3_storage, get_settings
from config.settings import TestingSettings
from database.models.accounts import (
    GenderEnum,
    User,
    UserGroup,
    UserGroupEnum,
    UserProfile,
)
from database.models.base import Base
from database.session import get_db
from exceptions.storage import S3FileUploadError
from main import app
from storages.interfaces import S3StorageInterface


@pytest_asyncio.fixture()
async def test_engine():
    """In-memory SQLite, one connection shared across the whole test (StaticPool)."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture()
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    session_factory = async_sessionmaker(bind=test_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture()
async def user_group(db_session: AsyncSession) -> UserGroup:
    """Registration depends on a USER group already existing."""
    group = UserGroup(name=UserGroupEnum.USER)
    db_session.add(group)
    await db_session.commit()
    await db_session.refresh(group)
    return group


@pytest_asyncio.fixture()
async def client(db_session: AsyncSession):
    """HTTP client with DB and settings dependencies overridden for tests."""

    async def override_get_db():
        yield db_session

    def override_get_settings():
        return TestingSettings()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_settings] = override_get_settings

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def mock_celery_tasks():
    """Автоматично мокає метод .delay() для всіх Celery тасок у тестах."""
    with patch("celery.app.task.Task.delay") as mock_delay:
        yield mock_delay


class FakeS3Storage(S3StorageInterface):
    """In-memory stand-in for S3StorageClient — no real network calls in tests."""

    def __init__(self) -> None:
        self.uploaded: dict[str, bytes] = {}
        self.should_fail = False

    async def upload_file(self, file_data: bytes, file_name: str) -> str:
        if self.should_fail:
            raise S3FileUploadError("Simulated upload failure.")
        self.uploaded[file_name] = file_data
        return await self.get_file_url(file_name)

    async def get_file_url(self, file_name: str) -> str:
        return f"http://fake-s3.local/test-bucket/{file_name}"

    async def delete_file(self, file_name: str) -> None:
        self.uploaded.pop(file_name, None)


@pytest_asyncio.fixture()
async def fake_storage() -> FakeS3Storage:
    return FakeS3Storage()


@pytest_asyncio.fixture()
async def active_user(db_session: AsyncSession, user_group: UserGroup) -> User:
    user = User.create(
        email="owner@example.com",
        raw_password="StrongP@ssw0rd!",
        group_id=user_group.id,
    )
    user.is_active = True
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture()
async def other_user(db_session: AsyncSession, user_group: UserGroup) -> User:
    user = User.create(
        email="other@example.com",
        raw_password="StrongP@ssw0rd!",
        group_id=user_group.id,
    )
    user.is_active = True
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture()
async def user_profile(db_session: AsyncSession, active_user: User) -> UserProfile:
    profile = UserProfile(
        user_id=active_user.id,
        first_name="Test",
        last_name="User",
        gender=GenderEnum.WOMAN,
        info="Test bio",
    )
    db_session.add(profile)
    await db_session.commit()
    await db_session.refresh(profile)
    return profile


@pytest_asyncio.fixture()
async def authenticated_client(client, active_user: User, fake_storage: FakeS3Storage):
    """Same AsyncClient as `client`, but requests are authenticated as active_user."""
    app.dependency_overrides[get_current_user] = lambda: active_user
    app.dependency_overrides[get_s3_storage] = lambda: fake_storage
    yield client
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_s3_storage, None)


@pytest_asyncio.fixture()
async def admin_group(db_session: AsyncSession) -> UserGroup:
    group = UserGroup(name=UserGroupEnum.ADMIN)
    db_session.add(group)
    await db_session.commit()
    await db_session.refresh(group)
    return group


@pytest_asyncio.fixture()
async def moderator_group(db_session: AsyncSession) -> UserGroup:
    group = UserGroup(name=UserGroupEnum.MODERATOR)
    db_session.add(group)
    await db_session.commit()
    await db_session.refresh(group)
    return group


@pytest_asyncio.fixture()
async def admin_user(db_session: AsyncSession, admin_group: UserGroup) -> User:
    user = User.create(
        email="admin@example.com",
        raw_password="StrongP@ssw0rd!",
        group_id=admin_group.id,
    )
    user.is_active = True
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture()
async def authenticated_admin_client(
    client, admin_user: User, fake_storage: FakeS3Storage
):
    """Same AsyncClient as `client`, but requests are authenticated as admin_user."""
    app.dependency_overrides[get_current_user] = lambda: admin_user
    app.dependency_overrides[get_s3_storage] = lambda: fake_storage
    yield client
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_s3_storage, None)


@pytest_asyncio.fixture()
async def moderator_user(db_session: AsyncSession, moderator_group: UserGroup) -> User:
    user = User.create(
        email="moderator@example.com",
        raw_password="StrongP@ssw0rd!",
        group_id=moderator_group.id,
    )
    user.is_active = True
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture()
async def authenticated_moderator_client(
    client, moderator_user: User, fake_storage: FakeS3Storage
):
    """Same AsyncClient as `client`, but requests
    are authenticated as moderator_user."""
    app.dependency_overrides[get_current_user] = lambda: moderator_user
    app.dependency_overrides[get_s3_storage] = lambda: fake_storage
    yield client
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_s3_storage, None)


@pytest_asyncio.fixture()
async def certification(db_session: AsyncSession) -> Certification:
    cert = Certification(name="PG-13")
    db_session.add(cert)
    await db_session.commit()
    await db_session.refresh(cert)
    return cert


@pytest_asyncio.fixture()
async def genre(db_session: AsyncSession) -> Genre:
    g = Genre(name="Action")
    db_session.add(g)
    await db_session.commit()
    await db_session.refresh(g)
    return g


@pytest_asyncio.fixture()
async def director(db_session: AsyncSession) -> Director:
    d = Director(name="Christopher Nolan")
    db_session.add(d)
    await db_session.commit()
    await db_session.refresh(d)
    return d


@pytest_asyncio.fixture()
async def star(db_session: AsyncSession) -> Star:
    s = Star(name="Leonardo DiCaprio")
    db_session.add(s)
    await db_session.commit()
    await db_session.refresh(s)
    return s


async def create_movie(
    db_session: AsyncSession, certification: Certification, **overrides
) -> Movie:
    """Test helper, not a fixture — call directly so each test
    controls its own field values."""
    defaults = {
        "name": "Inception",
        "year": 2010,
        "time": 148,
        "imdb": 8.8,
        "votes": 2000000,
        "description": "A thief who steals corporate secrets "
        "through dream-sharing technology.",
        "price": 9.99,
        "certification_id": certification.id,
    }
    defaults.update(overrides)
    movie = Movie(**defaults)
    db_session.add(movie)
    await db_session.commit()
    await db_session.refresh(movie, attribute_names=["genres", "directors", "stars"])
    return movie
