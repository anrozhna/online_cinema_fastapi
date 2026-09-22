import pytest
from sqlalchemy.exc import IntegrityError

from database.models.base import Base
from database.models.movies import Certification, Director, Genre, Movie, Star


@pytest.fixture()
def genre(sync_session) -> Genre:
    g = Genre(name="Action")
    sync_session.add(g)
    sync_session.commit()
    return g


@pytest.fixture()
def director(sync_session) -> Director:
    d = Director(name="Christopher Nolan")
    sync_session.add(d)
    sync_session.commit()
    return d


@pytest.fixture()
def star(sync_session) -> Star:
    s = Star(name="Leonardo DiCaprio")
    sync_session.add(s)
    sync_session.commit()
    return s


class TestModelsMapping:
    """Ensures all movie models are mapped without configuration errors."""

    def test_metadata_creates_all_tables_without_error(self, sync_engine):
        expected_tables = {
            "genres",
            "stars",
            "directors",
            "certifications",
            "movies",
            "movie_genres",
            "movie_directors",
            "movie_stars",
        }
        assert expected_tables.issubset(set(Base.metadata.tables.keys()))


class TestGenre:
    def test_create_genre(self, sync_session):
        g = Genre(name="Comedy")
        sync_session.add(g)
        sync_session.commit()

        fetched = sync_session.query(Genre).filter_by(name="Comedy").one()
        assert fetched.id is not None
        assert fetched.name == "Comedy"

    def test_genre_name_must_be_unique(self, sync_session):
        sync_session.add(Genre(name="Drama"))
        sync_session.commit()

        sync_session.add(Genre(name="Drama"))
        with pytest.raises(IntegrityError):
            sync_session.commit()


class TestStar:
    def test_create_star(self, sync_session):
        s = Star(name="Meryl Streep")
        sync_session.add(s)
        sync_session.commit()

        fetched = sync_session.query(Star).filter_by(name="Meryl Streep").one()
        assert fetched.id is not None

    def test_star_name_must_be_unique(self, sync_session):
        sync_session.add(Star(name="Tom Hanks"))
        sync_session.commit()

        sync_session.add(Star(name="Tom Hanks"))
        with pytest.raises(IntegrityError):
            sync_session.commit()


class TestDirector:
    def test_create_director(self, sync_session):
        d = Director(name="Quentin Tarantino")
        sync_session.add(d)
        sync_session.commit()

        fetched = sync_session.query(Director).filter_by(name="Quentin Tarantino").one()
        assert fetched.id is not None

    def test_director_name_must_be_unique(self, sync_session):
        sync_session.add(Director(name="Steven Spielberg"))
        sync_session.commit()

        sync_session.add(Director(name="Steven Spielberg"))
        with pytest.raises(IntegrityError):
            sync_session.commit()


class TestCertification:
    def test_create_certification(self, sync_session):
        cert = Certification(name="R")
        sync_session.add(cert)
        sync_session.commit()

        fetched = sync_session.query(Certification).filter_by(name="R").one()
        assert fetched.id is not None

    def test_certification_name_must_be_unique(self, sync_session):
        sync_session.add(Certification(name="PG"))
        sync_session.commit()

        sync_session.add(Certification(name="PG"))
        with pytest.raises(IntegrityError):
            sync_session.commit()


class TestMovie:
    def test_create_movie_with_required_fields(self, sync_session, sync_movie_data):
        movie = Movie(**sync_movie_data)
        sync_session.add(movie)
        sync_session.commit()

        fetched = sync_session.query(Movie).filter_by(name="Inception").one()
        assert fetched.id is not None
        assert fetched.uuid is not None
        assert fetched.certification_id == sync_movie_data["certification_id"]

    def test_movie_uuid_is_auto_generated_and_unique(
        self, sync_session, sync_movie_data
    ):
        movie1 = Movie(**sync_movie_data)
        sync_session.add(movie1)
        sync_session.commit()

        other_data = {
            **sync_movie_data,
            "name": "Interstellar",
            "year": 2014,
            "time": 169,
        }
        movie2 = Movie(**other_data)
        sync_session.add(movie2)
        sync_session.commit()

        assert movie1.uuid != movie2.uuid

    def test_movie_optional_fields_default_to_none(self, sync_session, sync_movie_data):
        movie = Movie(**sync_movie_data)
        sync_session.add(movie)
        sync_session.commit()

        assert movie.meta_score is None
        assert movie.gross is None

    def test_movie_requires_certification(self, sync_session, sync_movie_data):
        data = {**sync_movie_data}
        data.pop("certification_id")
        movie = Movie(**data)
        sync_session.add(movie)

        with pytest.raises(IntegrityError):
            sync_session.commit()

    def test_movie_unique_constraint_on_name_year_time(
        self, sync_session, sync_movie_data
    ):
        sync_session.add(Movie(**sync_movie_data))
        sync_session.commit()

        sync_session.add(Movie(**sync_movie_data))
        with pytest.raises(IntegrityError):
            sync_session.commit()

    def test_same_name_different_year_is_allowed(self, sync_session, sync_movie_data):
        sync_session.add(Movie(**sync_movie_data))
        sync_session.commit()

        remake_data = {**sync_movie_data, "year": 2030}
        sync_session.add(Movie(**remake_data))
        sync_session.commit()  # should not raise

        assert (
            sync_session.query(Movie).filter_by(name=sync_movie_data["name"]).count()
            == 2
        )

    def test_movie_certification_relationship(
        self, sync_session, sync_movie_data, sync_certification
    ):
        movie = Movie(**sync_movie_data)
        sync_session.add(movie)
        sync_session.commit()

        assert movie.certification.name == sync_certification.name
        assert movie in sync_certification.movies


