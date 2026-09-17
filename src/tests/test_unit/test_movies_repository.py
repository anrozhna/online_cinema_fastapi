from sqlalchemy.ext.asyncio import AsyncSession

from database.models.movies import Certification, Director, Star
from repositories.movies import MovieRepository, MovieSortField
from tests.conftest import create_movie


class TestMovieRepositoryFiltering:
    async def test_filters_by_year(
        self, db_session: AsyncSession, certification: Certification
    ):
        repo = MovieRepository(db=db_session)
        await create_movie(db_session, certification, name="Old", year=2000)
        await create_movie(db_session, certification, name="New", year=2020)

        results = await repo.list_movies(limit=10, offset=0, year=2020)

        assert len(results) == 1
        assert results[0].name == "New"

    async def test_filters_by_min_imdb(
        self, db_session: AsyncSession, certification: Certification
    ):
        repo = MovieRepository(db=db_session)
        await create_movie(db_session, certification, name="Low", year=2001, imdb=5.0)
        await create_movie(db_session, certification, name="High", year=2002, imdb=9.0)

        results = await repo.list_movies(limit=10, offset=0, min_imdb=8.0)

        assert len(results) == 1
        assert results[0].name == "High"

    async def test_count_matches_filtered_results(
        self, db_session: AsyncSession, certification: Certification
    ):
        repo = MovieRepository(db=db_session)
        await create_movie(db_session, certification, name="A", year=2010)
        await create_movie(db_session, certification, name="B", year=2010)
        await create_movie(db_session, certification, name="C", year=2011)

        total = await repo.count_movies(year=2010)

        assert total == 2


class TestMovieRepositorySorting:
    async def test_sorts_by_price_ascending(
        self, db_session: AsyncSession, certification: Certification
    ):
        repo = MovieRepository(db=db_session)
        await create_movie(
            db_session, certification, name="Expensive", year=2001, price=50.0
        )
        await create_movie(
            db_session, certification, name="Cheap", year=2002, price=5.0
        )

        results = await repo.list_movies(
            limit=10, offset=0, sort_by=MovieSortField.PRICE, sort_desc=False
        )

        assert [m.name for m in results] == ["Cheap", "Expensive"]

    async def test_sorts_by_imdb_descending(
        self, db_session: AsyncSession, certification: Certification
    ):
        repo = MovieRepository(db=db_session)
        await create_movie(db_session, certification, name="Lower", year=2001, imdb=6.0)
        await create_movie(
            db_session, certification, name="Higher", year=2002, imdb=9.5
        )

        results = await repo.list_movies(
            limit=10, offset=0, sort_by=MovieSortField.IMDB, sort_desc=True
        )

        assert [m.name for m in results] == ["Higher", "Lower"]


