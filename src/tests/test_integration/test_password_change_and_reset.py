import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.accounts import PasswordResetToken, User


@pytest.fixture()
async def logged_in_user(client: AsyncClient, user_group, db_session: AsyncSession):
    await client.post(
        "/accounts/register/",
        json={"email": "pwd-user@example.com", "password": "StrongP@ssw0rd!"},
    )
    result = await db_session.execute(
        select(User).where(User.email == "pwd-user@example.com")
    )
    user = result.scalar()
    user.is_active = True
    await db_session.commit()

    login_response = await client.post(
        "/accounts/login/",
        json={"email": "pwd-user@example.com", "password": "StrongP@ssw0rd!"},
    )
    return login_response.json()["access_token"]


class TestChangePassword:
    async def test_change_password_with_correct_old_password_returns_200(
        self, client: AsyncClient, logged_in_user
    ):
        response = await client.post(
            "/accounts/change-password/",
            json={"old_password": "StrongP@ssw0rd!", "new_password": "EvenStr0nger!"},
            headers={"Authorization": f"Bearer {logged_in_user}"},
        )
        assert response.status_code == 200

    async def test_change_password_wrong_old_password_returns_401(
        self, client: AsyncClient, logged_in_user
    ):
        response = await client.post(
            "/accounts/change-password/",
            json={
                "old_password": "wrong-old-password",
                "new_password": "EvenStr0nger!",
            },
            headers={"Authorization": f"Bearer {logged_in_user}"},
        )
        assert response.status_code == 401

    async def test_change_password_same_as_old_returns_422(
        self, client: AsyncClient, logged_in_user
    ):
        response = await client.post(
            "/accounts/change-password/",
            json={"old_password": "StrongP@ssw0rd!", "new_password": "StrongP@ssw0rd!"},
            headers={"Authorization": f"Bearer {logged_in_user}"},
        )
        assert response.status_code == 422

    async def test_change_password_without_auth_header_returns_401_or_403(
        self, client: AsyncClient
    ):
        response = await client.post(
            "/accounts/change-password/",
            json={"old_password": "whatever", "new_password": "EvenStr0nger!"},
        )
        assert response.status_code in (401, 403)


class TestPasswordResetRequest:
    async def test_request_for_active_user_creates_token(
        self, client: AsyncClient, user_group, db_session: AsyncSession
    ):
        await client.post(
            "/accounts/register/",
            json={"email": "reset-me@example.com", "password": "StrongP@ssw0rd!"},
        )
        result = await db_session.execute(
            select(User).where(User.email == "reset-me@example.com")
        )
        user = result.scalar()
        user.is_active = True
        await db_session.commit()

        response = await client.post(
            "/accounts/password-reset/request/", json={"email": "reset-me@example.com"}
        )
        assert response.status_code == 200

        result = await db_session.execute(
            select(PasswordResetToken).where(PasswordResetToken.user_id == user.id)
        )
        assert result.scalar() is not None

    async def test_request_for_nonexistent_email_returns_generic_200(
        self, client: AsyncClient
    ):
        response = await client.post(
            "/accounts/password-reset/request/", json={"email": "ghost@example.com"}
        )
        assert response.status_code == 200


class TestPasswordResetComplete:
    async def test_reset_with_valid_token_changes_password(
        self, client: AsyncClient, user_group, db_session: AsyncSession
    ):
        await client.post(
            "/accounts/register/",
            json={"email": "complete-reset@example.com", "password": "OldP@ssw0rd!"},
        )
        result = await db_session.execute(
            select(User).where(User.email == "complete-reset@example.com")
        )
        user = result.scalar()
        user.is_active = True
        await db_session.commit()

        await client.post(
            "/accounts/password-reset/request/",
            json={"email": "complete-reset@example.com"},
        )
        result = await db_session.execute(
            select(PasswordResetToken).where(PasswordResetToken.user_id == user.id)
        )
        reset_token = result.scalar()

        response = await client.post(
            "/accounts/reset-password/complete/",
            json={
                "email": "complete-reset@example.com",
                "token": reset_token.token,
                "password": "BrandNewP@ss1!",
            },
        )
        assert response.status_code == 200

        login_response = await client.post(
            "/accounts/login/",
            json={"email": "complete-reset@example.com", "password": "BrandNewP@ss1!"},
        )
        assert login_response.status_code == 200

    async def test_reset_with_wrong_token_returns_400(
        self, client: AsyncClient, user_group, db_session: AsyncSession
    ):
        await client.post(
            "/accounts/register/",
            json={"email": "wrong-reset-token@example.com", "password": "OldP@ssw0rd!"},
        )
        result = await db_session.execute(
            select(User).where(User.email == "wrong-reset-token@example.com")
        )
        user = result.scalar()
        user.is_active = True
        await db_session.commit()

        response = await client.post(
            "/accounts/reset-password/complete/",
            json={
                "email": "wrong-reset-token@example.com",
                "token": "not-the-real-token",
                "password": "BrandNewP@ss1!",
            },
        )
        assert response.status_code == 400
