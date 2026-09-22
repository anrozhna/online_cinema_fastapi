from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import stripe
from fastapi import HTTPException

from services.payments import PaymentService


@pytest.fixture()
def mock_payment_repo():
    return AsyncMock()


@pytest.fixture()
def mock_order_repo():
    return AsyncMock()


@pytest.fixture()
def mock_user_repo():
    return AsyncMock()


@pytest.fixture()
def mock_settings():
    settings = MagicMock()
    settings.STRIPE_SECRET_KEY = "sk_test_fake"
    settings.STRIPE_WEBHOOK_SECRET = "whsec_fake"
    return settings


@pytest.fixture()
def payment_service(mock_payment_repo, mock_order_repo, mock_user_repo, mock_settings):
    return PaymentService(
        payment_repo=mock_payment_repo,
        order_repo=mock_order_repo,
        user_repo=mock_user_repo,
        settings=mock_settings,
    )


class TestWebhookSignatureValidation:
    async def test_raises_400_on_invalid_signature(self, payment_service):
        with patch(
            "stripe.Webhook.construct_event",
            side_effect=stripe.error.SignatureVerificationError(
                "bad sig", "sig_header"
            ),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await payment_service.handle_webhook_event(
                    payload=b"{}", signature="bad_sig"
                )

        assert exc_info.value.status_code == 400
        assert "signature" in exc_info.value.detail.lower()

    async def test_raises_400_on_malformed_payload(self, payment_service):
        with patch(
            "stripe.Webhook.construct_event",
            side_effect=ValueError("malformed payload"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await payment_service.handle_webhook_event(
                    payload=b"not json", signature="sig"
                )

        assert exc_info.value.status_code == 400

    async def test_accepts_valid_signature_and_processes_event(
        self, payment_service, mock_payment_repo
    ):
        fake_event = {
            "type": "checkout.session.completed",
            "data": {"object": {"id": "cs_test_123"}},
        }
        mock_payment_repo.get_by_external_payment_id.return_value = (
            None  # unknown -> no-op
        )

        with patch("stripe.Webhook.construct_event", return_value=fake_event):
            # should not raise — valid signature, unknown payment is a silent no-op
            await payment_service.handle_webhook_event(
                payload=b"{}", signature="good_sig"
            )

        mock_payment_repo.get_by_external_payment_id.assert_called_once_with(
            "cs_test_123"
        )

    async def test_ignores_unhandled_event_types(
        self, payment_service, mock_payment_repo
    ):
        fake_event = {"type": "customer.created", "data": {"object": {"id": "cus_123"}}}

        with patch("stripe.Webhook.construct_event", return_value=fake_event):
            await payment_service.handle_webhook_event(
                payload=b"{}", signature="good_sig"
            )

        mock_payment_repo.get_by_external_payment_id.assert_not_called()
