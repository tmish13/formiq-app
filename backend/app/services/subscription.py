from typing import Optional
from sqlalchemy.orm import Session
from app.models.subscription import Subscription
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.core.logging import get_logger
import stripe

logger = get_logger(__name__)

class SubscriptionService:
    """Service for subscription operations."""
    
    def __init__(self):
        self.repository = UserRepository()
        stripe.api_key = "your_stripe_secret_key"  # TODO: Move to config

    def create_subscription(
        self, 
        db: Session, 
        *, 
        user: User, 
        stripe_customer_id: str,
        stripe_subscription_id: str,
        plan_type: str
    ) -> Subscription:
        """Create a new subscription."""
        subscription = Subscription(
            user_id=user.id,
            stripe_customer_id=stripe_customer_id,
            stripe_subscription_id=stripe_subscription_id,
            plan_type=plan_type,
            status="active"
        )
        db.add(subscription)
        db.commit()
        db.refresh(subscription)
        return subscription

    def update_subscription_status(
        self, 
        db: Session, 
        *, 
        subscription: Subscription, 
        status: str
    ) -> Subscription:
        """Update subscription status."""
        subscription.status = status
        db.commit()
        db.refresh(subscription)
        return subscription

    def cancel_subscription(self, db: Session, *, subscription: Subscription) -> Subscription:
        """Cancel a subscription."""
        try:
            # Cancel subscription in Stripe
            stripe.Subscription.delete(subscription.stripe_subscription_id)
            
            # Update local subscription status
            subscription.status = "cancelled"
            db.commit()
            db.refresh(subscription)
            return subscription
        except stripe.error.StripeError as e:
            logger.error(f"Failed to cancel Stripe subscription: {str(e)}")
            raise

    def get_subscription_by_user(self, db: Session, *, user_id: int) -> Optional[Subscription]:
        """Get subscription for a user."""
        return db.query(Subscription).filter(Subscription.user_id == user_id).first()

    def handle_subscription_webhook(self, db: Session, *, event: dict) -> None:
        """Handle Stripe subscription webhook events."""
        event_type = event.get("type")
        data = event.get("data", {}).get("object", {})

        if event_type == "customer.subscription.updated":
            subscription_id = data.get("id")
            user = self.repository.get_by_stripe_subscription(db, subscription_id=subscription_id)
            if user:
                subscription = self.get_subscription_by_user(db, user_id=user.id)
                if subscription:
                    subscription.status = data.get("status", "active")
                    db.commit()

        elif event_type == "customer.subscription.deleted":
            subscription_id = data.get("id")
            user = self.repository.get_by_stripe_subscription(db, subscription_id=subscription_id)
            if user:
                subscription = self.get_subscription_by_user(db, user_id=user.id)
                if subscription:
                    subscription.status = "cancelled"
                    db.commit() 