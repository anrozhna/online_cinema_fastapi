from fastapi import APIRouter, status

from config.dependencies import CurrentUser
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
