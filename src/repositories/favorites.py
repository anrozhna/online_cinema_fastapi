from sqlalchemy import select

from database.models.movies import Favorite, Movie
from repositories.base_movie import BaseMovieRepository


class FavoriteRepository(BaseMovieRepository):
    model = Favorite

    async def get_by_user_and_movie(
        self, user_id: int, movie_id: int
    ) -> Favorite | None:
        stmt = select(Favorite).where(
            Favorite.user_id == user_id, Favorite.movie_id == movie_id
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_favorite_movies(
        self,
        user_id: int,
        limit: int,
        offset: int,
        year: int | None = None,
        min_imdb: float | None = None,
        search: str | None = None,
        sort_by=None,
        sort_desc: bool = False,
    ) -> list[Movie]:
        base_stmt = (
            select(Movie)
            .join(Favorite, Favorite.movie_id == Movie.id)
            .where(Favorite.user_id == user_id)
        )
        stmt = self._apply_filters(
            stmt=base_stmt, year=year, min_imdb=min_imdb, search=search
        )
        return await self._paginate_and_sort(
            stmt=stmt, limit=limit, offset=offset, sort_by=sort_by, sort_desc=sort_desc
        )

    async def count_favorite_movies(
        self,
        user_id: int,
        year: int | None = None,
        min_imdb: float | None = None,
        search: str | None = None,
    ) -> int:
        base_stmt = (
            select(Movie)
            .join(Favorite, Favorite.movie_id == Movie.id)
            .where(Favorite.user_id == user_id)
        )
        stmt = self._apply_filters(base_stmt, year, min_imdb, search)
        return await self._count(stmt)
