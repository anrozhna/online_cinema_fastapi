from typing import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from database.models.accounts import User, UserGroup, UserGroupEnum
from database.models.base import Base
from database.models.cart import Cart, CartItem
from database.models.movies import Certification, Movie


@pytest.fixture()
def engine():
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
    u = User(email="cart-owner@example.com", group_id=user_group.id, is_active=True)
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


class TestCart:
    def test_create_cart(self, session, user):
        cart = Cart(user_id=user.id)
        session.add(cart)
        session.commit()

        fetched = session.query(Cart).filter_by(user_id=user.id).one()
        assert fetched.id is not None
        assert fetched.created_at is not None

    def test_user_can_have_only_one_cart(self, session, user):
        session.add(Cart(user_id=user.id))
        session.commit()

        session.add(Cart(user_id=user.id))
        with pytest.raises(IntegrityError):
            session.commit()

    def test_deleting_cart_cascades_to_items(self, session, user, movie):
        cart = Cart(user_id=user.id)
        session.add(cart)
        session.commit()

        item = CartItem(cart_id=cart.id, movie_id=movie.id)
        session.add(item)
        session.commit()
        item_id = item.id

        session.delete(cart)
        session.commit()

        assert session.query(CartItem).filter_by(id=item_id).one_or_none() is None


class TestCartItem:
    def test_create_cart_item(self, session, user, movie):
        cart = Cart(user_id=user.id)
        session.add(cart)
        session.commit()

        item = CartItem(cart_id=cart.id, movie_id=movie.id)
        session.add(item)
        session.commit()

        fetched = session.query(CartItem).filter_by(cart_id=cart.id).one()
        assert fetched.movie_id == movie.id
        assert fetched.added_at is not None

    def test_same_movie_cannot_be_added_twice_to_same_cart(self, session, user, movie):
        cart = Cart(user_id=user.id)
        session.add(cart)
        session.commit()

        session.add(CartItem(cart_id=cart.id, movie_id=movie.id))
        session.commit()

        session.add(CartItem(cart_id=cart.id, movie_id=movie.id))
        with pytest.raises(IntegrityError):
            session.commit()

    def test_cart_can_have_multiple_different_movies(
        self, session, user, certification, movie
    ):
        cart = Cart(user_id=user.id)
        session.add(cart)
        session.commit()

        second_movie = Movie(
            name="Interstellar",
            year=2014,
            time=169,
            imdb=8.6,
            votes=1800000,
            description="A team travels through a wormhole.",
            price=12.99,
            certification_id=certification.id,
        )
        session.add(second_movie)
        session.commit()

        session.add(CartItem(cart_id=cart.id, movie_id=movie.id))
        session.add(CartItem(cart_id=cart.id, movie_id=second_movie.id))
        session.commit()

        assert session.query(CartItem).filter_by(cart_id=cart.id).count() == 2

    def test_cart_relationship_returns_items(self, session, user, movie):
        cart = Cart(user_id=user.id)
        session.add(cart)
        session.commit()

        item = CartItem(cart_id=cart.id, movie_id=movie.id)
        session.add(item)
        session.commit()

        session.refresh(cart)
        assert len(cart.items) == 1
        assert cart.items[0].movie_id == movie.id
