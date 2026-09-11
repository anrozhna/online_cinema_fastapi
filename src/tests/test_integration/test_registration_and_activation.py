from datetime import datetime, timedelta, timezone

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.accounts import ActivationToken, User


class TestRegistration:
    async def test_register_returns_201_and_creates_inactive_user(
        self, client: AsyncClient, user_group, db_session: AsyncSession
    ):
        response = await client.post(
            "/accounts/register/",
            json={"email": "new@example.com", "password": "StrongP@ssw0rd!"},
        )
        assert response.status_code == 201

        result = await db_session.execute(
            select(User).where(User.email == "new@example.com")
        )
        user = result.scalar()
        assert user is not None
        assert user.is_active is False

    async def test_register_creates_activation_token(
        self, client: AsyncClient, user_group, db_session: AsyncSession
    ):
        await client.post(
            "/accounts/register/",
            json={"email": "token-check@example.com", "password": "StrongP@ssw0rd!"},
        )
        result = await db_session.execute(
            select(User).where(User.email == "token-check@example.com")
        )
        user = result.scalar_one()

        result = await db_session.execute(
            select(ActivationToken).where(ActivationToken.user_id == user.id)
        )
        assert result.scalar() is not None

    async def test_register_duplicate_email_returns_409(
        self, client: AsyncClient, user_group
    ):
        payload = {"email": "dup@example.com", "password": "StrongP@ssw0rd!"}
        await client.post("/accounts/register/", json=payload)
        response = await client.post("/accounts/register/", json=payload)
        assert response.status_code == 409

    async def test_register_weak_password_returns_422(
        self, client: AsyncClient, user_group
    ):
        response = await client.post(
            "/accounts/register/",
            json={"email": "weak@example.com", "password": "weak"},
        )
        assert response.status_code == 422


class TestActivation:
    async def test_activate_with_valid_token_returns_200_and_activates(
        self, client: AsyncClient, user_group, db_session: AsyncSession
    ):
        await client.post(
            "/accounts/register/",
            json={"email": "activate-me@example.com", "password": "StrongP@ssw0rd!"},
        )
        result = await db_session.execute(
            select(User).where(User.email == "activate-me@example.com")
        )
        user = result.scalar_one()
        result = await db_session.execute(
            select(ActivationToken).where(ActivationToken.user_id == user.id)
        )
        token = result.scalar_one()

        response = await client.post(
            "/accounts/activate/",
            json={"email": "activate-me@example.com", "token": token.token},
        )
        assert response.status_code == 200

        await db_session.refresh(user)
        assert user.is_active is True

    async def test_activate_with_wrong_token_returns_400(
        self, client: AsyncClient, user_group
    ):
        await client.post(
            "/accounts/register/",
            json={"email": "wrong-token@example.com", "password": "StrongP@ssw0rd!"},
        )
        response = await client.post(
            "/accounts/activate/",
            json={"email": "wrong-token@example.com", "token": "not-the-real-token"},
        )
        assert response.status_code == 400

    async def test_activate_expired_token_returns_400_and_deletes_token(
        self, client: AsyncClient, user_group, db_session: AsyncSession
    ):
        await client.post(
            "/accounts/register/",
            json={"email": "expired@example.com", "password": "StrongP@ssw0rd!"},
        )
        result = await db_session.execute(
            select(User).where(User.email == "expired@example.com")
        )
        user = result.scalar_one()
        result = await db_session.execute(
            select(ActivationToken).where(ActivationToken.user_id == user.id)
        )
        token = result.scalar_one()
        token.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        await db_session.commit()

        response = await client.post(
            "/accounts/activate/",
            json={"email": "expired@example.com", "token": token.token},
        )
        assert response.status_code == 400

        result = await db_session.execute(
            select(ActivationToken).where(ActivationToken.user_id == user.id)
        )
        assert result.scalar() is None

    async def test_activate_already_active_user_returns_400(
        self, client: AsyncClient, user_group, db_session: AsyncSession
    ):
        await client.post(
            "/accounts/register/",
            json={"email": "already-active@example.com", "password": "StrongP@ssw0rd!"},
        )
        result = await db_session.execute(
            select(User).where(User.email == "already-active@example.com")
        )
        user = result.scalar_one()
        result = await db_session.execute(
            select(ActivationToken).where(ActivationToken.user_id == user.id)
        )
        first_token = result.scalar_one()

        # First activation succeeds and deletes the token.
        await client.post(
            "/accounts/activate/",
            json={"email": "already-active@example.com", "token": first_token.token},
        )

        # Simulate a second, stray activation token for an already-active user
        # (e.g. from a race condition or a stale email link) to reach the
        # "already active" branch specifically, not "token not found".
        stray_token = ActivationToken(user_id=user.id)
        db_session.add(stray_token)
        await db_session.commit()

        response = await client.post(
            "/accounts/activate/",
            json={"email": "already-active@example.com", "token": stray_token.token},
        )
        assert response.status_code == 400
        assert "already active" in response.json()["detail"].lower()


class TestResendActivationLink:
    async def test_resend_for_nonexistent_user_returns_generic_200(
        self, client: AsyncClient, user_group
    ):
        response = await client.post(
            "/accounts/activate/resend-link/",
            json={"email": "does-not-exist@example.com"},
        )
        assert response.status_code == 200

    async def test_resend_replaces_old_token_with_new_one(
        self, client: AsyncClient, user_group, db_session: AsyncSession
    ):
        await client.post(
            "/accounts/register/",
            json={"email": "resend@example.com", "password": "StrongP@ssw0rd!"},
        )
        result = await db_session.execute(
            select(User).where(User.email == "resend@example.com")
        )
        user = result.scalar_one()
        result = await db_session.execute(
            select(ActivationToken).where(ActivationToken.user_id == user.id)
        )
        old_token = result.scalar_one().token

        response = await client.post(
            "/accounts/activate/resend-link/", json={"email": "resend@example.com"}
        )
        assert response.status_code == 200

        result = await db_session.execute(
            select(ActivationToken).where(ActivationToken.user_id == user.id)
        )
        new_token = result.scalar()
        assert new_token is not None
        assert new_token.token != old_token
