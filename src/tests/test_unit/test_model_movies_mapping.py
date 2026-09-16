from typing import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from database.models.base import Base
from database.models.movies import Certification, Director, Genre, Movie, Star


@pytest.fixture()
def engine():
    """In-memory SQLite engine, recreated for each test for full isolation."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture()
def session(engine) -> Generator[Session]:
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    yield session
    session.close()


@pytest.fixture()
def certification(session) -> Certification:
    cert = Certification(name="PG-13")
    session.add(cert)
    session.commit()
    return cert


@pytest.fixture()
def genre(session) -> Genre:
    g = Genre(name="Action")
    session.add(g)
    session.commit()
    return g


@pytest.fixture()
def director(session) -> Director:
    d = Director(name="Christopher Nolan")
    session.add(d)
    session.commit()
    return d


@pytest.fixture()
def star(session) -> Star:
    s = Star(name="Leonardo DiCaprio")
    session.add(s)
    session.commit()
    return s


@pytest.fixture()
def movie_data(certification) -> dict:
    """Base valid attributes for a Movie, without relationships."""
    return {
        "name": "Inception",
        "year": 2010,
        "time": 148,
        "imdb": 8.8,
        "votes": 2000000,
        "description": "A thief who steals corporate secrets through "
        "dream-sharing technology.",
        "price": 9.99,
        "certification_id": certification.id,
    }


class TestModelsMapping:
    """Ensures all movie models are mapped without configuration errors."""

    def test_metadata_creates_all_tables_without_error(self, engine):
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
    def test_create_genre(self, session):
        g = Genre(name="Comedy")
        session.add(g)
        session.commit()

        fetched = session.query(Genre).filter_by(name="Comedy").one()
        assert fetched.id is not None
        assert fetched.name == "Comedy"

    def test_genre_name_must_be_unique(self, session):
        session.add(Genre(name="Drama"))
        session.commit()

        session.add(Genre(name="Drama"))
        with pytest.raises(IntegrityError):
            session.commit()


class TestStar:
    def test_create_star(self, session):
        s = Star(name="Meryl Streep")
        session.add(s)
        session.commit()

        fetched = session.query(Star).filter_by(name="Meryl Streep").one()
        assert fetched.id is not None

    def test_star_name_must_be_unique(self, session):
        session.add(Star(name="Tom Hanks"))
        session.commit()

        session.add(Star(name="Tom Hanks"))
        with pytest.raises(IntegrityError):
            session.commit()


class TestDirector:
    def test_create_director(self, session):
        d = Director(name="Quentin Tarantino")
        session.add(d)
        session.commit()

        fetched = session.query(Director).filter_by(name="Quentin Tarantino").one()
        assert fetched.id is not None

    def test_director_name_must_be_unique(self, session):
        session.add(Director(name="Steven Spielberg"))
        session.commit()

        session.add(Director(name="Steven Spielberg"))
        with pytest.raises(IntegrityError):
            session.commit()


class TestCertification:
    def test_create_certification(self, session):
        cert = Certification(name="R")
        session.add(cert)
        session.commit()

        fetched = session.query(Certification).filter_by(name="R").one()
        assert fetched.id is not None

    def test_certification_name_must_be_unique(self, session):
        session.add(Certification(name="PG"))
        session.commit()

        session.add(Certification(name="PG"))
        with pytest.raises(IntegrityError):
            session.commit()


class TestMovie:
    def test_create_movie_with_required_fields(self, session, movie_data):
        movie = Movie(**movie_data)
        session.add(movie)
        session.commit()

        fetched = session.query(Movie).filter_by(name="Inception").one()
        assert fetched.id is not None
        assert fetched.uuid is not None
        assert fetched.certification_id == movie_data["certification_id"]

    def test_movie_uuid_is_auto_generated_and_unique(self, session, movie_data):
        movie1 = Movie(**movie_data)
        session.add(movie1)
        session.commit()

        other_data = {**movie_data, "name": "Interstellar", "year": 2014, "time": 169}
        movie2 = Movie(**other_data)
        session.add(movie2)
        session.commit()

        assert movie1.uuid != movie2.uuid

    def test_movie_optional_fields_default_to_none(self, session, movie_data):
        movie = Movie(**movie_data)
        session.add(movie)
        session.commit()

        assert movie.meta_score is None
        assert movie.gross is None

    def test_movie_requires_certification(self, session, movie_data):
        data = {**movie_data}
        data.pop("certification_id")
        movie = Movie(**data)
        session.add(movie)

        with pytest.raises(IntegrityError):
            session.commit()

    def test_movie_unique_constraint_on_name_year_time(self, session, movie_data):
        session.add(Movie(**movie_data))
        session.commit()

        session.add(Movie(**movie_data))
        with pytest.raises(IntegrityError):
            session.commit()

    def test_same_name_different_year_is_allowed(self, session, movie_data):
        session.add(Movie(**movie_data))
        session.commit()

        remake_data = {**movie_data, "year": 2030}
        session.add(Movie(**remake_data))
        session.commit()  # should not raise

        assert session.query(Movie).filter_by(name=movie_data["name"]).count() == 2

    def test_movie_certification_relationship(self, session, movie_data, certification):
        movie = Movie(**movie_data)
        session.add(movie)
        session.commit()

        assert movie.certification.name == certification.name
        assert movie in certification.movies


class TestMovieGenreRelationship:
    def test_movie_can_have_multiple_genres(self, session, movie_data):
        genre1 = Genre(name="Sci-Fi")
        genre2 = Genre(name="Thriller")
        session.add_all([genre1, genre2])
        session.commit()

        movie = Movie(**movie_data)
        movie.genres.extend([genre1, genre2])
        session.add(movie)
        session.commit()

        fetched = session.query(Movie).filter_by(name=movie_data["name"]).one()
        assert {g.name for g in fetched.genres} == {"Sci-Fi", "Thriller"}

    def test_genre_can_belong_to_multiple_movies(self, session, movie_data, genre):
        movie1 = Movie(**movie_data)
        movie1.genres.append(genre)

        second_data = {
            **movie_data,
            "name": "The Dark Knight",
            "year": 2008,
            "time": 152,
        }
        movie2 = Movie(**second_data)
        movie2.genres.append(genre)

        session.add_all([movie1, movie2])
        session.commit()

        fetched_genre = session.query(Genre).filter_by(name=genre.name).one()
        assert {m.name for m in fetched_genre.movies} == {movie1.name, movie2.name}

    def test_removing_movie_does_not_delete_genre(self, session, movie_data, genre):
        movie = Movie(**movie_data)
        movie.genres.append(genre)
        session.add(movie)
        session.commit()

        session.delete(movie)
        session.commit()

        assert session.query(Genre).filter_by(name=genre.name).one_or_none() is not None


class TestMovieDirectorRelationship:
    def test_movie_can_have_multiple_directors(self, session, movie_data):
        director1 = Director(name="Directorial Duo A")
        director2 = Director(name="Directorial Duo B")
        session.add_all([director1, director2])
        session.commit()

        movie = Movie(**movie_data)
        movie.directors.extend([director1, director2])
        session.add(movie)
        session.commit()

        fetched = session.query(Movie).filter_by(name=movie_data["name"]).one()
        assert len(fetched.directors) == 2

    def test_director_can_direct_multiple_movies(self, session, movie_data, director):
        movie1 = Movie(**movie_data)
        movie1.directors.append(director)

        second_data = {**movie_data, "name": "Dunkirk", "year": 2017, "time": 106}
        movie2 = Movie(**second_data)
        movie2.directors.append(director)

        session.add_all([movie1, movie2])
        session.commit()

        fetched_director = session.query(Director).filter_by(name=director.name).one()
        assert len(fetched_director.movies) == 2


class TestMovieStarRelationship:
    def test_movie_can_have_multiple_stars(self, session, movie_data):
        star1 = Star(name="Joseph Gordon-Levitt")
        star2 = Star(name="Elliot Page")
        session.add_all([star1, star2])
        session.commit()

        movie = Movie(**movie_data)
        movie.stars.extend([star1, star2])
        session.add(movie)
        session.commit()

        fetched = session.query(Movie).filter_by(name=movie_data["name"]).one()
        assert len(fetched.stars) == 2

    def test_star_can_appear_in_multiple_movies(self, session, movie_data, star):
        movie1 = Movie(**movie_data)
        movie1.stars.append(star)

        second_data = {**movie_data, "name": "Titanic", "year": 1997, "time": 195}
        movie2 = Movie(**second_data)
        movie2.stars.append(star)

        session.add_all([movie1, movie2])
        session.commit()

        fetched_star = session.query(Star).filter_by(name=star.name).one()
        assert len(fetched_star.movies) == 2
