from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from database.models.accounts import User
from database.models.cart import Cart, CartItem
from database.models.movies import Movie
from database.models.orders import Order, OrderItem, OrderStatusEnum
from services.orders import OrderService


@pytest.fixture()
def mock_order_repo():
    return AsyncMock()


@pytest.fixture()
def mock_cart_repo():
    return AsyncMock()


@pytest.fixture()
def mock_cart_item_repo():
    return AsyncMock()


@pytest.fixture()
def mock_user_repo():
    return AsyncMock()


@pytest.fixture()
def order_service(mock_order_repo, mock_cart_repo, mock_cart_item_repo, mock_user_repo):
    return OrderService(
        order_repo=mock_order_repo,
        cart_repo=mock_cart_repo,
        cart_item_repo=mock_cart_item_repo,
        user_repo=mock_user_repo,
    )


def _movie(id_, name, price):
    m = Movie(id=id_, name=name, price=Decimal(str(price)))
    m.genres = []
    return m


def _cart_with_items(*movies_and_ids: tuple[int, str, float]) -> Cart:
    """Build an in-memory Cart with one CartItem per (movie_id, name, price)
    tuple — avoids repeating the movie+CartItem+Cart wiring in every test.
    """
    cart = Cart(id=1, user_id=1)
    cart.items = []
    for movie_id, name, price in movies_and_ids:
        movie = _movie(movie_id, name, price)
        item = CartItem(id=movie_id, cart_id=1, movie_id=movie_id)
        item.movie = movie
        cart.items.append(item)
    return cart


class TestPlaceOrderValidation:
    async def test_raises_400_when_cart_is_empty(self, order_service, mock_cart_repo):
        cart = Cart(id=1, user_id=1)
        cart.items = []
        mock_cart_repo.get_or_create_for_user.return_value = cart

        with pytest.raises(HTTPException) as exc_info:
            await order_service.place_order(user_id=1)

        assert exc_info.value.status_code == 400
        assert "empty" in exc_info.value.detail.lower()

    async def test_excludes_already_purchased_movie(
        self, order_service, mock_cart_repo, mock_order_repo, mock_user_repo
    ):
        cart = _cart_with_items((1, "Inception", 9.99))

        mock_cart_repo.get_or_create_for_user.return_value = cart
        mock_order_repo.is_movie_purchased_by_user.return_value = True
        mock_order_repo.is_movie_in_pending_order.return_value = False

        with pytest.raises(HTTPException) as exc_info:
            await order_service.place_order(user_id=1)

        # all items excluded -> 400, since valid_items ends up empty
        assert exc_info.value.status_code == 400
        assert "already purchased" in exc_info.value.detail.lower()

    async def test_excludes_movie_already_in_pending_order(
        self, order_service, mock_cart_repo, mock_order_repo
    ):
        cart = _cart_with_items((1, "Inception", 9.99))
        mock_cart_repo.get_or_create_for_user.return_value = cart
        mock_order_repo.is_movie_purchased_by_user.return_value = False
        mock_order_repo.is_movie_in_pending_order.return_value = True

        with pytest.raises(HTTPException) as exc_info:
            await order_service.place_order(user_id=1)

        assert exc_info.value.status_code == 400

    async def test_sends_notification_when_some_items_excluded(
        self,
        order_service,
        mock_cart_repo,
        mock_order_repo,
        mock_user_repo,
        mock_cart_item_repo,
    ):
        cart = _cart_with_items((1, "Already Owned", 9.99), (2, "New Movie", 12.99))
        mock_cart_repo.get_or_create_for_user.return_value = cart

        async def is_purchased(user_id, movie_id):
            return movie_id == 1

        mock_order_repo.is_movie_purchased_by_user.side_effect = is_purchased
        mock_order_repo.is_movie_in_pending_order.return_value = False

        order = Order(
            id=10,
            user_id=1,
            total_amount=Decimal("12.99"),
            status=OrderStatusEnum.PENDING,
            created_at=datetime.now(timezone.utc),
        )
        order.items = []
        mock_order_repo.get_by_id_with_items.return_value = order

        mock_user_repo.get_by_id.return_value = User(id=1, email="user@example.com")

        with patch(
            "services.orders.send_order_items_excluded_notification_task"
        ) as mock_task:
            result = await order_service.place_order(user_id=1)

            mock_task.delay.assert_called_once_with(
                email="user@example.com", excluded_movie_names="Already Owned"
            )

        assert result.excluded_movie_names == ["Already Owned"]


class TestCancelOrderValidation:
    async def test_raises_404_when_order_belongs_to_another_user(
        self, order_service, mock_order_repo
    ):
        order = Order(id=1, user_id=999, status=OrderStatusEnum.PENDING)
        mock_order_repo.get_by_id_with_items.return_value = order

        with pytest.raises(HTTPException) as exc_info:
            await order_service.cancel_order(user_id=1, order_id=1)

        assert exc_info.value.status_code == 404

    async def test_raises_400_when_order_is_not_pending(
        self, order_service, mock_order_repo
    ):
        order = Order(id=1, user_id=1, status=OrderStatusEnum.PAID)
        order.items = []
        mock_order_repo.get_by_id_with_items.return_value = order

        with pytest.raises(HTTPException) as exc_info:
            await order_service.cancel_order(user_id=1, order_id=1)

        assert exc_info.value.status_code == 400
        assert "pending" in exc_info.value.detail.lower()


class TestRefundValidation:
    async def test_raises_400_when_order_is_not_paid(
        self, order_service, mock_order_repo
    ):
        order = Order(id=1, user_id=1, status=OrderStatusEnum.PENDING)
        order.items = []
        mock_order_repo.get_by_id_with_items.return_value = order

        with pytest.raises(HTTPException) as exc_info:
            await order_service.request_refund(user_id=1, order_id=1)

        assert exc_info.value.status_code == 400
        assert "paid" in exc_info.value.detail.lower()

    async def test_raises_404_when_order_belongs_to_another_user(
        self, order_service, mock_order_repo
    ):
        order = Order(id=1, user_id=999, status=OrderStatusEnum.PAID)
        mock_order_repo.get_by_id_with_items.return_value = order

        with pytest.raises(HTTPException) as exc_info:
            await order_service.request_refund(user_id=1, order_id=1)

        assert exc_info.value.status_code == 404


class TestRevalidateTotalAmount:
    def test_sums_price_at_order_from_items(self, order_service):

        order = Order(id=1, user_id=1)
        item1 = OrderItem(id=1, order_id=1, movie_id=1, price_at_order=Decimal("9.99"))
        item2 = OrderItem(id=2, order_id=1, movie_id=2, price_at_order=Decimal("12.99"))
        order.items = [item1, item2]

        total = order_service.revalidate_total_amount(order)

        assert total == Decimal("22.98")
