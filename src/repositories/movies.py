from enum import Enum

from sqlalchemy import func, or_, select
from sqlalchemy.orm import joinedload, selectinload

from database.models.movies import Certification, Director, Genre, Movie, Star
from repositories.base import BaseRepository, NamedEntityRepository


class MovieSortField(str, Enum):
    PRICE = "price"
    YEAR = "year"
    IMDB = "imdb"


class MovieRepository(BaseRepository[Movie]):
    model = Movie

    async def get_by_uuid(self, movie_uuid) -> Movie | None:
        stmt = (
            select(Movie)
            .options(
                joinedload(Movie.certification),
                selectinload(Movie.genres),
                selectinload(Movie.directors),
                selectinload(Movie.stars),
            )
            .where(Movie.uuid == movie_uuid)
        )
        result = await self.db.execute(stmt)
        return result.unique().scalar_one_or_none()

    @staticmethod
    def _build_filtered_query(
        year: int | None,
        min_imdb: float | None,
        search: str | None,
    ):
        """Shared WHERE/JOIN logic for both list_movies and count_movies —
        keeps filtering and counting always in sync."""
        stmt = select(Movie)

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

    async def list_movies(
        self,
        limit: int,
        offset: int,
        year: int | None = None,
        min_imdb: float | None = None,
        search: str | None = None,
        sort_by: MovieSortField | None = None,
        sort_desc: bool = False,
    ) -> list[Movie]:
        stmt = self._build_filtered_query(year, min_imdb, search)
        stmt = stmt.options(selectinload(Movie.genres))

        if sort_by is not None:
            column = getattr(Movie, sort_by.value)
            stmt = stmt.order_by(column.desc() if sort_desc else column.asc())

        stmt = stmt.limit(limit).offset(offset)
        result = await self.db.execute(stmt)
        return list(result.unique().scalars().all())

    async def count_movies(
        self,
        year: int | None = None,
        min_imdb: float | None = None,
        search: str | None = None,
    ) -> int:
        base_stmt = self._build_filtered_query(year, min_imdb, search)
        stmt = select(func.count()).select_from(base_stmt.subquery())
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def exists_by_name_year_time(self, name: str, year: int, time: int) -> bool:
        stmt = select(Movie.id).where(
            Movie.name == name, Movie.year == year, Movie.time == time
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is not None


class GenreRepository(NamedEntityRepository[Genre]):
    model = Genre


class StarRepository(NamedEntityRepository[Star]):
    model = Star


class DirectorRepository(NamedEntityRepository[Director]):
    model = Director


class CertificationRepository(NamedEntityRepository[Certification]):
    model = Certification
