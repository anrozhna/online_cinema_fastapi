from typing import Generator

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from database.models.accounts import User, UserGroup, UserGroupEnum
from database.models.base import Base
from database.models.movies import Certification, Movie


@pytest.fixture()
def sync_engine():
    """In-memory SQLite engine, recreated for each test for full isolation.

    Foreign key enforcement is off in SQLite by default (unlike PostgreSQL,
    where ondelete='CASCADE' is always active) — enabling it here makes
    these tests actually exercise the cascade behavior declared in models,
    rather than silently passing regardless of it.
    """
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture()
def sync_session(sync_engine) -> Generator[Session]:
    session_factory = sessionmaker(bind=sync_engine)
    session = session_factory()
    yield session
    session.close()


@pytest.fixture()
def sync_user_group(sync_session) -> UserGroup:
    group = UserGroup(name=UserGroupEnum.USER)
    sync_session.add(group)
    sync_session.commit()
    return group


@pytest.fixture()
def sync_user(sync_session, sync_user_group) -> User:
    """Bypasses the password setter/bcrypt entirely — these tests only
    need a real User row for FK purposes, not password correctness."""
    u = User(email="test-user@example.com", group_id=sync_user_group.id, is_active=True)
    u._hashed_password = "test-hash"
    sync_session.add(u)
    sync_session.commit()
    return u


@pytest.fixture()
def sync_certification(sync_session) -> Certification:
    cert = Certification(name="PG-13")
    sync_session.add(cert)
    sync_session.commit()
    return cert


@pytest.fixture()
def sync_movie(sync_session, sync_certification) -> Movie:
    m = Movie(
        name="Inception",
        year=2010,
        time=148,
        imdb=8.8,
        votes=2000000,
        description="A thief who steals corporate secrets "
        "through dream-sharing technology.",
        price=9.99,
        certification_id=sync_certification.id,
    )
    sync_session.add(m)
    sync_session.commit()
    return m


@pytest.fixture()
def sync_movie_data(sync_certification) -> dict:
    """Base valid attributes for a Movie, without relationships."""
    return {
        "name": "Inception",
        "year": 2010,
        "time": 148,
        "imdb": 8.8,
        "votes": 2000000,
        "description": "A thief who steals corporate secrets through "
        "dream-sharing technology.",
        "price": 9.99,
        "certification_id": sync_certification.id,
    }
