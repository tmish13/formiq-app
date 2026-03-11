"""
Unit tests for validate_password() in app.core.validators.

Canonical rules (must match frontend ModernAuthPage.tsx validateForm):
  - Min length  : 8
  - Max length  : 100
  - Digit       : at least one (0–9)
  - Special char: at least one from !@#$%^&*()_-+=[]{}|;:'",.<>/?`~
  - NO uppercase/lowercase requirement
"""
import pytest
from app.core.exceptions import ValidationException
from app.core.validators import validate_password, PASSWORD_MIN_LENGTH, PASSWORD_MAX_LENGTH


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _valid_base() -> str:
    """A password that satisfies every rule (8 chars, digit, special)."""
    return "Abcdef1!"


def _pw_of_length(n: int) -> str:
    """Build a password of exact length n that meets all other rules."""
    # pattern: start with "Aa1!" then pad with 'x'
    prefix = "Aa1!"
    if n <= len(prefix):
        return (prefix + "x" * 100)[:n]      # best-effort for tiny n
    return prefix + "x" * (n - len(prefix))


# ---------------------------------------------------------------------------
# Constant sanity
# ---------------------------------------------------------------------------

class TestConstants:
    def test_min_is_8(self):
        assert PASSWORD_MIN_LENGTH == 8

    def test_max_is_100(self):
        assert PASSWORD_MAX_LENGTH == 100


# ---------------------------------------------------------------------------
# Length boundary tests
# ---------------------------------------------------------------------------

class TestLengthBoundaries:
    def test_password_of_length_8_passes(self):
        pw = _pw_of_length(8)
        assert validate_password(pw) is True   # returns True on success

    def test_password_of_length_100_passes(self):
        """Exactly 100 characters must be accepted (upper boundary)."""
        pw = _pw_of_length(100)
        assert len(pw) == 100
        assert validate_password(pw) is True

    def test_password_of_length_101_fails(self):
        """101 characters must be rejected with a message mentioning '100'."""
        pw = _pw_of_length(101)
        with pytest.raises(ValidationException) as exc_info:
            validate_password(pw)
        assert "100" in exc_info.value.message, (
            f"Error message should mention '100', got: {exc_info.value.message!r}"
        )

    def test_password_of_length_7_fails(self):
        """Below minimum (7 chars) must be rejected."""
        pw = _pw_of_length(7)
        with pytest.raises(ValidationException) as exc_info:
            validate_password(pw)
        assert "8" in exc_info.value.message

    def test_empty_password_fails(self):
        with pytest.raises(ValidationException):
            validate_password("")


# ---------------------------------------------------------------------------
# Digit requirement
# ---------------------------------------------------------------------------

class TestDigitRequirement:
    def test_no_digit_fails(self):
        with pytest.raises(ValidationException) as exc_info:
            validate_password("Abcdefg!")
        assert "number" in exc_info.value.message.lower()

    def test_digit_present_passes(self):
        assert validate_password("Abcdef1!") is True


# ---------------------------------------------------------------------------
# Special character requirement
# ---------------------------------------------------------------------------

class TestSpecialCharRequirement:
    def test_no_special_char_fails(self):
        with pytest.raises(ValidationException) as exc_info:
            validate_password("Abcdefg1")
        assert "special" in exc_info.value.message.lower()

    @pytest.mark.parametrize("special", list("!@#$%^&*()_-+=[]{}|;:'\",.<>/?`~"))
    def test_each_special_char_passes(self, special: str):
        pw = f"Abcdef1{special}"
        assert validate_password(pw) is True, f"Special char {special!r} should be accepted"


# ---------------------------------------------------------------------------
# No uppercase / lowercase requirement
# ---------------------------------------------------------------------------

class TestNoUpperLowerRequirement:
    def test_all_lowercase_passes(self):
        """No uppercase required — all-lowercase must pass if other rules met."""
        assert validate_password("abcdef1!") is True

    def test_all_uppercase_passes(self):
        """No lowercase required — all-uppercase must pass if other rules met."""
        assert validate_password("ABCDEF1!") is True
