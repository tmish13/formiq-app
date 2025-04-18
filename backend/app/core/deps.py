"""Dependency injection module."""
from typing import Generator, Optional, AsyncGenerator, Dict, Any, Union
from uuid import UUID
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.token import ALGORITHM
from app.core.security import get_current_user, get_current_active_user
from app.db.session import async_session, SessionLocal, get_db
from app.models.user import User
from app.models.form_check import FormCheck, FeedbackItem
from app.models.enums import SubscriptionTier
from app.repositories.user_repository import UserRepository
from app.repositories.form_check_repository import FormCheckRepository
from app.repositories.feedback_repository import FeedbackRepository
from app.schemas.token import TokenPayload

# OAuth2 password bearer for token authentication
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login"
)

# Dictionary to store application dependencies
dependencies: Dict[str, Any] = {}

# Async database dependency
async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session."""
    async with async_session() as session:
        yield session


# Sync database dependency
def get_db() -> Generator[Session, None, None]:
    """Get sync database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Auth dependencies
async def get_current_user(token: str = Depends(oauth2_scheme)):
    """Get current user from token."""
    # This is a placeholder function
    return {"id": "123", "email": "user@example.com"}


# Get current user for sync operations
def get_current_user_sync(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
) -> User:
    """Get current user for synchronous operations."""
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[ALGORITHM]
        )
        token_data = TokenPayload(**payload)
    except (JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    user_repo = UserRepository(db)
    user = user_repo.get_by_email(email=token_data.sub)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def get_current_active_user(current_user = Depends(get_current_user)):
    """Get current active user."""
    # This is a placeholder function
    return current_user


# Get current active user for sync operations
def get_current_active_user_sync(
    current_user: User = Depends(get_current_user_sync),
) -> User:
    """Get current active user for synchronous operations."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )
    return current_user


async def get_current_active_superuser(current_user = Depends(get_current_user)):
    """Get current active superuser."""
    # This is a placeholder function
    return current_user


async def check_subscription_tier(required_tier: str, current_user = Depends(get_current_user)):
    """Check if user has required subscription tier."""
    # This is a placeholder function
    return True


async def validate_form_check_access(form_check_id: str, current_user = Depends(get_current_user)):
    """Validate user has access to form check."""
    # This is a placeholder function
    return True


async def validate_feedback_access(feedback_id: str, current_user = Depends(get_current_user)):
    """Validate user has access to feedback."""
    # This is a placeholder function
    return True 