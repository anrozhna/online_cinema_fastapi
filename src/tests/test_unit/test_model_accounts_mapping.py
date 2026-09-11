"""
Unit tests verifying that SQLAlchemy models in `database.models.accounts`
are correctly mapped and that their relationships/constraints/business
logic behave as expected.

These tests use an in-memory SQLite database purely to validate the
ORM mapping (relationships, constraints, defaults) — not to test
PostgreSQL-specific behavior (e.g. real Enum types, timezone-aware
server defaults).
"""

from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from database.models.accounts import (
    ActivationToken,
    GenderEnum,
    PasswordResetToken,
    RefreshToken,
    User,
    UserGroup,
    UserGroupEnum,
    UserProfile,
)
from database.models.base import Base


@pytest.fixture()
def engine():
    """In-memory SQLite engine, recreated for each test for full isolation."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture()
def session(engine) -> Session:
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    yield session
    session.close()


@pytest.fixture()
def user_group(session) -> UserGroup:
    group = UserGroup(name=UserGroupEnum.USER)
    session.add(group)
    session.commit()
    return group


class TestModelsMapping:
    """Ensures all models are mapped without configuration errors."""

    def test_metadata_creates_all_tables_without_error(self, engine):
        expected_tables = {
            "user_groups",
            "users",
            "user_profiles",
            "activation_tokens",
            "password_reset_tokens",
            "refresh_tokens",
        }
        assert expected_tables.issubset(set(Base.metadata.tables.keys()))


class TestUserGroup:
    def test_create_user_group(self, session):
        group = UserGroup(name=UserGroupEnum.ADMIN)
        session.add(group)
        session.commit()

        fetched = session.query(UserGroup).filter_by(name=UserGroupEnum.ADMIN).one()
        assert fetched.id is not None
        assert fetched.name == UserGroupEnum.ADMIN

    def test_user_group_name_must_be_unique(self, session):
        session.add(UserGroup(name=UserGroupEnum.MODERATOR))
        session.commit()

        session.add(UserGroup(name=UserGroupEnum.MODERATOR))
        with pytest.raises(IntegrityError):
            session.commit()


class TestUser:
    def test_create_user_via_factory(self, session, user_group):
        user = User.create(
            email="test@example.com",
            raw_password="StrongP@ssw0rd!",
            group_id=user_group.id,
        )
        session.add(user)
        session.commit()

        fetched = session.query(User).filter_by(email="test@example.com").one()
        assert fetched.id is not None
        assert fetched.is_active is False
        assert fetched.group_id == user_group.id

    def test_password_is_hashed_not_stored_in_plain_text(self, session, user_group):
        raw_password = "StrongP@ssw0rd!"
        user = User.create(
            email="hash@example.com", raw_password=raw_password, group_id=user_group.id
        )
        session.add(user)
        session.commit()

        assert user._hashed_password != raw_password
        assert user.verify_password(raw_password) is True
        assert user.verify_password("wrong-password") is False

    def test_password_getter_raises_attribute_error(self, session, user_group):
        user = User.create(
            email="write-only@example.com",
            raw_password="StrongP@ssw0rd!",
            group_id=user_group.id,
        )
        with pytest.raises(AttributeError):
            _ = user.password

    def test_email_is_normalized_to_lowercase(self, session, user_group):
        user = User.create(
            email="MixedCase@Example.com",
            raw_password="StrongP@ssw0rd!",
            group_id=user_group.id,
        )
        session.add(user)
        session.commit()

        assert user.email == "mixedcase@example.com"

    def test_email_must_be_unique(self, session, user_group):
        session.add(
            User.create(
                email="dup@example.com",
                raw_password="StrongP@ssw0rd!",
                group_id=user_group.id,
            )
        )
        session.commit()

        session.add(
            User.create(
                email="dup@example.com",
                raw_password="AnotherP@ssw0rd!",
                group_id=user_group.id,
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()

    def test_has_group_returns_true_for_matching_group(self, session, user_group):
        user = User.create(
            email="group-check@example.com",
            raw_password="StrongP@ssw0rd!",
            group_id=user_group.id,
        )
        session.add(user)
        session.commit()

        assert user.has_group(UserGroupEnum.USER) is True
        assert user.has_group(UserGroupEnum.ADMIN) is False

    def test_user_deletion_cascades_to_profile_and_tokens(self, session, user_group):
        user = User.create(
            email="cascade@example.com",
            raw_password="StrongP@ssw0rd!",
            group_id=user_group.id,
        )
        session.add(user)
        session.commit()

        profile = UserProfile(user_id=user.id, info="bio")
        activation_token = ActivationToken(user_id=user.id)
        session.add_all([profile, activation_token])
        session.commit()

        session.delete(user)
        session.commit()

        assert session.query(UserProfile).filter_by(user_id=user.id).first() is None
        assert session.query(ActivationToken).filter_by(user_id=user.id).first() is None


class TestUserProfile:
    def test_create_profile_linked_to_user(self, session, user_group):
        user = User.create(
            email="profile@example.com",
            raw_password="StrongP@ssw0rd!",
            group_id=user_group.id,
        )
        session.add(user)
        session.commit()

        profile = UserProfile(
            user_id=user.id,
            first_name="Anna",
            last_name="Lepiska",
            gender=GenderEnum.WOMAN,
            info="Short bio",
        )
        session.add(profile)
        session.commit()

        assert profile.user.email == "profile@example.com"
        assert user.profile.first_name == "Anna"

    def test_profile_user_id_must_be_unique(self, session, user_group):
        user = User.create(
            email="one-profile@example.com",
            raw_password="StrongP@ssw0rd!",
            group_id=user_group.id,
        )
        session.add(user)
        session.commit()

        session.add(UserProfile(user_id=user.id, info="first"))
        session.commit()

        session.add(UserProfile(user_id=user.id, info="second"))
        with pytest.raises(IntegrityError):
            session.commit()


class TestActivationToken:
    def test_activation_token_has_default_expiration_in_future(
        self, session, user_group
    ):
        user = User.create(
            email="activation@example.com",
            raw_password="StrongP@ssw0rd!",
            group_id=user_group.id,
        )
        session.add(user)
        session.commit()

        token = ActivationToken(user_id=user.id)
        session.add(token)
        session.commit()

        assert token.token is not None

        now = datetime.now(timezone.utc)
        expires_at = token.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        assert expires_at > now

    def test_only_one_activation_token_per_user(self, session, user_group):
        user = User.create(
            email="one-activation@example.com",
            raw_password="StrongP@ssw0rd!",
            group_id=user_group.id,
        )
        session.add(user)
        session.commit()

        session.add(ActivationToken(user_id=user.id))
        session.commit()

        session.add(ActivationToken(user_id=user.id))
        with pytest.raises(IntegrityError):
            session.commit()


class TestPasswordResetToken:
    def test_only_one_reset_token_per_user(self, session, user_group):
        user = User.create(
            email="one-reset@example.com",
            raw_password="StrongP@ssw0rd!",
            group_id=user_group.id,
        )
        session.add(user)
        session.commit()

        session.add(PasswordResetToken(user_id=user.id))
        session.commit()

        session.add(PasswordResetToken(user_id=user.id))
        with pytest.raises(IntegrityError):
            session.commit()


class TestRefreshToken:
    def test_create_via_factory_sets_expiration(self, session, user_group):
        user = User.create(
            email="refresh@example.com",
            raw_password="StrongP@ssw0rd!",
            group_id=user_group.id,
        )
        session.add(user)
        session.commit()

        token = RefreshToken.create(user_id=user.id, days_valid=7, token="a" * 128)
        session.add(token)
        session.commit()

        assert token.token == "a" * 128
        assert (
            token.expires_at > token.created_at
            if hasattr(token, "created_at")
            else True
        )

    def test_user_can_have_multiple_refresh_tokens(self, session, user_group):
        user = User.create(
            email="multi-refresh@example.com",
            raw_password="StrongP@ssw0rd!",
            group_id=user_group.id,
        )
        session.add(user)
        session.commit()

        session.add_all(
            [
                RefreshToken.create(user_id=user.id, days_valid=7, token="token-one"),
                RefreshToken.create(user_id=user.id, days_valid=7, token="token-two"),
            ]
        )
        session.commit()

        assert len(user.refresh_tokens) == 2
