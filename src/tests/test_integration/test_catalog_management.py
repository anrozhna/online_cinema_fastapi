from httpx import AsyncClient

from tests.conftest import create_movie


class TestMovieCrud:
    async def test_admin_can_create_movie(
        self, authenticated_admin_client: AsyncClient, certification
    ):
        response = await authenticated_admin_client.post(
            "/moderation/movies/",
            json={
                "name": "Inception",
                "year": 2010,
                "time": 148,
                "imdb": 8.8,
                "votes": 2000000,
                "description": "A thief who steals corporate secrets.",
                "price": 9.99,
                "certification_id": certification.id,
            },
        )

        assert response.status_code == 201
        assert response.json()["name"] == "Inception"

    async def test_moderator_can_create_movie(
        self, authenticated_moderator_client: AsyncClient, certification
    ):
        response = await authenticated_moderator_client.post(
            "/moderation/movies/",
            json={
                "name": "Interstellar",
                "year": 2014,
                "time": 169,
                "imdb": 8.6,
                "votes": 1800000,
                "description": "A team travels through a wormhole.",
                "price": 12.99,
                "certification_id": certification.id,
            },
        )

        assert response.status_code == 201

    async def test_regular_user_cannot_create_movie(
        self, authenticated_client: AsyncClient, certification
    ):
        response = await authenticated_client.post(
            "/moderation/movies/",
            json={
                "name": "Unauthorized Movie",
                "year": 2020,
                "time": 100,
                "imdb": 5.0,
                "votes": 100,
                "description": "Should not be created.",
                "price": 5.0,
                "certification_id": certification.id,
            },
        )

        assert response.status_code == 403

    async def test_create_movie_rejects_duplicate_name_year_time(
        self, authenticated_admin_client: AsyncClient, db_session, certification
    ):
        await create_movie(
            db_session, certification, name="Titanic", year=1997, time=195
        )

        response = await authenticated_admin_client.post(
            "/moderation/movies/",
            json={
                "name": "Titanic",
                "year": 1997,
                "time": 195,
                "imdb": 7.9,
                "votes": 1000000,
                "description": "Duplicate attempt.",
                "price": 8.99,
                "certification_id": certification.id,
            },
        )

        assert response.status_code == 409

    async def test_create_movie_rejects_unknown_certification(
        self, authenticated_admin_client: AsyncClient
    ):
        response = await authenticated_admin_client.post(
            "/moderation/movies/",
            json={
                "name": "No Certification Movie",
                "year": 2020,
                "time": 100,
                "imdb": 5.0,
                "votes": 100,
                "description": "Missing certification.",
                "price": 5.0,
                "certification_id": 999999,
            },
        )

        assert response.status_code == 400

    async def test_create_movie_resolves_genre_ids(
        self, authenticated_admin_client: AsyncClient, certification, genre
    ):
        response = await authenticated_admin_client.post(
            "/moderation/movies/",
            json={
                "name": "Action Movie",
                "year": 2021,
                "time": 110,
                "imdb": 6.5,
                "votes": 500,
                "description": "Full of action.",
                "price": 7.99,
                "certification_id": certification.id,
                "genre_ids": [genre.id],
            },
        )

        assert response.status_code == 201
        body = response.json()
        assert len(body["genres"]) == 1
        assert body["genres"][0]["name"] == genre.name

    async def test_create_movie_rejects_unknown_genre_id(
        self, authenticated_admin_client: AsyncClient, certification
    ):
        response = await authenticated_admin_client.post(
            "/moderation/movies/",
            json={
                "name": "Bad Genre Movie",
                "year": 2021,
                "time": 110,
                "imdb": 6.5,
                "votes": 500,
                "description": "Has invalid genre.",
                "price": 7.99,
                "certification_id": certification.id,
                "genre_ids": [999999],
            },
        )

        assert response.status_code == 400

    async def test_admin_can_update_movie(
        self, authenticated_admin_client: AsyncClient, db_session, certification
    ):
        movie = await create_movie(db_session, certification)

        response = await authenticated_admin_client.put(
            f"/moderation/movies/{movie.id}/",
            json={
                "name": "Inception (Updated)",
                "year": movie.year,
                "time": movie.time,
                "imdb": movie.imdb,
                "votes": movie.votes,
                "description": movie.description,
                "price": 19.99,
                "certification_id": certification.id,
            },
        )

        assert response.status_code == 200
        body = response.json()
        assert body["name"] == "Inception (Updated)"
        assert body["price"] == 19.99

    async def test_update_movie_not_found(
        self, authenticated_admin_client: AsyncClient, certification
    ):
        response = await authenticated_admin_client.put(
            "/moderation/movies/999999/",
            json={
                "name": "Ghost Movie",
                "year": 2020,
                "time": 100,
                "imdb": 5.0,
                "votes": 100,
                "description": "Does not exist.",
                "price": 5.0,
                "certification_id": certification.id,
            },
        )

        assert response.status_code == 404

    async def test_admin_can_delete_movie(
        self, authenticated_admin_client: AsyncClient, db_session, certification
    ):
        movie = await create_movie(db_session, certification)

        response = await authenticated_admin_client.delete(
            f"/moderation/movies/{movie.id}/"
        )

        assert response.status_code == 204

    async def test_delete_movie_not_found(
        self, authenticated_admin_client: AsyncClient
    ):
        response = await authenticated_admin_client.delete("/moderation/movies/999999/")

        assert response.status_code == 404

    async def test_delete_movie_requires_admin_or_moderator(
        self, authenticated_client: AsyncClient, db_session, certification
    ):
        movie = await create_movie(db_session, certification)

        response = await authenticated_client.delete(f"/moderation/movies/{movie.id}/")

        assert response.status_code == 403


