from sqlalchemy import select

from database.models.movies import Favorite, Movie
from repositories.base import BaseRepository
from repositories.base_movie import BaseMovieRepository


class FavoriteMoviesRepository(BaseMovieRepository):
    """Returns Movie rows scoped to a user's favorites — same filtering,
    sorting and pagination as the full catalog (via BaseMovieRepository),
    just joined through the Favorite table."""

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
        stmt = self._apply_filters(base_stmt, year, min_imdb, search)
        return await self._paginate_and_sort(stmt, limit, offset, sort_by, sort_desc)

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


class FavoriteRepository(BaseRepository[Favorite]):
    """CRUD for Favorite rows themselves — adding/removing a user's
    favorite marker on a movie, independent of Movie querying."""

    model = Favorite

    async def get_by_user_and_movie(
        self, user_id: int, movie_id: int
    ) -> Favorite | None:
        stmt = select(Favorite).where(
            Favorite.user_id == user_id, Favorite.movie_id == movie_id
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
