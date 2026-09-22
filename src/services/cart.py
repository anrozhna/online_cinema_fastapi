from typing import Annotated

from fastapi import Depends, HTTPException, status

from config.dependencies import CartItemRepo, CartRepo, MovieRepo
from database.models.cart import Cart, CartItem
from schemas.cart import CartItemResponseSchema, CartResponseSchema


class CartService:
    def __init__(
        self, cart_repo: CartRepo, cart_item_repo: CartItemRepo, movie_repo: MovieRepo
    ):
        self.cart_repo = cart_repo
        self.cart_item_repo = cart_item_repo
        self.movie_repo = movie_repo

    @staticmethod
    def _build_cart_response(cart: Cart) -> CartResponseSchema:
        items = [
            CartItemResponseSchema(
                id=item.id,
                movie_id=item.movie_id,
                movie_name=item.movie.name,
                movie_price=item.movie.price,
                movie_year=item.movie.year,
                movie_genres=[g.name for g in item.movie.genres],
                added_at=item.added_at,
            )
            for item in cart.items
        ]
        return CartResponseSchema(
            id=cart.id,
            items=items,
            total_price=sum(item.movie_price for item in items),
        )

    async def get_cart(self, user_id: int) -> CartResponseSchema:
        cart = await self.cart_repo.get_or_create_for_user(user_id)
        return self._build_cart_response(cart)

    async def add_to_cart(self, user_id: int, movie_id: int) -> CartResponseSchema:
        movie = await self.movie_repo.get_by_id(movie_id)
        if movie is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Movie not found."
            )

        # TODO(orders): once Order/OrderItem exist, check here whether the
        # user has already purchased this movie and raise 409 if so. For
        # now there is no purchase record anywhere in the system.
        is_purchased = False
        if is_purchased:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You have already purchased this movie.",
            )

        cart = await self.cart_repo.get_or_create_for_user(user_id)

        existing = await self.cart_item_repo.get_by_cart_and_movie(cart.id, movie_id)
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This movie is already in your cart.",
            )

        item = CartItem(cart_id=cart.id, movie_id=movie_id)
        self.cart_item_repo.add(item)
        await self.cart_item_repo.db.commit()

        cart = await self.cart_repo.get_by_user_id(user_id)
        return self._build_cart_response(cart)

    async def remove_from_cart(self, user_id: int, movie_id: int) -> CartResponseSchema:
        cart = await self.cart_repo.get_or_create_for_user(user_id)

        item = await self.cart_item_repo.get_by_cart_and_movie(cart.id, movie_id)
        if item is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Movie is not in your cart.",
            )

        await self.cart_item_repo.delete(item)
        await self.cart_item_repo.db.commit()

        cart = await self.cart_repo.get_by_user_id(user_id)
        return self._build_cart_response(cart)

    async def clear_cart(self, user_id: int) -> None:
        cart = await self.cart_repo.get_or_create_for_user(user_id)
        for item in list(cart.items):
            await self.cart_item_repo.delete(item)
        await self.cart_item_repo.db.commit()

    async def checkout(self, user_id: int) -> None:
        cart = await self.cart_repo.get_or_create_for_user(user_id)
        if not cart.items:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Cart is empty."
            )

        # TODO(orders): once Order/OrderItem exist, this should create an
        # Order + OrderItem rows from the cart's contents (and trigger
        # payment), then clear the cart. For now this only clears the cart
        # so the endpoint is wired end-to-end and ready to be extended.
        for item in list(cart.items):
            await self.cart_item_repo.delete(item)
        await self.cart_item_repo.db.commit()


CartServiceDep = Annotated[CartService, Depends()]
