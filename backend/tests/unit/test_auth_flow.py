"""
Unit tests for authentication + email verification flows.

All tests are pure-Python — no real database, no real SMTP.
Service methods are exercised directly with mocked dependencies.
Endpoint tests use TestClient with dependency overrides.
"""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime

from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers / shared data
# ---------------------------------------------------------------------------

def _make_user(
    *,
    is_email_verified: bool = False,
    is_active: bool = True,
    email: str = "alice@example.com",
) -> MagicMock:
    """Return a minimal User-like MagicMock."""
    u = MagicMock()
    u.id = uuid4()
    u.email = email
    u.is_email_verified = is_email_verified
    u.is_active = is_active
    u.is_verified = is_email_verified
    u.full_name = None
    u.username = "alice"
    u.subscription_tier = "free"
    u.has_completed_onboarding = False
    u.is_superuser = False
    u.created_at = datetime(2026, 1, 1)
    u.updated_at = None
    u.subscription_end_date = None
    u.onboarding_completed_at = None
    u.fitness_goal = None
    u.preferred_exercises = None
    u.fitness_level = None
    u.profile_image_url = None
    return u


# ---------------------------------------------------------------------------
# AuthService: send_verification_email
# ---------------------------------------------------------------------------

class TestSendVerificationEmail:
    """AuthService.send_verification_email behaviour."""

    @pytest.mark.asyncio
    async def test_skips_when_emails_disabled(self):
        """When emails_enabled=False the method returns silently — no attempt to send."""
        from app.services.auth_service import AuthService

        svc = AuthService(
            db=AsyncMock(),
            user_service=AsyncMock(),
            email_service=MagicMock(),
            redis_client=None,
        )
        with patch("app.services.auth_service.settings") as mock_settings:
            mock_settings.emails_enabled = False
            # Should NOT raise, NOT call email service
            await svc.send_verification_email("alice@example.com")
        # If we got here without exception — pass

    @pytest.mark.asyncio
    async def test_returns_silently_for_nonexistent_user(self):
        """Unknown email → silently no-op; must not raise."""
        from app.services.auth_service import AuthService

        user_service = AsyncMock()
        user_service.get_by_email_async.return_value = None  # user not found

        svc = AuthService(
            db=AsyncMock(),
            user_service=user_service,
            email_service=MagicMock(),
            redis_client=None,
        )
        with patch("app.services.auth_service.settings") as mock_settings:
            mock_settings.emails_enabled = True
            mock_settings.FRONTEND_URL = "http://localhost:3000"
            await svc.send_verification_email("nobody@example.com")

    @pytest.mark.asyncio
    async def test_returns_silently_for_already_verified_user(self):
        """Already-verified email → silently no-op; email service NOT called."""
        from app.services.auth_service import AuthService

        user = _make_user(is_email_verified=True)
        user_service = AsyncMock()
        user_service.get_by_email_async.return_value = user

        email_service = AsyncMock()
        svc = AuthService(
            db=AsyncMock(),
            user_service=user_service,
            email_service=email_service,
            redis_client=None,
        )
        with patch("app.services.auth_service.settings") as mock_settings:
            mock_settings.emails_enabled = True
            mock_settings.FRONTEND_URL = "http://localhost:3000"
            await svc.send_verification_email(user.email)

        email_service.send_verification_email.assert_not_called()

    @pytest.mark.asyncio
    async def test_calls_email_service_for_unverified_user(self):
        """Unverified user with SMTP configured → EmailService.send_verification_email called."""
        from app.services.auth_service import AuthService

        user = _make_user(is_email_verified=False)
        user_service = AsyncMock()
        user_service.get_by_email_async.return_value = user

        with (
            patch("app.services.auth_service.settings") as mock_settings,
            patch("app.services.auth_service.create_email_verification_token", return_value="tok123"),
            patch("app.services.auth_service.EmailService") as mock_es,
        ):
            mock_settings.emails_enabled = True
            mock_settings.FRONTEND_URL = "http://localhost:3000"
            mock_es.send_verification_email = AsyncMock(return_value=True)

            svc = AuthService(
                db=AsyncMock(),
                user_service=user_service,
                email_service=MagicMock(),
                redis_client=None,
            )
            await svc.send_verification_email(user.email)

        mock_es.send_verification_email.assert_awaited_once()
        call_kwargs = mock_es.send_verification_email.call_args
        assert "tok123" in str(call_kwargs)


# ---------------------------------------------------------------------------
# AuthService: verify_email
# ---------------------------------------------------------------------------

