from sqlalchemy import select

from database.models.accounts import UserProfile
from repositories.base import BaseRepository


class ProfileRepository(BaseRepository[UserProfile]):
    model = UserProfile

    async def get_by_user_id(self, user_id: int) -> UserProfile | None:
        stmt = select(UserProfile).where(UserProfile.user_id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
