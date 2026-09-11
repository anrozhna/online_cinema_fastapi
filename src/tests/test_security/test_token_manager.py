from datetime import timedelta

import pytest

from config.settings import TestingSettings as _TestingSettings
from exceptions.security import InvalidTokenError, TokenExpiredError
from security.token_manager import JWTAuthManager


@pytest.fixture()
def jwt_manager() -> JWTAuthManager:
    settings = _TestingSettings()
    return JWTAuthManager(
        secret_key_access=settings.SECRET_KEY_ACCESS,
        secret_key_refresh=settings.SECRET_KEY_REFRESH,
        algorithm=settings.JWT_SIGNING_ALGORITHM,
    )


class TestCreateAndDecodeAccessToken:
    def test_decoded_payload_contains_original_data(self, jwt_manager):
        token = jwt_manager.create_access_token({"user_id": 1})
        payload = jwt_manager.decode_access_token(token)
        assert payload["user_id"] == 1

    def test_expired_access_token_raises(self, jwt_manager):
        token = jwt_manager.create_access_token(
            {"user_id": 1}, expires_delta=timedelta(seconds=-1)
        )
        with pytest.raises(TokenExpiredError):
            jwt_manager.decode_access_token(token)

    def test_tampered_token_raises_invalid(self, jwt_manager):
        token = jwt_manager.create_access_token({"user_id": 1})
        # Tamper a character in the middle of the signature segment,
        # not the last character — base64's final character can have
        # redundant padding bits that don't always affect decoded bytes.
        middle_index = len(token) // 2
        tampered_char = "a" if token[middle_index] != "a" else "b"
        tampered = token[:middle_index] + tampered_char + token[middle_index + 1 :]

        with pytest.raises(InvalidTokenError):
            jwt_manager.decode_access_token(tampered)


class TestCreateAndDecodeRefreshToken:
    def test_decoded_payload_contains_original_data(self, jwt_manager):
        token = jwt_manager.create_refresh_token({"user_id": 1})
        payload = jwt_manager.decode_refresh_token(token)
        assert payload["user_id"] == 1

    def test_expired_refresh_token_raises(self, jwt_manager):
        token = jwt_manager.create_refresh_token(
            {"user_id": 1}, expires_delta=timedelta(seconds=-1)
        )
        with pytest.raises(TokenExpiredError):
            jwt_manager.decode_refresh_token(token)


class TestAccessAndRefreshSecretsAreIndependent:
    def test_access_token_cannot_be_decoded_as_refresh(self, jwt_manager):
        """Access and refresh use different secret keys — cross-use must fail."""
        access_token = jwt_manager.create_access_token({"user_id": 1})
        with pytest.raises(InvalidTokenError):
            jwt_manager.decode_refresh_token(access_token)

    def test_refresh_token_cannot_be_decoded_as_access(self, jwt_manager):
        refresh_token = jwt_manager.create_refresh_token({"user_id": 1})
        with pytest.raises(InvalidTokenError):
            jwt_manager.decode_access_token(refresh_token)


class TestVerifyOrRaise:
    def test_verify_access_token_or_raise_passes_for_valid_token(self, jwt_manager):
        token = jwt_manager.create_access_token({"user_id": 1})
        jwt_manager.verify_access_token_or_raise(token)  # no exception

    def test_verify_refresh_token_or_raise_raises_for_expired(self, jwt_manager):
        token = jwt_manager.create_refresh_token(
            {"user_id": 1}, expires_delta=timedelta(seconds=-1)
        )
        with pytest.raises(TokenExpiredError):
            jwt_manager.verify_refresh_token_or_raise(token)
