from datetime import datetime

from fastapi import APIRouter, Depends, Header, Query, Request, status

from config.dependencies import CurrentUser, require_admin_or_moderator
from database.models.payments import PaymentStatusEnum
from schemas.payments import CreateCheckoutSessionResponseSchema, PaymentResponseSchema
from services.payments import PaymentServiceDep

router = APIRouter()


@router.post(
    path="/orders/{order_id}/checkout/",
    response_model=CreateCheckoutSessionResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create a Stripe checkout session for an order",
    description=(
        "Create a Stripe Checkout session for one of the current user's "
        "pending orders and return the URL to redirect the user to. "
        "Requires a valid Bearer access token."
    ),
    responses={
        201: {"description": "Checkout session created successfully."},
        400: {"description": "Only pending orders can be paid."},
        401: {"description": "Invalid or missing access token."},
        404: {"description": "Order not found."},
        502: {"description": "Failed to create Stripe checkout session."},
    },
)
async def create_checkout_session(
    order_id: int, current_user: CurrentUser, payment_service: PaymentServiceDep
):
    return await payment_service.create_checkout_session(current_user.id, order_id)


@router.get(
    path="/",
    response_model=list[PaymentResponseSchema],
    status_code=status.HTTP_200_OK,
    summary="List my payment history",
    description="Retrieve all payments made by the current user. "
    "Requires a valid Bearer access token.",
    responses={
        200: {"description": "Payments retrieved successfully."},
        401: {"description": "Invalid or missing access token."},
    },
)
async def list_payments(current_user: CurrentUser, payment_service: PaymentServiceDep):
    return await payment_service.list_payments(current_user.id)


@router.post(
    path="/webhook/",
    status_code=status.HTTP_200_OK,
    summary="Stripe webhook endpoint",
    description=(
        "Receives payment confirmation/failure events from Stripe. "
        "Not intended to be called directly by clients — Stripe verifies "
        "the request signature against STRIPE_WEBHOOK_SECRET."
    ),
    responses={
        200: {"description": "Event processed (or acknowledged and ignored)."},
        400: {"description": "Invalid webhook signature."},
    },
)
async def stripe_webhook(
    request: Request,
    payment_service: PaymentServiceDep,
    stripe_signature: str = Header(..., alias="Stripe-Signature"),
):
    payload = await request.body()
    await payment_service.handle_webhook_event(payload, stripe_signature)
    return {"received": True}


@router.get(
    path="/admin/",
    response_model=list[PaymentResponseSchema],
    status_code=status.HTTP_200_OK,
    summary="List all payments (admin/moderator)",
    description=(
        "Retrieve all payments across all users, with optional filters by "
        "user ID, status, and date range. "
        "Requires administrator or moderator privileges."
    ),
    responses={
        200: {"description": "Payments retrieved successfully."},
        403: {"description": "Admin or moderator privileges required."},
        422: {"description": "Invalid query parameter value."},
    },
    dependencies=[Depends(require_admin_or_moderator)],
)
async def list_all_payments(
    payment_service: PaymentServiceDep,
    user_id: int | None = Query(default=None, description="Filter by user ID."),
    payment_status: PaymentStatusEnum | None = Query(
        default=None, alias="status", description="Filter by payment status."
    ),
    created_after: datetime | None = Query(
        default=None,
        description="Filter to payments created on or after this timestamp.",
    ),
    created_before: datetime | None = Query(
        default=None,
        description="Filter to payments created on or before this timestamp.",
    ),
):
    return await payment_service.list_all_payments(
        user_id=user_id,
        payment_status=payment_status,
        created_after=created_after,
        created_before=created_before,
    )
