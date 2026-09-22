from decimal import Decimal
from unittest.mock import MagicMock, patch

from httpx import AsyncClient

from database.models.orders import Order, OrderStatusEnum
from tests.conftest import create_movie


class TestCreateCheckoutSession:
    async def test_creates_session_for_pending_order(
        self, authenticated_client: AsyncClient, db_session, certification
    ):
        movie = await create_movie(db_session, certification)
        await authenticated_client.post(f"/cart/{movie.id}/")
        place_response = await authenticated_client.post("/orders/")
        order_id = place_response.json()["order"]["id"]

        fake_session = MagicMock()
        fake_session.id = "cs_test_fake123"
        fake_session.url = "https://checkout.stripe.com/c/pay/cs_test_fake123"

        with patch(
            "stripe.checkout.Session.create", return_value=fake_session
        ) as mock_create:
            response = await authenticated_client.post(
                f"/payments/orders/{order_id}/checkout/"
            )

        assert response.status_code == 201
        body = response.json()
        assert body["checkout_url"] == fake_session.url
        mock_create.assert_called_once()

    async def test_returns_404_for_nonexistent_order(
        self, authenticated_client: AsyncClient
    ):
        response = await authenticated_client.post("/payments/orders/999999/checkout/")

        assert response.status_code == 404

    async def test_returns_400_for_non_pending_order(
        self, authenticated_client: AsyncClient, active_user, db_session
    ):
        order = Order(
            user_id=active_user.id,
            status=OrderStatusEnum.CANCELED,
            total_amount=Decimal("9.99"),
        )
        db_session.add(order)
        await db_session.commit()
        await db_session.refresh(order)

        response = await authenticated_client.post(
            f"/payments/orders/{order.id}/checkout/"
        )

        assert response.status_code == 400

    async def test_returns_502_when_stripe_call_fails(
        self, authenticated_client: AsyncClient, db_session, certification
    ):
        import stripe

        movie = await create_movie(db_session, certification)
        await authenticated_client.post(f"/cart/{movie.id}/")
        place_response = await authenticated_client.post("/orders/")
        order_id = place_response.json()["order"]["id"]

        with patch(
            "stripe.checkout.Session.create",
            side_effect=stripe.error.StripeError("card declined"),
        ):
            response = await authenticated_client.post(
                f"/payments/orders/{order_id}/checkout/"
            )

        assert response.status_code == 502

    async def test_cannot_checkout_other_users_order(
        self, authenticated_client: AsyncClient, other_user, db_session, user_group
    ):
        other_order = Order(
            user_id=other_user.id,
            status=OrderStatusEnum.PENDING,
            total_amount=Decimal("9.99"),
        )
        db_session.add(other_order)
        await db_session.commit()
        await db_session.refresh(other_order)

        response = await authenticated_client.post(
            f"/payments/orders/{other_order.id}/checkout/"
        )

        assert response.status_code == 404

    async def test_requires_authentication(self, client: AsyncClient):
        response = await client.post("/payments/orders/1/checkout/")

        assert response.status_code == 401


class TestPaymentHistory:
    async def test_lists_created_payments(
        self, authenticated_client: AsyncClient, db_session, certification
    ):
        movie = await create_movie(db_session, certification)
        await authenticated_client.post(f"/cart/{movie.id}/")
        place_response = await authenticated_client.post("/orders/")
        order_id = place_response.json()["order"]["id"]

        fake_session = MagicMock()
        fake_session.id = "cs_test_fake456"
        fake_session.url = "https://checkout.stripe.com/c/pay/cs_test_fake456"

        with patch("stripe.checkout.Session.create", return_value=fake_session):
            await authenticated_client.post(f"/payments/orders/{order_id}/checkout/")

        response = await authenticated_client.get("/payments/")

        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]["status"] == "pending"

    async def test_empty_history_for_new_user(self, authenticated_client: AsyncClient):
        response = await authenticated_client.get("/payments/")

        assert response.status_code == 200
        assert response.json() == []
