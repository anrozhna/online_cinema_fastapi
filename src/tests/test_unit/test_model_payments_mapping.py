from decimal import Decimal

import pytest

from database.models.orders import Order, OrderItem, OrderStatusEnum
from database.models.payments import Payment, PaymentItem, PaymentStatusEnum


@pytest.fixture()
def sync_order(sync_session, sync_user) -> Order:
    order = Order(
        user_id=sync_user.id,
        status=OrderStatusEnum.PENDING,
        total_amount=Decimal("9.99"),
    )
    sync_session.add(order)
    sync_session.commit()
    return order


@pytest.fixture()
def sync_order_item(sync_session, sync_order, sync_movie) -> OrderItem:
    item = OrderItem(
        order_id=sync_order.id, movie_id=sync_movie.id, price_at_order=Decimal("9.99")
    )
    sync_session.add(item)
    sync_session.commit()
    return item


class TestPayment:
    def test_create_payment_defaults_to_pending(
        self, sync_session, sync_user, sync_order
    ):
        payment = Payment(
            user_id=sync_user.id, order_id=sync_order.id, amount=Decimal("9.99")
        )
        sync_session.add(payment)
        sync_session.commit()

        fetched = sync_session.query(Payment).filter_by(order_id=sync_order.id).one()
        assert fetched.status == PaymentStatusEnum.PENDING
        assert fetched.external_payment_id is None

    def test_order_can_have_multiple_payment_attempts(
        self, sync_session, sync_user, sync_order
    ):
        sync_session.add(
            Payment(
                user_id=sync_user.id, order_id=sync_order.id, amount=Decimal("9.99")
            )
        )
        sync_session.add(
            Payment(
                user_id=sync_user.id, order_id=sync_order.id, amount=Decimal("9.99")
            )
        )
        sync_session.commit()

        assert (
            sync_session.query(Payment).filter_by(order_id=sync_order.id).count() == 2
        )

    def test_deleting_payment_cascades_to_items(
        self, sync_session, sync_user, sync_order, sync_order_item
    ):
        payment = Payment(
            user_id=sync_user.id, order_id=sync_order.id, amount=Decimal("9.99")
        )
        sync_session.add(payment)
        sync_session.commit()

        item = PaymentItem(
            payment_id=payment.id,
            order_item_id=sync_order_item.id,
            price_at_payment=Decimal("9.99"),
        )
        sync_session.add(item)
        sync_session.commit()
        item_id = item.id

        sync_session.delete(payment)
        sync_session.commit()

        assert (
            sync_session.query(PaymentItem).filter_by(id=item_id).one_or_none() is None
        )


class TestPaymentItem:
    def test_deleting_order_item_with_payment_item_is_restricted(
        self, sync_session, sync_user, sync_order, sync_order_item
    ):
        payment = Payment(
            user_id=sync_user.id, order_id=sync_order.id, amount=Decimal("9.99")
        )
        sync_session.add(payment)
        sync_session.commit()

        sync_session.add(
            PaymentItem(
                payment_id=payment.id,
                order_item_id=sync_order_item.id,
                price_at_payment=Decimal("9.99"),
            )
        )
        sync_session.commit()

        sync_session.delete(sync_order_item)
        with pytest.raises(Exception):  # IntegrityError
            sync_session.commit()

    def test_external_payment_id_can_be_set_after_creation(
        self, sync_session, sync_user, sync_order
    ):
        payment = Payment(
            user_id=sync_user.id, order_id=sync_order.id, amount=Decimal("9.99")
        )
        sync_session.add(payment)
        sync_session.commit()

        payment.external_payment_id = "pi_1234567890"
        payment.status = PaymentStatusEnum.SUCCESSFUL
        sync_session.commit()

        sync_session.refresh(payment)
        assert payment.external_payment_id == "pi_1234567890"
        assert payment.status == PaymentStatusEnum.SUCCESSFUL
