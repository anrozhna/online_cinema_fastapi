from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.accounts import ActivationToken


class TestFullRegistrationToLoginFlow:
    async def test_register_activate_login_end_to_end(
        self, client: AsyncClient, db_session: AsyncSession, user_group
    ):
        # 1. Register
        register_response = await client.post(
            "/accounts/register/",
            json={"email": "newcomer@example.com", "password": "StrongP@ssw0rd!"},
        )
        assert register_response.status_code == 201
        user_id = register_response.json()["id"]

        # 2. User cannot log in before activation
        premature_login = await client.post(
            "/accounts/login/",
            json={"email": "newcomer@example.com", "password": "StrongP@ssw0rd!"},
        )
        assert premature_login.status_code == 403

        # 3. Fetch the real activation token from the DB (no real email in tests)
        result = await db_session.execute(
            select(ActivationToken).where(ActivationToken.user_id == user_id)
        )
        activation_token = result.scalar_one()

        # 4. Activate
        activate_response = await client.post(
            "/accounts/activate/",
            json={"email": "newcomer@example.com", "token": activation_token.token},
        )
        assert activate_response.status_code == 200

        # 5. Login now succeeds
        login_response = await client.post(
            "/accounts/login/",
            json={"email": "newcomer@example.com", "password": "StrongP@ssw0rd!"},
        )
        assert login_response.status_code == 200
        tokens = login_response.json()
        assert "access_token" in tokens
        assert "refresh_token" in tokens

        # 6. Access token works on a protected endpoint
        profile_response = await client.get(
            f"/profiles/profile/{user_id}/",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        # Profile exists (created during registration) but has no data yet
        assert profile_response.status_code in (200, 404)

        # 7. Refresh token issues a new access token
        refresh_response = await client.post(
            "/accounts/refresh/", json={"refresh_token": tokens["refresh_token"]}
        )
        assert refresh_response.status_code == 200
        assert "access_token" in refresh_response.json()

        # 8. Logout invalidates the refresh token
        logout_response = await client.post(
            "/accounts/logout/", json={"refresh_token": tokens["refresh_token"]}
        )
        assert logout_response.status_code == 200

        second_refresh = await client.post(
            "/accounts/refresh/", json={"refresh_token": tokens["refresh_token"]}
        )
        assert second_refresh.status_code == 401
