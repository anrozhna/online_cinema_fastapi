import time

import jwt
import pytest

from exceptions.security import BaseSecurityError
from security.token_manager import JWTAuthManager


@pytest.fixture()
def jwt_manager():
    return JWTAuthManager(
        secret_key_access="test-access-secret",
        secret_key_refresh="test-refresh-secret",
        algorithm="HS256",
    )


class TestJWTEdgeCases:
    def test_decode_valid_access_token_succeeds(self, jwt_manager):
        token = jwt_manager.create_access_token({"user_id": 1})
        payload = jwt_manager.decode_access_token(token)

        assert payload["user_id"] == 1

    def test_decode_expired_token_raises(self, jwt_manager):
        expired_payload = {"user_id": 1, "exp": int(time.time()) - 10}
        expired_token = jwt.encode(
            expired_payload, "test-access-secret", algorithm="HS256"
        )

        with pytest.raises(BaseSecurityError):
            jwt_manager.decode_access_token(expired_token)

    def test_decode_token_with_wrong_secret_raises(self, jwt_manager):
        tampered_token = jwt.encode(
            {"user_id": 1, "exp": int(time.time()) + 3600},
            "wrong-secret",
            algorithm="HS256",
        )

        with pytest.raises(BaseSecurityError):
            jwt_manager.decode_access_token(tampered_token)

    def test_decode_malformed_token_raises(self, jwt_manager):
        with pytest.raises(BaseSecurityError):
            jwt_manager.decode_access_token("not.a.valid.jwt.token")

    def test_access_token_cannot_be_decoded_as_refresh_token(self, jwt_manager):
        access_token = jwt_manager.create_access_token({"user_id": 1})

        with pytest.raises(BaseSecurityError):
            jwt_manager.decode_refresh_token(access_token)

    def test_refresh_token_cannot_be_decoded_as_access_token(self, jwt_manager):
        refresh_token = jwt_manager.create_refresh_token({"user_id": 1})

        with pytest.raises(BaseSecurityError):
            jwt_manager.decode_access_token(refresh_token)

    def test_decode_token_missing_user_id_claim(self, jwt_manager):
        token = jwt.encode(
            {"exp": int(time.time()) + 3600}, "test-access-secret", algorithm="HS256"
        )

        payload = jwt_manager.decode_access_token(token)
        assert payload.get("user_id") is None  # caller must handle this explicitly
