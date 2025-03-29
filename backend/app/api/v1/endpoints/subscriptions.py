"""Subscription endpoints."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user
from app.models.enums import SubscriptionTier
from app.schemas.subscription import (
    SubscriptionCreate,
    SubscriptionUpdate,
    SubscriptionResponse,
    StripeWebhookEvent,
    SubscriptionUsageResponse
)
from app.services.subscription_service import SubscriptionService
from app.core.logging import logger

router = APIRouter()

@router.post("/", response_model=SubscriptionResponse)
async def create_subscription(
    *,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    tier: SubscriptionTier,
    payment_method_id: str
) -> SubscriptionResponse:
    """Create a new subscription."""
    try:
        subscription_service = SubscriptionService()
        return await subscription_service.create_subscription(
            db,
            user_id=current_user.id,
            tier=tier,
            payment_method_id=payment_method_id
        )
    except Exception as e:
        logger.error("Error creating subscription", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/webhook")
async def stripe_webhook(
    *,
    db: Session = Depends(get_db),
    request: Request
) -> Response:
    """Handle Stripe webhook events."""
    try:
        # Get webhook payload and signature
        payload = await request.body()
        signature = request.headers.get("stripe-signature")
        
        subscription_service = SubscriptionService()
        await subscription_service.handle_webhook(
            db,
            event=StripeWebhookEvent(
                payload=payload,
                signature=signature
            )
        )
        
        return Response(status_code=status.HTTP_200_OK)
    except Exception as e:
        logger.error("Error handling webhook", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/current", response_model=Optional[SubscriptionResponse])
async def get_current_subscription(
    *,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
) -> Optional[SubscriptionResponse]:
    """Get user's current active subscription."""
    try:
        subscription_service = SubscriptionService()
        return await subscription_service.get_active_subscription(
            db,
            user_id=current_user.id
        )
    except Exception as e:
        logger.error("Error getting current subscription", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.put("/current", response_model=SubscriptionResponse)
async def update_subscription(
    *,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    new_tier: SubscriptionTier
) -> SubscriptionResponse:
    """Update subscription tier."""
    try:
        subscription_service = SubscriptionService()
        return await subscription_service.update_subscription(
            db,
            user_id=current_user.id,
            new_tier=new_tier
        )
    except Exception as e:
        logger.error("Error updating subscription", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.delete("/current", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_subscription(
    *,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
) -> None:
    """Cancel current subscription."""
    try:
        subscription_service = SubscriptionService()
        await subscription_service.cancel_subscription(
            db,
            user_id=current_user.id
        )
    except Exception as e:
        logger.error("Error canceling subscription", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/usage", response_model=SubscriptionUsageResponse)
async def get_subscription_usage(
    *,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
) -> SubscriptionUsageResponse:
    """Get current subscription usage metrics."""
    try:
        subscription_service = SubscriptionService()
        subscription = await subscription_service.get_active_subscription(
            db,
            user_id=current_user.id
        )
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active subscription found"
            )
        
        # Get usage metrics
        form_checks_used = await subscription_service.repository.count_monthly_submissions(
            db,
            user_id=current_user.id
        )
        
        return SubscriptionUsageResponse(
            tier=subscription.tier,
            form_checks_used=form_checks_used,
            form_checks_limit=subscription.tier.monthly_form_checks,
            period_start=subscription.current_period_start,
            period_end=subscription.current_period_end
        )
    except Exception as e:
        logger.error("Error getting subscription usage", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        ) 