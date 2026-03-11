"""
Unit tests for POST /debug/email-test.

Verifies the HTTP contract without hitting SMTP or the database:
  - emails_enabled=False  → 200, sent=False, error explains config problem
  - emails_enabled=True, SMTP succeeds → 200, sent=True, error=None
  - emails_enabled=True, SMTP fails   → 200, sent=False, error describes failure
  - production environment            → 404 (endpoint hidden)

No database, no real SMTP.  All service layer calls are patched.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def client():
    """TestClient with a stub async-db dependency."""
    from app.main import app
    from app.api import deps

    async def _stub_db():
        yield AsyncMock()

    app.dependency_overrides[deps.get_async_db] = _stub_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.pop(deps.get_async_db, None)


_VALID_BODY = {"to": "recipient@example.com"}


# ---------------------------------------------------------------------------
# emails_enabled = False  (placeholder / missing config)
# ---------------------------------------------------------------------------

class TestDebugEmailDisabledConfig:
    """When emails_enabled returns False the endpoint must short-circuit."""

    def test_returns_200_not_500(self, client):
        with patch("app.api.v1.endpoints.debug.settings") as mock_settings:
            mock_settings.emails_enabled = False
            mock_settings.MAIL_SERVER = "smtp.gmail.com"
            mock_settings.MAIL_PORT = 587
            mock_settings.MAIL_USERNAME = "your_email@gmail.com"
            mock_settings.ENVIRONMENT = "development"

            resp = client.post("/api/v1/debug/email-test", json=_VALID_BODY)

        assert resp.status_code == 200

    def test_sent_is_false(self, client):
        with patch("app.api.v1.endpoints.debug.settings") as mock_settings:
            mock_settings.emails_enabled = False
            mock_settings.MAIL_SERVER = "smtp.gmail.com"
            mock_settings.MAIL_PORT = 587
            mock_settings.MAIL_USERNAME = "your_email@gmail.com"
            mock_settings.ENVIRONMENT = "development"

            resp = client.post("/api/v1/debug/email-test", json=_VALID_BODY)

        assert resp.json()["sent"] is False

    def test_error_field_mentions_placeholder(self, client):
        with patch("app.api.v1.endpoints.debug.settings") as mock_settings:
            mock_settings.emails_enabled = False
            mock_settings.MAIL_SERVER = "smtp.gmail.com"
            mock_settings.MAIL_PORT = 587
            mock_settings.MAIL_USERNAME = "your_email@gmail.com"
            mock_settings.ENVIRONMENT = "development"

            resp = client.post("/api/v1/debug/email-test", json=_VALID_BODY)

        error = resp.json().get("error", "")
        # Must mention configuration / placeholder / disabled — not a cryptic trace
        assert error, "error field must not be empty"
        keywords = ("placeholder", "disabled", "credentials", "MAIL_")
        assert any(kw.lower() in error.lower() for kw in keywords), (
            f"error should reference config problem; got: {error!r}"
        )

    def test_smtp_send_not_called_when_disabled(self, client):
        """EmailService.send_email must NOT be invoked when config gate fires."""
        with patch("app.api.v1.endpoints.debug.settings") as mock_settings, \
             patch("app.api.v1.endpoints.debug.EmailService.send_email") as mock_send:
            mock_settings.emails_enabled = False
            mock_settings.MAIL_SERVER = "smtp.gmail.com"
            mock_settings.MAIL_PORT = 587
            mock_settings.MAIL_USERNAME = "your_email@gmail.com"
            mock_settings.ENVIRONMENT = "development"

            client.post("/api/v1/debug/email-test", json=_VALID_BODY)

        mock_send.assert_not_called()


# ---------------------------------------------------------------------------
# emails_enabled = True, SMTP succeeds
# ---------------------------------------------------------------------------

class TestDebugEmailSuccessPath:
    """Happy path: real-looking credentials + SMTP succeeds."""

    def test_sent_true_on_success(self, client):
        with patch("app.api.v1.endpoints.debug.settings") as mock_settings, \
             patch("app.api.v1.endpoints.debug.EmailService.send_email", new=AsyncMock(return_value=True)):
            mock_settings.emails_enabled = True
            mock_settings.MAIL_SERVER = "smtp.gmail.com"
            mock_settings.MAIL_PORT = 587
            mock_settings.MAIL_USERNAME = "real@gmail.com"
            mock_settings.ENVIRONMENT = "development"

            resp = client.post("/api/v1/debug/email-test", json=_VALID_BODY)

        assert resp.status_code == 200
        body = resp.json()
        assert body["sent"] is True
        assert body["error"] is None

    def test_response_includes_smtp_server_field(self, client):
        with patch("app.api.v1.endpoints.debug.settings") as mock_settings, \
             patch("app.api.v1.endpoints.debug.EmailService.send_email", new=AsyncMock(return_value=True)):
            mock_settings.emails_enabled = True
            mock_settings.MAIL_SERVER = "smtp.gmail.com"
            mock_settings.MAIL_PORT = 587
            mock_settings.MAIL_USERNAME = "real@gmail.com"
            mock_settings.ENVIRONMENT = "development"

            resp = client.post("/api/v1/debug/email-test", json=_VALID_BODY)

        body = resp.json()
        assert "smtp_server" in body
        assert "smtp.gmail.com" in body["smtp_server"]


# ---------------------------------------------------------------------------
# emails_enabled = True, SMTP fails
# ---------------------------------------------------------------------------

class TestDebugEmailSmtpFailure:
    """When SMTP call returns False the endpoint should still return 200."""

    def test_returns_200_on_smtp_failure(self, client):
        with patch("app.api.v1.endpoints.debug.settings") as mock_settings, \
             patch("app.api.v1.endpoints.debug.EmailService.send_email", new=AsyncMock(return_value=False)):
            mock_settings.emails_enabled = True
            mock_settings.MAIL_SERVER = "smtp.gmail.com"
            mock_settings.MAIL_PORT = 587
            mock_settings.MAIL_USERNAME = "real@gmail.com"
            mock_settings.ENVIRONMENT = "development"

            resp = client.post("/api/v1/debug/email-test", json=_VALID_BODY)

        assert resp.status_code == 200

    def test_sent_false_on_smtp_failure(self, client):
        with patch("app.api.v1.endpoints.debug.settings") as mock_settings, \
             patch("app.api.v1.endpoints.debug.EmailService.send_email", new=AsyncMock(return_value=False)):
            mock_settings.emails_enabled = True
            mock_settings.MAIL_SERVER = "smtp.gmail.com"
            mock_settings.MAIL_PORT = 587
            mock_settings.MAIL_USERNAME = "real@gmail.com"
            mock_settings.ENVIRONMENT = "development"

            resp = client.post("/api/v1/debug/email-test", json=_VALID_BODY)

        assert resp.json()["sent"] is False

    def test_error_field_describes_smtp_failure(self, client):
        with patch("app.api.v1.endpoints.debug.settings") as mock_settings, \
             patch("app.api.v1.endpoints.debug.EmailService.send_email", new=AsyncMock(return_value=False)):
            mock_settings.emails_enabled = True
            mock_settings.MAIL_SERVER = "smtp.gmail.com"
            mock_settings.MAIL_PORT = 587
            mock_settings.MAIL_USERNAME = "real@gmail.com"
            mock_settings.ENVIRONMENT = "development"

            resp = client.post("/api/v1/debug/email-test", json=_VALID_BODY)

        error = resp.json().get("error", "")
        assert error, "error field must not be empty on SMTP failure"
        keywords = ("smtp", "send", "failed", "log", "password")
        assert any(kw.lower() in error.lower() for kw in keywords), (
            f"error should explain the failure; got: {error!r}"
        )

    def test_returns_200_on_unexpected_exception(self, client):
        """Even if EmailService raises, endpoint must not return 5xx."""
        with patch("app.api.v1.endpoints.debug.settings") as mock_settings, \
             patch(
                 "app.api.v1.endpoints.debug.EmailService.send_email",
                 new=AsyncMock(side_effect=RuntimeError("SMTP timeout")),
             ):
            mock_settings.emails_enabled = True
            mock_settings.MAIL_SERVER = "smtp.gmail.com"
            mock_settings.MAIL_PORT = 587
            mock_settings.MAIL_USERNAME = "real@gmail.com"
            mock_settings.ENVIRONMENT = "development"

            resp = client.post("/api/v1/debug/email-test", json=_VALID_BODY)

        assert resp.status_code == 200
        assert resp.json()["sent"] is False


# ---------------------------------------------------------------------------
# Production environment — endpoint must be hidden (404)
# ---------------------------------------------------------------------------

class TestDebugEmailProductionHidden:
    """In production the endpoint must return 404."""

    def test_returns_404_in_production(self, client):
        with patch("app.api.v1.endpoints.debug.settings") as mock_settings:
            mock_settings.ENVIRONMENT = "production"
            mock_settings.emails_enabled = True
            mock_settings.MAIL_SERVER = "smtp.gmail.com"
            mock_settings.MAIL_PORT = 587
            mock_settings.MAIL_USERNAME = "real@gmail.com"

            resp = client.post("/api/v1/debug/email-test", json=_VALID_BODY)

        assert resp.status_code == 404
