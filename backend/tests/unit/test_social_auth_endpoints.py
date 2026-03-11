"""
Unit tests for /auth/social/google and /auth/social/apple endpoints.

SocialAuthService is fully mocked — no real HTTP calls to Google/Apple,
no real database.  Tests verify the HTTP contract:
  - Happy path → 200 with access_token + user dict (including has_completed_onboarding)
  - AuthenticationException from service layer → 400
  - Unexpected exception from service layer → 500
"""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime

from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_MOCK_USER = {
    "id": str(uuid4()),
    "email": "alice@gmail.com",
    "username": "alice",
    "full_name": "Alice Smith",
    "is_active": True,
    "is_verified": True,
    "has_completed_onboarding": False,
    "subscription_tier": "free",
    "created_at": datetime(2026, 1, 1).isoformat(),
}

_MOCK_AUTH_RESULT = {
    "access_token": "fake-access-token",
    "refresh_token": "fake-refresh-token",
    "token_type": "bearer",
    "user": _MOCK_USER,
}


@pytest.fixture(scope="module")
def client():
    """TestClient with a stub async-db dependency."""
    from app.main import app
    from app.api import deps

    async def _stub_db():
        db = AsyncMock()
        yield db

    app.dependency_overrides[deps.get_async_db] = _stub_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.pop(deps.get_async_db, None)


# ---------------------------------------------------------------------------
# /auth/social/google
# ---------------------------------------------------------------------------

class TestGoogleAuthEndpoint:
    def test_happy_path_returns_200_and_user_dict(self, client: TestClient):
        """POST /auth/social/google → 200 with access_token + has_completed_onboarding."""
        with patch(
            "app.services.social_auth_service.SocialAuthService.handle_social_login",
            new_callable=AsyncMock,
            return_value=_MOCK_AUTH_RESULT,
        ):
            resp = client.post(
                "/api/v1/auth/social/google",
                content=json.dumps("google-access-token"),
                headers={"Content-Type": "application/json"},
            )

        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["access_token"] == "fake-access-token"
        assert data["user"]["has_completed_onboarding"] is False
        assert data["user"]["email"] == "alice@gmail.com"

    def test_authentication_exception_returns_400(self, client: TestClient):
        """AuthenticationException from service layer → HTTP 400."""
        from app.core.exceptions import AuthenticationException

        with patch(
            "app.services.social_auth_service.SocialAuthService.handle_social_login",
            new_callable=AsyncMock,
            side_effect=AuthenticationException("Invalid Google token"),
        ):
            resp = client.post(
                "/api/v1/auth/social/google",
                content=json.dumps("bad-token"),
                headers={"Content-Type": "application/json"},
            )

        assert resp.status_code == 400
        body = resp.json()
        # Custom exception handler may use "message" or "detail" depending on config
        error_text = body.get("message", body.get("detail", ""))
        assert "Invalid Google token" in error_text

    def test_generic_exception_returns_500(self, client: TestClient):
        """Unexpected exception from service layer → HTTP 500."""
        with patch(
            "app.services.social_auth_service.SocialAuthService.handle_social_login",
            new_callable=AsyncMock,
            side_effect=RuntimeError("unexpected"),
        ):
            resp = client.post(
                "/api/v1/auth/social/google",
                content=json.dumps("bad-token"),
                headers={"Content-Type": "application/json"},
            )

        assert resp.status_code == 500

    def test_new_user_has_completed_onboarding_false(self, client: TestClient):
        """Newly created social users always have has_completed_onboarding=False."""
        new_user_result = {
            **_MOCK_AUTH_RESULT,
            "user": {**_MOCK_USER, "has_completed_onboarding": False},
        }
        with patch(
            "app.services.social_auth_service.SocialAuthService.handle_social_login",
            new_callable=AsyncMock,
            return_value=new_user_result,
        ):
            resp = client.post(
                "/api/v1/auth/social/google",
                content=json.dumps("valid-token"),
                headers={"Content-Type": "application/json"},
            )

        assert resp.status_code == 200
        assert resp.json()["user"]["has_completed_onboarding"] is False

    def test_returning_onboarded_user_has_completed_onboarding_true(self, client: TestClient):
        """Returning user who finished onboarding gets has_completed_onboarding=True."""
        returning_user_result = {
            **_MOCK_AUTH_RESULT,
            "user": {**_MOCK_USER, "has_completed_onboarding": True},
        }
        with patch(
            "app.services.social_auth_service.SocialAuthService.handle_social_login",
            new_callable=AsyncMock,
            return_value=returning_user_result,
        ):
            resp = client.post(
                "/api/v1/auth/social/google",
                content=json.dumps("valid-token"),
                headers={"Content-Type": "application/json"},
            )

        assert resp.status_code == 200
        assert resp.json()["user"]["has_completed_onboarding"] is True

    def test_deactivated_user_returns_400(self, client: TestClient):
        """Deactivated account → service raises AuthenticationException → 400."""
        from app.core.exceptions import AuthenticationException

        with patch(
            "app.services.social_auth_service.SocialAuthService.handle_social_login",
            new_callable=AsyncMock,
            side_effect=AuthenticationException("This account has been deactivated"),
        ):
            resp = client.post(
                "/api/v1/auth/social/google",
                content=json.dumps("valid-token"),
                headers={"Content-Type": "application/json"},
            )

        assert resp.status_code == 400
        body = resp.json()
        error_text = body.get("message", body.get("detail", ""))
        assert "deactivated" in error_text.lower()


