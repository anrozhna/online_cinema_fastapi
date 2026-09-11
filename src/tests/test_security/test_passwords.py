from security.passwords import hash_password, verify_password


class TestHashPassword:
    def test_hash_differs_from_raw_password(self):
        raw = "StrongP@ssw0rd!"
        assert hash_password(raw) != raw

    def test_same_password_produces_different_hashes(self):
        """Bcrypt salts each hash — two hashes of the same password must differ."""
        raw = "StrongP@ssw0rd!"
        assert hash_password(raw) != hash_password(raw)


class TestVerifyPassword:
    def test_correct_password_verifies(self):
        raw = "StrongP@ssw0rd!"
        hashed = hash_password(raw)
        assert verify_password(raw, hashed) is True

    def test_incorrect_password_fails(self):
        hashed = hash_password("StrongP@ssw0rd!")
        assert verify_password("wrong-password", hashed) is False
