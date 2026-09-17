from typing import Generic, TypeVar

from sqlalchemy import select

from database.models.base import Base
from database.session import DataBase

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Generic CRUD helpers shared by every model-specific repository.

    Subclasses set `model` to the SQLAlchemy model class they wrap.
    Session lifecycle (commit/rollback) stays the caller's (service's)
    responsibility — the repository only builds and executes queries.
    """

    model: type[ModelType]

    def __init__(self, db: DataBase):
        self.db = db

    async def get_by_id(self, record_id: int) -> ModelType | None:
        stmt = select(self.model).where(self.model.id == record_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    def add(self, instance: ModelType) -> None:
        self.db.add(instance)

    async def delete(self, instance: ModelType) -> None:
        await self.db.delete(instance)


class NamedEntityRepository(BaseRepository[ModelType]):
    """For simple reference models with a unique `name` column
    (Genre, Star, Director, Certification)."""

    async def get_by_name(self, name: str) -> ModelType | None:
        stmt = select(self.model).where(self.model.name == name)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
