from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from database.models.cart import Cart, CartItem
from database.models.movies import Movie
from repositories.base import BaseRepository


class CartRepository(BaseRepository[Cart]):
    model = Cart

    async def get_by_user_id(self, user_id: int) -> Cart | None:
        stmt = (
            select(Cart)
            .options(
                selectinload(Cart.items)
                .selectinload(CartItem.movie)
                .selectinload(Movie.genres)
            )
            .where(Cart.user_id == user_id)
            .execution_options(populate_existing=True)
        )
        result = await self.db.execute(stmt)
        return result.unique().scalar_one_or_none()

    async def get_or_create_for_user(self, user_id: int) -> Cart:
        cart = await self.get_by_user_id(user_id)
        if cart is not None:
            return cart

        cart = Cart(user_id=user_id)
        self.add(cart)
        await self.db.commit()
        await self.db.refresh(cart)
        return await self.get_by_user_id(user_id)


class CartItemRepository(BaseRepository[CartItem]):
    model = CartItem

    async def get_by_cart_and_movie(
        self, cart_id: int, movie_id: int
    ) -> CartItem | None:
        stmt = select(CartItem).where(
            CartItem.cart_id == cart_id, CartItem.movie_id == movie_id
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def count_by_movie_id(self, movie_id: int) -> int:
        stmt = (
            select(func.count())
            .select_from(CartItem)
            .where(CartItem.movie_id == movie_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one()
