from fastapi import APIRouter, status

from config.dependencies import CurrentUser
from schemas.orders import OrderResponseSchema, PlaceOrderResponseSchema
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


@router.get(
    path="/",
    response_model=list[OrderResponseSchema],
    status_code=status.HTTP_200_OK,
    summary="List my orders",
    description="Retrieve all orders placed by the current user. "
    "Requires a valid Bearer access token.",
    responses={
        200: {"description": "Orders retrieved successfully."},
        401: {"description": "Invalid or missing access token."},
    },
)
async def list_orders(current_user: CurrentUser, order_service: OrderServiceDep):
    return await order_service.list_orders(current_user.id)
