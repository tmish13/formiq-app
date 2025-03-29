"""User service for authentication and user management."""
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from fastapi import Depends

from app.core.database import get_db
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token
)
from app.core.config import settings
from app.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ValidationError,
    NotFoundException,
    UserAlreadyExists,
    InvalidCredentials
)
from app.models.user import User
from app.schemas.user import (
    UserCreate,
    UserUpdate,
    UserFilter,
    UserResponse,
    TokenResponse
)
from app.repositories.user_repository import UserRepository
from app.services.base import BaseService
from app.core.email import send_email
from app.core.logging import logger

class UserService(BaseService[User, UserCreate, UserUpdate, UserFilter]):
    """
    User service with authentication and authorization.
    
    Features:
    - User registration and verification
    - Authentication and token management
    - Password reset and update
    - User profile management
    - Role-based authorization
    """
    
    def __init__(self):
        super().__init__(
            repository=UserRepository,
            model=User,
            create_schema=UserCreate,
            update_schema=UserUpdate,
            filter_schema=UserFilter
        )

    async def register(self, db: Session, data: dict) -> User:
        """Register a new user."""
        # Check if user exists
        if await self.get_by_email(db, data["email"]):
            raise UserAlreadyExists("Email already registered")

        # Create user
        user = User(
            email=data["email"],
            hashed_password=get_password_hash(data["password"]),
            full_name=data["full_name"],
            is_active=True,
            is_verified=False
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    async def authenticate(self, db: Session, email: str, password: str) -> dict:
        """Authenticate user and return tokens."""
        user = await self.get_by_email(db, email)
        if not user or not verify_password(password, user.hashed_password):
            raise InvalidCredentials("Invalid email or password")
        
        if not user.is_active:
            raise InvalidCredentials("User is inactive")
        
        if not user.is_verified:
            raise InvalidCredentials("Email not verified")

        return {
            "access_token": create_access_token(user.id),
            "refresh_token": create_refresh_token(user.id),
            "token_type": "bearer"
        }

    async def verify_email(self, db: Session, token: str) -> None:
        """Verify user's email."""
        user = await self.get_by_verification_token(db, token)
        if not user:
            raise InvalidCredentials("Invalid verification token")
        
        user.is_verified = True
        user.verification_token = None
        user.verification_token_expires = None
        await db.commit()

    async def refresh_token(self, db: Session, refresh_token: str) -> dict:
        """Refresh access token using refresh token."""
        user = await self.get_by_refresh_token(db, refresh_token)
        if not user:
            raise InvalidCredentials("Invalid refresh token")
        
        return {
            "access_token": create_access_token(user.id),
            "refresh_token": create_refresh_token(user.id),
            "token_type": "bearer"
        }

    async def request_password_reset(self, db: Session, email: str) -> None:
        """Request password reset."""
        user = await self.get_by_email(db, email)
        if user:
            # Generate reset token
            user.reset_token = create_refresh_token(user.id)
            user.reset_token_expires = datetime.utcnow() + timedelta(hours=24)
            await db.commit()
            
            # Send reset email (implement email sending)

    async def reset_password(self, db: Session, token: str, new_password: str) -> None:
        """Reset password using token."""
        user = await self.get_by_reset_token(db, token)
        if not user:
            raise InvalidCredentials("Invalid reset token")
        
        user.hashed_password = get_password_hash(new_password)
        user.reset_token = None
        user.reset_token_expires = None
        await db.commit()

    async def get_by_email(self, db: Session, email: str) -> Optional[User]:
        """Get user by email."""
        return await db.query(User).filter(User.email == email).first()

    async def get_by_verification_token(self, db: Session, token: str) -> Optional[User]:
        """Get user by verification token."""
        return await db.query(User).filter(
            User.verification_token == token,
            User.verification_token_expires > datetime.utcnow()
        ).first()

    async def get_by_refresh_token(self, db: Session, token: str) -> Optional[User]:
        """Get user by refresh token."""
        return await db.query(User).filter(
            User.refresh_token == token,
            User.refresh_token_expires > datetime.utcnow()
        ).first()

    async def get_by_reset_token(self, db: Session, token: str) -> Optional[User]:
        """Get user by reset token."""
        return await db.query(User).filter(
            User.reset_token == token,
            User.reset_token_expires > datetime.utcnow()
        ).first()

    async def update_password(
        self,
        db: Session = Depends(get_db),
        *,
        user_id: UUID,
        current_password: str,
        new_password: str
    ) -> User:
        """
        Update user's password.
        
        Args:
            db: Database session
            user_id: User's ID
            current_password: Current password
            new_password: New password
        """
        try:
            user = await self.get(db, id=user_id)
            
            # Verify current password
            if not verify_password(current_password, user.hashed_password):
                raise ValidationError("Invalid current password")
            
            # Update password
            return await self.update(
                db,
                id=user_id,
                data={"hashed_password": get_password_hash(new_password)}
            )
        except Exception as e:
            logger.error("Error in password update", exc_info=e)
            raise

    async def update_profile(
        self,
        db: Session = Depends(get_db),
        *,
        user_id: UUID,
        data: Dict[str, Any]
    ) -> User:
        """
        Update user's profile.
        
        Args:
            db: Database session
            user_id: User's ID
            data: Profile update data
        """
        try:
            # Ensure email uniqueness if being updated
            if "email" in data:
                existing = self.repository.get_by_email(db, email=data["email"])
                if existing and existing.id != user_id:
                    raise ValidationError("Email already taken")
            
            return await self.update(db, id=user_id, data=data)
        except Exception as e:
            logger.error("Error in profile update", exc_info=e)
            raise

    def _generate_token(self, length: int = 32) -> str:
        """Generate a random token."""
        import secrets
        return secrets.token_urlsafe(length)

    async def _send_verification_email(self, user: User) -> None:
        """Send verification email to user."""
        try:
            await send_email(
                to_email=user.email,
                subject="Verify your email",
                template="verification",
                context={
                    "name": user.full_name,
                    "url": f"{settings.FRONTEND_URL}/verify-email?token={user.verification_token}"
                }
            )
        except Exception as e:
            logger.error("Error sending verification email", exc_info=e)
            raise

    async def _send_reset_email(self, user: User, token: str) -> None:
        """Send password reset email to user."""
        try:
            await send_email(
                to_email=user.email,
                subject="Reset your password",
                template="reset_password",
                context={
                    "name": user.full_name,
                    "url": f"{settings.FRONTEND_URL}/reset-password?token={token}"
                }
            )
        except Exception as e:
            logger.error("Error sending reset email", exc_info=e)
            raise 