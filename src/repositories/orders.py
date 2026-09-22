from sqlalchemy import select
from sqlalchemy.orm import selectinload

from database.models.orders import Order, OrderItem, OrderStatusEnum
from repositories.base import BaseRepository
from repositories.query_helpers import list_all_with_filters


class OrderRepository(BaseRepository[Order]):
    model = Order

    async def get_by_id_with_items(self, order_id: int) -> Order | None:
        stmt = (
            select(Order)
            .options(selectinload(Order.items).selectinload(OrderItem.movie))
            .where(Order.id == order_id)
            .execution_options(populate_existing=True)
        )
        result = await self.db.execute(stmt)
        return result.unique().scalar_one_or_none()

    async def list_by_user(self, user_id: int) -> list[Order]:
        stmt = (
            select(Order)
            .options(selectinload(Order.items).selectinload(OrderItem.movie))
            .where(Order.user_id == user_id)
            .order_by(Order.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.unique().scalars().all())

    async def is_movie_purchased_by_user(self, user_id: int, movie_id: int) -> bool:
        stmt = (
            select(OrderItem.id)
            .join(Order, Order.id == OrderItem.order_id)
            .where(
                Order.user_id == user_id,
                Order.status == OrderStatusEnum.PAID,
                OrderItem.movie_id == movie_id,
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def is_movie_in_pending_order(self, user_id: int, movie_id: int) -> bool:
        stmt = (
            select(OrderItem.id)
            .join(Order, Order.id == OrderItem.order_id)
            .where(
                Order.user_id == user_id,
                Order.status == OrderStatusEnum.PENDING,
                OrderItem.movie_id == movie_id,
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def list_all(
        self, user_id=None, status=None, created_after=None, created_before=None
    ):
        return await list_all_with_filters(
            self.db,
            Order,
            [selectinload(Order.items).selectinload(OrderItem.movie)],
            user_id,
            status,
            created_after,
            created_before,
        )
