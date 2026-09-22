from datetime import datetime
from typing import Any, Sequence, TypeVar

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.strategy_options import _AbstractLoad

ModelType = TypeVar("ModelType")


def apply_user_status_date_filters(
    stmt: Select,
    model,
    user_id: int | None,
    status,
    created_after: datetime | None,
    created_before: datetime | None,
) -> Select:
    """Shared WHERE-clause logic for any admin 'list all X with filters'
    endpoint — used by OrderRepository.list_all and PaymentRepository.list_all.
    """
    if user_id is not None:
        stmt = stmt.where(model.user_id == user_id)
    if status is not None:
        stmt = stmt.where(model.status == status)
    if created_after is not None:
        stmt = stmt.where(model.created_at >= created_after)
    if created_before is not None:
        stmt = stmt.where(model.created_at <= created_before)
    return stmt.order_by(model.created_at.desc())


async def list_all_with_filters(
    db: AsyncSession,
    model: type[ModelType],
    load_options: Sequence[_AbstractLoad],
    user_id: int | None,
    status: Any,
    created_after: datetime | None,
    created_before: datetime | None,
) -> list[ModelType]:
    """Full 'admin list with filters' query: builds the SELECT with eager
    loading, applies the shared WHERE/ORDER BY logic, executes, and
    returns unique results. Used by OrderRepository.list_all and
    PaymentRepository.list_all — the only thing that differs between the
    two is the model and its eager-load options.
    """
    stmt = select(model).options(*load_options)
    stmt = apply_user_status_date_filters(
        stmt, model, user_id, status, created_after, created_before
    )
    result = await db.execute(stmt)
    return list(result.unique().scalars().all())
