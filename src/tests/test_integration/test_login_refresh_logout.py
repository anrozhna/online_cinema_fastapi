import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.accounts import User


@pytest.fixture()
async def activated_user(client: AsyncClient, user_group, db_session: AsyncSession):
    await client.post(
        "/accounts/register/",
        json={"email": "login-user@example.com", "password": "StrongP@ssw0rd!"},
    )
    result = await db_session.execute(
        select(User).where(User.email == "login-user@example.com")
    )
    user = result.scalar_one()
    user.is_active = True
    await db_session.commit()
    return user


class TestLogin:
    async def test_login_with_valid_credentials_returns_token_pair(
        self, client: AsyncClient, activated_user
    ):
        response = await client.post(
            "/accounts/login/",
            json={"email": "login-user@example.com", "password": "StrongP@ssw0rd!"},
        )
        assert response.status_code == 200
        body = response.json()
        assert "access_token" in body
        assert "refresh_token" in body
        assert body["token_type"] == "bearer"

    async def test_login_wrong_password_returns_401(
        self, client: AsyncClient, activated_user
    ):
        response = await client.post(
            "/accounts/login/",
            json={"email": "login-user@example.com", "password": "wrong-password"},
        )
        assert response.status_code == 401

    async def test_login_inactive_user_returns_403(
        self, client: AsyncClient, user_group
    ):
        await client.post(
            "/accounts/register/",
            json={"email": "inactive@example.com", "password": "StrongP@ssw0rd!"},
        )
        response = await client.post(
            "/accounts/login/",
            json={"email": "inactive@example.com", "password": "StrongP@ssw0rd!"},
        )
        assert response.status_code == 403

    async def test_login_nonexistent_email_returns_401(self, client: AsyncClient):
        response = await client.post(
            "/accounts/login/",
            json={"email": "ghost@example.com", "password": "whatever"},
        )
        assert response.status_code == 401


class TestRefresh:
    async def test_refresh_with_valid_token_returns_new_access_token(
        self, client: AsyncClient, activated_user
    ):
        login_response = await client.post(
            "/accounts/login/",
            json={"email": "login-user@example.com", "password": "StrongP@ssw0rd!"},
        )
        refresh_token = login_response.json()["refresh_token"]

        response = await client.post(
            "/accounts/refresh/", json={"refresh_token": refresh_token}
        )
        assert response.status_code == 200
        assert "access_token" in response.json()

    async def test_refresh_with_garbage_token_returns_400(self, client: AsyncClient):
        response = await client.post(
            "/accounts/refresh/", json={"refresh_token": "not-a-real-jwt"}
        )
        assert response.status_code == 400

    async def test_refresh_with_revoked_token_returns_401(
        self, client: AsyncClient, activated_user
    ):
        login_response = await client.post(
            "/accounts/login/",
            json={"email": "login-user@example.com", "password": "StrongP@ssw0rd!"},
        )
        refresh_token = login_response.json()["refresh_token"]

        await client.post("/accounts/logout/", json={"refresh_token": refresh_token})

        response = await client.post(
            "/accounts/refresh/", json={"refresh_token": refresh_token}
        )
        assert response.status_code == 401


class TestLogout:
    async def test_logout_with_valid_token_returns_200(
        self, client: AsyncClient, activated_user
    ):
        login_response = await client.post(
            "/accounts/login/",
            json={"email": "login-user@example.com", "password": "StrongP@ssw0rd!"},
        )
        refresh_token = login_response.json()["refresh_token"]

        response = await client.post(
            "/accounts/logout/", json={"refresh_token": refresh_token}
        )
        assert response.status_code == 200

    async def test_logout_with_invalid_token_returns_401(self, client: AsyncClient):
        response = await client.post(
            "/accounts/logout/", json={"refresh_token": "not-a-real-token"}
        )
        assert response.status_code == 401

    async def test_logout_twice_with_same_token_fails_second_time(
        self, client: AsyncClient, activated_user
    ):
        login_response = await client.post(
            "/accounts/login/",
            json={"email": "login-user@example.com", "password": "StrongP@ssw0rd!"},
        )
        refresh_token = login_response.json()["refresh_token"]

        await client.post("/accounts/logout/", json={"refresh_token": refresh_token})
        response = await client.post(
            "/accounts/logout/", json={"refresh_token": refresh_token}
        )
        assert response.status_code == 401
