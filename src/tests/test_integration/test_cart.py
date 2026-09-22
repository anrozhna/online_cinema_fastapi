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


class TestViewUserCart:
    async def test_admin_can_view_any_user_cart(
        self,
        authenticated_admin_client: AsyncClient,
        active_user,
        db_session,
        certification,
    ):
        from database.models.cart import Cart, CartItem

        movie = await create_movie(db_session, certification)

        cart = Cart(user_id=active_user.id)
        db_session.add(cart)
        await db_session.commit()
        await db_session.refresh(cart)

        db_session.add(CartItem(cart_id=cart.id, movie_id=movie.id))
        await db_session.commit()

        response = await authenticated_admin_client.get(
            f"/cart/users/{active_user.id}/"
        )

        assert response.status_code == 200
        body = response.json()
        assert len(body["items"]) == 1
        assert body["items"][0]["movie_name"] == movie.name

    async def test_moderator_can_view_any_user_cart(
        self, authenticated_moderator_client: AsyncClient, active_user
    ):
        response = await authenticated_moderator_client.get(
            f"/cart/users/{active_user.id}/"
        )

        assert response.status_code == 200

    async def test_regular_user_cannot_view_other_carts(
        self, authenticated_client: AsyncClient, other_user
    ):
        response = await authenticated_client.get(f"/cart/users/{other_user.id}/")

        assert response.status_code == 403

    async def test_view_user_cart_requires_authentication(
        self, client: AsyncClient, active_user
    ):
        response = await client.get(f"/cart/users/{active_user.id}/")

        assert response.status_code == 401


class TestMovieDeletionNotifiesModerators:
    async def test_deleting_movie_in_cart_succeeds(
        self,
        authenticated_admin_client: AsyncClient,
        db_session,
        certification,
        moderator_group,
        user_group,
    ):
        from database.models.accounts import User
        from database.models.cart import Cart, CartItem

        moderator = User.create(
            email="mod-notify@example.com",
            raw_password="StrongP@ssw0rd!",
            group_id=moderator_group.id,
        )
        moderator.is_active = True
        db_session.add(moderator)
        await db_session.commit()

        movie = await create_movie(db_session, certification)

        cart_owner = User.create(
            email="cart-owner-del@example.com",
            raw_password="StrongP@ssw0rd!",
            group_id=user_group.id,
        )
        cart_owner.is_active = True
        db_session.add(cart_owner)
        await db_session.commit()

        cart = Cart(user_id=cart_owner.id)
        db_session.add(cart)
        await db_session.commit()
        await db_session.refresh(cart)

        db_session.add(CartItem(cart_id=cart.id, movie_id=movie.id))
        await db_session.commit()

        response = await authenticated_admin_client.delete(
            f"/moderation/movies/{movie.id}/"
        )

        # The Celery task itself is mocked (mock_celery_tasks autouse fixture);
        # this confirms the endpoint completes successfully with a movie
        # present in a cart, i.e. the notification branch doesn't raise.
        assert response.status_code == 204

    async def test_deleting_movie_not_in_any_cart_succeeds(
        self, authenticated_admin_client: AsyncClient, db_session, certification
    ):
        movie = await create_movie(db_session, certification)

        response = await authenticated_admin_client.delete(
            f"/moderation/movies/{movie.id}/"
        )

        assert response.status_code == 204
