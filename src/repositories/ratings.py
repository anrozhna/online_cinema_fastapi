from sqlalchemy import func, select

from database.models.movies import Rating
from repositories.base import BaseRepository


class RatingRepository(BaseRepository[Rating]):
    model = Rating

    async def get_by_user_and_movie(self, user_id: int, movie_id: int) -> Rating | None:
        stmt = select(Rating).where(
            Rating.user_id == user_id, Rating.movie_id == movie_id
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_average_for_movie(self, movie_id: int) -> float | None:
        stmt = select(func.avg(Rating.score)).where(Rating.movie_id == movie_id)
        result = await self.db.execute(stmt)
        return result.scalar_one()
