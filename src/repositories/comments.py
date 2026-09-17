from sqlalchemy import select

from database.models.movies import Comment
from repositories.base import BaseRepository


class CommentRepository(BaseRepository[Comment]):
    model = Comment

    async def list_by_movie(self, movie_id: int) -> list[Comment]:
        """Returns a FLAT list of all comments for the movie, ordered by
        creation time. Deliberately does not eager-load `replies` —
        the reply tree has unbounded depth, so SQLAlchemy's selectinload
        (which must name each level explicitly) can't express it. The
        service builds the nested tree from this flat list in Python
        instead of letting Pydantic walk unloaded relationships (which
        would trigger a lazy load and MissingGreenlet in async context).
        """
        stmt = (
            select(Comment)
            .where(Comment.movie_id == movie_id)
            .order_by(Comment.created_at.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
