"""User endpoints."""
from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate, UserResponse
from app.services.user_service import UserService
from app.core.utils import stripe as stripe_utils
from app.core.utils.email import generate_verification_token, send_verification_email, send_password_reset_email
from app.core.logging import logger

router = APIRouter()

@router.post("/", response_model=UserResponse)
async def create_user(
    user: UserCreate,
    db: Session = Depends(get_db)
):
    """Create new user."""
    user_service = UserService(db)
    return user_service.create_user(user)

@router.get("/me", response_model=UserResponse)
async def read_users_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user."""
    user_service = UserService(db)
    return user_service.get_user(current_user.id)

@router.put("/me", response_model=UserResponse)
async def update_user_me(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update current user."""
    user_service = UserService(db)
    return user_service.update_user(current_user.id, user_update)

@router.delete("/me")
async def delete_user_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete current user."""
    user_service = UserService(db)
    user_service.delete_user(current_user.id)
    return {"message": "User deleted successfully"}

@router.post("/verify-email")
async def verify_email(
    token: str,
    db: Session = Depends(get_db)
):
    """Verify user email."""
    user_service = UserService(db)
    return user_service.verify_email(token)

@router.post("/resend-verification")
async def resend_verification(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Resend verification email."""
    user_service = UserService(db)
    return user_service.resend_verification_email(current_user)

@router.post("/forgot-password")
async def forgot_password(
    email: str,
    db: Session = Depends(get_db)
):
    """Send password reset email."""
    user_service = UserService(db)
    return user_service.send_password_reset_email(email)

@router.post("/reset-password")
async def reset_password(
    token: str,
    new_password: str,
    db: Session = Depends(get_db)
):
    """Reset user password."""
    user_service = UserService(db)
    return user_service.reset_password(token, new_password)

@router.post("/change-password")
async def change_password(
    current_password: str,
    new_password: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change user password."""
    user_service = UserService(db)
    return user_service.change_password(current_user.id, current_password, new_password)

@router.get("/subscription")
async def get_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user subscription."""
    user_service = UserService(db)
    return user_service.get_subscription(current_user.id)

@router.post("/subscription")
async def create_subscription(
    price_id: str,
    payment_method_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create user subscription."""
    user_service = UserService(db)
    return user_service.create_subscription(current_user.id, price_id, payment_method_id)

@router.delete("/subscription")
async def cancel_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cancel user subscription."""
    user_service = UserService(db)
    return user_service.cancel_subscription(current_user.id)

@router.post("/subscribe")
async def create_subscription(
    request: Request,
    tier: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
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
            user=current_user,
            db=db,
            price_id=price_id,
            success_url=success_url,
            cancel_url=cancel_url
        )
        
        return session
        
    except Exception as e:
        logger.error(f"Failed to create subscription for user {current_user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create subscription"
        ) 