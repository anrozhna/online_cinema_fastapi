from fastapi import APIRouter, Depends, status

from config.dependencies import CurrentUser, require_admin_or_moderator
from schemas.cart import CartResponseSchema
from services.cart import CartServiceDep

router = APIRouter()


@router.post(
    path="/checkout/",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Checkout the cart",
    description=(
        "Checkout the current cart. Currently clears the cart without creating "
        "an order — full order/payment flow will be added once Orders exist. "
        "Requires a valid Bearer access token."
    ),
    responses={
        204: {"description": "Checkout completed successfully."},
        400: {"description": "Cart is empty."},
        401: {"description": "Invalid or missing access token."},
    },
)
async def checkout_cart(current_user: CurrentUser, cart_service: CartServiceDep):
    await cart_service.checkout(current_user.id)


@router.post(
    path="/{movie_id}/",
    response_model=CartResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Add a movie to the cart",
    description="Add a movie to the current user's cart. "
    "Requires a valid Bearer access token.",
    responses={
        201: {"description": "Movie added to cart successfully."},
        401: {"description": "Invalid or missing access token."},
        404: {"description": "Movie not found."},
        409: {"description": "Movie already in cart, or already purchased."},
    },
)
async def add_to_cart(
    movie_id: int, current_user: CurrentUser, cart_service: CartServiceDep
):
    return await cart_service.add_to_cart(user_id=current_user.id, movie_id=movie_id)


@router.get(
    path="/",
    response_model=CartResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="View cart",
    description="Retrieve the current user's cart contents, "
    "with movie title, price, genres and year. "
    "Requires a valid Bearer access token.",
    responses={
        200: {"description": "Cart retrieved successfully."},
        401: {"description": "Invalid or missing access token."},
    },
)
async def view_cart(current_user: CurrentUser, cart_service: CartServiceDep):
    return await cart_service.get_cart(current_user.id)


@router.delete(
    path="/{movie_id}/",
    response_model=CartResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Remove a movie from the cart",
    description="Remove a movie from the current user's cart. "
    "Requires a valid Bearer access token.",
    responses={
        200: {"description": "Movie removed from cart successfully."},
        401: {"description": "Invalid or missing access token."},
        404: {"description": "Movie is not in your cart."},
        422: {"description": "Invalid movie_id path parameter."},
    },
)
async def remove_from_cart(
    movie_id: int, current_user: CurrentUser, cart_service: CartServiceDep
):
    return await cart_service.remove_from_cart(
        user_id=current_user.id, movie_id=movie_id
    )


@router.delete(
    path="/",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Clear the cart",
    description="Remove all movies from the current user's cart. "
    "Requires a valid Bearer access token.",
    responses={
        204: {"description": "Cart cleared successfully."},
        401: {"description": "Invalid or missing access token."},
    },
)
async def clear_cart(current_user: CurrentUser, cart_service: CartServiceDep):
    await cart_service.clear_cart(current_user.id)


@router.get(
    path="/users/{user_id}/",
    response_model=CartResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="View any user's cart",
    description=(
        "Retrieve any user's cart contents by user ID. "
        "Requires administrator or moderator privileges."
    ),
    responses={
        200: {"description": "Cart retrieved successfully."},
        403: {"description": "Admin or moderator privileges required."},
        422: {"description": "Invalid movie_id path parameter."},
    },
    dependencies=[Depends(require_admin_or_moderator)],
)
async def view_user_cart(user_id: int, cart_service: CartServiceDep):
    return await cart_service.get_cart(user_id)