# ---------------------------------------------------------------------------
# /auth/social/apple
# ---------------------------------------------------------------------------

class TestAppleAuthEndpoint:
    def test_happy_path_returns_200_and_user_dict(self, client: TestClient):
        """POST /auth/social/apple → 200 with access_token + has_completed_onboarding."""
        apple_result = {
            **_MOCK_AUTH_RESULT,
            "user": {**_MOCK_USER, "email": "bob@privaterelay.appleid.com"},
        }
        with patch(
            "app.services.social_auth_service.SocialAuthService.handle_social_login",
            new_callable=AsyncMock,
            return_value=apple_result,
        ):
            resp = client.post(
                "/api/v1/auth/social/apple",
                content=json.dumps("apple-id-token"),
                headers={"Content-Type": "application/json"},
            )

        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["access_token"] == "fake-access-token"
        assert data["user"]["has_completed_onboarding"] is False

    def test_authentication_exception_returns_400(self, client: TestClient):
        """AuthenticationException (e.g. bad iss/aud) → HTTP 400."""
        from app.core.exceptions import AuthenticationException

        with patch(
            "app.services.social_auth_service.SocialAuthService.handle_social_login",
            new_callable=AsyncMock,
            side_effect=AuthenticationException("Apple token validation failed: bad iss"),
        ):
            resp = client.post(
                "/api/v1/auth/social/apple",
                content=json.dumps("bad-token"),
                headers={"Content-Type": "application/json"},
            )

        assert resp.status_code == 400

    def test_not_configured_returns_400(self, client: TestClient):
        """APPLE_CLIENT_ID not set → service raises → HTTP 400."""
        from app.core.exceptions import AuthenticationException

        with patch(
            "app.services.social_auth_service.SocialAuthService.handle_social_login",
            new_callable=AsyncMock,
            side_effect=AuthenticationException("Apple Sign-In is not configured on this server"),
        ):
            resp = client.post(
                "/api/v1/auth/social/apple",
                content=json.dumps("some-token"),
                headers={"Content-Type": "application/json"},
            )

        assert resp.status_code == 400
        body = resp.json()
        error_text = body.get("message", body.get("detail", ""))
        assert "not configured" in error_text.lower()

    def test_generic_exception_returns_500(self, client: TestClient):
        """Unexpected exception → HTTP 500."""
        with patch(
            "app.services.social_auth_service.SocialAuthService.handle_social_login",
            new_callable=AsyncMock,
            side_effect=RuntimeError("unexpected crash"),
        ):
            resp = client.post(
                "/api/v1/auth/social/apple",
                content=json.dumps("some-token"),
                headers={"Content-Type": "application/json"},
            )

        assert resp.status_code == 500