class TestMovieGenreRelationship:
    def test_movie_can_have_multiple_genres(self, sync_session, sync_movie_data):
        genre1 = Genre(name="Sci-Fi")
        genre2 = Genre(name="Thriller")
        sync_session.add_all([genre1, genre2])
        sync_session.commit()

        movie = Movie(**sync_movie_data)
        movie.genres.extend([genre1, genre2])
        sync_session.add(movie)
        sync_session.commit()

        fetched = (
            sync_session.query(Movie).filter_by(name=sync_movie_data["name"]).one()
        )
        assert {g.name for g in fetched.genres} == {"Sci-Fi", "Thriller"}

    def test_genre_can_belong_to_multiple_movies(
        self, sync_session, sync_movie_data, genre
    ):
        movie1 = Movie(**sync_movie_data)
        movie1.genres.append(genre)

        second_data = {
            **sync_movie_data,
            "name": "The Dark Knight",
            "year": 2008,
            "time": 152,
        }
        movie2 = Movie(**second_data)
        movie2.genres.append(genre)

        sync_session.add_all([movie1, movie2])
        sync_session.commit()

        fetched_genre = sync_session.query(Genre).filter_by(name=genre.name).one()
        assert {m.name for m in fetched_genre.movies} == {movie1.name, movie2.name}

    def test_removing_movie_does_not_delete_genre(
        self, sync_session, sync_movie_data, genre
    ):
        movie = Movie(**sync_movie_data)
        movie.genres.append(genre)
        sync_session.add(movie)
        sync_session.commit()

        sync_session.delete(movie)
        sync_session.commit()

        assert (
            sync_session.query(Genre).filter_by(name=genre.name).one_or_none()
            is not None
        )


class TestMovieDirectorRelationship:
    def test_movie_can_have_multiple_directors(self, sync_session, sync_movie_data):
        director1 = Director(name="Directorial Duo A")
        director2 = Director(name="Directorial Duo B")
        sync_session.add_all([director1, director2])
        sync_session.commit()

        movie = Movie(**sync_movie_data)
        movie.directors.extend([director1, director2])
        sync_session.add(movie)
        sync_session.commit()

        fetched = (
            sync_session.query(Movie).filter_by(name=sync_movie_data["name"]).one()
        )
        assert len(fetched.directors) == 2

    def test_director_can_direct_multiple_movies(
        self, sync_session, sync_movie_data, director
    ):
        movie1 = Movie(**sync_movie_data)
        movie1.directors.append(director)

        second_data = {**sync_movie_data, "name": "Dunkirk", "year": 2017, "time": 106}
        movie2 = Movie(**second_data)
        movie2.directors.append(director)

        sync_session.add_all([movie1, movie2])
        sync_session.commit()

        fetched_director = (
            sync_session.query(Director).filter_by(name=director.name).one()
        )
        assert len(fetched_director.movies) == 2


class TestMovieStarRelationship:
    def test_movie_can_have_multiple_stars(self, sync_session, sync_movie_data):
        star1 = Star(name="Joseph Gordon-Levitt")
        star2 = Star(name="Elliot Page")
        sync_session.add_all([star1, star2])
        sync_session.commit()

        movie = Movie(**sync_movie_data)
        movie.stars.extend([star1, star2])
        sync_session.add(movie)
        sync_session.commit()

        fetched = (
            sync_session.query(Movie).filter_by(name=sync_movie_data["name"]).one()
        )
        assert len(fetched.stars) == 2

    def test_star_can_appear_in_multiple_movies(
        self, sync_session, sync_movie_data, star
    ):
        movie1 = Movie(**sync_movie_data)
        movie1.stars.append(star)

        second_data = {**sync_movie_data, "name": "Titanic", "year": 1997, "time": 195}
        movie2 = Movie(**second_data)
        movie2.stars.append(star)

        sync_session.add_all([movie1, movie2])
        sync_session.commit()

        fetched_star = sync_session.query(Star).filter_by(name=star.name).one()
        assert len(fetched_star.movies) == 2
