import pytest
from sqlalchemy.exc import IntegrityError

from database.models.cart import Cart, CartItem
from database.models.movies import Movie


class TestCart:
    def test_create_cart(self, sync_session, sync_user):
        cart = Cart(user_id=sync_user.id)
        sync_session.add(cart)
        sync_session.commit()

        fetched = sync_session.query(Cart).filter_by(user_id=sync_user.id).one()
        assert fetched.id is not None
        assert fetched.created_at is not None

    def test_user_can_have_only_one_cart(self, sync_session, sync_user):
        sync_session.add(Cart(user_id=sync_user.id))
        sync_session.commit()

        sync_session.add(Cart(user_id=sync_user.id))
        with pytest.raises(IntegrityError):
            sync_session.commit()

    def test_deleting_cart_cascades_to_items(self, sync_session, sync_user, sync_movie):
        cart = Cart(user_id=sync_user.id)
        sync_session.add(cart)
        sync_session.commit()

        item = CartItem(cart_id=cart.id, movie_id=sync_movie.id)
        sync_session.add(item)
        sync_session.commit()
        item_id = item.id

        sync_session.delete(cart)
        sync_session.commit()

        assert sync_session.query(CartItem).filter_by(id=item_id).one_or_none() is None


class TestCartItem:
    def test_create_cart_item(self, sync_session, sync_user, sync_movie):
        cart = Cart(user_id=sync_user.id)
        sync_session.add(cart)
        sync_session.commit()

        item = CartItem(cart_id=cart.id, movie_id=sync_movie.id)
        sync_session.add(item)
        sync_session.commit()

        fetched = sync_session.query(CartItem).filter_by(cart_id=cart.id).one()
        assert fetched.movie_id == sync_movie.id
        assert fetched.added_at is not None

    def test_same_movie_cannot_be_added_twice_to_same_cart(
        self, sync_session, sync_user, sync_movie
    ):
        cart = Cart(user_id=sync_user.id)
        sync_session.add(cart)
        sync_session.commit()

        sync_session.add(CartItem(cart_id=cart.id, movie_id=sync_movie.id))
        sync_session.commit()

        sync_session.add(CartItem(cart_id=cart.id, movie_id=sync_movie.id))
        with pytest.raises(IntegrityError):
            sync_session.commit()

    def test_cart_can_have_multiple_different_movies(
        self, sync_session, sync_user, sync_certification, sync_movie
    ):
        cart = Cart(user_id=sync_user.id)
        sync_session.add(cart)
        sync_session.commit()

        second_sync_movie = Movie(
            name="Interstellar",
            year=2014,
            time=169,
            imdb=8.6,
            votes=1800000,
            description="A team travels through a wormhole.",
            price=12.99,
            certification_id=sync_certification.id,
        )
        sync_session.add(second_sync_movie)
        sync_session.commit()

        sync_session.add(CartItem(cart_id=cart.id, movie_id=sync_movie.id))
        sync_session.add(CartItem(cart_id=cart.id, movie_id=second_sync_movie.id))
        sync_session.commit()

        assert sync_session.query(CartItem).filter_by(cart_id=cart.id).count() == 2

    def test_cart_relationship_returns_items(self, sync_session, sync_user, sync_movie):
        cart = Cart(user_id=sync_user.id)
        sync_session.add(cart)
        sync_session.commit()

        item = CartItem(cart_id=cart.id, movie_id=sync_movie.id)
        sync_session.add(item)
        sync_session.commit()

        sync_session.refresh(cart)
        assert len(cart.items) == 1
        assert cart.items[0].movie_id == sync_movie.id
