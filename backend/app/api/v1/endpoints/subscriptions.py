from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.api import deps
from app.models.subscription import Subscription
from app.models.user import User
from app.schemas.subscription import SubscriptionCreate, SubscriptionResponse
from app.services.subscription import SubscriptionService
from app.core.logging import get_logger
import stripe

logger = get_logger(__name__)
router = APIRouter()
subscription_service = SubscriptionService()

@router.post("/", response_model=SubscriptionResponse)
def create_subscription(
    *,
    db: Session = Depends(deps.get_db),
    subscription_in: SubscriptionCreate,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Create new subscription."""
    try:
        # Create Stripe customer if not exists
        if not current_user.stripe_customer_id:
            customer = stripe.Customer.create(
                email=current_user.email,
                metadata={"user_id": current_user.id}
            )
            current_user.stripe_customer_id = customer.id
            db.commit()

        # Create Stripe subscription
        subscription = stripe.Subscription.create(
            customer=current_user.stripe_customer_id,
            items=[{"price": subscription_in.price_id}],
            payment_behavior="default_incomplete",
            payment_settings={"save_default_payment_method": "on_subscription"},
            expand=["latest_invoice.payment_intent"],
        )

        # Create local subscription record
        db_subscription = subscription_service.create_subscription(
            db,
            user=current_user,
            stripe_customer_id=current_user.stripe_customer_id,
            stripe_subscription_id=subscription.id,
            plan_type=subscription_in.plan_type
        )

        return db_subscription

    except stripe.error.StripeError as e:
        logger.error(f"Stripe error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/webhook")
async def stripe_webhook(
    *,
    request: Request,
    db: Session = Depends(deps.get_db),
) -> Any:
    """Handle Stripe webhook events."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, "your_webhook_secret"  # TODO: Move to config
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payload"
        )
    except stripe.error.SignatureVerificationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid signature"
        )

    subscription_service.handle_subscription_webhook(db, event=event)
    return {"status": "success"}

@router.post("/{subscription_id}/cancel")
def cancel_subscription(
    *,
    db: Session = Depends(deps.get_db),
    subscription_id: int,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Cancel subscription."""
    subscription = subscription_service.get_subscription_by_user(db, user_id=current_user.id)
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )
    
    try:
        subscription = subscription_service.cancel_subscription(db, subscription=subscription)
        return subscription
    except stripe.error.StripeError as e:
        logger.error(f"Failed to cancel subscription: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        ) 