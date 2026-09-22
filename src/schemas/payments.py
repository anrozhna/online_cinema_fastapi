from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from database.models.payments import PaymentStatusEnum


class PaymentItemResponseSchema(BaseModel):
    id: int = Field(..., description="Unique identifier of the payment item.")
    price_at_payment: Decimal = Field(
        ..., description="Price charged for this item.", examples=["9.99"]
    )


class PaymentResponseSchema(BaseModel):
    id: int = Field(..., description="Unique identifier of the payment.")
    order_id: int = Field(..., description="ID of the order this payment is for.")
    status: PaymentStatusEnum = Field(
        ..., description="Current status of the payment.", examples=["pending"]
    )
    amount: Decimal = Field(..., description="Amount charged.", examples=["9.99"])
    created_at: datetime = Field(
        ..., description="Timestamp when the payment was created."
    )
    items: list[PaymentItemResponseSchema] = Field(default_factory=list)
    retry_recommended: bool = Field(
        default=False,
        description="True if this payment failed and the order can still be retried.",
    )


class CreateCheckoutSessionResponseSchema(BaseModel):
    payment_id: int = Field(..., description="ID of the created Payment record.")
    checkout_url: str = Field(
        ...,
        description="Stripe-hosted checkout page URL to redirect the user to.",
        examples=["https://checkout.stripe.com/c/pay/cs_test_..."],
    )
