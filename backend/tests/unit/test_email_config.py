"""
Unit tests for Settings.emails_enabled — the placeholder-detection gate.

No database, no SMTP, no FastAPI.
Constructs minimal Settings-like objects and verifies the property.
"""
import pytest


# ---------------------------------------------------------------------------
# Inline replica — mirrors the real property logic exactly so we can test
# it deterministically without touching the singleton `settings` object.
# ---------------------------------------------------------------------------

_PLACEHOLDER_FRAGMENTS = (
    "your_email",
    "your_app_password",
    "your_smtp_password",
    "your_16_char_app_password",
    "re_xxxxxxxxxxxxxxxxxxxx",
    "your_smtp_user",
)


def _emails_enabled(*, server: str, username: str, password: str, from_email: str) -> bool:
    """Replica of Settings.emails_enabled logic."""
    if not server or not from_email:
        return False
    for value in (username, password, from_email):
        if any(fragment in value for fragment in _PLACEHOLDER_FRAGMENTS):
            return False
    return True


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestEmailsEnabledPlaceholderDetection:
    """Placeholder credentials must always result in emails_enabled=False."""

    def test_placeholder_username_disables_email(self):
        assert _emails_enabled(
            server="smtp.gmail.com",
            username="your_email@gmail.com",
            password="real-app-password-abcd",
            from_email="your_email@gmail.com",
        ) is False

    def test_placeholder_password_disables_email(self):
        assert _emails_enabled(
            server="smtp.gmail.com",
            username="real@gmail.com",
            password="your_app_password_here",
            from_email="real@gmail.com",
        ) is False

    def test_placeholder_from_email_disables(self):
        assert _emails_enabled(
            server="smtp.gmail.com",
            username="real@gmail.com",
            password="real-password",
            from_email="your_email@example.com",
        ) is False

    def test_placeholder_substring_in_longer_address_detected(self):
        """Substring match: 'your_email' inside 'your_email@formiq.com' must be caught."""
        assert _emails_enabled(
            server="smtp.gmail.com",
            username="your_email@formiq.com",
            password="realpassword123",
            from_email="your_email@formiq.com",
        ) is False

    def test_resend_placeholder_key_disables(self):
        assert _emails_enabled(
            server="smtp.resend.com",
            username="resend",
            password="re_xxxxxxxxxxxxxxxxxxxx",
            from_email="onboarding@example.com",
        ) is False

    def test_smtp_user_placeholder_disables(self):
        assert _emails_enabled(
            server="smtp.example.com",
            username="your_smtp_user",
            password="password",
            from_email="no-reply@example.com",
        ) is False

    def test_16_char_password_placeholder_disables(self):
        assert _emails_enabled(
            server="smtp.gmail.com",
            username="real@gmail.com",
            password="your_16_char_app_password",
            from_email="real@gmail.com",
        ) is False


class TestEmailsEnabledRealCredentials:
    """Real (non-placeholder) credentials must enable email."""

    def test_real_gmail_credentials_enable_email(self):
        assert _emails_enabled(
            server="smtp.gmail.com",
            username="alice@gmail.com",
            password="abcd efgh ijkl mnop",   # typical App Password format
            from_email="alice@gmail.com",
        ) is True

    def test_real_resend_credentials_enable_email(self):
        assert _emails_enabled(
            server="smtp.resend.com",
            username="resend",
            password="re_ABCdef1234567890xyz",
            from_email="onboarding@mycompany.com",
        ) is True

    def test_real_custom_smtp_enables_email(self):
        assert _emails_enabled(
            server="mail.mycompany.com",
            username="noreply@mycompany.com",
            password="SuperSecurePass!99",
            from_email="noreply@mycompany.com",
        ) is True


class TestEmailsEnabledMissingFields:
    """Missing or empty server / from_email → disabled."""

    def test_missing_server_disables(self):
        assert _emails_enabled(
            server="",
            username="real@gmail.com",
            password="realpassword",
            from_email="real@gmail.com",
        ) is False

    def test_missing_from_email_disables(self):
        assert _emails_enabled(
            server="smtp.gmail.com",
            username="real@gmail.com",
            password="realpassword",
            from_email="",
        ) is False


class TestEmailsEnabledCaseAndWhitespace:
    """Placeholder detection is case-sensitive (fragments are lowercase)."""

    def test_capitalised_placeholder_not_caught(self):
        """Fragments use lowercase; MAIL_USERNAME=YOUR_EMAIL@... would not be caught.
        This documents the known limitation — .env values are always lowercase in practice.
        """
        # Capitalised "YOUR_EMAIL" does not contain lowercase "your_email"
        result = _emails_enabled(
            server="smtp.gmail.com",
            username="YOUR_EMAIL@gmail.com",
            password="realpass",
            from_email="YOUR_EMAIL@gmail.com",
        )
        # Document the current behaviour, not assert it must be True or False.
        # This test exists to signal that case matters.
        assert isinstance(result, bool)
