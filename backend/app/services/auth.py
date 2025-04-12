"""Authentication service for handling user authentication and authorization."""
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any
import logging
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    verify_password_reset_token,
    create_password_reset_token,
    track_login_attempt,
    get_password_hash,
    create_session_token,
    verify_session_token,
    verify_refresh_token
)
from app.core.exceptions import AuthenticationException, ValidationException
from app.models.user import User
from app.schemas.token import Token, TokenPayload
from app.schemas.user import UserCreate, UserPasswordReset
from app.services.user_service import UserService
from app.services.session_service import SessionService
from app.core.monitoring import (
    track_failed_login,
    track_password_reset,
    track_email_verification,
    track_session_start
)

logger = logging.getLogger(__name__)

class AuthService:
    def __init__(
        self,
        db: Session,
        user_service: UserService,
        session_service: SessionService
    ):
        self.db = db
        self.user_service = user_service
        self.session_service = session_service

    async def authenticate_user(
        self, email: str, password: str
    ) -> Tuple[Optional[User], Optional[str]]:
        """
        Authenticate a user by email and password.
        Returns the user if authentication is successful, None otherwise.
        Also returns an error message if authentication fails.
        """
        user = await self.user_service.get_by_email(email)
        if not user:
            track_failed_login(email)
            return None, "Incorrect email or password"
        
        if not user.is_active:
            return None, "User account is inactive"
        
        if not user.verify_password(password):
            track_failed_login(email)
            return None, "Incorrect email or password"
        
        return user, None

    async def create_tokens(self, user: User) -> Token:
        """Create access and refresh tokens for a user."""
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        
        access_token = create_access_token(
            data={"sub": user.email},
            expires_delta=access_token_expires
        )
        refresh_token = create_refresh_token(
            data={"sub": user.email},
            expires_delta=refresh_token_expires
        )
        
        # Create a new session
        session = await self.session_service.create_session(user.id)
        
        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            session_id=session.id
        )

    async def refresh_access_token(self, refresh_token: str) -> Token:
        """Refresh an access token using a refresh token."""
        try:
            payload = verify_refresh_token(refresh_token)
            email: str = payload.get("sub")
            if email is None:
                raise AuthenticationException("Invalid refresh token")
            
            user = await self.user_service.get_by_email(email)
            if not user:
                raise AuthenticationException("User not found")
            
            if not user.is_active:
                raise AuthenticationException("User is inactive")
            
            return await self.create_tokens(user)
            
        except Exception as e:
            logger.error(f"Error refreshing token: {str(e)}")
            raise AuthenticationException("Invalid refresh token")

    async def reset_password(self, email: str) -> None:
        """Initiate password reset process."""
        user = await self.user_service.get_by_email(email)
        if user:
            token = create_password_reset_token(data={"sub": email})
            await self.user_service.send_password_reset_email(user, token)
            track_password_reset(email)

    async def confirm_password_reset(
        self, token: str, new_password: str
    ) -> None:
        """Confirm password reset with token."""
        try:
            email = verify_password_reset_token(token)
            user = await self.user_service.get_by_email(email)
            if not user:
                raise ValidationException("User not found")
            
            await self.user_service.update_password(user, new_password)
            track_password_reset(email)
            
        except Exception as e:
            logger.error(f"Error confirming password reset: {str(e)}")
            raise ValidationException("Invalid or expired reset token")

    async def verify_email(self, token: str) -> None:
        """Verify user email with token."""
        try:
            email = verify_password_reset_token(token)
            user = await self.user_service.get_by_email(email)
            if not user:
                raise ValidationException("User not found")
            
            if user.is_verified:
                raise ValidationException("Email already verified")
            
            await self.user_service.verify_email(user)
            track_email_verification(email)
            
        except Exception as e:
            logger.error(f"Error verifying email: {str(e)}")
            raise ValidationException("Invalid or expired verification token")

    async def logout(self, session_id: str) -> None:
        """Logout user by invalidating their session."""
        await self.session_service.invalidate_session(session_id)

    async def logout_all(self, user_id: int) -> None:
        """Logout user from all devices by invalidating all their sessions."""
        await self.session_service.invalidate_all_sessions(user_id) 