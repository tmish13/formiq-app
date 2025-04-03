"""Dependency injection module."""
from typing import Generator, Optional, AsyncGenerator
from uuid import UUID
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import ALGORITHM
from app.db.session import async_session, SessionLocal
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
async def get_current_user(
    db: AsyncSession = Depends(get_async_db),
    token: str = Depends(oauth2_scheme),
) -> User:
    """
    Get current authenticated user.
    
    Args:
        db: Database session
        token: JWT token
        
    Returns:
        Current user
        
    Raises:
        HTTPException: If authentication fails
    """
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
        
    user_repository = UserRepository(db)
    user = await user_repository.get(token_data.sub)
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
        
    user_repo = UserRepository(db)
    user = user_repo.get_by_email(email=token_data.sub)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Get current active user.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Current active user
        
    Raises:
        HTTPException: If user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
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


async def get_current_active_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Get current active superuser.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Current active superuser
        
    Raises:
        HTTPException: If user is not a superuser
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges",
        )
    return current_user


async def check_subscription_tier(
    required_tier: SubscriptionTier,
    db: Session,
    current_user: User,
) -> None:
    """
    Check if user has required subscription tier.
    
    Args:
        required_tier: Required subscription tier
        db: Database session
        current_user: Current user
        
    Raises:
        HTTPException: If user doesn't have required subscription tier
    """
    user_tier = current_user.subscription_tier or SubscriptionTier.FREE
    
    tier_values = {
        SubscriptionTier.FREE: 0,
        SubscriptionTier.BASIC: 1,
        SubscriptionTier.PRO: 2,
        SubscriptionTier.PREMIUM: 3
    }
    
    if tier_values[user_tier] < tier_values[required_tier]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"This feature requires a {required_tier.value} subscription or higher"
        )


async def validate_form_check_access(
    form_check_id: UUID,
    db: Session,
    current_user: User,
) -> FormCheck:
    """
    Validate user access to a form check.
    
    Args:
        form_check_id: Form check ID
        db: Database session
        current_user: Current user
        
    Returns:
        Form check if access is allowed
        
    Raises:
        HTTPException: If form check not found or access not allowed
    """
    form_check_repo = FormCheckRepository(db)
    form_check = form_check_repo.get(id=form_check_id)
    
    if not form_check:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Form check not found"
        )
    
    # Superusers can access any form check
    if current_user.is_superuser:
        return form_check
    
    # Users can only access their own form checks
    if form_check.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this form check"
        )
    
    return form_check


async def validate_feedback_access(
    feedback_id: int,
    db: Session,
    current_user: User,
) -> FeedbackItem:
    """
    Validate user access to a feedback item.
    
    Args:
        feedback_id: Feedback item ID
        db: Database session
        current_user: Current user
        
    Returns:
        Feedback item if access is allowed
        
    Raises:
        HTTPException: If feedback item not found or access not allowed
    """
    feedback_repo = FeedbackRepository(db)
    feedback_item = feedback_repo.get(id=feedback_id)
    
    if not feedback_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback item not found"
        )
    
    # Get the associated form check
    form_check_repo = FormCheckRepository(db)
    form_check = form_check_repo.get(id=feedback_item.form_check_id)
    
    if not form_check:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated form check not found"
        )
    
    # Superusers can access any feedback
    if current_user.is_superuser:
        return feedback_item
    
    # Users can only access feedback for their own form checks
    if form_check.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this feedback"
        )
    
    return feedback_item 