class TestMovieRepositorySearch:
    async def test_search_matches_movie_name(
        self, db_session: AsyncSession, certification: Certification
    ):
        repo = MovieRepository(db=db_session)
        await create_movie(db_session, certification, name="Inception", year=2010)
        await create_movie(db_session, certification, name="Titanic", year=1997)

        results = await repo.list_movies(limit=10, offset=0, search="incep")

        assert len(results) == 1
        assert results[0].name == "Inception"

    async def test_search_is_case_insensitive(
        self, db_session: AsyncSession, certification: Certification
    ):
        repo = MovieRepository(db=db_session)
        await create_movie(db_session, certification, name="Inception", year=2010)

        results = await repo.list_movies(limit=10, offset=0, search="INCEPTION")

        assert len(results) == 1

    async def test_search_matches_director_name(
        self, db_session: AsyncSession, certification: Certification, director: Director
    ):
        repo = MovieRepository(db=db_session)
        movie = await create_movie(db_session, certification, name="Dunkirk", year=2017)

        await db_session.refresh(movie, attribute_names=["directors"])
        movie.directors.append(director)
        await db_session.commit()

        results = await repo.list_movies(limit=10, offset=0, search="nolan")

        assert len(results) == 1
        assert results[0].name == "Dunkirk"

    async def test_search_matches_star_name(
        self, db_session: AsyncSession, certification: Certification, star: Star
    ):
        repo = MovieRepository(db=db_session)
        movie = await create_movie(db_session, certification, name="Titanic", year=1997)

        await db_session.refresh(movie, attribute_names=["stars"])
        movie.stars.append(star)
        await db_session.commit()

        results = await repo.list_movies(limit=10, offset=0, search="dicaprio")

        assert len(results) == 1

    async def test_search_does_not_duplicate_movie_with_multiple_matching_stars(
        self, db_session: AsyncSession, certification: Certification
    ):
        """A movie matching the search via more than one joined star must
        still appear exactly once — this is what `.distinct()` protects
        against in `_build_filtered_query`."""
        from database.models.movies import Star as StarModel

        star_a = StarModel(name="Actor Alpha")
        star_b = StarModel(name="Actor Beta")
        db_session.add_all([star_a, star_b])
        await db_session.commit()

        repo = MovieRepository(db=db_session)
        movie = await create_movie(
            db_session, certification, name="Ensemble Movie", year=2015
        )

        await db_session.refresh(movie, attribute_names=["stars"])
        movie.stars.extend([star_a, star_b])
        await db_session.commit()

        results = await repo.list_movies(limit=10, offset=0, search="Actor")

        assert len(results) == 1


class TestMovieRepositoryPagination:
    async def test_limit_and_offset_paginate_correctly(
        self, db_session: AsyncSession, certification: Certification
    ):
        repo = MovieRepository(db=db_session)
        for i in range(5):
            await create_movie(
                db_session, certification, name=f"Movie {i}", year=2000 + i
            )

        page_1 = await repo.list_movies(limit=2, offset=0)
        page_2 = await repo.list_movies(limit=2, offset=2)

        assert len(page_1) == 2
        assert len(page_2) == 2
        assert {m.name for m in page_1}.isdisjoint({m.name for m in page_2})


class TestMovieRepositoryUniqueness:
    async def test_exists_by_name_year_time_true_for_duplicate(
        self, db_session: AsyncSession, certification: Certification
    ):
        repo = MovieRepository(db=db_session)
        await create_movie(
            db_session, certification, name="Inception", year=2010, time=148
        )

        exists = await repo.exists_by_name_year_time("Inception", 2010, 148)

        assert exists is True

    async def test_exists_by_name_year_time_false_for_different_year(
        self, db_session: AsyncSession, certification: Certification
    ):
        repo = MovieRepository(db=db_session)
        await create_movie(
            db_session, certification, name="Inception", year=2010, time=148
        )

        exists = await repo.exists_by_name_year_time("Inception", 2011, 148)

        assert exists is False


class TestMovieRepositoryGetByUuid:
    async def test_get_by_uuid_returns_movie_with_relationships_loaded(
        self,
        db_session: AsyncSession,
        certification: Certification,
        genre,
        director,
        star,
    ):
        repo = MovieRepository(db=db_session)
        movie = await create_movie(
            db_session, certification, name="Inception", year=2010
        )

        await db_session.refresh(
            movie, attribute_names=["genres", "directors", "stars"]
        )
        movie.genres.append(genre)
        movie.directors.append(director)
        movie.stars.append(star)
        await db_session.commit()

        fetched = await repo.get_by_uuid(movie.uuid)

        assert fetched is not None
        assert fetched.certification.name == certification.name
        assert [g.name for g in fetched.genres] == [genre.name]

    async def test_get_by_uuid_returns_none_for_missing_uuid(
        self, db_session: AsyncSession
    ):
        import uuid

        repo = MovieRepository(db=db_session)
        result = await repo.get_by_uuid(uuid.uuid4())

        assert result is None
