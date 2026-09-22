from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from database.models.movies import Movie
from database.models.orders import Order, OrderItem, OrderStatusEnum


@pytest.fixture()
def sync_second_movie(sync_session, sync_certification) -> Movie:
    m = Movie(
        name="Interstellar",
        year=2014,
        time=169,
        imdb=8.6,
        votes=1800000,
        description="A team travels through a wormhole.",
        price=12.99,
        certification_id=sync_certification.id,
    )
    sync_session.add(m)
    sync_session.commit()
    return m


class TestOrder:
    def test_create_order_defaults_to_pending(self, sync_session, sync_user):
        order = Order(user_id=sync_user.id, total_amount=9.99)
        sync_session.add(order)
        sync_session.commit()

        fetched = sync_session.query(Order).filter_by(user_id=sync_user.id).one()
        assert fetched.status == OrderStatusEnum.PENDING
        assert fetched.created_at is not None

    def test_user_can_have_multiple_orders(self, sync_session, sync_user):
        sync_session.add(Order(user_id=sync_user.id, total_amount=9.99))
        sync_session.add(Order(user_id=sync_user.id, total_amount=12.99))
        sync_session.commit()

        assert sync_session.query(Order).filter_by(user_id=sync_user.id).count() == 2

    def test_deleting_order_cascades_to_items(
        self, sync_session, sync_user, sync_movie
    ):
        order = Order(user_id=sync_user.id, total_amount=9.99)
        sync_session.add(order)
        sync_session.commit()

        item = OrderItem(order_id=order.id, movie_id=sync_movie.id, price_at_order=9.99)
        sync_session.add(item)
        sync_session.commit()
        item_id = item.id

        sync_session.delete(order)
        sync_session.commit()

        assert sync_session.query(OrderItem).filter_by(id=item_id).one_or_none() is None


class TestOrderItem:
    def test_create_order_item_snapshots_price(
        self, sync_session, sync_user, sync_movie
    ):
        order = Order(user_id=sync_user.id, total_amount=9.99)
        sync_session.add(order)
        sync_session.commit()

        item = OrderItem(order_id=order.id, movie_id=sync_movie.id, price_at_order=9.99)
        sync_session.add(item)
        sync_session.commit()

        fetched = sync_session.query(OrderItem).filter_by(order_id=order.id).one()
        assert fetched.price_at_order == Decimal("9.99")

    def test_same_movie_cannot_be_added_twice_to_same_order(
        self, sync_session, sync_user, sync_movie
    ):
        order = Order(user_id=sync_user.id, total_amount=19.98)
        sync_session.add(order)
        sync_session.commit()

        sync_session.add(
            OrderItem(order_id=order.id, movie_id=sync_movie.id, price_at_order=9.99)
        )
        sync_session.commit()

        sync_session.add(
            OrderItem(order_id=order.id, movie_id=sync_movie.id, price_at_order=9.99)
        )
        with pytest.raises(IntegrityError):
            sync_session.commit()

    def test_order_can_have_multiple_different_movies(
        self, sync_session, sync_user, sync_movie, sync_second_movie
    ):
        order = Order(user_id=sync_user.id, total_amount=22.98)
        sync_session.add(order)
        sync_session.commit()

        sync_session.add(
            OrderItem(order_id=order.id, movie_id=sync_movie.id, price_at_order=9.99)
        )
        sync_session.add(
            OrderItem(
                order_id=order.id, movie_id=sync_second_movie.id, price_at_order=12.99
            )
        )
        sync_session.commit()

        assert sync_session.query(OrderItem).filter_by(order_id=order.id).count() == 2

    def test_deleting_movie_with_order_item_is_restricted(
        self, sync_session, sync_user, sync_movie
    ):
        """Confirms the RESTRICT foreign key: unlike CartItem, a Movie that
        has ever been ordered cannot be deleted — this is what will let
        MovieService.delete_movie replace its TODO(orders) placeholder
        with a real check, once the orders service layer exists."""
        order = Order(user_id=sync_user.id, total_amount=9.99)
        sync_session.add(order)
        sync_session.commit()

        sync_session.add(
            OrderItem(order_id=order.id, movie_id=sync_movie.id, price_at_order=9.99)
        )
        sync_session.commit()

        sync_session.delete(sync_movie)
        with pytest.raises(IntegrityError):
            sync_session.commit()

    def test_price_at_order_is_independent_of_current_movie_price(
        self, sync_session, sync_user, sync_movie
    ):
        order = Order(user_id=sync_user.id, total_amount=9.99)
        sync_session.add(order)
        sync_session.commit()

        item = OrderItem(order_id=order.id, movie_id=sync_movie.id, price_at_order=9.99)
        sync_session.add(item)
        sync_session.commit()

        sync_movie.price = 19.99
        sync_session.commit()

        sync_session.refresh(item)
        assert item.price_at_order == Decimal("9.99")
