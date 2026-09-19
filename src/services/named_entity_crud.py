from typing import Generic, TypeVar

from fastapi import HTTPException, status

from database.models.base import Base
from repositories.base import NamedEntityRepository

ModelType = TypeVar("ModelType", bound=Base)


class NamedEntityCrud(Generic[ModelType]):
    """Generic create/update/delete for any simple `name`-only reference
    entity (Genre, Star, Director, Certification). One instance per entity
    type, constructed via DI, replaces near-identical CRUD methods that
    would otherwise be duplicated once per entity.
    """

    def __init__(self, repo: NamedEntityRepository[ModelType]):
        self.repo = repo

    async def create(self, data) -> ModelType:
        existing = await self.repo.get_by_name(data.name)
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An entity with this name already exists.",
            )
        entity = self.repo.model(name=data.name)
        self.repo.add(entity)
        await self.repo.db.commit()
        await self.repo.db.refresh(entity)
        return entity

    async def update(self, entity_id: int, data) -> ModelType:
        entity = await self.repo.get_by_id(entity_id)
        if entity is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Not found."
            )
        entity.name = data.name
        await self.repo.db.commit()
        await self.repo.db.refresh(entity)
        return entity

    async def delete(self, entity_id: int) -> None:
        entity = await self.repo.get_by_id(entity_id)
        if entity is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Not found."
            )
        await self.repo.delete(entity)
        await self.repo.db.commit()
