from decimal import Decimal

from httpx import AsyncClient

from database.models.orders import Order, OrderItem, OrderStatusEnum
from tests.conftest import create_movie


class TestPlaceOrder:
    async def test_place_order_from_cart(
        self, authenticated_client: AsyncClient, db_session, certification
    ):
        movie = await create_movie(db_session, certification)
        await authenticated_client.post(f"/cart/{movie.id}/")

        response = await authenticated_client.post("/orders/")

        assert response.status_code == 201
        body = response.json()
        assert body["order"] is not None
        assert len(body["order"]["items"]) == 1
        assert body["order"]["status"] == "pending"
        assert body["excluded_movie_names"] == []

    async def test_place_order_empties_cart(
        self, authenticated_client: AsyncClient, db_session, certification
    ):
        movie = await create_movie(db_session, certification)
        await authenticated_client.post(f"/cart/{movie.id}/")

        await authenticated_client.post("/orders/")

        cart_response = await authenticated_client.get("/cart/")
        assert cart_response.json()["items"] == []

    async def test_place_order_with_empty_cart_returns_400(
        self, authenticated_client: AsyncClient
    ):
        response = await authenticated_client.post("/orders/")

        assert response.status_code == 400

    async def test_place_order_requires_authentication(self, client: AsyncClient):
        response = await client.post("/orders/")

        assert response.status_code == 401


class TestListOrders:
    async def test_list_orders_returns_placed_order(
        self, authenticated_client: AsyncClient, db_session, certification
    ):
        movie = await create_movie(db_session, certification)
        await authenticated_client.post(f"/cart/{movie.id}/")
        await authenticated_client.post("/orders/")

        response = await authenticated_client.get("/orders/")

        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]["status"] == "pending"


class TestCancelOrder:
    async def test_cancel_pending_order(
        self, authenticated_client: AsyncClient, db_session, certification
    ):
        movie = await create_movie(db_session, certification)
        await authenticated_client.post(f"/cart/{movie.id}/")
        place_response = await authenticated_client.post("/orders/")
        order_id = place_response.json()["order"]["id"]

        response = await authenticated_client.post(f"/orders/{order_id}/cancel/")

        assert response.status_code == 200
        assert response.json()["status"] == "canceled"

    async def test_cancel_already_canceled_order_returns_400(
        self, authenticated_client: AsyncClient, db_session, certification
    ):
        movie = await create_movie(db_session, certification)
        await authenticated_client.post(f"/cart/{movie.id}/")
        place_response = await authenticated_client.post("/orders/")
        order_id = place_response.json()["order"]["id"]

        await authenticated_client.post(f"/orders/{order_id}/cancel/")
        response = await authenticated_client.post(f"/orders/{order_id}/cancel/")

        assert response.status_code == 400

    async def test_cancel_nonexistent_order_returns_404(
        self, authenticated_client: AsyncClient
    ):
        response = await authenticated_client.post("/orders/999999/cancel/")

        assert response.status_code == 404

    async def test_cannot_cancel_other_users_order(
        self,
        authenticated_client: AsyncClient,
        other_user,
        db_session,
        certification,
        user_group,
    ):
        other_order = Order(
            user_id=other_user.id,
            status=OrderStatusEnum.PENDING,
            total_amount=Decimal("9.99"),
        )
        db_session.add(other_order)
        await db_session.commit()
        await db_session.refresh(other_order)

        response = await authenticated_client.post(f"/orders/{other_order.id}/cancel/")

        assert response.status_code == 404


class TestRequestRefund:
    async def test_refund_non_paid_order_returns_400(
        self, authenticated_client: AsyncClient, db_session, certification
    ):
        movie = await create_movie(db_session, certification)
        await authenticated_client.post(f"/cart/{movie.id}/")
        place_response = await authenticated_client.post("/orders/")
        order_id = place_response.json()["order"]["id"]

        response = await authenticated_client.post(f"/orders/{order_id}/refund/")

        assert response.status_code == 400

    async def test_refund_paid_order_succeeds(
        self, authenticated_client: AsyncClient, active_user, db_session
    ):
        order = Order(
            user_id=active_user.id,
            status=OrderStatusEnum.PAID,
            total_amount=Decimal("9.99"),
        )
        db_session.add(order)
        await db_session.commit()
        await db_session.refresh(order)

        response = await authenticated_client.post(f"/orders/{order.id}/refund/")

        assert response.status_code == 200
        assert response.json()["status"] == "refunded"


class TestOrderExcludesPurchasedMovies:
    async def test_movie_already_paid_is_excluded_from_new_order(
        self, authenticated_client: AsyncClient, active_user, db_session, certification
    ):
        movie = await create_movie(db_session, certification)

        paid_order = Order(
            user_id=active_user.id,
            status=OrderStatusEnum.PAID,
            total_amount=movie.price,
        )
        db_session.add(paid_order)
        await db_session.commit()
        await db_session.refresh(paid_order)

        db_session.add(
            OrderItem(
                order_id=paid_order.id, movie_id=movie.id, price_at_order=movie.price
            )
        )
        await db_session.commit()

        await authenticated_client.post(f"/cart/{movie.id}/")

        response = await authenticated_client.post("/orders/")

        assert response.status_code == 400
        assert "already purchased" in response.json()["detail"].lower()


class TestListAllOrdersModerator:
    async def test_admin_can_list_all_orders(
        self, authenticated_admin_client, active_user, db_session
    ):
        order = Order(
            user_id=active_user.id,
            status=OrderStatusEnum.PENDING,
            total_amount=Decimal("9.99"),
        )
        db_session.add(order)
        await db_session.commit()

        response = await authenticated_admin_client.get("/orders/admin/")

        assert response.status_code == 200
        assert len(response.json()) == 1

    async def test_moderator_can_list_all_orders(self, authenticated_moderator_client):
        response = await authenticated_moderator_client.get("/orders/admin/")

        assert response.status_code == 200

    async def test_regular_user_cannot_list_all_orders(self, authenticated_client):
        response = await authenticated_client.get("/orders/admin/")

        assert response.status_code == 403

    async def test_filter_by_status(
        self, authenticated_admin_client, active_user, db_session
    ):
        pending = Order(
            user_id=active_user.id,
            status=OrderStatusEnum.PENDING,
            total_amount=Decimal("9.99"),
        )
        canceled = Order(
            user_id=active_user.id,
            status=OrderStatusEnum.CANCELED,
            total_amount=Decimal("12.99"),
        )
        db_session.add_all([pending, canceled])
        await db_session.commit()

        response = await authenticated_admin_client.get(
            "/orders/admin/", params={"status": "pending"}
        )

        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]["status"] == "pending"

    async def test_filter_by_user_id(
        self, authenticated_admin_client, active_user, other_user, db_session
    ):
        db_session.add(
            Order(
                user_id=active_user.id,
                status=OrderStatusEnum.PENDING,
                total_amount=Decimal("9.99"),
            )
        )
        db_session.add(
            Order(
                user_id=other_user.id,
                status=OrderStatusEnum.PENDING,
                total_amount=Decimal("12.99"),
            )
        )
        await db_session.commit()

        response = await authenticated_admin_client.get(
            "/orders/admin/", params={"user_id": other_user.id}
        )

        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
