from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple

import secrets

from fastapi import HTTPException, status, Request # Request might be used by authenticate_user
# OAuth2PasswordBearer is typically for endpoint dependency, might not be used directly by service methods after refactor
# from fastapi.security import OAuth2PasswordBearer 
from jose import jwt, JWTError
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.constants import ROLE_PERMISSIONS, Roles # Assuming Roles is defined here
from app.core.exceptions import AuthenticationException, AuthorizationException, ValidationException, EmailError, NotFoundException
from app.core.logging import logger
# User model for type hinting and ORM interaction, though user_service will often be the interface
from app.models.user import User as DBUser 
from app.schemas.user import User # Pydantic User schema for returns
from app.schemas.token import TokenPayload
from app.services.user_service import UserService
from app.services.email_service import EmailService # Correctly imported, methods are static
from app.core.security import create_email_verification_token, verify_email_verification_token_and_get_email, create_password_reset_token, verify_password_reset_token
from app.core.security import (
    verify_password,
    track_login_attempt,
    create_access_token,
    create_refresh_token,
    verify_token_payload,
    is_token_blacklisted,
    blacklist_token,
    get_password_hash,
)

# oauth2_scheme = OAuth2PasswordBearer(
# tokenUrl=f"{settings.API_V1_STR}/auth/login"
# ) # This is for endpoint dependency, not directly for service class

from app.schemas.user import UserUpdate


