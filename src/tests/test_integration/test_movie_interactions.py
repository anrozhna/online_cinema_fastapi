from httpx import AsyncClient

from tests.conftest import create_movie


class TestMovieReaction:
    async def test_authenticated_user_can_like_movie(
        self, authenticated_client: AsyncClient, db_session, certification
    ):
        movie = await create_movie(db_session, certification)

        response = await authenticated_client.post(
            f"/movies/{movie.id}/reaction/", json={"is_like": True}
        )

        assert response.status_code == 200
        body = response.json()
        assert body["is_like"] is True
        assert body["movie_id"] == movie.id

    async def test_reacting_again_updates_existing_reaction(
        self, authenticated_client: AsyncClient, db_session, certification
    ):
        movie = await create_movie(db_session, certification)

        await authenticated_client.post(
            f"/movies/{movie.id}/reaction/", json={"is_like": True}
        )
        response = await authenticated_client.post(
            f"/movies/{movie.id}/reaction/", json={"is_like": False}
        )

        assert response.status_code == 200
        assert response.json()["is_like"] is False

    async def test_reaction_requires_authentication(
        self, client: AsyncClient, db_session, certification
    ):
        movie = await create_movie(db_session, certification)

        response = await client.post(
            f"/movies/{movie.id}/reaction/", json={"is_like": True}
        )

        assert response.status_code == 401

    async def test_reaction_not_found_for_missing_movie(
        self, authenticated_client: AsyncClient
    ):
        response = await authenticated_client.post(
            "/movies/999999/reaction/", json={"is_like": True}
        )

        assert response.status_code == 404


class TestMovieRating:
    async def test_authenticated_user_can_rate_movie(
        self, authenticated_client: AsyncClient, db_session, certification
    ):
        movie = await create_movie(db_session, certification)

        response = await authenticated_client.post(
            f"/movies/{movie.id}/rating/", json={"score": 8}
        )

        assert response.status_code == 200
        body = response.json()
        assert body["score"] == 8
        assert body["movie_id"] == movie.id

    async def test_rating_again_updates_existing_rating(
        self, authenticated_client: AsyncClient, db_session, certification
    ):
        movie = await create_movie(db_session, certification)

        await authenticated_client.post(
            f"/movies/{movie.id}/rating/", json={"score": 5}
        )
        response = await authenticated_client.post(
            f"/movies/{movie.id}/rating/", json={"score": 9}
        )

        assert response.status_code == 200
        assert response.json()["score"] == 9

    async def test_rating_rejects_score_above_ten(
        self, authenticated_client: AsyncClient, db_session, certification
    ):
        movie = await create_movie(db_session, certification)

        response = await authenticated_client.post(
            f"/movies/{movie.id}/rating/", json={"score": 15}
        )

        assert response.status_code == 422

    async def test_rating_rejects_score_below_one(
        self, authenticated_client: AsyncClient, db_session, certification
    ):
        movie = await create_movie(db_session, certification)

        response = await authenticated_client.post(
            f"/movies/{movie.id}/rating/", json={"score": 0}
        )

        assert response.status_code == 422

    async def test_rating_requires_authentication(
        self, client: AsyncClient, db_session, certification
    ):
        movie = await create_movie(db_session, certification)

        response = await client.post(f"/movies/{movie.id}/rating/", json={"score": 7})

        assert response.status_code == 401


