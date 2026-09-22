from typing import Annotated

import stripe
from fastapi import Depends, HTTPException, status

from config.dependencies import GetSettings, OrderRepo, PaymentRepo
from database.models.orders import OrderStatusEnum
from database.models.payments import Payment, PaymentItem
from schemas.payments import (
    CreateCheckoutSessionResponseSchema,
    PaymentItemResponseSchema,
    PaymentResponseSchema,
)


class PaymentService:
    def __init__(
        self, payment_repo: PaymentRepo, order_repo: OrderRepo, settings: GetSettings
    ):
        self.payment_repo = payment_repo
        self.order_repo = order_repo
        self.settings = settings
        stripe.api_key = settings.STRIPE_SECRET_KEY

    @staticmethod
    def _build_payment_response(payment: Payment) -> PaymentResponseSchema:
        return PaymentResponseSchema(
            id=payment.id,
            order_id=payment.order_id,
            status=payment.status,
            amount=payment.amount,
            created_at=payment.created_at,
            items=[
                PaymentItemResponseSchema(id=i.id, price_at_payment=i.price_at_payment)
                for i in payment.items
            ],
        )

    async def create_checkout_session(
        self, user_id: int, order_id: int
    ) -> CreateCheckoutSessionResponseSchema:
        order = await self.order_repo.get_by_id_with_items(order_id)
        if order is None or order.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Order not found."
            )

        if order.status != OrderStatusEnum.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only pending orders can be paid.",
            )

        # Recompute the total from stored OrderItem snapshots — never trust
        # a client-suppliable amount, and guard against any total_amount
        # drift since the order was placed.
        from services.orders import OrderService

        validated_total = OrderService.revalidate_total_amount(order)

        payment = Payment(user_id=user_id, order_id=order.id, amount=validated_total)
        self.payment_repo.add(payment)
        await self.payment_repo.db.flush()

        for order_item in order.items:
            self.payment_repo.db.add(
                PaymentItem(
                    payment_id=payment.id,
                    order_item_id=order_item.id,
                    price_at_payment=order_item.price_at_order,
                )
            )
        await self.payment_repo.db.commit()

        try:
            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                mode="payment",
                line_items=[
                    {
                        "price_data": {
                            "currency": "usd",
                            "product_data": {"name": item.movie.name},
                            "unit_amount": int(item.price_at_order * 100),
                        },
                        "quantity": 1,
                    }
                    for item in order.items
                ],
                success_url=f"{self.settings.SITE_URL}/orders/{order.id}/",
                cancel_url=f"{self.settings.SITE_URL}/orders/{order.id}/",
                metadata={"payment_id": str(payment.id), "order_id": str(order.id)},
            )
        except stripe.error.StripeError as error:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to create Stripe checkout session: {error}",
            )

        payment.external_payment_id = session.id
        await self.payment_repo.db.commit()

        return CreateCheckoutSessionResponseSchema(
            payment_id=payment.id, checkout_url=session.url
        )

    async def list_payments(self, user_id: int) -> list[PaymentResponseSchema]:
        payments = await self.payment_repo.list_by_user(user_id)
        return [self._build_payment_response(p) for p in payments]


PaymentServiceDep = Annotated[PaymentService, Depends()]