class TestVerifyEmail:
    """AuthService.verify_email behaviour."""

    @pytest.mark.asyncio
    async def test_raises_on_invalid_token(self):
        """A bad JWT (JWTError) → verify_email() raises ValidationException."""
        from app.services.auth_service import AuthService
        from app.core.exceptions import ValidationException
        from jose import JWTError

        with patch(
            "app.services.auth_service.verify_email_verification_token_and_get_email",
            side_effect=JWTError("bad jwt"),
        ):
            svc = AuthService(
                db=AsyncMock(),
                user_service=AsyncMock(),
                email_service=MagicMock(),
                redis_client=None,
            )
            with pytest.raises(ValidationException):
                await svc.verify_email("not-a-valid-token")

    @pytest.mark.asyncio
    async def test_raises_when_token_returns_no_email(self):
        """Token that decodes to None → ValidationException."""
        from app.services.auth_service import AuthService
        from app.core.exceptions import ValidationException

        with patch(
            "app.services.auth_service.verify_email_verification_token_and_get_email",
            return_value=None,
        ):
            svc = AuthService(
                db=AsyncMock(),
                user_service=AsyncMock(),
                email_service=MagicMock(),
                redis_client=None,
            )
            with pytest.raises(ValidationException):
                await svc.verify_email("empty-email-token")

    @pytest.mark.asyncio
    async def test_idempotent_for_already_verified_user(self):
        """Second call for an already-verified user returns silently — no DB write."""
        from app.services.auth_service import AuthService

        user = _make_user(is_email_verified=True)
        user_service = AsyncMock()
        user_service.get_by_email_async.return_value = user

        with patch(
            "app.services.auth_service.verify_email_verification_token_and_get_email",
            return_value=user.email,
        ):
            svc = AuthService(
                db=AsyncMock(),
                user_service=user_service,
                email_service=MagicMock(),
                redis_client=None,
            )
            await svc.verify_email("some-valid-token")

        user_service.update_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_happy_path_sets_is_email_verified_true(self):
        """Valid token for unverified user → update_async called with is_email_verified=True."""
        from app.services.auth_service import AuthService

        user = _make_user(is_email_verified=False)
        user_service = AsyncMock()
        user_service.get_by_email_async.return_value = user
        user_service.update_async.return_value = user

        with patch(
            "app.services.auth_service.verify_email_verification_token_and_get_email",
            return_value=user.email,
        ):
            svc = AuthService(
                db=AsyncMock(),
                user_service=user_service,
                email_service=MagicMock(),
                redis_client=None,
            )
            await svc.verify_email("valid-token")

        user_service.update_async.assert_awaited_once()
        call_kwargs = user_service.update_async.call_args.kwargs
        assert call_kwargs["db_obj"] is user
        assert call_kwargs["obj_in"]["is_email_verified"] is True
        assert "email_verified_at" not in call_kwargs["obj_in"]

    @pytest.mark.asyncio
    async def test_verify_email_with_token_delegates(self):
        """verify_email_with_token is a thin wrapper over verify_email."""
        from app.services.auth_service import AuthService

        svc = AuthService(
            db=AsyncMock(),
            user_service=AsyncMock(),
            email_service=MagicMock(),
            redis_client=None,
        )
        svc.verify_email = AsyncMock()
        await svc.verify_email_with_token("mytoken")
        svc.verify_email.assert_awaited_once_with("mytoken")

    @pytest.mark.asyncio
    async def test_request_email_verification_delegates(self):
        """request_email_verification delegates to send_verification_email."""
        from app.services.auth_service import AuthService

        svc = AuthService(
            db=AsyncMock(),
            user_service=AsyncMock(),
            email_service=MagicMock(),
            redis_client=None,
        )
        svc.send_verification_email = AsyncMock()
        await svc.request_email_verification("bob@example.com")
        svc.send_verification_email.assert_awaited_once_with("bob@example.com")


# ---------------------------------------------------------------------------
# Endpoint: POST /auth/register
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def _register_client():
    from app.main import app
    from app.api import deps

    async def _stub_db():
        yield AsyncMock()

    app.dependency_overrides[deps.get_async_db] = _stub_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.pop(deps.get_async_db, None)


class TestRegisterEndpoint:
    """POST /auth/register contract tests."""

    def test_register_duplicate_email_returns_400(self, _register_client: TestClient):
        """Registering an already-existing email → 400."""
        existing = _make_user(is_email_verified=False)

        with (
            patch("app.services.user_service.UserService.get_by_email_async", new_callable=AsyncMock, return_value=existing),
        ):
            resp = _register_client.post(
                "/api/v1/auth/register",
                json={
                    "email": existing.email,
                    "password": "TestPass1!",
                    "confirm_password": "TestPass1!",
                    "username": "alice",
                },
            )
        assert resp.status_code == 400
        assert "already exists" in resp.json().get("message", "").lower()

    def test_register_weak_password_returns_422(self, _register_client: TestClient):
        """Password without a number returns 422 validation error."""
        resp = _register_client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "weakpassword",
                "confirm_password": "weakpassword",
            },
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Endpoint: POST /auth/login — unverified user gate
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def _login_client():
    from app.main import app
    from app.api import deps

    async def _stub_db():
        yield AsyncMock()

    app.dependency_overrides[deps.get_async_db] = _stub_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.pop(deps.get_async_db, None)