class TestMovieComments:
    async def test_authenticated_user_can_post_top_level_comment(
        self, authenticated_client: AsyncClient, db_session, certification
    ):
        movie = await create_movie(db_session, certification)

        response = await authenticated_client.post(
            f"/movies/{movie.id}/comments/", json={"text": "Great movie!"}
        )

        assert response.status_code == 201
        body = response.json()
        assert body["text"] == "Great movie!"
        assert body["parent_comment_id"] is None
        assert body["replies"] == []

    async def test_user_can_reply_to_existing_comment(
        self, authenticated_client: AsyncClient, db_session, certification
    ):
        movie = await create_movie(db_session, certification)

        parent_response = await authenticated_client.post(
            f"/movies/{movie.id}/comments/", json={"text": "Loved it!"}
        )
        parent_id = parent_response.json()["id"]

        reply_response = await authenticated_client.post(
            f"/movies/{movie.id}/comments/",
            json={"text": "Agreed!", "parent_comment_id": parent_id},
        )

        assert reply_response.status_code == 201
        assert reply_response.json()["parent_comment_id"] == parent_id

    async def test_list_comments_returns_nested_reply_tree(
        self, authenticated_client: AsyncClient, db_session, certification
    ):
        movie = await create_movie(db_session, certification)

        parent_response = await authenticated_client.post(
            f"/movies/{movie.id}/comments/", json={"text": "Loved it!"}
        )
        parent_id = parent_response.json()["id"]
        await authenticated_client.post(
            f"/movies/{movie.id}/comments/",
            json={"text": "Agreed!", "parent_comment_id": parent_id},
        )

        response = await authenticated_client.get(f"/movies/{movie.id}/comments/")

        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert len(body[0]["replies"]) == 1
        assert body[0]["replies"][0]["text"] == "Agreed!"

    async def test_reply_to_comment_from_different_movie_rejected(
        self, authenticated_client: AsyncClient, db_session, certification
    ):
        movie = await create_movie(
            db_session, certification, name="Inception", year=2010
        )
        other_movie = await create_movie(
            db_session, certification, name="Titanic", year=1997
        )

        parent_response = await authenticated_client.post(
            f"/movies/{movie.id}/comments/", json={"text": "On Inception"}
        )
        parent_id = parent_response.json()["id"]

        response = await authenticated_client.post(
            f"/movies/{other_movie.id}/comments/",
            json={"text": "Cross-movie reply attempt", "parent_comment_id": parent_id},
        )

        assert response.status_code == 400

    async def test_list_comments_public_without_authentication(
        self, client: AsyncClient, db_session, certification
    ):
        movie = await create_movie(db_session, certification)

        response = await client.get(f"/movies/{movie.id}/comments/")

        assert response.status_code == 200
        assert response.json() == []

    async def test_create_comment_requires_authentication(
        self, client: AsyncClient, db_session, certification
    ):
        movie = await create_movie(db_session, certification)

        response = await client.post(
            f"/movies/{movie.id}/comments/", json={"text": "Anonymous comment"}
        )

        assert response.status_code == 401


class TestFavorites:
    async def test_add_movie_to_favorites(
        self, authenticated_client: AsyncClient, db_session, certification
    ):
        movie = await create_movie(db_session, certification)

        response = await authenticated_client.post(f"/movies/{movie.id}/favorite/")

        assert response.status_code == 204

    async def test_adding_same_movie_twice_is_idempotent(
        self, authenticated_client: AsyncClient, db_session, certification
    ):
        movie = await create_movie(db_session, certification)

        first = await authenticated_client.post(f"/movies/{movie.id}/favorite/")
        second = await authenticated_client.post(f"/movies/{movie.id}/favorite/")

        assert first.status_code == 204
        assert second.status_code == 204

    async def test_list_favorites_returns_added_movie(
        self, authenticated_client: AsyncClient, db_session, certification
    ):
        movie = await create_movie(db_session, certification)
        await authenticated_client.post(f"/movies/{movie.id}/favorite/")

        response = await authenticated_client.get("/movies/favorites/")

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["items"][0]["name"] == "Inception"

    async def test_remove_from_favorites(
        self, authenticated_client: AsyncClient, db_session, certification
    ):
        movie = await create_movie(db_session, certification)
        await authenticated_client.post(f"/movies/{movie.id}/favorite/")

        response = await authenticated_client.delete(f"/movies/{movie.id}/favorite/")

        assert response.status_code == 204

        list_response = await authenticated_client.get("/movies/favorites/")
        assert list_response.json()["total"] == 0

    async def test_remove_from_favorites_not_found_if_never_added(
        self, authenticated_client: AsyncClient, db_session, certification
    ):
        movie = await create_movie(db_session, certification)

        response = await authenticated_client.delete(f"/movies/{movie.id}/favorite/")

        assert response.status_code == 404

    async def test_favorites_require_authentication(self, client: AsyncClient):
        response = await client.get("/movies/favorites/")

        assert response.status_code == 401
