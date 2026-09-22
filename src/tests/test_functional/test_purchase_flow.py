from unittest.mock import MagicMock, patch

from httpx import AsyncClient

from tests.conftest import create_movie


class TestFullPurchaseFlow:
    async def test_cart_to_order_to_payment_end_to_end(
        self, authenticated_client: AsyncClient, db_session, certification
    ):
        movie = await create_movie(
            db_session, certification, name="Inception", price=9.99
        )

        # 1. Add to cart
        add_response = await authenticated_client.post(f"/cart/{movie.id}/")
        assert add_response.status_code == 201
        assert add_response.json()["total_price"] == 9.99

        # 2. View cart confirms the item
        cart_response = await authenticated_client.get("/cart/")
        assert len(cart_response.json()["items"]) == 1

        # 3. Place order from cart
        order_response = await authenticated_client.post("/orders/")
        assert order_response.status_code == 201
        order_body = order_response.json()
        assert order_body["excluded_movie_names"] == []
        order_id = order_body["order"]["id"]
        assert order_body["order"]["status"] == "pending"

        # 4. Cart is now empty
        empty_cart = await authenticated_client.get("/cart/")
        assert empty_cart.json()["items"] == []

        # 5. Order appears in the user's order list
        orders_list = await authenticated_client.get("/orders/")
        assert len(orders_list.json()) == 1

        # 6. Create a Stripe checkout session (Stripe itself is mocked)
        fake_session = MagicMock()
        fake_session.id = "cs_test_e2e_fake"
        fake_session.url = "https://checkout.stripe.com/c/pay/cs_test_e2e_fake"

        with patch("stripe.checkout.Session.create", return_value=fake_session):
            checkout_response = await authenticated_client.post(
                f"/payments/orders/{order_id}/checkout/"
            )
        assert checkout_response.status_code == 201
        assert checkout_response.json()["checkout_url"] == fake_session.url

        # 7. Payment history shows the pending payment
        payments_response = await authenticated_client.get("/payments/")
        assert len(payments_response.json()) == 1
        assert payments_response.json()[0]["status"] == "pending"

        # 8. Simulate Stripe confirming payment via webhook
        fake_event = {
            "type": "checkout.session.completed",
            "data": {"object": {"id": "cs_test_e2e_fake"}},
        }
        with patch("stripe.Webhook.construct_event", return_value=fake_event):
            webhook_response = await authenticated_client.post(
                "/payments/webhook/",
                content=b"{}",
                headers={"Stripe-Signature": "fake_signature"},
            )
        assert webhook_response.status_code == 200

        # 9. Order is now paid, payment is successful
        final_orders = await authenticated_client.get("/orders/")
        assert final_orders.json()[0]["status"] == "paid"

        final_payments = await authenticated_client.get("/payments/")
        assert final_payments.json()[0]["status"] == "successful"