class TestLoginUnverifiedGate:
    """Unverified users must be blocked (403) when BETA_ALLOW_UNVERIFIED=False."""

    def test_unverified_user_blocked_when_flag_off(self, _login_client: TestClient):
        """Unverified user + BETA_ALLOW_UNVERIFIED=False → 403."""
        unverified = _make_user(is_email_verified=False)

        with (
            patch("app.services.auth_service.AuthService.authenticate_user",
                  new_callable=AsyncMock,
                  return_value=(unverified, False, True)),
            patch("app.api.v1.endpoints.auth.settings") as mock_settings,
        ):
            mock_settings.BETA_ALLOW_UNVERIFIED = False
            resp = _login_client.post(
                "/api/v1/auth/login",
                data={"username": unverified.email, "password": "TestPass1!"},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

        assert resp.status_code == 403
        body = resp.json()
        # Backend returns "EMAIL_NOT_VERIFIED" as the machine-readable error code.
        error_text = body.get("message", "") or body.get("detail", "")
        assert "EMAIL_NOT_VERIFIED" in error_text, f"Expected EMAIL_NOT_VERIFIED in response; got: {body!r}"

    def test_unverified_user_allowed_when_flag_on(self, _login_client: TestClient):
        """Unverified user + BETA_ALLOW_UNVERIFIED=True → not blocked at the verification gate."""
        # We only test that a 403 is NOT returned due to the verification gate.
        # The request may still fail at session creation; that's outside this scope.
        unverified = _make_user(is_email_verified=False)

        with (
            patch("app.services.auth_service.AuthService.authenticate_user",
                  new_callable=AsyncMock,
                  return_value=(unverified, False, True)),
            patch("app.api.v1.endpoints.auth.settings") as mock_settings,
        ):
            mock_settings.BETA_ALLOW_UNVERIFIED = True
            resp = _login_client.post(
                "/api/v1/auth/login",
                data={"username": unverified.email, "password": "TestPass1!"},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

        # 403 because of email-verification gate must NOT appear
        assert resp.status_code != 403 or "verify" not in resp.text.lower()


# ---------------------------------------------------------------------------
# Endpoint: POST /auth/verify-email/confirm
# ---------------------------------------------------------------------------

class TestVerifyEmailConfirmEndpoint:
    """POST /auth/verify-email/confirm endpoint contract."""

    def test_valid_token_returns_200(self, _login_client: TestClient):
        """Valid token → 200 with success message."""
        with patch(
            "app.services.auth_service.AuthService.verify_email_with_token",
            new_callable=AsyncMock,
        ):
            resp = _login_client.post(
                "/api/v1/auth/verify-email/confirm",
                json={"token": "valid-test-token"},
            )
        assert resp.status_code == 200
        assert "verified" in resp.json().get("message", "").lower()

    def test_invalid_token_returns_error(self, _login_client: TestClient):
        """Invalid token → 4xx response, not a 500."""
        from app.core.exceptions import ValidationException

        with patch(
            "app.services.auth_service.AuthService.verify_email_with_token",
            new_callable=AsyncMock,
            side_effect=ValidationException("Invalid token"),
        ):
            resp = _login_client.post(
                "/api/v1/auth/verify-email/confirm",
                json={"token": "bad-token"},
            )
        assert 400 <= resp.status_code < 500

    def test_expired_token_shows_actionable_message(self, _login_client: TestClient):
        """Expired token → response body contains a human-readable error, not an internal traceback."""
        from app.core.exceptions import ValidationException

        with patch(
            "app.services.auth_service.AuthService.verify_email_with_token",
            new_callable=AsyncMock,
            side_effect=ValidationException("Invalid or expired verification token"),
        ):
            resp = _login_client.post(
                "/api/v1/auth/verify-email/confirm",
                json={"token": "expired-token"},
            )
        # Must be a 4xx, not 500
        assert resp.status_code < 500
        body_text = resp.text
        # Response should not contain raw Python traceback markers
        assert "Traceback" not in body_text
        assert "File " not in body_text


# ---------------------------------------------------------------------------
# Endpoint: POST /auth/verify-email/request
# ---------------------------------------------------------------------------

class TestRequestVerificationEndpoint:
    """POST /auth/verify-email/request must always return 202 (safe enumeration)."""

    def test_known_email_returns_202(self, _login_client: TestClient):
        with patch(
            "app.services.auth_service.AuthService.request_email_verification",
            new_callable=AsyncMock,
        ):
            resp = _login_client.post(
                "/api/v1/auth/verify-email/request",
                json={"email": "known@example.com"},
            )
        assert resp.status_code == 202

    def test_unknown_email_also_returns_202(self, _login_client: TestClient):
        """Endpoint must not reveal whether an email is registered."""
        with patch(
            "app.services.auth_service.AuthService.request_email_verification",
            new_callable=AsyncMock,
        ):
            resp = _login_client.post(
                "/api/v1/auth/verify-email/request",
                json={"email": "nobody@example.com"},
            )
        assert resp.status_code == 202

    def test_response_body_is_deliberately_vague(self, _login_client: TestClient):
        """Body should not confirm whether the email exists."""
        with patch(
            "app.services.auth_service.AuthService.request_email_verification",
            new_callable=AsyncMock,
        ):
            resp = _login_client.post(
                "/api/v1/auth/verify-email/request",
                json={"email": "test@example.com"},
            )
        body = resp.json().get("message", "")
        assert "if" in body.lower()   # "If account exists..." pattern
