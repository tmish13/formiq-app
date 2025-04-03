"""User service module."""
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
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
from app.api import deps

class UserService:
    """User service."""
    
    def __init__(self, db: Session = Depends(deps.get_db)):
        """Initialize service with repository."""
        self.repository = UserRepository(db)
        self._is_async = isinstance(db, AsyncSession)

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

    async def create(self, user_data: UserCreate) -> User:
        """Create a new user."""
        # Hash the password
        hashed_password = get_password_hash(user_data.password)
        
        # Create a modified user object with hashed password
        user_data_dict = user_data.dict()
        user_data_dict["password"] = hashed_password
        
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

    async def authenticate(self, email: str, password: str) -> Optional[User]:
        """Authenticate a user."""
        user = await self.get_by_email(email)
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