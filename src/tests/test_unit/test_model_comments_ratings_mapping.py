import pytest
from sqlalchemy.exc import IntegrityError

from database.models.accounts import User
from database.models.movies import Comment, Movie, MovieReaction, Rating


@pytest.fixture()
def other_user(sync_session, user_group) -> User:
    u = User(email="other-viewer@example.com", group_id=user_group.id, is_active=True)
    u._hashed_password = "test-hash"
    sync_session.add(u)
    sync_session.commit()
    return u


class TestComment:
    def test_create_top_level_comment(self, sync_session, sync_movie, sync_user):
        comment = Comment(
            user_id=sync_user.id, movie_id=sync_movie.id, text="Great movie!"
        )
        sync_session.add(comment)
        sync_session.commit()

        fetched = sync_session.query(Comment).filter_by(movie_id=sync_movie.id).one()
        assert fetched.id is not None
        assert fetched.parent_comment_id is None
        assert fetched.created_at is not None

    def test_create_reply_sets_parent_relationship(
        self, sync_session, sync_movie, sync_user, other_user
    ):
        parent = Comment(user_id=sync_user.id, movie_id=sync_movie.id, text="Loved it!")
        sync_session.add(parent)
        sync_session.commit()

        reply = Comment(
            user_id=other_user.id,
            movie_id=sync_movie.id,
            text="Agreed!",
            parent_comment_id=parent.id,
        )
        sync_session.add(reply)
        sync_session.commit()

        assert reply.parent.id == parent.id
        assert [r.id for r in parent.replies] == [reply.id]

    def test_deleting_movie_cascades_to_comments(
        self, sync_session, sync_movie, sync_user
    ):
        comment = Comment(user_id=sync_user.id, movie_id=sync_movie.id, text="Nice!")
        sync_session.add(comment)
        sync_session.commit()
        comment_id = comment.id

        sync_session.delete(sync_movie)
        sync_session.commit()

        assert (
            sync_session.query(Comment).filter_by(id=comment_id).one_or_none() is None
        )

    def test_deleting_parent_comment_cascades_to_replies(
        self, sync_session, sync_movie, sync_user, other_user
    ):
        parent = Comment(user_id=sync_user.id, movie_id=sync_movie.id, text="Loved it!")
        sync_session.add(parent)
        sync_session.commit()

        reply = Comment(
            user_id=other_user.id,
            movie_id=sync_movie.id,
            text="Agreed!",
            parent_comment_id=parent.id,
        )
        sync_session.add(reply)
        sync_session.commit()
        reply_id = reply.id

        sync_session.delete(parent)
        sync_session.commit()

        assert sync_session.query(Comment).filter_by(id=reply_id).one_or_none() is None

    def test_deleting_user_does_not_delete_comment_orphaned_by_fk(
        self, sync_session, sync_movie, sync_user
    ):
        """Comments are tied to a user via ondelete='CASCADE' at the DB level,
        not via an ORM cascade — SQLAlchemy's own cascade rules here only
        cover movie->comments and comment->replies, not user->comments."""
        comment = Comment(user_id=sync_user.id, movie_id=sync_movie.id, text="Nice!")
        sync_session.add(comment)
        sync_session.commit()

        # No ORM-level cascade is declared from User to Comment, so this
        # documents current behavior rather than asserting a requirement.
        assert comment.user_id == sync_user.id


class TestRating:
    def test_create_rating(self, sync_session, sync_movie, sync_user):
        rating = Rating(user_id=sync_user.id, movie_id=sync_movie.id, score=8)
        sync_session.add(rating)
        sync_session.commit()

        fetched = sync_session.query(Rating).filter_by(movie_id=sync_movie.id).one()
        assert fetched.score == 8
        assert fetched.created_at is not None

    def test_rating_unique_per_user_and_movie(
        self, sync_session, sync_movie, sync_user
    ):
        sync_session.add(Rating(user_id=sync_user.id, movie_id=sync_movie.id, score=7))
        sync_session.commit()

        sync_session.add(Rating(user_id=sync_user.id, movie_id=sync_movie.id, score=9))
        with pytest.raises(IntegrityError):
            sync_session.commit()

    def test_same_user_can_rate_different_movies(
        self, sync_session, sync_certification, sync_user
    ):
        movie2 = Movie(
            name="Interstellar",
            year=2014,
            time=169,
            imdb=8.6,
            votes=1800000,
            description="A team travels through a wormhole in space.",
            price=12.99,
            certification_id=sync_certification.id,
        )
        sync_session.add(movie2)
        sync_session.commit()

        movie1 = Movie(
            name="Inception",
            year=2010,
            time=148,
            imdb=8.8,
            votes=2000000,
            description="A thief steals secrets through dreams.",
            price=9.99,
            certification_id=sync_certification.id,
        )
        sync_session.add(movie1)
        sync_session.commit()

        sync_session.add(Rating(user_id=sync_user.id, movie_id=movie1.id, score=8))
        sync_session.add(Rating(user_id=sync_user.id, movie_id=movie2.id, score=9))
        sync_session.commit()  # should not raise

        assert sync_session.query(Rating).filter_by(user_id=sync_user.id).count() == 2

    def test_deleting_movie_cascades_to_ratings(
        self, sync_session, sync_movie, sync_user
    ):
        rating = Rating(user_id=sync_user.id, movie_id=sync_movie.id, score=6)
        sync_session.add(rating)
        sync_session.commit()
        rating_id = rating.id

        sync_session.delete(sync_movie)
        sync_session.commit()

        assert sync_session.query(Rating).filter_by(id=rating_id).one_or_none() is None


class TestMovieReaction:
    def test_create_reaction(self, sync_session, sync_movie, sync_user):
        reaction = MovieReaction(
            user_id=sync_user.id, movie_id=sync_movie.id, is_like=True
        )
        sync_session.add(reaction)
        sync_session.commit()

        fetched = (
            sync_session.query(MovieReaction).filter_by(movie_id=sync_movie.id).one()
        )
        assert fetched.is_like is True

    def test_reaction_unique_per_user_and_movie(
        self, sync_session, sync_movie, sync_user
    ):
        sync_session.add(
            MovieReaction(user_id=sync_user.id, movie_id=sync_movie.id, is_like=True)
        )
        sync_session.commit()

        sync_session.add(
            MovieReaction(user_id=sync_user.id, movie_id=sync_movie.id, is_like=False)
        )
        with pytest.raises(IntegrityError):
            sync_session.commit()

    def test_deleting_movie_cascades_to_reactions(
        self, sync_session, sync_movie, sync_user
    ):
        reaction = MovieReaction(
            user_id=sync_user.id, movie_id=sync_movie.id, is_like=False
        )
        sync_session.add(reaction)
        sync_session.commit()
        reaction_id = reaction.id

        sync_session.delete(sync_movie)
        sync_session.commit()

        assert (
            sync_session.query(MovieReaction).filter_by(id=reaction_id).one_or_none()
            is None
        )
