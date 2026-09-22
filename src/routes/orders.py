from datetime import datetime

from fastapi import APIRouter, Depends, Query, status

from config.dependencies import CurrentUser, require_admin_or_moderator
from database.models.orders import OrderStatusEnum
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


@router.post(
    path="/{order_id}/cancel/",
    response_model=OrderResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Cancel a pending order",
    description="Cancel one of the current user's own pending orders. "
    "Requires a valid Bearer access token.",
    responses={
        200: {"description": "Order canceled successfully."},
        400: {"description": "Only pending orders can be canceled."},
        401: {"description": "Invalid or missing access token."},
        404: {"description": "Order not found."},
        422: {"description": "Invalid order_id path parameter."},
    },
)
async def cancel_order(
    order_id: int, current_user: CurrentUser, order_service: OrderServiceDep
):
    return await order_service.cancel_order(current_user.id, order_id)


@router.post(
    path="/{order_id}/refund/",
    response_model=OrderResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Request a refund for a paid order",
    description=(
        "Mark one of the current user's own paid orders as refunded. "
        "Requires a valid Bearer access token."
    ),
    responses={
        200: {"description": "Order refunded successfully."},
        400: {"description": "Only paid orders can be refunded."},
        401: {"description": "Invalid or missing access token."},
        404: {"description": "Order not found."},
        422: {"description": "Invalid order_id path parameter."},
    },
)
async def request_refund(
    order_id: int, current_user: CurrentUser, order_service: OrderServiceDep
):
    return await order_service.request_refund(current_user.id, order_id)


@router.get(
    path="/admin/",
    response_model=list[OrderResponseSchema],
    status_code=status.HTTP_200_OK,
    summary="List all orders (admin/moderator)",
    description=(
        "Retrieve all orders across all users, with optional filters by "
        "user ID, status, and date range. "
        "Requires administrator or moderator privileges."
    ),
    responses={
        200: {"description": "Orders retrieved successfully."},
        403: {"description": "Admin or moderator privileges required."},
        422: {
            "description": "Invalid query parameter value "
            "(e.g. malformed date or status)."
        },
    },
    dependencies=[Depends(require_admin_or_moderator)],
)
async def list_all_orders(
    order_service: OrderServiceDep,
    user_id: int | None = Query(default=None, description="Filter by user ID."),
    order_status: OrderStatusEnum | None = Query(
        default=None, alias="status", description="Filter by order status."
    ),
    created_after: datetime | None = Query(
        default=None, description="Filter to orders created on or after this timestamp."
    ),
    created_before: datetime | None = Query(
        default=None,
        description="Filter to orders created on or before this timestamp.",
    ),
):
    return await order_service.list_all_orders(
        user_id=user_id,
        order_status=order_status,
        created_after=created_after,
        created_before=created_before,
    )
