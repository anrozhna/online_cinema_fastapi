from httpx import AsyncClient


class TestDocsAccessRestriction:
    async def test_docs_requires_token(self, client: AsyncClient):
        response = await client.get("/docs")

        assert response.status_code == 422  # missing required query param

    async def test_docs_rejects_invalid_token(self, client: AsyncClient):
        response = await client.get("/docs", params={"token": "not-a-real-token"})

        assert response.status_code == 401

    async def test_docs_rejects_non_admin_token(
        self, authenticated_client: AsyncClient, active_user
    ):
        from config.dependencies import get_jwt_auth_manager
        from config.settings import get_settings

        jwt_manager = get_jwt_auth_manager(get_settings())
        token = jwt_manager.create_access_token({"user_id": active_user.id})

        response = await authenticated_client.get("/docs", params={"token": token})

        assert response.status_code == 403

    async def test_docs_allows_admin_token(self, client: AsyncClient, admin_user):
        from config.dependencies import get_jwt_auth_manager
        from config.settings import get_settings

        jwt_manager = get_jwt_auth_manager(get_settings())
        token = jwt_manager.create_access_token({"user_id": admin_user.id})

        response = await client.get("/docs", params={"token": token})

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    async def test_openapi_json_allows_admin_token(
        self, client: AsyncClient, admin_user
    ):
        from config.dependencies import get_jwt_auth_manager
        from config.settings import get_settings

        jwt_manager = get_jwt_auth_manager(get_settings())
        token = jwt_manager.create_access_token({"user_id": admin_user.id})

        response = await client.get("/openapi.json", params={"token": token})

        assert response.status_code == 200
        body = response.json()
        assert body["info"]["title"] == "Online Cinema API"
