from sqlalchemy import select
from sqlalchemy.orm import joinedload, selectinload

from database.models.movies import Certification, Director, Genre, Movie, Star
from repositories.base import NamedEntityRepository
from repositories.base_movie import BaseMovieRepository, MovieSortField


class MovieRepository(BaseMovieRepository):
    model = Movie

    async def _get_with_relations(self, **filters) -> Movie | None:
        """Shared eager-loading query for fetching a single Movie with all
        its relationships loaded — used by both UUID lookup (public API)
        and ID lookup (internal, e.g. before an update)."""
        stmt = select(Movie).options(
            joinedload(Movie.certification),
            selectinload(Movie.genres),
            selectinload(Movie.directors),
            selectinload(Movie.stars),
        )
        for field, value in filters.items():
            stmt = stmt.where(getattr(Movie, field) == value)

        result = await self.db.execute(stmt)
        return result.unique().scalar_one_or_none()

    async def get_by_uuid(self, movie_uuid) -> Movie | None:
        return await self._get_with_relations(uuid=movie_uuid)

    async def get_by_id_with_relations(self, movie_id: int) -> Movie | None:
        return await self._get_with_relations(id=movie_id)

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
        stmt = self._apply_filters(
            stmt=select(Movie), year=year, min_imdb=min_imdb, search=search
        )
        return await self._paginate_and_sort(
            stmt=stmt, limit=limit, offset=offset, sort_by=sort_by, sort_desc=sort_desc
        )

    async def count_movies(
        self,
        year: int | None = None,
        min_imdb: float | None = None,
        search: str | None = None,
    ) -> int:
        stmt = self._apply_filters(
            stmt=select(Movie), year=year, min_imdb=min_imdb, search=search
        )
        return await self._count(stmt)

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
