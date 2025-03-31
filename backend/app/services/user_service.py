"""User service module."""
from typing import Optional, List
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from fastapi import Depends
from jose import jwt

from app.core.config import settings
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token
)
from app.core.exceptions import (
    AuthenticationException,
    ValidationException,
    NotFoundException
)
from app.repositories.user_repository import UserRepository
from app.schemas.user import (
    UserCreate,
    UserUpdate,
    User,
    UserFilter,
    UserInDB
)
from app.schemas.token import Token

class UserService:
    """User service class."""

    def __init__(self, db: Session):
        """Initialize user service.

        Args:
            db: Database session
        """
        self.repository = UserRepository(db)

    def get(self, db: Session, user_id: UUID) -> Optional[User]:
        """Get a user by ID."""
        user = self.repository.get(db, user_id)
        if not user:
            raise NotFoundException("User not found")
        return User.from_orm(user)

    def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email.

        Args:
            email: User email

        Returns:
            User if found, None otherwise
        """
        return self.repository.get_by_email(email)

    def get_by_id(self, user_id: int) -> Optional[User]:
        """Get user by id.

        Args:
            user_id: User id

        Returns:
            User if found, None otherwise
        """
        return self.repository.get_by_id(user_id)

    def get_all(self) -> List[User]:
        """Get all users.

        Returns:
            List of users
        """
        return self.repository.get_all()

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

    def create(self, user_in: UserCreate) -> User:
        """Create new user.

        Args:
            user_in: User create schema

        Returns:
            Created user
        """
        user = User(
            email=user_in.email,
            hashed_password=get_password_hash(user_in.password),
            full_name=user_in.full_name,
            is_active=True,
        )
        return self.repository.create(user)

    def update(self, user: User, user_in: UserUpdate) -> User:
        """Update user.

        Args:
            user: User to update
            user_in: User update schema

        Returns:
            Updated user
        """
        update_data = user_in.dict(exclude_unset=True)
        if update_data.get("password"):
            hashed_password = get_password_hash(update_data["password"])
            del update_data["password"]
            update_data["hashed_password"] = hashed_password
        return self.repository.update(user, update_data)

    def delete(self, db: Session, *, user_id: UUID) -> User:
        """Delete a user."""
        user = self.repository.delete(db, id=user_id)
        if not user:
            raise NotFoundException("User not found")
        return User.from_orm(user)

    def authenticate(self, email: str, password: str) -> Optional[User]:
        """Authenticate user.

        Args:
            email: User email
            password: User password

        Returns:
            User if authentication successful, None otherwise
        """
        user = self.get_by_email(email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

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