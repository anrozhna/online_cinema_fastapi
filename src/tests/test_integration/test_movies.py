from httpx import AsyncClient

from tests.conftest import create_movie


class TestListMovies:
    async def test_list_movies_returns_paginated_response(
        self, client: AsyncClient, db_session, certification
    ):
        await create_movie(db_session, certification, name="Inception", year=2010)
        await create_movie(db_session, certification, name="Titanic", year=1997)

        response = await client.get("/movies/")

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 2
        assert len(body["items"]) == 2
        assert body["limit"] == 20
        assert body["offset"] == 0

    async def test_list_movies_filters_by_year(
        self, client: AsyncClient, db_session, certification
    ):
        await create_movie(db_session, certification, name="Old", year=2000)
        await create_movie(db_session, certification, name="New", year=2020)

        response = await client.get("/movies/", params={"year": 2020})

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["items"][0]["name"] == "New"

    async def test_list_movies_rejects_invalid_min_imdb(self, client: AsyncClient):
        response = await client.get("/movies/", params={"min_imdb": 15})

        assert response.status_code == 422

    async def test_list_movies_rejects_limit_above_max(self, client: AsyncClient):
        response = await client.get("/movies/", params={"limit": 1000})

        assert response.status_code == 422


class TestGetMovie:
    async def test_get_movie_by_uuid_success(
        self, client: AsyncClient, db_session, certification
    ):
        movie = await create_movie(
            db_session, certification, name="Inception", year=2010
        )

        response = await client.get(f"/movies/{movie.uuid}/")

        assert response.status_code == 200
        body = response.json()
        assert body["name"] == "Inception"
        assert body["uuid"] == str(movie.uuid)

    async def test_get_movie_by_uuid_not_found(self, client: AsyncClient):
        import uuid

        response = await client.get(f"/movies/{uuid.uuid4()}/")

        assert response.status_code == 404
        assert response.json()["detail"] == "Movie not found."

    async def test_get_movie_rejects_invalid_uuid_format(self, client: AsyncClient):
        response = await client.get("/movies/not-a-uuid/")

        assert response.status_code == 422
