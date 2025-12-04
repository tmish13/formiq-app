"""Subscription endpoints."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.core import deps
from app.models.user import User
from app.models.enums import SubscriptionTier
from app.schemas.subscription import (
    SubscriptionCreate,
    SubscriptionUpdate,
    SubscriptionResponse,
    StripeWebhookEvent,
    SubscriptionUsageResponse
)
from app.services.subscription_service import SubscriptionService, get_async_subscription_service
from app.core.logging import logger

router = APIRouter()

@router.post("/", response_model=SubscriptionResponse)
async def create_subscription(
    *,
    current_user: User = Depends(deps.get_current_active_user),
    tier: SubscriptionTier,
    payment_method_id: str,
    subscription_service: SubscriptionService = Depends(get_async_subscription_service)
) -> SubscriptionResponse:
    """Create a new subscription."""
    try:
        return await subscription_service.create_subscription_async(
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
    request: Request,
    subscription_service: SubscriptionService = Depends(get_async_subscription_service)
) -> Response:
    """Handle Stripe webhook events."""
    try:
        payload = await request.body()
        signature = request.headers.get("stripe-signature")
        
        await subscription_service.handle_stripe_webhook_async(
            event_payload=payload.decode(),
            stripe_signature=signature
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
    current_user: User = Depends(deps.get_current_active_user),
    subscription_service: SubscriptionService = Depends(get_async_subscription_service)
) -> Optional[SubscriptionResponse]:
    """Get user's current active subscription."""
    try:
        return await subscription_service.get_active_subscription_async(
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
    current_user: User = Depends(deps.get_current_active_user),
    new_tier: SubscriptionTier,
    subscription_service: SubscriptionService = Depends(get_async_subscription_service)
) -> SubscriptionResponse:
    """Update subscription tier."""
    try:
        return await subscription_service.update_subscription_tier_async(
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
    current_user: User = Depends(deps.get_current_active_user),
    subscription_service: SubscriptionService = Depends(get_async_subscription_service)
) -> None:
    """Cancel current subscription."""
    try:
        await subscription_service.cancel_subscription_async(
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
    current_user: User = Depends(deps.get_current_active_user),
    subscription_service: SubscriptionService = Depends(get_async_subscription_service)
) -> SubscriptionUsageResponse:
    """Get current subscription usage metrics."""
    try:
        subscription = await subscription_service.get_active_subscription_async(
            user_id=current_user.id
        )
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active subscription found"
            )
        
        form_checks_used = await subscription_service.count_monthly_form_checks_for_user_async(user_id=current_user.id)
        
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