"""Unit tests for SocialAuthService — authenticate_social_user() and helpers.

All DB calls are mocked; no database is required.
Covers:
  - New user via Google (provider+id set, email set)
  - New user via Apple with email (provider+id set)
  - Repeat Apple login with no email (step-1 provider-id lookup)
  - Existing email-only user → backfill on first social login
  - Existing user linked to a different provider → clear error
  - Deactivated account → blocked
  - verify_google_token / verify_apple_token unit paths (mocked HTTP)
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from uuid import uuid4
from datetime import datetime

from app.services.social_auth_service import SocialAuthService, _b64url_to_int, _rsa_pem_from_jwk
from app.schemas.social_auth import SocialUserInfo
from app.core.exceptions import AuthenticationException


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(
    *,
    email="test@example.com",
    social_provider=None,
    social_id=None,
    is_active=True,
    has_completed_onboarding=False,
):
    """Return a minimal mock User object."""
    user = MagicMock()
    user.id = uuid4()
    user.email = email
    user.username = email.split("@")[0]
    user.full_name = None
    user.is_active = is_active
    user.is_verified = True
    user.social_provider = social_provider
    user.social_id = social_id
    user.has_completed_onboarding = has_completed_onboarding
    user.subscription_tier = "free"
    user.created_at = datetime(2026, 1, 1)
    return user


def _make_db(provider_user=None, email_user=None, username_free=True):
    """Return a mock AsyncSession that yields given users for each lookup."""
    db = AsyncMock()

    async def _execute(stmt):
        result = MagicMock()
        # Inspect only the WHERE clause to avoid false-positives from the
        # SELECT column list (which includes every User column by name).
        stmt_str = str(stmt)
        where_idx = stmt_str.upper().find("WHERE")
        where_part = stmt_str[where_idx:] if where_idx != -1 else ""

        if "social_provider" in where_part and "social_id" in where_part:
            result.scalars.return_value.first.return_value = provider_user
        elif "email" in where_part:
            result.scalars.return_value.first.return_value = email_user
        elif "username" in where_part:
            # Return None → username is free
            result.scalars.return_value.first.return_value = None if username_free else _make_user()
        else:
            result.scalars.return_value.first.return_value = None
        return result

    db.execute = _execute
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    return db


GOOGLE_USER_INFO = SocialUserInfo(
    email="alice@gmail.com",
    first_name="Alice",
    provider="google",
    provider_id="google-uid-001",
)

APPLE_USER_INFO_WITH_EMAIL = SocialUserInfo(
    email="bob@privaterelay.appleid.com",
    provider="apple",
    provider_id="apple-sub-001",
)

APPLE_USER_INFO_NO_EMAIL = SocialUserInfo(
    email=None,  # repeat sign-in — Apple omitted email
    provider="apple",
    provider_id="apple-sub-001",
)


# ---------------------------------------------------------------------------
# JWT helper unit tests
# ---------------------------------------------------------------------------

class TestJWKHelpers:
    def test_b64url_to_int_simple(self):
        # base64url of b'\x01' → 1
        assert _b64url_to_int("AQ") == 1

    def test_b64url_to_int_with_padding(self):
        # AQAB is the standard RSA e=65537 exponent in base64url
        assert _b64url_to_int("AQAB") == 65537


# ---------------------------------------------------------------------------
# authenticate_social_user — new user
# ---------------------------------------------------------------------------

class TestNewUser:
    @pytest.mark.asyncio
    async def test_new_google_user_created_with_provider_fields(self):
        """New Google user: creates row with social_provider + social_id."""
        db = _make_db(provider_user=None, email_user=None)
        svc = SocialAuthService()

        created_user = _make_user(
            email="alice@gmail.com",
            social_provider="google",
            social_id="google-uid-001",
        )
        db.refresh = AsyncMock(side_effect=lambda u: setattr(u, "id", uuid4()) or None)

        with patch("app.services.social_auth_service.create_access_token", return_value="at"), \
             patch("app.services.social_auth_service.create_refresh_token", return_value="rt"):

            result = await svc.authenticate_social_user(GOOGLE_USER_INFO, db)

        assert result["access_token"] == "at"
        assert result["refresh_token"] == "rt"
        assert result["user"]["email"] == "alice@gmail.com"
        db.add.assert_called_once()
        db.commit.assert_awaited()

    @pytest.mark.asyncio
    async def test_new_apple_user_with_email_created(self):
        """New Apple user (with email): creates row."""
        db = _make_db(provider_user=None, email_user=None)
        svc = SocialAuthService()

        db.refresh = AsyncMock(side_effect=lambda u: setattr(u, "id", uuid4()) or None)

        with patch("app.services.social_auth_service.create_access_token", return_value="at"), \
             patch("app.services.social_auth_service.create_refresh_token", return_value="rt"):

            result = await svc.authenticate_social_user(APPLE_USER_INFO_WITH_EMAIL, db)

        assert result["user"]["email"] == "bob@privaterelay.appleid.com"
        db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_new_apple_user_no_email_raises(self):
        """Step-3 create without email must raise a clear error."""
        db = _make_db(provider_user=None, email_user=None)
        svc = SocialAuthService()

        with pytest.raises(AuthenticationException, match="email"):
            await svc.authenticate_social_user(APPLE_USER_INFO_NO_EMAIL, db)


# ---------------------------------------------------------------------------
# authenticate_social_user — repeat login
# ---------------------------------------------------------------------------

class TestRepeatLogin:
    @pytest.mark.asyncio
    async def test_repeat_google_login_resolved_by_provider_id(self):
        """Existing Google user found via (provider, social_id) — step 1."""
        existing = _make_user(
            email="alice@gmail.com",
            social_provider="google",
            social_id="google-uid-001",
        )
        db = _make_db(provider_user=existing)
        svc = SocialAuthService()

        with patch("app.services.social_auth_service.create_access_token", return_value="at"), \
             patch("app.services.social_auth_service.create_refresh_token", return_value="rt"):

            result = await svc.authenticate_social_user(GOOGLE_USER_INFO, db)

        assert result["user"]["email"] == "alice@gmail.com"
        db.add.assert_not_called()  # no new user created

    @pytest.mark.asyncio
    async def test_repeat_apple_login_no_email_resolved_by_sub(self):
        """Repeat Apple sign-in (no email in token) resolved by provider_id."""
        existing = _make_user(
            email="bob@privaterelay.appleid.com",
            social_provider="apple",
            social_id="apple-sub-001",
        )
        db = _make_db(provider_user=existing)
        svc = SocialAuthService()

        with patch("app.services.social_auth_service.create_access_token", return_value="at"), \
             patch("app.services.social_auth_service.create_refresh_token", return_value="rt"):

            result = await svc.authenticate_social_user(APPLE_USER_INFO_NO_EMAIL, db)

        assert result["user"]["email"] == "bob@privaterelay.appleid.com"
        db.add.assert_not_called()


# ---------------------------------------------------------------------------
# authenticate_social_user — email fallback + backfill
# ---------------------------------------------------------------------------

class TestEmailFallback:
    @pytest.mark.asyncio
    async def test_existing_email_user_backfilled_on_first_social_login(self):
        """Email/password user signs in with Google for the first time.
        social_provider + social_id are written back (backfill)."""
        email_user = _make_user(
            email="alice@gmail.com",
            social_provider=None,
            social_id=None,
        )
        db = _make_db(provider_user=None, email_user=email_user)
        svc = SocialAuthService()

        with patch("app.services.social_auth_service.create_access_token", return_value="at"), \
             patch("app.services.social_auth_service.create_refresh_token", return_value="rt"):

            result = await svc.authenticate_social_user(GOOGLE_USER_INFO, db)

        # Backfill happened
        assert email_user.social_provider == "google"
        assert email_user.social_id == "google-uid-001"
        db.commit.assert_awaited()
        db.add.assert_not_called()
        assert result["user"]["email"] == "alice@gmail.com"

    @pytest.mark.asyncio
    async def test_email_linked_to_different_provider_raises(self):
        """Email already linked to Apple — Google login must be blocked."""
        email_user = _make_user(
            email="alice@gmail.com",
            social_provider="apple",
            social_id="different-sub",
        )
        db = _make_db(provider_user=None, email_user=email_user)
        svc = SocialAuthService()

        with pytest.raises(AuthenticationException, match="different sign-in method"):
            await svc.authenticate_social_user(GOOGLE_USER_INFO, db)


# ---------------------------------------------------------------------------
# authenticate_social_user — security
# ---------------------------------------------------------------------------

class TestActiveCheck:
    @pytest.mark.asyncio
    async def test_deactivated_account_blocked(self):
        """is_active=False must raise regardless of provider match."""
        inactive = _make_user(
            email="alice@gmail.com",
            social_provider="google",
            social_id="google-uid-001",
            is_active=False,
        )
        db = _make_db(provider_user=inactive)
        svc = SocialAuthService()

        with pytest.raises(AuthenticationException, match="deactivated"):
            await svc.authenticate_social_user(GOOGLE_USER_INFO, db)


# ---------------------------------------------------------------------------
# verify_google_token (mocked HTTP)
# ---------------------------------------------------------------------------

class TestVerifyGoogleToken:
    @pytest.mark.asyncio
    async def test_happy_path(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "id": "gid1",
            "email": "alice@gmail.com",
            "verified_email": True,
            "given_name": "Alice",
            "family_name": "Smith",
            "name": "Alice Smith",
        }

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            mock_client.get.return_value = mock_resp

            svc = SocialAuthService()
            info = await svc.verify_google_token("some-access-token")

        assert info.provider == "google"
        assert info.provider_id == "gid1"
        assert str(info.email) == "alice@gmail.com"

    @pytest.mark.asyncio
    async def test_non_200_raises(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 401

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            mock_client.get.return_value = mock_resp

            svc = SocialAuthService()
            with pytest.raises(AuthenticationException, match="Invalid Google token"):
                await svc.verify_google_token("bad-token")

    @pytest.mark.asyncio
    async def test_unverified_email_raises(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "id": "gid2",
            "email": "alice@gmail.com",
            "verified_email": False,
        }

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            mock_client.get.return_value = mock_resp

            svc = SocialAuthService()
            with pytest.raises(AuthenticationException, match="not verified"):
                await svc.verify_google_token("token")


# ---------------------------------------------------------------------------
# verify_apple_token — config guard
# ---------------------------------------------------------------------------

class TestVerifyAppleToken:
    @pytest.mark.asyncio
    async def test_no_client_id_raises(self):
        svc = SocialAuthService()
        with patch("app.services.social_auth_service.settings") as mock_settings:
            mock_settings.APPLE_CLIENT_ID = ""
            with pytest.raises(AuthenticationException, match="not configured"):
                await svc.verify_apple_token("some-token")

    @pytest.mark.asyncio
    async def test_happy_path_returns_social_user_info(self):
        """Valid Apple token (mocked JWKS + mocked jose decode) → SocialUserInfo."""
        mock_keys_resp = MagicMock()
        mock_keys_resp.status_code = 200
        mock_keys_resp.json.return_value = {
            "keys": [{"kid": "key1", "kty": "RSA", "n": "AQAB", "e": "AQAB"}]
        }

        with patch("app.services.social_auth_service.settings") as mock_settings, \
             patch("httpx.AsyncClient") as mock_client_cls, \
             patch("app.services.social_auth_service.jose_jwt.get_unverified_header") as mock_header, \
             patch("app.services.social_auth_service._rsa_pem_from_jwk") as mock_pem, \
             patch("app.services.social_auth_service.jose_jwt.decode") as mock_decode:

            mock_settings.APPLE_CLIENT_ID = "com.example.formiq"
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            mock_client.get.return_value = mock_keys_resp

            mock_header.return_value = {"kid": "key1", "alg": "RS256"}
            mock_pem.return_value = "-----BEGIN PUBLIC KEY-----\nfake\n-----END PUBLIC KEY-----"
            mock_decode.return_value = {
                "sub": "apple-sub-xyz",
                "email": "user@privaterelay.appleid.com",
                "iss": "https://appleid.apple.com",
                "aud": "com.example.formiq",
            }

            svc = SocialAuthService()
            info = await svc.verify_apple_token("some-id-token")

        assert info.provider == "apple"
        assert info.provider_id == "apple-sub-xyz"
        assert str(info.email) == "user@privaterelay.appleid.com"

    @pytest.mark.asyncio
    async def test_repeat_signin_no_email_is_none(self):
        """On repeat sign-in Apple omits email; email field should be None."""
        mock_keys_resp = MagicMock()
        mock_keys_resp.status_code = 200
        mock_keys_resp.json.return_value = {
            "keys": [{"kid": "key2", "kty": "RSA", "n": "AQAB", "e": "AQAB"}]
        }

        with patch("app.services.social_auth_service.settings") as mock_settings, \
             patch("httpx.AsyncClient") as mock_client_cls, \
             patch("app.services.social_auth_service.jose_jwt.get_unverified_header") as mock_header, \
             patch("app.services.social_auth_service._rsa_pem_from_jwk") as mock_pem, \
             patch("app.services.social_auth_service.jose_jwt.decode") as mock_decode:

            mock_settings.APPLE_CLIENT_ID = "com.example.formiq"
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            mock_client.get.return_value = mock_keys_resp

            mock_header.return_value = {"kid": "key2", "alg": "RS256"}
            mock_pem.return_value = "fake-pem"
            mock_decode.return_value = {
                "sub": "apple-sub-xyz",
                # email intentionally absent (repeat sign-in)
            }

            svc = SocialAuthService()
            info = await svc.verify_apple_token("some-id-token")

        assert info.provider_id == "apple-sub-xyz"
        assert info.email is None

    @pytest.mark.asyncio
    async def test_bad_aud_raises_authentication_exception(self):
        """jose_jwt.decode raises JWTError for wrong aud → AuthenticationException."""
        from jose import JWTError

        mock_keys_resp = MagicMock()
        mock_keys_resp.status_code = 200
        mock_keys_resp.json.return_value = {
            "keys": [{"kid": "key3", "kty": "RSA", "n": "AQAB", "e": "AQAB"}]
        }

        with patch("app.services.social_auth_service.settings") as mock_settings, \
             patch("httpx.AsyncClient") as mock_client_cls, \
             patch("app.services.social_auth_service.jose_jwt.get_unverified_header") as mock_header, \
             patch("app.services.social_auth_service._rsa_pem_from_jwk") as mock_pem, \
             patch("app.services.social_auth_service.jose_jwt.decode") as mock_decode:

            mock_settings.APPLE_CLIENT_ID = "com.example.formiq"
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            mock_client.get.return_value = mock_keys_resp

            mock_header.return_value = {"kid": "key3", "alg": "RS256"}
            mock_pem.return_value = "fake-pem"
            mock_decode.side_effect = JWTError("Invalid audience")

            svc = SocialAuthService()
            with pytest.raises(AuthenticationException, match="validation failed"):
                await svc.verify_apple_token("some-id-token")

    @pytest.mark.asyncio
    async def test_kid_not_in_jwks_raises(self):
        """Token kid not found in Apple JWKS → AuthenticationException."""
        mock_keys_resp = MagicMock()
        mock_keys_resp.status_code = 200
        mock_keys_resp.json.return_value = {
            "keys": [{"kid": "other-key", "kty": "RSA", "n": "AQAB", "e": "AQAB"}]
        }

        with patch("app.services.social_auth_service.settings") as mock_settings, \
             patch("httpx.AsyncClient") as mock_client_cls, \
             patch("app.services.social_auth_service.jose_jwt.get_unverified_header") as mock_header:

            mock_settings.APPLE_CLIENT_ID = "com.example.formiq"
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            mock_client.get.return_value = mock_keys_resp

            mock_header.return_value = {"kid": "no-such-key", "alg": "RS256"}

            svc = SocialAuthService()
            with pytest.raises(AuthenticationException, match="kid mismatch"):
                await svc.verify_apple_token("some-id-token")

    @pytest.mark.asyncio
    async def test_missing_sub_raises(self):
        """Token missing 'sub' claim → AuthenticationException."""
        mock_keys_resp = MagicMock()
        mock_keys_resp.status_code = 200
        mock_keys_resp.json.return_value = {
            "keys": [{"kid": "key5", "kty": "RSA", "n": "AQAB", "e": "AQAB"}]
        }

        with patch("app.services.social_auth_service.settings") as mock_settings, \
             patch("httpx.AsyncClient") as mock_client_cls, \
             patch("app.services.social_auth_service.jose_jwt.get_unverified_header") as mock_header, \
             patch("app.services.social_auth_service._rsa_pem_from_jwk") as mock_pem, \
             patch("app.services.social_auth_service.jose_jwt.decode") as mock_decode:

            mock_settings.APPLE_CLIENT_ID = "com.example.formiq"
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            mock_client.get.return_value = mock_keys_resp

            mock_header.return_value = {"kid": "key5", "alg": "RS256"}
            mock_pem.return_value = "fake-pem"
            mock_decode.return_value = {
                # sub intentionally absent
                "email": "user@example.com",
            }

            svc = SocialAuthService()
            with pytest.raises(AuthenticationException, match="sub"):
                await svc.verify_apple_token("some-id-token")
