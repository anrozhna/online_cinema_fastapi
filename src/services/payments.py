from typing import Annotated

import stripe
from fastapi import Depends, HTTPException, status

from config.dependencies import GetSettings, OrderRepo, PaymentRepo, UserRepo
from database.models.orders import OrderStatusEnum
from database.models.payments import Payment, PaymentItem, PaymentStatusEnum
from notifications.tasks import send_order_confirmation_email_task
from schemas.payments import (
    CreateCheckoutSessionResponseSchema,
    PaymentItemResponseSchema,
    PaymentResponseSchema,
)


class PaymentService:
    def __init__(
        self,
        payment_repo: PaymentRepo,
        order_repo: OrderRepo,
        user_repo: UserRepo,
        settings: GetSettings,
    ):
        self.payment_repo = payment_repo
        self.order_repo = order_repo
        self.user_repo = user_repo
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
            retry_recommended=payment.status == PaymentStatusEnum.FAILED,
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

    def _construct_stripe_event(self, payload: bytes, signature: str) -> stripe.Event:
        try:
            return stripe.Webhook.construct_event(
                payload, signature, self.settings.STRIPE_WEBHOOK_SECRET
            )
        except (ValueError, stripe.error.SignatureVerificationError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid webhook signature.",
            )

    async def handle_webhook_event(self, payload: bytes, signature: str) -> None:
        event = self._construct_stripe_event(payload, signature)

        if event["type"] == "checkout.session.completed":
            await self._handle_payment_success(event["data"]["object"])
        elif event["type"] in (
            "checkout.session.expired",
            "payment_intent.payment_failed",
        ):
            await self._handle_payment_failure(event["data"]["object"])
        # Any other event type is acknowledged but ignored — Stripe expects
        # a 200 for events we don't act on, not an error.

    async def _handle_payment_success(self, stripe_object) -> None:
        payment = await self.payment_repo.get_by_external_payment_id(
            stripe_object["id"]
        )
        if payment is None:
            return  # unknown session — nothing to do, avoid raising to Stripe

        if payment.status == PaymentStatusEnum.SUCCESSFUL:
            return  # already processed — Stripe may retry the same webhook

        payment.status = PaymentStatusEnum.SUCCESSFUL
        order = await self.order_repo.get_by_id_with_items(payment.order_id)
        order.status = OrderStatusEnum.PAID
        await self.payment_repo.db.commit()

        user = await self.user_repo.get_by_id(payment.user_id)
        if user is not None:
            movie_names = ", ".join(item.movie.name for item in order.items)
            send_order_confirmation_email_task.delay(
                email=user.email, order_id=order.id, movie_names=movie_names
            )

    async def _handle_payment_failure(self, stripe_object) -> None:
        payment = await self.payment_repo.get_by_external_payment_id(
            stripe_object["id"]
        )
        if payment is None:
            return

        if payment.status == PaymentStatusEnum.FAILED:
            return

        payment.status = PaymentStatusEnum.FAILED
        await self.payment_repo.db.commit()


PaymentServiceDep = Annotated[PaymentService, Depends()]