class AuthService:
    """Enhanced authentication service with security features."""

    def __init__(self, db: AsyncSession, user_service: UserService, email_service: EmailService, redis_client=None):
        self.db = db
        self.user_service = user_service
        self.email_service = email_service
        self.redis_client = redis_client

    async def authenticate_user(
        self, request: Request, email: str, password: str
    ) -> Tuple[Optional[DBUser], bool, bool]:
        """
        Authenticate a user with email and password with rate limiting protection.
        IP from request is used for logging.
        """
        client_ip = request.client.host if request.client else "unknown"

        from app.core.redis import get_redis
        from app.core.security import is_account_locked
        redis_client = get_redis()

        # Read-only lockout check — does NOT increment failed attempts
        if is_account_locked(email.lower(), redis_client):
            logger.warning(
                "Account locked due to too many failed attempts",
                extra={
                    "email": email, "ip": client_ip,
                    "request_id": getattr(request.state, "request_id", None)
                }
            )
            return None, True, False

        stmt = select(DBUser).filter(DBUser.email == email.lower())
        result = await self.db.execute(stmt)
        user: Optional[DBUser] = result.scalars().first()

        if not user:
            # Track failed attempt AFTER we know it's a failure
            track_login_attempt(email.lower(), success=False, redis_client=redis_client)
            logger.warning(
                "Login attempt with non-existent user",
                extra={
                    "email": email, "ip": client_ip,
                    "request_id": getattr(request.state, "request_id", None)
                }
            )
            return None, False, False

        if not verify_password(password, user.hashed_password):
            # Track failed attempt AFTER we know password is wrong
            track_login_attempt(email.lower(), success=False, redis_client=redis_client)
            logger.warning(
                "Failed login attempt",
                extra={
                    "user_id": user.id, "email": email, "ip": client_ip,
                    "request_id": getattr(request.state, "request_id", None)
                }
            )
            return None, False, False

        track_login_attempt(email.lower(), success=True, redis_client=redis_client) # Reset failed attempts

        logger.info(
            "Successful login",
            extra={
                "user_id": user.id, "email": email, "ip": client_ip,
                "request_id": getattr(request.state, "request_id", None)
            }
        )

        # Instead of direct DB update for last_login, use UserService
        try:
            await self.user_service.update_user_async(
                user_id=user.id, 
                user_in=UserUpdate(last_login=datetime.utcnow()) # Pass only last_login
            )
            # Refresh the user object if needed, though update_user_async might return the updated one
            # For this flow, the original user object is returned, and UserService handles the update side effect.
        except Exception as e_update:
            # Log error but don't fail authentication for this, as it's a secondary update
            logger.error(f"Failed to update last_login for user {user.id}: {e_update}", exc_info=True)

        return user, False, True

    async def get_current_user(self, token: str) -> DBUser:
        """Get the current authenticated user from a token."""
        try:
            if is_token_blacklisted(token, self.redis_client):
                raise AuthenticationException("Token is blacklisted or revoked")

            payload = jwt.decode(
                token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
            )
            token_data = TokenPayload(**payload)

            if datetime.fromtimestamp(token_data.exp) < datetime.utcnow():
                raise AuthenticationException("Token has expired")

            if "type" in payload and payload["type"] != "access":
                raise AuthenticationException("Invalid token type")

        except (JWTError, ValidationError) as e:
            logger.warning("Token validation error", extra={"error": str(e)})
            raise AuthenticationException("Could not validate credentials")

        user: Optional[DBUser] = await self.user_service.get_by_id_async(str(token_data.sub)) # Use UserService
        
        if not user:
            raise AuthenticationException("User not found")
        if not user.is_active:
            raise AuthenticationException("User account is disabled")
            
        return user

    async def get_current_active_user(self, current_user: DBUser) -> DBUser:
        """Get the current active user (expects an already resolved user object)."""
        if not current_user.is_active:
            raise AuthenticationException("Inactive user account")
        return current_user

    async def check_permission(
        self, current_user: DBUser, required_permission: str = None
    ) -> DBUser:
        """Check if user has the required permission (expects resolved user object)."""
        if required_permission is None:
            return current_user

        # Assuming current_user.role is compatible with Roles enum/values
        # And ROLE_PERMISSIONS is a dict like {role_enum_or_str: [permission_str]}
        role_permissions = ROLE_PERMISSIONS.get(current_user.role, []) 

        if current_user.role == Roles.ADMIN or required_permission in role_permissions:
            return current_user

        logger.warning(
            "Permission denied",
            extra={
                "user_id": current_user.id,
                "required_permission": required_permission,
                "user_role": current_user.role,
            },
        )
        raise AuthorizationException("Not enough permissions")

    async def generate_tokens(self, user_id: Any, user_role: str = None) -> Dict[str, Any]:
        """Generate access and refresh tokens for a user."""
        additional_data = {}
        if user_role:
            additional_data["role"] = user_role
        
        token_id = secrets.token_hex(16) # jti for revocation
        additional_data["jti"] = token_id

        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            subject=str(user_id), expires_delta=access_token_expires
        )
        refresh_token = create_refresh_token(subject=str(user_id))

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        }

    async def send_verification_email(self, email: str) -> None:
        """Sends an email verification link to the user if not already verified."""
        # Early-exit when SMTP is not configured — avoids a silent SMTP auth failure.
        if not settings.emails_enabled:
            logger.warning(
                "Skipping verification email — SMTP credentials are missing or still "
                "placeholder values. Set MAIL_USERNAME / MAIL_PASSWORD in backend/.env. "
                "For Gmail use an App Password (myaccount.google.com/apppasswords). "
                "For Resend set MAIL_SERVER=smtp.resend.com, MAIL_USERNAME=resend, "
                "MAIL_PASSWORD=re_<your_key>.",
                extra={"email": email},
            )
            return

        user_db_obj = await self.user_service.get_by_email_async(email)
        if not user_db_obj:
            logger.debug("Verification email requested for unknown address")
            return

        if user_db_obj.is_email_verified:
            logger.debug("Verification email requested but address already verified")
            return

        token = create_email_verification_token(email)
        verify_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"

        try:
            sent = await EmailService.send_verification_email(
                user=user_db_obj,
                verification_url=verify_url,
                verification_code=token,
            )
            if sent:
                logger.info(f"Verification email sent to {email}")
            else:
                # EmailService.send_email caught the SMTP error and returned False.
                # The detailed error (server, username, hint) is already in the log from there.
                logger.warning(
                    "Verification email was NOT delivered — SMTP returned False. "
                    "Check earlier log lines for the SMTP error details.",
                    extra={"email": email},
                )
        except Exception as e:
            logger.error(f"Unexpected error sending verification email to {email}: {str(e)}")
            raise EmailError(f"Failed to send verification email: {str(e)}")


    async def verify_email(self, token: str) -> None:
        """Verifies a user's email address using a verification token."""
        try:
            email_from_token = verify_email_verification_token_and_get_email(token, self.redis_client)  # Bug 3 fixed: pass redis_client
            if not email_from_token:
                raise ValidationException("Invalid verification token: no email")
        except (JWTError, ValidationException) as e:
            logger.warning(f"Email verification failed: Invalid token. Error: {str(e)}")
            raise ValidationException(f"Invalid or expired verification token: {str(e)}")

        user = await self.user_service.get_by_email_async(email_from_token)
        if not user:
            logger.warning(f"Email verification failed: User not found for email {email_from_token}")
            raise NotFoundException("User not found from verification token.")

        if user.is_email_verified:
            logger.info(f"Email {user.email} already verified.")
            # Burn the token even if already verified — prevent any future reuse
            blacklist_token(token, self.redis_client)
            return

        try:
            await self.user_service.update_async(
                db_obj=user,
                obj_in={"is_email_verified": True}
            )
            # Burn the token after successful verification — one-time use
            blacklist_token(token, self.redis_client)
            logger.info(f"Email {user.email} successfully verified.")
        except Exception as e:
            logger.error(f"Email verification: failed to update user {user.email}. Error: {str(e)}")
            raise ValidationException(f"Could not update user during email verification: {str(e)}")

    async def verify_email_with_token(self, token: str) -> None:
        """Called by POST /verify-email/confirm. Delegates to verify_email()."""
        await self.verify_email(token)

    async def request_email_verification(self, email: str) -> None:
        """
        Unauthenticated resend of verification email.
        Always returns silently — does not reveal whether email exists.
        send_verification_email() handles non-existent + already-verified silently.
        """
        await self.send_verification_email(email)

    async def request_password_reset(self, email: str) -> None:
        """Handles a request to reset a user's password."""
        user_db_obj = await self.user_service.get_by_email_async(email)
        if not user_db_obj:
            logger.debug("Password reset requested for unknown address")
            return

        token = create_password_reset_token(email=user_db_obj.email) 
        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"
        expire_hours = settings.PASSWORD_RESET_TOKEN_EXPIRE_HOURS

        try:
            # Call the static method on EmailService
            # EmailService.send_password_reset_email expects user, reset_url, reset_code, expire_hours
            await EmailService.send_password_reset_email(
                user=user_db_obj, # Pass the DBUser object
                reset_url=reset_url,
                reset_code=token, # The token itself can serve as the code
                expire_hours=expire_hours
            )
            logger.info(f"Password reset email sent to {user_db_obj.email}")
        except Exception as e:
            logger.error(f"Failed to send password reset email to {user_db_obj.email}: {str(e)}")
            raise EmailError(f"Failed to send password reset email: {str(e)}")

    async def confirm_password_reset(self, token: str, new_password: str) -> User:
        """Confirms a password reset attempt using a token and sets a new password."""
        try:
            email_from_token = verify_password_reset_token(token, self.redis_client)
            if not email_from_token:
                raise ValidationException("Invalid password reset token: no email")
        except (JWTError, ValidationException) as e:
            logger.warning(f"Password reset failed: Invalid token. Error: {str(e)}")
            raise ValidationException(f"Invalid or expired password reset token: {str(e)}")

        # Burn the token immediately — prevent replay before the password write commits
        blacklist_token(token, self.redis_client)

        user_db_obj = await self.user_service.get_by_email_async(email_from_token)
        if not user_db_obj:
            logger.warning(f"Password reset failed: User not found for email {email_from_token} from token.")
            raise NotFoundException("User not found from password reset token.")

        if not user_db_obj.is_active:
            logger.warning(f"Password reset attempt for inactive user: {user_db_obj.email}")
            raise AuthenticationException("Cannot reset password for an inactive account.")

        hashed_password = get_password_hash(new_password)
        try:
            updated_user = await self.user_service.update_async(
                db_obj=user_db_obj,
                obj_in={"hashed_password": hashed_password}
            )
            if not updated_user:
                 logger.error(f"Failed to update password for user {user_db_obj.email}.")
                 raise ValidationException("Failed to update password.")
            logger.info(f"Password successfully reset for user {user_db_obj.email}")
            # Any post-password-reset actions, like invalidating old sessions, could go here or be a separate step.
            return updated_user
        except Exception as e:
            logger.error(f"Password reset: failed to update user {user_db_obj.email}. Error: {str(e)}")
            raise ValidationException(f"Could not update password during reset: {str(e)}")

    async def refresh_access_token(self, refresh_token_str: str) -> Dict[str, Any]:
        """Refreshes an access token using a valid refresh token."""
        try:
            # Use verify_token_payload for refresh tokens
            payload = verify_token_payload(
                token=refresh_token_str,
                redis_client=self.redis_client,
                expected_token_type="refresh"
            )
            if not payload:
                logger.warning("Refresh token verification failed or token is invalid/blacklisted.")
                raise AuthenticationException("Invalid refresh token")

            user_id = payload.get("sub")
            if not user_id:
                logger.error("User ID (sub) not found in refresh token payload.")
                raise AuthenticationException("Invalid refresh token payload")

            # Check if the user account is still valid and active
            user = await self.user_service.get_by_id_async(user_id)
            if not user:
                logger.warning(f"User {user_id} from refresh token not found.")
                raise AuthenticationException("User not found")
            if not user.is_active:
                logger.warning(f"User {user_id} from refresh token is inactive.")
                raise AuthenticationException("User account is inactive")

            # Rotate: issue new access + refresh tokens, blacklist the old refresh token
            access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
            new_access_token = create_access_token(
                subject=str(user_id),
                expires_delta=access_token_expires,
            )
            new_refresh_token = create_refresh_token(subject=str(user_id))

            # Blacklist the consumed refresh token — prevents reuse
            blacklist_token(
                refresh_token_str,
                self.redis_client,
                expires_in_seconds=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
            )

            logger.info(f"Tokens rotated for user {user_id}")
            return {
                "access_token": new_access_token,
                "refresh_token": new_refresh_token,
                "token_type": "bearer",
                "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                "user_id": str(user_id),
            }

        except AuthenticationException: # Re-raise specific auth exceptions
            raise
        except (JWTError, ValidationError) as e:
            logger.error(f"Error refreshing access token: {str(e)}", exc_info=True)
            raise AuthenticationException("Invalid refresh token")
        except Exception as e:
            logger.error(f"Unexpected error refreshing access token: {str(e)}", exc_info=True)
            raise AuthenticationException("Could not refresh access token")

# Note: Further steps involve updating dependencies (deps.py) and calling code (endpoints/auth.py)
# and then deleting the old core/auth.py file.
