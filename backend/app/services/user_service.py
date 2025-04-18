"""User service module."""
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt
from fastapi import Depends, HTTPException, status

from app.core.config import settings
from app.core.token import (
    create_access_token,
    create_refresh_token,
    create_email_verification_token,
    verify_email_token
)
from app.core.exceptions import (
    AuthenticationException,
    ValidationException,
    NotFoundException,
    EmailError,
    ValidationError
)
from app.repositories.user_repository import UserRepository, get_user_repository
from app.schemas.user import (
    UserCreate,
    UserUpdate,
    User,
    UserFilter,
    UserInDB
)
from app.schemas.token import Token
from app.services.email_service import EmailService
from app.core.database import get_db
from app.core.password import get_password_hash, verify_password
from app.models.user import User as DBUser
from app.services.base import BaseService

class UserService:
    """User service."""
    
    def __init__(self, repository: UserRepository):
        """Initialize service with repository."""
        self.repository = repository
        self._is_async = isinstance(repository.db, AsyncSession)

    def get(self, db: Session, user_id: UUID) -> Optional[User]:
        """Get a user by ID."""
        user = self.repository.get(db, user_id)
        if not user:
            raise NotFoundException("User not found")
        return User.from_orm(user)

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        return await self.repository.get_by_email(email)

    async def get_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        return await self.repository.get_by_id(user_id)

    async def get_all(self) -> List[User]:
        """Get all users."""
        return await self.repository.get_all()

    def get_multi(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[UserFilter] = None
    ) -> List[User]:
        """Get multiple users."""
        users = self.repository.get_multi(db, skip=skip, limit=limit)
        return [User.from_orm(user) for user in users]

    async def create(self, user_data: UserCreate, is_superuser: bool = False) -> User:
        """Create a new user.

        Args:
            user_data: User create schema
            is_superuser: Whether the user should be a superuser (default: False)

        Returns:
            Created user
        """
        # Hash the password
        hashed_password = get_password_hash(user_data.password)
        
        # Create a modified user object with hashed password
        user_data_dict = user_data.dict()
        user_data_dict["password"] = hashed_password
        user_data_dict["is_superuser"] = is_superuser
        
        # Create new user with modified data
        return await self.repository.create(UserCreate(**user_data_dict))

    async def update(self, user_id: str, user_data: Dict[str, Any]) -> Optional[User]:
        """Update a user."""
        # Handle password hashing if password is provided
        if "password" in user_data:
            user_data["password"] = get_password_hash(user_data["password"])
            
        # Update user with processed data
        update_data = UserUpdate(**user_data)
        return await self.repository.update(user_id, update_data)

    async def delete(self, user_id: str) -> bool:
        """Delete a user."""
        return await self.repository.delete(user_id)

    async def authenticate(
        self,
        email: str,
        password: str,
        device_info: Optional[Dict[str, Any]] = None
    ) -> Optional[User]:
        """Authenticate a user.
        
        Args:
            email: User's email
            password: User's password
            device_info: Optional device information for session tracking
            
        Returns:
            Optional[User]: Authenticated user or None
            
        Raises:
            AuthenticationException: If authentication fails
        """
        try:
            # Get user by email
            user = await self.get_by_email(email)
            if not user:
                # Use constant time comparison to prevent timing attacks
                verify_password("dummy", "dummy")
                return None
            
            # Check if account is locked
            if user.locked_until and user.locked_until > datetime.utcnow():
                raise AuthenticationException(
                    "Account is locked. Try again later.",
                    retry_after=int((user.locked_until - datetime.utcnow()).total_seconds())
                )
            
            # Verify password
            if not verify_password(password, user.hashed_password):
                # Increment failed attempts
                failed_attempts = user.failed_login_attempts + 1
                lock_data = {}
                
                # Lock account after 5 failed attempts
                if failed_attempts >= 5:
                    lock_duration = timedelta(minutes=15)  # 15 minutes lockout
                    lock_data["locked_until"] = datetime.utcnow() + lock_duration
                
                # Update user
                await self.repository.update(
                    user.id,
                    {
                        "failed_login_attempts": failed_attempts,
                        **lock_data
                    }
                )
                
                return None
            
            # Authentication successful - update user
            await self.repository.update(
                user.id,
                {
                    "last_login": datetime.utcnow(),
                    "failed_login_attempts": 0,
                    "locked_until": None
                }
            )
            
            return user
            
        except Exception as e:
            logger.error(f"Authentication failed: {str(e)}")
            raise AuthenticationException("Authentication failed")

    def is_active(self, user: User) -> bool:
        """Check if user is active.

        Args:
            user: User to check

        Returns:
            True if user is active, False otherwise
        """
        return user.is_active

    def create_access_token(self, *, user_id: UUID, expires_delta: Optional[timedelta] = None) -> Token:
        """Create access token for user."""
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode = {"exp": expire, "sub": str(user_id)}
        access_token = create_access_token(data=to_encode)
        refresh_token = create_refresh_token(data=to_encode)
        
        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer"
        )

    def refresh_token(self, *, refresh_token: str) -> Token:
        """Refresh access token using refresh token."""
        try:
            payload = jwt.decode(
                refresh_token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM]
            )
            user_id = UUID(payload["sub"])
            return self.create_access_token(user_id=user_id)
        except (jwt.JWTError, ValueError):
            raise AuthenticationException("Invalid refresh token")

    async def send_verification_email(self, user: User) -> None:
        """Send email verification link to user.
        
        Args:
            user: User to send verification email to
            
        Raises:
            EmailError: If email sending fails
        """
        # Generate verification token
        token = create_email_verification_token(user.email)
        
        # Create verification URL
        verify_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"
        
        # Send email
        try:
            email_service = EmailService()
            await email_service.send_email(
                to_email=user.email,
                subject="Verify your FormIQ account",
                body=f"""
                <html>
                    <body>
                        <h2>Welcome to FormIQ!</h2>
                        <p>Please verify your email address by clicking the link below:</p>
                        <p><a href="{verify_url}">Verify Email</a></p>
                        <p>This link will expire in 24 hours.</p>
                        <p>If you did not create an account, please ignore this email.</p>
                        <p>Best regards,<br>The FormIQ Team</p>
                    </body>
                </html>
                """,
                is_html=True
            )
            logger.info(f"Sent verification email to {user.email}")
        except Exception as e:
            logger.error(f"Failed to send verification email: {str(e)}")
            raise EmailError(f"Failed to send verification email: {str(e)}")

    async def verify_email(self, token: str) -> None:
        """Verify user's email using verification token.
        
        Args:
            token: Email verification token
            
        Raises:
            ValidationError: If token is invalid or expired
        """
        try:
            # Verify token and get email
            email = verify_email_token(token)
            if not email:
                raise ValidationError("Invalid or expired verification token")
            
            # Get user by email
            user = await self.get_by_email(email)
            if not user:
                raise ValidationError("User not found")
            
            # Update user verification status
            user.is_verified = True
            user.verified_at = datetime.now()
            await self.repository.update(user.id, {"is_verified": True, "verified_at": user.verified_at})
            
            logger.info(f"Verified email for user {user.id}")
        except Exception as e:
            logger.error(f"Failed to verify email: {str(e)}")
            raise ValidationError(f"Failed to verify email: {str(e)}")

def get_user_service(
    repository: UserRepository = Depends(get_user_repository),
) -> UserService:
    """Get user service instance.
    
    Args:
        repository: User repository instance
        
    Returns:
        User service instance
    """
    return UserService(repository=repository)