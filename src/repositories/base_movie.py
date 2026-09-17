from enum import Enum

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import selectinload

from database.models.movies import Director, Movie, Star
from repositories.base import BaseRepository


class MovieSortField(str, Enum):
    PRICE = "price"
    YEAR = "year"
    IMDB = "imdb"


class BaseMovieRepository(BaseRepository[Movie]):
    """Shared query-building and result-shaping logic for any repository
    that selects Movie rows — used by MovieRepository (full catalog) and
    FavoriteRepository (a user's favorited movies). Neither subclass
    duplicates filtering, sorting, or pagination logic.
    """

    model = Movie

    @staticmethod
    def _apply_filters(
        stmt: Select, year: int | None, min_imdb: float | None, search: str | None
    ) -> Select:
        if search:
            stmt = (
                stmt.outerjoin(Movie.directors)
                .outerjoin(Movie.stars)
                .where(
                    or_(
                        Movie.name.ilike(f"%{search}%"),
                        Movie.description.ilike(f"%{search}%"),
                        Director.name.ilike(f"%{search}%"),
                        Star.name.ilike(f"%{search}%"),
                    )
                )
                .distinct()
            )

        if year is not None:
            stmt = stmt.where(Movie.year == year)
        if min_imdb is not None:
            stmt = stmt.where(Movie.imdb >= min_imdb)

        return stmt

    async def _paginate_and_sort(
        self,
        stmt: Select,
        limit: int,
        offset: int,
        sort_by: MovieSortField | None = None,
        sort_desc: bool = False,
    ) -> list[Movie]:
        stmt = stmt.options(selectinload(Movie.genres))

        if sort_by is not None:
            column = getattr(Movie, sort_by.value)
            stmt = stmt.order_by(column.desc() if sort_desc else column.asc())

        stmt = stmt.limit(limit).offset(offset)
        result = await self.db.execute(stmt)
        return list(result.unique().scalars().all())

    async def _count(self, stmt: Select) -> int:
        count_stmt = select(func.count()).select_from(stmt.subquery())
        result = await self.db.execute(count_stmt)
        return result.scalar_one()
