from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from database.models.cart import Cart, CartItem
from database.models.movies import Movie
from services.cart import CartService


@pytest.fixture()
def mock_cart_repo():
    return AsyncMock()


@pytest.fixture()
def mock_cart_item_repo():
    return AsyncMock()


@pytest.fixture()
def mock_movie_repo():
    return AsyncMock()


@pytest.fixture()
def cart_service(mock_cart_repo, mock_cart_item_repo, mock_movie_repo):
    return CartService(
        cart_repo=mock_cart_repo,
        cart_item_repo=mock_cart_item_repo,
        movie_repo=mock_movie_repo,
    )


class TestAddToCartValidation:
    async def test_raises_404_when_movie_does_not_exist(
        self, cart_service, mock_movie_repo
    ):
        mock_movie_repo.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await cart_service.add_to_cart(user_id=1, movie_id=999)

        assert exc_info.value.status_code == 404

    async def test_raises_409_when_movie_already_in_cart(
        self, cart_service, mock_movie_repo, mock_cart_repo, mock_cart_item_repo
    ):
        mock_movie_repo.get_by_id.return_value = Movie(id=1, name="Inception")
        mock_cart_repo.get_or_create_for_user.return_value = Cart(id=1, user_id=1)
        mock_cart_item_repo.get_by_cart_and_movie.return_value = CartItem(
            id=1, cart_id=1, movie_id=1
        )

        with pytest.raises(HTTPException) as exc_info:
            await cart_service.add_to_cart(user_id=1, movie_id=1)

        assert exc_info.value.status_code == 409
        assert "already in your cart" in exc_info.value.detail

    async def test_allows_adding_movie_not_yet_in_cart(
        self, cart_service, mock_movie_repo, mock_cart_repo, mock_cart_item_repo
    ):
        movie = Movie(id=1, name="Inception", price=9.99, year=2010)
        movie.genres = []
        cart = Cart(id=1, user_id=1)
        cart.items = []

        mock_movie_repo.get_by_id.return_value = movie
        mock_cart_repo.get_or_create_for_user.return_value = cart
        mock_cart_item_repo.get_by_cart_and_movie.return_value = None
        mock_cart_repo.get_by_user_id.return_value = cart

        result = await cart_service.add_to_cart(user_id=1, movie_id=1)

        mock_cart_item_repo.add.assert_called_once()
        assert result.items == []


class TestRemoveFromCartValidation:
    async def test_raises_404_when_movie_not_in_cart(
        self, cart_service, mock_cart_repo, mock_cart_item_repo
    ):
        cart = Cart(id=1, user_id=1)
        mock_cart_repo.get_or_create_for_user.return_value = cart
        mock_cart_item_repo.get_by_cart_and_movie.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await cart_service.remove_from_cart(user_id=1, movie_id=999)

        assert exc_info.value.status_code == 404
        assert "not in your cart" in exc_info.value.detail


class TestCheckoutValidation:
    async def test_raises_400_when_cart_is_empty(self, cart_service, mock_cart_repo):
        cart = Cart(id=1, user_id=1)
        cart.items = []
        mock_cart_repo.get_or_create_for_user.return_value = cart

        with pytest.raises(HTTPException) as exc_info:
            await cart_service.checkout(user_id=1)

        assert exc_info.value.status_code == 400
        assert "empty" in exc_info.value.detail.lower()

    async def test_clears_cart_items_on_successful_checkout(
        self, cart_service, mock_cart_repo, mock_cart_item_repo
    ):
        item = CartItem(id=1, cart_id=1, movie_id=1)
        cart = Cart(id=1, user_id=1)
        cart.items = [item]
        mock_cart_repo.get_or_create_for_user.return_value = cart

        await cart_service.checkout(user_id=1)

        mock_cart_item_repo.delete.assert_called_once_with(item)
