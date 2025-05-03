"""Dependency injection module."""
from typing import Generator, Optional, AsyncGenerator, Dict, Any, Union
from uuid import UUID
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from datetime import datetime

from app.core.config import settings
from app.core.token import ALGORITHM
from app.core.database import get_async_db as core_get_async_db
from app.core.database import SessionLocal
from app.models.user import User
from app.models.form_check import FormCheck, FeedbackItem
from app.models.enums import SubscriptionTier
from app.schemas.token import TokenPayload

# OAuth2 password bearer for token authentication
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login"
)

# Dictionary to store application dependencies
dependencies: Dict[str, Any] = {}

# Async database dependency
async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session using the core function."""
    async for session in core_get_async_db():
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
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_async_db)
) -> User:
    """
    Get current authenticated user based on JWT token.
    
    Args:
        token: JWT access token from Authorization header
        db: Database session
        
    Returns:
        User model instance
        
    Raises:
        HTTPException: If token is invalid or user not found
    """
    try:
        # Decode the JWT token
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[ALGORITHM]
        )
        token_data = TokenPayload(**payload)
        
        # Check token expiration
        if token_data.exp is not None and token_data.exp < datetime.timestamp(datetime.utcnow()):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        # Get user ID from token
        user_id = token_data.sub
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except (JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user from repository
    # This will be deferred until we have properly finished loading all dependencies
    # Use a dependency function that will be registered later
    from app.repositories.user_repository import UserRepository
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id_async(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


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
    
    from app.repositories.user_repository import UserRepository
    user_repo = UserRepository(db)
    user = user_repo.get_by_id(token_data.sub)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Get current active user.
    
    Args:
        current_user: User model instance from get_current_user dependency
        
    Returns:
        User model instance if active
        
    Raises:
        HTTPException: If user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
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


async def get_current_active_superuser(current_user: User = Depends(get_current_user)) -> User:
    """
    Get current active superuser.
    
    Args:
        current_user: User model instance from get_current_user dependency
        
    Returns:
        User model instance if active and superuser
        
    Raises:
        HTTPException: If user is not a superuser
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges",
        )
    return current_user


async def check_subscription_tier(required_tier: SubscriptionTier, current_user: User = Depends(get_current_user)) -> bool:
    """
    Check if user has required subscription tier.
    
    Args:
        required_tier: Required subscription tier
        current_user: User model instance from get_current_user dependency
        
    Returns:
        True if user has required tier or higher
        
    Raises:
        HTTPException: If user doesn't have required tier
    """
    user_tier = current_user.subscription_tier or SubscriptionTier.FREE
    
    if user_tier.value < required_tier.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"This feature requires a {required_tier.name} subscription",
        )
    return True


async def validate_form_check_access(form_check_id: UUID, current_user: User = Depends(get_current_user)) -> FormCheck:
    """
    Validate user has access to form check.
    
    Args:
        form_check_id: Form check ID
        current_user: User model instance from get_current_user dependency
        
    Returns:
        FormCheck model instance if user has access
        
    Raises:
        HTTPException: If user doesn't have access to form check
    """
    from app.repositories.form_check_repository import FormCheckRepository
    
    # Get form check
    form_check_repo = FormCheckRepository(AsyncSession)
    form_check = await form_check_repo.get_by_id_async(form_check_id)
    
    if not form_check:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Form check not found",
        )
    
    # Check if user is owner or has admin privileges
    if form_check.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this form check",
        )
        
    return form_check


async def validate_feedback_access(feedback_id: UUID, current_user: User = Depends(get_current_user)) -> FeedbackItem:
    """
    Validate user has access to feedback.
    
    Args:
        feedback_id: Feedback ID
        current_user: User model instance from get_current_user dependency
        
    Returns:
        FeedbackItem model instance if user has access
        
    Raises:
        HTTPException: If user doesn't have access to feedback
    """
    from app.repositories.feedback_repository import FeedbackRepository
    
    # Get feedback
    feedback_repo = FeedbackRepository(AsyncSession)
    feedback = await feedback_repo.get_by_id_async(feedback_id)
    
    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback not found",
        )
    
    # Check if user is owner of the associated form check or has admin privileges
    form_check = feedback.form_check
    if form_check.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this feedback",
        )
        
    return feedback 