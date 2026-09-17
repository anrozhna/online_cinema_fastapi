from sqlalchemy import func, select

from database.models.movies import MovieReaction
from repositories.base import BaseRepository


class MovieReactionRepository(BaseRepository[MovieReaction]):
    model = MovieReaction

    async def get_by_user_and_movie(
        self, user_id: int, movie_id: int
    ) -> MovieReaction | None:
        stmt = select(MovieReaction).where(
            MovieReaction.user_id == user_id, MovieReaction.movie_id == movie_id
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def count_likes_and_dislikes(self, movie_id: int) -> tuple[int, int]:
        """Returns (likes_count, dislikes_count) in a single query."""
        stmt = select(
            func.count().filter(MovieReaction.is_like.is_(True)),
            func.count().filter(MovieReaction.is_like.is_(False)),
        ).where(MovieReaction.movie_id == movie_id)
        result = await self.db.execute(stmt)
        likes, dislikes = result.one()
        return likes, dislikes
