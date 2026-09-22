from sqlalchemy import select
from sqlalchemy.orm import selectinload

from database.models.payments import Payment, PaymentItem
from repositories.base import BaseRepository
from repositories.query_helpers import list_all_with_filters


class PaymentRepository(BaseRepository[Payment]):
    model = Payment

    async def get_by_external_payment_id(
        self, external_payment_id: str
    ) -> Payment | None:
        stmt = select(Payment).where(Payment.external_payment_id == external_payment_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_user(self, user_id: int) -> list[Payment]:
        return await list_all_with_filters(
            self.db,
            Payment,
            [selectinload(Payment.items).selectinload(PaymentItem.order_item)],
            user_id=user_id,
            status=None,
            created_after=None,
            created_before=None,
        )

    async def list_all(
        self, user_id=None, status=None, created_after=None, created_before=None
    ):
        return await list_all_with_filters(
            self.db,
            Payment,
            [selectinload(Payment.items).selectinload(PaymentItem.order_item)],
            user_id,
            status,
            created_after,
            created_before,
        )
