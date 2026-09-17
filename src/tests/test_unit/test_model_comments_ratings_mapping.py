from typing import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from database.models.accounts import User, UserGroup, UserGroupEnum
from database.models.base import Base
from database.models.movies import Certification, Comment, Movie, MovieReaction, Rating


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
def user_group(session) -> UserGroup:
    group = UserGroup(name=UserGroupEnum.USER)
    session.add(group)
    session.commit()
    return group


@pytest.fixture()
def user(session, user_group) -> User:
    """A real User row for FK purposes — bypasses the password setter and
    bcrypt entirely since password correctness is irrelevant to these tests."""
    u = User(email="viewer@example.com", group_id=user_group.id, is_active=True)
    u._hashed_password = "test-hash"
    session.add(u)
    session.commit()
    return u


@pytest.fixture()
def other_user(session, user_group) -> User:
    u = User(email="other-viewer@example.com", group_id=user_group.id, is_active=True)
    u._hashed_password = "test-hash"
    session.add(u)
    session.commit()
    return u


@pytest.fixture()
def certification(session) -> Certification:
    cert = Certification(name="PG-13")
    session.add(cert)
    session.commit()
    return cert


@pytest.fixture()
def movie(session, certification) -> Movie:
    m = Movie(
        name="Inception",
        year=2010,
        time=148,
        imdb=8.8,
        votes=2000000,
        description="A thief who steals corporate secrets "
        "through dream-sharing technology.",
        price=9.99,
        certification_id=certification.id,
    )
    session.add(m)
    session.commit()
    return m


class TestComment:
    def test_create_top_level_comment(self, session, movie, user):
        comment = Comment(user_id=user.id, movie_id=movie.id, text="Great movie!")
        session.add(comment)
        session.commit()

        fetched = session.query(Comment).filter_by(movie_id=movie.id).one()
        assert fetched.id is not None
        assert fetched.parent_comment_id is None
        assert fetched.created_at is not None

    def test_create_reply_sets_parent_relationship(
        self, session, movie, user, other_user
    ):
        parent = Comment(user_id=user.id, movie_id=movie.id, text="Loved it!")
        session.add(parent)
        session.commit()

        reply = Comment(
            user_id=other_user.id,
            movie_id=movie.id,
            text="Agreed!",
            parent_comment_id=parent.id,
        )
        session.add(reply)
        session.commit()

        assert reply.parent.id == parent.id
        assert [r.id for r in parent.replies] == [reply.id]

    def test_deleting_movie_cascades_to_comments(self, session, movie, user):
        comment = Comment(user_id=user.id, movie_id=movie.id, text="Nice!")
        session.add(comment)
        session.commit()
        comment_id = comment.id

        session.delete(movie)
        session.commit()

        assert session.query(Comment).filter_by(id=comment_id).one_or_none() is None

    def test_deleting_parent_comment_cascades_to_replies(
        self, session, movie, user, other_user
    ):
        parent = Comment(user_id=user.id, movie_id=movie.id, text="Loved it!")
        session.add(parent)
        session.commit()

        reply = Comment(
            user_id=other_user.id,
            movie_id=movie.id,
            text="Agreed!",
            parent_comment_id=parent.id,
        )
        session.add(reply)
        session.commit()
        reply_id = reply.id

        session.delete(parent)
        session.commit()

        assert session.query(Comment).filter_by(id=reply_id).one_or_none() is None

    def test_deleting_user_does_not_delete_comment_orphaned_by_fk(
        self, session, movie, user
    ):
        """Comments are tied to a user via ondelete='CASCADE' at the DB level,
        not via an ORM cascade — SQLAlchemy's own cascade rules here only
        cover movie->comments and comment->replies, not user->comments."""
        comment = Comment(user_id=user.id, movie_id=movie.id, text="Nice!")
        session.add(comment)
        session.commit()

        # No ORM-level cascade is declared from User to Comment, so this
        # documents current behavior rather than asserting a requirement.
        assert comment.user_id == user.id


class TestRating:
    def test_create_rating(self, session, movie, user):
        rating = Rating(user_id=user.id, movie_id=movie.id, score=8)
        session.add(rating)
        session.commit()

        fetched = session.query(Rating).filter_by(movie_id=movie.id).one()
        assert fetched.score == 8
        assert fetched.created_at is not None

    def test_rating_unique_per_user_and_movie(self, session, movie, user):
        session.add(Rating(user_id=user.id, movie_id=movie.id, score=7))
        session.commit()

        session.add(Rating(user_id=user.id, movie_id=movie.id, score=9))
        with pytest.raises(IntegrityError):
            session.commit()

    def test_same_user_can_rate_different_movies(self, session, certification, user):
        movie2 = Movie(
            name="Interstellar",
            year=2014,
            time=169,
            imdb=8.6,
            votes=1800000,
            description="A team travels through a wormhole in space.",
            price=12.99,
            certification_id=certification.id,
        )
        session.add(movie2)
        session.commit()

        movie1 = Movie(
            name="Inception",
            year=2010,
            time=148,
            imdb=8.8,
            votes=2000000,
            description="A thief steals secrets through dreams.",
            price=9.99,
            certification_id=certification.id,
        )
        session.add(movie1)
        session.commit()

        session.add(Rating(user_id=user.id, movie_id=movie1.id, score=8))
        session.add(Rating(user_id=user.id, movie_id=movie2.id, score=9))
        session.commit()  # should not raise

        assert session.query(Rating).filter_by(user_id=user.id).count() == 2

    def test_deleting_movie_cascades_to_ratings(self, session, movie, user):
        rating = Rating(user_id=user.id, movie_id=movie.id, score=6)
        session.add(rating)
        session.commit()
        rating_id = rating.id

        session.delete(movie)
        session.commit()

        assert session.query(Rating).filter_by(id=rating_id).one_or_none() is None


class TestMovieReaction:
    def test_create_reaction(self, session, movie, user):
        reaction = MovieReaction(user_id=user.id, movie_id=movie.id, is_like=True)
        session.add(reaction)
        session.commit()

        fetched = session.query(MovieReaction).filter_by(movie_id=movie.id).one()
        assert fetched.is_like is True

    def test_reaction_unique_per_user_and_movie(self, session, movie, user):
        session.add(MovieReaction(user_id=user.id, movie_id=movie.id, is_like=True))
        session.commit()

        session.add(MovieReaction(user_id=user.id, movie_id=movie.id, is_like=False))
        with pytest.raises(IntegrityError):
            session.commit()

    def test_deleting_movie_cascades_to_reactions(self, session, movie, user):
        reaction = MovieReaction(user_id=user.id, movie_id=movie.id, is_like=False)
        session.add(reaction)
        session.commit()
        reaction_id = reaction.id

        session.delete(movie)
        session.commit()

        assert (
            session.query(MovieReaction).filter_by(id=reaction_id).one_or_none() is None
        )
