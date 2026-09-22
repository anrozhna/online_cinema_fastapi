from sqlalchemy import select
from sqlalchemy.orm import selectinload

from database.models.payments import Payment, PaymentItem
from repositories.base import BaseRepository


class PaymentRepository(BaseRepository[Payment]):
    model = Payment

    async def get_by_external_payment_id(
        self, external_payment_id: str
    ) -> Payment | None:
        stmt = select(Payment).where(Payment.external_payment_id == external_payment_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_user(self, user_id: int) -> list[Payment]:
        stmt = (
            select(Payment)
            .options(selectinload(Payment.items).selectinload(PaymentItem.order_item))
            .where(Payment.user_id == user_id)
            .order_by(Payment.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.unique().scalars().all())
