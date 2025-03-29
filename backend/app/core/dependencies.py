"""API dependencies and utilities."""
from typing import AsyncGenerator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from app.core.config import settings
from app.core.database import SessionLocal
from app.core.security import verify_token
from app.services.user_service import UserService
from app.services.subscription_service import SubscriptionService
from app.models.enums import SubscriptionTier

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/auth/login")

async def get_db() -> AsyncGenerator[Session, None]:
    """Get database session."""
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()

async def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> dict:
    """Get current authenticated user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"}
    )
    
    try:
        # Verify token
        payload = verify_token(token)
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        
        # Get user
        user_service = UserService()
        user = await user_service.get(db, id=user_id)
        if user is None:
            raise credentials_exception
        
        # Check if user is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Inactive user"
            )
        
        return user
    except JWTError:
        raise credentials_exception

async def get_current_active_user(
    current_user = Depends(get_current_user)
) -> dict:
    """Get current active user."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user

async def get_current_superuser(
    current_user = Depends(get_current_user)
) -> dict:
    """Get current superuser."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough privileges"
        )
    return current_user

async def check_subscription_tier(
    required_tier: SubscriptionTier,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
) -> None:
    """Check if user has required subscription tier."""
    subscription_service = SubscriptionService()
    subscription = await subscription_service.get_active_subscription(
        db, user_id=current_user.id
    )
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Active subscription required"
        )
    
    if subscription.tier.value < required_tier.value:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"{required_tier.name} subscription required"
        )

async def get_subscription_tier(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
) -> Optional[SubscriptionTier]:
    """Get user's current subscription tier."""
    subscription_service = SubscriptionService()
    subscription = await subscription_service.get_active_subscription(
        db, user_id=current_user.id
    )
    return subscription.tier if subscription else None

async def validate_form_check_access(
    form_check_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
) -> None:
    """Validate user's access to form check."""
    from app.services.form_check_service import FormCheckService
    
    form_check_service = FormCheckService()
    form_check = await form_check_service.get(db, id=form_check_id)
    
    if not form_check:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Form check not found"
        )
    
    if form_check.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this form check"
        )

async def validate_workout_access(
    workout_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
) -> None:
    """Validate user's access to workout."""
    from app.services.workout_service import WorkoutService
    
    workout_service = WorkoutService()
    workout = await workout_service.get(db, id=workout_id)
    
    if not workout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout not found"
        )
    
    if workout.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this workout"
        ) 