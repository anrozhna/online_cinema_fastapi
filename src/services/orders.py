from datetime import datetime
from decimal import Decimal
from typing import Annotated

from fastapi import Depends, HTTPException, status

from config.dependencies import CartItemRepo, CartRepo, OrderRepo, UserRepo
from database.models.orders import Order, OrderItem, OrderStatusEnum
from notifications.tasks import send_order_items_excluded_notification_task
from schemas.orders import (
    OrderItemResponseSchema,
    OrderResponseSchema,
    PlaceOrderResponseSchema,
)


class OrderService:
    def __init__(
        self,
        order_repo: OrderRepo,
        cart_repo: CartRepo,
        cart_item_repo: CartItemRepo,
        user_repo: UserRepo,
    ):
        self.order_repo = order_repo
        self.cart_repo = cart_repo
        self.cart_item_repo = cart_item_repo
        self.user_repo = user_repo

    @staticmethod
    def _build_order_response(order: Order) -> OrderResponseSchema:
        return OrderResponseSchema(
            id=order.id,
            status=order.status,
            total_amount=order.total_amount,
            created_at=order.created_at,
            items=[
                OrderItemResponseSchema(
                    id=item.id,
                    movie_id=item.movie_id,
                    movie_name=item.movie.name,
                    price_at_order=item.price_at_order,
                )
                for item in order.items
            ],
        )

    async def place_order(self, user_id: int) -> PlaceOrderResponseSchema:
        cart = await self.cart_repo.get_or_create_for_user(user_id)
        if not cart.items:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Cart is empty."
            )

        valid_items = []
        excluded_names: list[str] = []

        for item in cart.items:
            if await self.order_repo.is_movie_purchased_by_user(user_id, item.movie_id):
                excluded_names.append(item.movie.name)
                continue
            if await self.order_repo.is_movie_in_pending_order(user_id, item.movie_id):
                excluded_names.append(item.movie.name)
                continue
            valid_items.append(item)

        if not valid_items:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="All items in your cart are already purchased "
                "or already in a pending order.",
            )

        total_amount: Decimal = sum(
            (item.movie.price for item in valid_items), Decimal("0")
        )

        order = Order(
            user_id=user_id, total_amount=total_amount, status=OrderStatusEnum.PENDING
        )
        self.order_repo.add(order)
        await self.order_repo.db.commit()
        await self.order_repo.db.refresh(order)

        for item in valid_items:
            order_item = OrderItem(
                order_id=order.id,
                movie_id=item.movie_id,
                price_at_order=item.movie.price,
            )
            self.order_repo.db.add(order_item)

        for item in valid_items:
            await self.cart_item_repo.delete(item)

        await self.order_repo.db.commit()

        if excluded_names:
            user = await self.user_repo.get_by_id(user_id)
            if user is not None:
                send_order_items_excluded_notification_task.delay(
                    email=user.email, excluded_movie_names=", ".join(excluded_names)
                )

        fetched_order = await self.order_repo.get_by_id_with_items(order.id)
        return PlaceOrderResponseSchema(
            order=self._build_order_response(fetched_order),
            excluded_movie_names=excluded_names,
        )

    async def list_orders(self, user_id: int) -> list[OrderResponseSchema]:
        orders = await self.order_repo.list_by_user(user_id)
        return [self._build_order_response(o) for o in orders]

    async def _get_owned_order_or_404(self, user_id: int, order_id: int) -> Order:
        order = await self.order_repo.get_by_id_with_items(order_id)
        if order is None or order.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Order not found."
            )
        return order

    async def cancel_order(self, user_id: int, order_id: int) -> OrderResponseSchema:
        order = await self._get_owned_order_or_404(user_id, order_id)

        if order.status != OrderStatusEnum.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only pending orders can be canceled.",
            )

        order.status = OrderStatusEnum.CANCELED
        await self.order_repo.db.commit()

        fetched_order = await self.order_repo.get_by_id_with_items(order_id)
        return self._build_order_response(fetched_order)

    async def request_refund(self, user_id: int, order_id: int) -> OrderResponseSchema:
        order = await self._get_owned_order_or_404(user_id, order_id)

        if order.status != OrderStatusEnum.PAID:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only paid orders can be refunded.",
            )

        order.status = OrderStatusEnum.REFUNDED
        await self.order_repo.db.commit()

        fetched_order = await self.order_repo.get_by_id_with_items(order_id)
        return self._build_order_response(fetched_order)

    @staticmethod
    def revalidate_total_amount(order: Order) -> Decimal:
        """Recompute the order total from its stored OrderItem snapshots,
        as the single source of truth before charging via a payment
        provider. Not exposed as an endpoint yet — will be called by the
        future Payments flow (Stripe) right before creating a charge, to
        guard against any total_amount drift or client-side tampering.
        """
        return sum((item.price_at_order for item in order.items), Decimal("0"))

    async def list_all_orders(
        self,
        user_id: int | None = None,
        order_status: OrderStatusEnum | None = None,
        created_after: datetime | None = None,
        created_before: datetime | None = None,
    ) -> list[OrderResponseSchema]:
        orders = await self.order_repo.list_all(
            user_id=user_id,
            status=order_status,
            created_after=created_after,
            created_before=created_before,
        )
        return [self._build_order_response(o) for o in orders]


OrderServiceDep = Annotated[OrderService, Depends()]
