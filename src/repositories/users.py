from sqlalchemy import select

from database.models.accounts import User, UserGroup, UserGroupEnum
from repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()


class UserGroupRepository(BaseRepository[UserGroup]):
    model = UserGroup

    async def get_by_name(self, name: UserGroupEnum) -> UserGroup | None:
        stmt = select(UserGroup).where(UserGroup.name == name)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
