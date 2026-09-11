import pytest

from database.validators.accounts import validate_email, validate_password_strength


class TestValidatePasswordStrength:
    @pytest.mark.parametrize(
        "weak_password,expected_message_part",
        [
            ("Sh0rt!", "at least 8 characters"),
            ("alllowercase1!", "uppercase letter"),
            ("ALLUPPERCASE1!", "lower letter"),
            ("NoDigitsHere!", "one digit"),
            ("NoSpecialChar1", "special character"),
        ],
    )
    def test_weak_passwords_raise_value_error_with_specific_message(
        self, weak_password, expected_message_part
    ):
        with pytest.raises(ValueError, match=expected_message_part):
            validate_password_strength(weak_password)

    def test_strong_password_passes_and_returns_same_value(self):
        password = "StrongP@ssw0rd!"
        assert validate_password_strength(password) == password

    @pytest.mark.parametrize("special_char", ["@", "$", "!", "%", "*", "?", "#", "&"])
    def test_each_allowed_special_character_is_accepted(self, special_char):
        password = f"Password1{special_char}"
        assert validate_password_strength(password) == password

    def test_special_character_outside_allowed_set_is_rejected(self):
        """'^' is not in the allowed set @$!%*?&# — must be rejected."""
        with pytest.raises(ValueError, match="special character"):
            validate_password_strength("Password1^")


class TestValidateEmail:
    def test_valid_email_returns_normalized_value(self):
        assert validate_email("Test@Example.com") == "Test@example.com"

    def test_invalid_email_raises_value_error(self):
        with pytest.raises(ValueError):
            validate_email("not-an-email")

    def test_email_without_domain_raises_value_error(self):
        with pytest.raises(ValueError):
            validate_email("user@")
