"""Service for managing user subscriptions using Stripe."""
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import stripe
from sqlalchemy.orm import Session
from app.models.subscription import Subscription
from app.models.user import User
from app.models.enums import SubscriptionTier
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

class SubscriptionError(Exception):
    """Custom exception for subscription service errors."""
    pass

class InvalidTierError(SubscriptionError):
    """Exception raised when an invalid subscription tier is provided."""
    pass

class PaymentError(SubscriptionError):
    """Exception raised when payment processing fails."""
    pass

class SubscriptionService:
    """Service for managing user subscriptions."""
    
    def __init__(self, db: Session):
        """Initialize subscription service with database session."""
        self.db = db
        stripe.api_key = settings.STRIPE_SECRET_KEY
        self.price_ids = {
            SubscriptionTier.FREE: None,
            SubscriptionTier.BASIC: settings.STRIPE_BASIC_PRICE_ID,
            SubscriptionTier.PRO: settings.STRIPE_PRO_PRICE_ID,
            SubscriptionTier.PREMIUM: settings.STRIPE_PREMIUM_PRICE_ID
        }

    def create_customer(self, user: User) -> str:
        """Create a Stripe customer for the user."""
        try:
            customer = stripe.Customer.create(
                email=user.email,
                metadata={"user_id": str(user.id)}
            )
            logger.info(f"Created Stripe customer for user {user.id}")
            return customer.id
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create Stripe customer: {str(e)}")
            raise PaymentError(f"Failed to create customer: {str(e)}")

    def create_subscription(self, user: User, tier: str, payment_method_id: str) -> Dict[str, Any]:
        """Create a new subscription for the user."""
        try:
            if tier not in self.price_ids or tier == SubscriptionTier.FREE:
                raise InvalidTierError(f"Invalid subscription tier: {tier}")

            # Create or get customer
            if not user.stripe_customer_id:
                customer_id = self.create_customer(user)
                user.stripe_customer_id = customer_id
                self.db.commit()
            
            # Attach payment method to customer
            stripe.PaymentMethod.attach(
                payment_method_id,
                customer=user.stripe_customer_id
            )
            
            # Set as default payment method
            stripe.Customer.modify(
                user.stripe_customer_id,
                invoice_settings={
                    "default_payment_method": payment_method_id
                }
            )
            
            # Create subscription
            subscription = stripe.Subscription.create(
                customer=user.stripe_customer_id,
                items=[{"price": self.price_ids[tier]}],
                payment_behavior="default_incomplete",
                expand=["latest_invoice.payment_intent"]
            )
            
            # Create local subscription record
            db_subscription = Subscription(
                user_id=user.id,
                stripe_subscription_id=subscription.id,
                tier=tier,
                status=subscription.status,
                current_period_start=datetime.fromtimestamp(subscription.current_period_start),
                current_period_end=datetime.fromtimestamp(subscription.current_period_end),
                cancel_at_period_end=subscription.cancel_at_period_end
            )
            self.db.add(db_subscription)
            
            # Update user's subscription tier
            user.subscription_tier = tier
            
            self.db.commit()
            logger.info(f"Created subscription for user {user.id}")
            
            return {
                "subscription_id": subscription.id,
                "client_secret": subscription.latest_invoice.payment_intent.client_secret,
                "status": subscription.status
            }
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create subscription: {str(e)}")
            self.db.rollback()
            raise PaymentError(f"Failed to create subscription: {str(e)}")
        except Exception as e:
            logger.error(f"Failed to create subscription: {str(e)}")
            self.db.rollback()
            raise SubscriptionError(f"Failed to create subscription: {str(e)}")

    def cancel_subscription(self, user: User) -> None:
        """Cancel user's subscription at the end of the current period."""
        try:
            subscription = self.db.query(Subscription).filter(
                Subscription.user_id == user.id,
                Subscription.status == "active"
            ).first()
            
            if not subscription:
                raise SubscriptionError("No active subscription found")
            
            # Cancel subscription in Stripe
            stripe_sub = stripe.Subscription.modify(
                subscription.stripe_subscription_id,
                cancel_at_period_end=True
            )
            
            # Update local subscription record
            subscription.cancel_at_period_end = True
            subscription.updated_at = datetime.now()
            
            self.db.commit()
            logger.info(f"Cancelled subscription for user {user.id}")
        except stripe.error.StripeError as e:
            logger.error(f"Failed to cancel subscription: {str(e)}")
            self.db.rollback()
            raise PaymentError(f"Failed to cancel subscription: {str(e)}")
        except Exception as e:
            logger.error(f"Failed to cancel subscription: {str(e)}")
            self.db.rollback()
            raise SubscriptionError(f"Failed to cancel subscription: {str(e)}")

    def update_subscription(self, user: User, new_tier: str) -> Dict[str, Any]:
        """Update user's subscription to a new tier."""
        try:
            if new_tier not in self.price_ids or new_tier == SubscriptionTier.FREE:
                raise InvalidTierError(f"Invalid subscription tier: {new_tier}")
            
            subscription = self.db.query(Subscription).filter(
                Subscription.user_id == user.id,
                Subscription.status == "active"
            ).first()
            
            if not subscription:
                raise SubscriptionError("No active subscription found")
            
            # Update subscription in Stripe
            stripe_sub = stripe.Subscription.modify(
                subscription.stripe_subscription_id,
                items=[{
                    "id": stripe.Subscription.retrieve(subscription.stripe_subscription_id).items.data[0].id,
                    "price": self.price_ids[new_tier]
                }]
            )
            
            # Update local subscription record
            subscription.tier = new_tier
            subscription.updated_at = datetime.now()
            user.subscription_tier = new_tier
            
            self.db.commit()
            logger.info(f"Updated subscription for user {user.id} to {new_tier}")
            
            return {
                "subscription_id": stripe_sub.id,
                "status": stripe_sub.status
            }
        except stripe.error.StripeError as e:
            logger.error(f"Failed to update subscription: {str(e)}")
            self.db.rollback()
            raise PaymentError(f"Failed to update subscription: {str(e)}")
        except Exception as e:
            logger.error(f"Failed to update subscription: {str(e)}")
            self.db.rollback()
            raise SubscriptionError(f"Failed to update subscription: {str(e)}")

    def handle_webhook_event(self, event_data: Dict[str, Any]) -> None:
        """Handle Stripe webhook events."""
        try:
            event = stripe.Event.construct_from(event_data, stripe.api_key)
            
            if event.type == "customer.subscription.updated":
                self._handle_subscription_updated(event.data.object)
            elif event.type == "customer.subscription.deleted":
                self._handle_subscription_deleted(event.data.object)
            elif event.type == "invoice.payment_failed":
                self._handle_payment_failed(event.data.object)
                
            logger.info(f"Processed webhook event: {event.type}")
        except Exception as e:
            logger.error(f"Failed to handle webhook event: {str(e)}")
            raise SubscriptionError(f"Failed to handle webhook event: {str(e)}")

    def _handle_subscription_updated(self, stripe_sub: Any) -> None:
        """Handle subscription updated event."""
        subscription = self.db.query(Subscription).filter(
            Subscription.stripe_subscription_id == stripe_sub.id
        ).first()
        
        if subscription:
            subscription.status = stripe_sub.status
            subscription.current_period_start = datetime.fromtimestamp(stripe_sub.current_period_start)
            subscription.current_period_end = datetime.fromtimestamp(stripe_sub.current_period_end)
            subscription.cancel_at_period_end = stripe_sub.cancel_at_period_end
            subscription.updated_at = datetime.now()
            self.db.commit()

    def _handle_subscription_deleted(self, stripe_sub: Any) -> None:
        """Handle subscription deleted event."""
        subscription = self.db.query(Subscription).filter(
            Subscription.stripe_subscription_id == stripe_sub.id
        ).first()
        
        if subscription:
            user = self.db.query(User).filter(User.id == subscription.user_id).first()
            if user:
                user.subscription_tier = SubscriptionTier.FREE
            subscription.status = "cancelled"
            subscription.updated_at = datetime.now()
            self.db.commit()

    def _handle_payment_failed(self, invoice: Any) -> None:
        """Handle payment failed event."""
        subscription = self.db.query(Subscription).filter(
            Subscription.stripe_subscription_id == invoice.subscription
        ).first()
        
        if subscription:
            subscription.status = "past_due"
            subscription.updated_at = datetime.now()
            self.db.commit() 