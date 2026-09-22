from httpx import AsyncClient

from tests.conftest import create_movie


class TestViewCart:
    async def test_view_empty_cart(self, authenticated_client: AsyncClient):
        response = await authenticated_client.get("/cart/")

        assert response.status_code == 200
        body = response.json()
        assert body["items"] == []
        assert body["total_price"] == 0

    async def test_view_cart_requires_authentication(self, client: AsyncClient):
        response = await client.get("/cart/")

        assert response.status_code == 401


class TestAddToCart:
    async def test_add_movie_to_cart(
        self, authenticated_client: AsyncClient, db_session, certification
    ):
        movie = await create_movie(db_session, certification)

        response = await authenticated_client.post(f"/cart/{movie.id}/")

        assert response.status_code == 201
        body = response.json()
        assert len(body["items"]) == 1
        assert body["items"][0]["movie_name"] == movie.name
        assert body["total_price"] == float(movie.price)

    async def test_add_same_movie_twice_returns_409(
        self, authenticated_client: AsyncClient, db_session, certification
    ):
        movie = await create_movie(db_session, certification)

        await authenticated_client.post(f"/cart/{movie.id}/")
        response = await authenticated_client.post(f"/cart/{movie.id}/")

        assert response.status_code == 409

    async def test_add_nonexistent_movie_returns_404(
        self, authenticated_client: AsyncClient
    ):
        response = await authenticated_client.post("/cart/999999/")

        assert response.status_code == 404


class TestRemoveFromCart:
    async def test_remove_movie_from_cart(
        self, authenticated_client: AsyncClient, db_session, certification
    ):
        movie = await create_movie(db_session, certification)
        await authenticated_client.post(f"/cart/{movie.id}/")

        response = await authenticated_client.delete(f"/cart/{movie.id}/")

        assert response.status_code == 200
        assert response.json()["items"] == []

    async def test_remove_movie_not_in_cart_returns_404(
        self, authenticated_client: AsyncClient, db_session, certification
    ):
        movie = await create_movie(db_session, certification)

        response = await authenticated_client.delete(f"/cart/{movie.id}/")

        assert response.status_code == 404


class TestClearCart:
    async def test_clear_cart_removes_all_items(
        self, authenticated_client: AsyncClient, db_session, certification
    ):
        movie1 = await create_movie(
            db_session, certification, name="Inception", year=2010
        )
        movie2 = await create_movie(
            db_session, certification, name="Titanic", year=1997
        )

        await authenticated_client.post(f"/cart/{movie1.id}/")
        await authenticated_client.post(f"/cart/{movie2.id}/")

        response = await authenticated_client.delete("/cart/")

        assert response.status_code == 204

        view_response = await authenticated_client.get("/cart/")
        assert view_response.json()["items"] == []


class TestCheckout:
    async def test_checkout_empty_cart_returns_400(
        self, authenticated_client: AsyncClient
    ):
        response = await authenticated_client.post("/cart/checkout/")

        assert response.status_code == 400

    async def test_checkout_clears_cart(
        self, authenticated_client: AsyncClient, db_session, certification
    ):
        movie = await create_movie(db_session, certification)
        await authenticated_client.post(f"/cart/{movie.id}/")

        response = await authenticated_client.post("/cart/checkout/")

        assert response.status_code == 204

        view_response = await authenticated_client.get("/cart/")
        assert view_response.json()["items"] == []