class TestGenreCrud:
    async def test_admin_can_create_genre(
        self, authenticated_admin_client: AsyncClient
    ):
        response = await authenticated_admin_client.post(
            "/moderation/genres/", json={"name": "Sci-Fi"}
        )

        assert response.status_code == 201
        assert response.json()["name"] == "Sci-Fi"

    async def test_create_genre_rejects_duplicate_name(
        self, authenticated_admin_client: AsyncClient, genre
    ):
        response = await authenticated_admin_client.post(
            "/moderation/genres/", json={"name": genre.name}
        )

        assert response.status_code == 409

    async def test_admin_can_update_genre(
        self, authenticated_admin_client: AsyncClient, genre
    ):
        response = await authenticated_admin_client.put(
            f"/moderation/genres/{genre.id}/", json={"name": "Renamed Genre"}
        )

        assert response.status_code == 200
        assert response.json()["name"] == "Renamed Genre"

    async def test_update_genre_not_found(
        self, authenticated_admin_client: AsyncClient
    ):
        response = await authenticated_admin_client.put(
            "/moderation/genres/999999/", json={"name": "Ghost Genre"}
        )

        assert response.status_code == 404

    async def test_admin_can_delete_genre(
        self, authenticated_admin_client: AsyncClient, genre
    ):
        response = await authenticated_admin_client.delete(
            f"/moderation/genres/{genre.id}/"
        )

        assert response.status_code == 204

    async def test_regular_user_cannot_manage_genres(
        self, authenticated_client: AsyncClient
    ):
        response = await authenticated_client.post(
            "/moderation/genres/", json={"name": "Unauthorized Genre"}
        )

        assert response.status_code == 403


class TestStarCrud:
    async def test_admin_can_create_star(self, authenticated_admin_client: AsyncClient):
        response = await authenticated_admin_client.post(
            "/moderation/stars/", json={"name": "Tom Hardy"}
        )

        assert response.status_code == 201

    async def test_moderator_can_delete_star(
        self, authenticated_moderator_client: AsyncClient, star
    ):
        response = await authenticated_moderator_client.delete(
            f"/moderation/stars/{star.id}/"
        )

        assert response.status_code == 204


class TestDirectorCrud:
    async def test_admin_can_create_director(
        self, authenticated_admin_client: AsyncClient
    ):
        response = await authenticated_admin_client.post(
            "/moderation/directors/", json={"name": "Denis Villeneuve"}
        )

        assert response.status_code == 201

    async def test_admin_can_update_director(
        self, authenticated_admin_client: AsyncClient, director
    ):
        response = await authenticated_admin_client.put(
            f"/moderation/directors/{director.id}/", json={"name": "Renamed Director"}
        )

        assert response.status_code == 200


class TestCertificationCrud:
    async def test_admin_can_create_certification(
        self, authenticated_admin_client: AsyncClient
    ):
        response = await authenticated_admin_client.post(
            "/moderation/certifications/", json={"name": "NC-17"}
        )

        assert response.status_code == 201

    async def test_create_certification_rejects_duplicate_name(
        self, authenticated_admin_client: AsyncClient, certification
    ):
        response = await authenticated_admin_client.post(
            "/moderation/certifications/", json={"name": certification.name}
        )

        assert response.status_code == 409

    async def test_admin_can_delete_certification(
        self, authenticated_admin_client: AsyncClient, certification
    ):
        response = await authenticated_admin_client.delete(
            f"/moderation/certifications/{certification.id}/"
        )

        assert response.status_code == 204
