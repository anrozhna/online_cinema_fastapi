from fastapi import APIRouter, status

from config.dependencies import CurrentUser
from schemas.orders import PlaceOrderResponseSchema
from services.orders import OrderServiceDep

router = APIRouter()


@router.post(
    path="/",
    response_model=PlaceOrderResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Place an order from the cart",
    description=(
        "Create an order from the current user's cart contents. Movies "
        "already purchased or already in a pending order are excluded, "
        "and the user is notified by email if any items were excluded. "
        "Requires a valid Bearer access token."
    ),
    responses={
        201: {"description": "Order placed successfully."},
        400: {"description": "Cart is empty, or all items were excluded."},
        401: {"description": "Invalid or missing access token."},
    },
)
async def place_order(current_user: CurrentUser, order_service: OrderServiceDep):
    return await order_service.place_order(current_user.id)
