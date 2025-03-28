from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.core.utils import stripe as stripe_utils
from app.core.utils.email import generate_verification_token, send_verification_email, send_password_reset_email
from app.core.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate, UserResponse
from app.core.auth import get_current_user
from app.core.logging import get_logger
from app.api import deps
from app.services.user import UserService

logger = get_logger(__name__)
router = APIRouter()
user_service = UserService()

@router.post("/", response_model=UserResponse)
def create_user(
    *,
    db: Session = Depends(deps.get_db),
    user_in: UserCreate,
) -> Any:
    """Create new user."""
    user = user_service.get_user_by_email(db, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    user = user_service.create_user(db, user_data=user_in.dict())
    return user

@router.get("/me", response_model=UserResponse)
def read_user_me(
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Get current user."""
    return current_user

@router.put("/me", response_model=UserResponse)
def update_user_me(
    *,
    db: Session = Depends(deps.get_db),
    user_in: UserUpdate,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Update current user."""
    user = user_service.update_user(db, user=current_user, user_data=user_in.dict(exclude_unset=True))
    return user

@router.post("/verify-email/{token}")
def verify_email(
    *,
    db: Session = Depends(deps.get_db),
    token: str,
) -> Any:
    """Verify user email."""
    user = user_service.verify_email(db, token=token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token"
        )
    return {"message": "Email verified successfully"}

@router.post("/forgot-password")
def forgot_password(
    *,
    db: Session = Depends(deps.get_db),
    email: str,
) -> Any:
    """Initiate password reset."""
    success = user_service.initiate_password_reset(db, email=email)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return {"message": "Password reset email sent"}

@router.post("/reset-password/{token}")
def reset_password(
    *,
    db: Session = Depends(deps.get_db),
    token: str,
    new_password: str,
) -> Any:
    """Reset password with token."""
    user = user_service.reset_password(db, token=token, new_password=new_password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    return {"message": "Password reset successfully"}

@router.post("/subscribe")
async def create_subscription(
    tier: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    request: Request
):
    """Create a subscription for the current user."""
    try:
        # Get price ID for the tier
        price_id = stripe_utils.SUBSCRIPTION_PRICES.get(tier)
        if not price_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid subscription tier"
            )
        
        # Create checkout session
        success_url = f"{request.headers.get('origin')}/subscription/success"
        cancel_url = f"{request.headers.get('origin')}/subscription/cancel"
        
        session = await stripe_utils.create_checkout_session(
            current_user,
            price_id,
            success_url,
            cancel_url
        )
        
        return session
        
    except Exception as e:
        logger.error(f"Failed to create subscription for user {current_user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create subscription"
        ) 