"""Social authentication service.

User lookup order (authenticate_social_user):
  1. (social_provider, social_id) — reliable for repeat logins; works for
     Apple even when the identity token omits the email on repeat sign-ins.
  2. email fallback with backfill — catches email/password (or pre-migration
     social) users signing in with a social provider for the first time.
     Provider fields are written back so step 1 works on all future logins.
  3. Create — brand-new user; email is required at this point.

Backfill (step 2) is self-healing: no offline job needed.
"""

import base64
import httpx
from typing import Optional

from jose import jwt as jose_jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicNumbers
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization

from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token
from app.core.exceptions import AuthenticationException
from app.models.user import User
from app.schemas.social_auth import SocialUserInfo


# ---------------------------------------------------------------------------
# JWK helpers
# ---------------------------------------------------------------------------

def _b64url_to_int(data: str) -> int:
    """Decode a base64url big-endian integer (JWK 'n'/'e' fields)."""
    padded = data + "=" * (4 - len(data) % 4)
    return int.from_bytes(base64.urlsafe_b64decode(padded), "big")


def _rsa_pem_from_jwk(jwk_data: dict) -> str:
    """Build a PEM-encoded RSA public key from a JWK dict."""
    n = _b64url_to_int(jwk_data["n"])
    e = _b64url_to_int(jwk_data["e"])
    pub_key = RSAPublicNumbers(e, n).public_key(default_backend())
    return pub_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class SocialAuthService:
    """Handle social authentication for Google and Apple."""

    # ------------------------------------------------------------------
    # Token verification
    # ------------------------------------------------------------------

    async def verify_google_token(self, token: str) -> SocialUserInfo:
        """Verify a Google access token via the userinfo API."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    "https://www.googleapis.com/oauth2/v2/userinfo",
                    headers={"Authorization": f"Bearer {token}"},
                )

            if resp.status_code != 200:
                raise AuthenticationException("Invalid Google token")

            info = resp.json()

            if not info.get("verified_email", False):
                raise AuthenticationException("Google account email is not verified")

            return SocialUserInfo(
                email=info["email"],
                first_name=info.get("given_name"),
                last_name=info.get("family_name"),
                name=info.get("name"),
                picture=info.get("picture"),
                provider="google",
                provider_id=info["id"],
            )

        except AuthenticationException:
            raise
        except Exception as exc:
            raise AuthenticationException(f"Google token verification failed: {exc}")

    async def verify_apple_token(self, token: str) -> SocialUserInfo:
        """Verify an Apple identity token using JWKS (RS256 + iss/aud checks).

        email is None when Apple omits it on repeat sign-ins.  The caller
        (authenticate_social_user) handles that via provider-id lookup.
        """
        APPLE_JWKS_URL = "https://appleid.apple.com/auth/keys"
        APPLE_ISSUER = "https://appleid.apple.com"

        if not settings.APPLE_CLIENT_ID:
            raise AuthenticationException(
                "Apple Sign-In is not configured on this server"
            )

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                keys_resp = await client.get(APPLE_JWKS_URL)

            if keys_resp.status_code != 200:
                raise AuthenticationException("Failed to fetch Apple public keys")

            apple_keys = keys_resp.json().get("keys", [])

            try:
                header = jose_jwt.get_unverified_header(token)
            except JWTError as exc:
                raise AuthenticationException(f"Apple token header invalid: {exc}")

            kid = header.get("kid")
            alg = header.get("alg", "RS256")

            key_data = next((k for k in apple_keys if k.get("kid") == kid), None)
            if not key_data:
                raise AuthenticationException(
                    "Apple token: no matching public key (kid mismatch)"
                )

            pem = _rsa_pem_from_jwk(key_data)
            try:
                decoded = jose_jwt.decode(
                    token,
                    pem,
                    algorithms=[alg],
                    audience=settings.APPLE_CLIENT_ID,
                    issuer=APPLE_ISSUER,
                )
            except JWTError as exc:
                raise AuthenticationException(f"Apple token validation failed: {exc}")

            sub = decoded.get("sub")
            if not sub:
                raise AuthenticationException(
                    "Apple token missing required 'sub' claim"
                )

            # email is present only on first sign-in; None on subsequent ones.
            email = decoded.get("email") or None

            return SocialUserInfo(
                email=email,  # may be None — handled in authenticate_social_user
                provider="apple",
                provider_id=sub,
            )

        except AuthenticationException:
            raise
        except Exception as exc:
            raise AuthenticationException(f"Apple token verification failed: {exc}")

    # ------------------------------------------------------------------
    # DB helpers
    # ------------------------------------------------------------------

    async def _lookup_by_provider(
        self, db: AsyncSession, provider: str, social_id: str
    ) -> Optional[User]:
        result = await db.execute(
            select(User).where(
                User.social_provider == provider,
                User.social_id == social_id,
            )
        )
        return result.scalars().first()

    async def _lookup_by_email(
        self, db: AsyncSession, email: str
    ) -> Optional[User]:
        result = await db.execute(
            select(User).where(User.email == email.lower())
        )
        return result.scalars().first()

    async def _unique_username(self, db: AsyncSession, base: str) -> str:
        """Return the first free variant of base (base, base1, base2, …)."""
        username = base.lower()[:28]
        counter = 1
        while True:
            result = await db.execute(
                select(User).where(User.username == username)
            )
            if result.scalars().first() is None:
                return username
            username = f"{base.lower()[:25]}{counter}"
            counter += 1

    # ------------------------------------------------------------------
    # Core authentication logic
    # ------------------------------------------------------------------

    async def authenticate_social_user(
        self, user_info: SocialUserInfo, db: AsyncSession
    ) -> dict:
        """Identify or create a user from a verified social identity.

        See module docstring for the three-step lookup contract.
        """
        user: Optional[User] = None

        # ── Step 1: provider-identity lookup (works even without email) ──
        user = await self._lookup_by_provider(
            db, user_info.provider, user_info.provider_id
        )

        # ── Step 2: email fallback + backfill ────────────────────────────
        if user is None and user_info.email:
            user = await self._lookup_by_email(db, str(user_info.email))
            if user is not None:
                if not user.social_provider and not user.social_id:
                    # Backfill so step 1 works on all future logins.
                    user.social_provider = user_info.provider
                    user.social_id = user_info.provider_id
                    await db.commit()
                elif (
                    user.social_provider != user_info.provider
                    or user.social_id != user_info.provider_id
                ):
                    raise AuthenticationException(
                        "This email is already linked to a different sign-in "
                        "method. Please use your original sign-in method."
                    )

        # ── Step 3: create new user ──────────────────────────────────────
        if user is None:
            if not user_info.email:
                raise AuthenticationException(
                    "Cannot create a new account without an email address. "
                    "This can happen on repeat Apple sign-ins before the "
                    "account exists in our system. Please use Apple Sign-In "
                    "from a fresh session (so Apple includes your email) or "
                    "sign in with email/password or Google."
                )

            email_str = str(user_info.email).lower()
            username = await self._unique_username(
                db, email_str.split("@")[0]
            )
            full_name = (
                user_info.name
                or " ".join(
                    filter(None, [user_info.first_name, user_info.last_name])
                )
                or None
            )

            # Pass hashed_password directly (not "password") so User.__init__
            # skips get_password_hash / validate_password_strength.
            # "!" is an impossible bcrypt hash — verify_password() always returns
            # False for it, so there is no way to authenticate as this user via
            # password-based login.
            user = User(
                email=email_str,
                username=username,
                hashed_password="!",
                full_name=full_name,
                is_active=True,
                is_verified=True,
                is_superuser=False,
                is_email_verified=True,
                social_provider=user_info.provider,
                social_id=user_info.provider_id,
                has_completed_onboarding=False,
            )

            db.add(user)
            await db.commit()
            await db.refresh(user)

        # ── Active guard (all paths) ─────────────────────────────────────
        if not user.is_active:
            raise AuthenticationException("This account has been deactivated")

        # ── Generate JWTs ─────────────────────────────────────────────────
        access_token = create_access_token(subject=str(user.id))
        refresh_token = create_refresh_token(subject=str(user.id))

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": {
                "id": str(user.id),
                "email": user.email,
                "username": user.username,
                "full_name": user.full_name or "",
                "is_active": user.is_active,
                "is_verified": user.is_verified,
                "has_completed_onboarding": user.has_completed_onboarding,
                "subscription_tier": str(
                    getattr(user, "subscription_tier", "free")
                ),
                "created_at": (
                    user.created_at.isoformat() if user.created_at else None
                ),
            },
            "token_type": "bearer",
        }

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------

    async def handle_social_login(
        self, provider: str, token: str, db: AsyncSession
    ) -> dict:
        """Verify provider token and authenticate/create the user."""
        if provider == "google":
            user_info = await self.verify_google_token(token)
        elif provider == "apple":
            user_info = await self.verify_apple_token(token)
        else:
            raise AuthenticationException(
                f"Unsupported social provider: {provider}"
            )
        return await self.authenticate_social_user(user_info, db)
