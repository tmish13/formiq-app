"""Subscription service implementation with Stripe integration."""
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import Depends
from stripe.error import StripeError
from app.core.exceptions import (
    ValidationError,
    NotFoundException,
    PaymentError,
    StripeWebhookError
)
from app.core.database import get_db
from app.core.logging import get_logger
from app.core.stripe.client import stripe_client as stripe
from app.core.config import settings
from app.models.subscription import Subscription
from app.models.enums import SubscriptionTier
from app.schemas.subscription import (
    SubscriptionCreate,
    SubscriptionUpdate,
    SubscriptionFilter,
    SubscriptionResponse,
    StripeWebhookEvent
)
from app.repositories.subscription import SubscriptionRepository
from app.services.base import BaseService

# Initialize logger
logger = get_logger(__name__)

class SubscriptionService(BaseService[Subscription, SubscriptionCreate, SubscriptionUpdate, SubscriptionFilter]):
    """
    Subscription service with Stripe integration.
    
    Features:
    - Subscription creation and management
    - Stripe payment processing
    - Webhook handling
    - Tier management
    - Usage tracking
    """
    
    def __init__(self):
        super().__init__(
            repository=SubscriptionRepository,
            model=Subscription,
            create_schema=SubscriptionCreate,
            update_schema=SubscriptionUpdate,
            filter_schema=SubscriptionFilter
        )

    async def create_subscription(
        self,
        db: Session = Depends(get_db),
        *,
        user_id: UUID,
        tier: SubscriptionTier,
        payment_method_id: str
    ) -> Subscription:
        """
        Create a new subscription.
        
        Args:
            db: Database session
            user_id: User's ID
            tier: Subscription tier
            payment_method_id: Stripe payment method ID
        """
        try:
            # Check for existing subscription
            existing = await self.get_active_subscription(db, user_id=user_id)
            if existing:
                raise ValidationError("User already has an active subscription")
            
            # Create Stripe customer if not exists
            customer = await self._get_or_create_customer(db, user_id)
            
            # Attach payment method to customer
            await stripe.PaymentMethod.attach(
                payment_method_id,
                customer=customer.id
            )
            
            # Set as default payment method
            await stripe.Customer.modify(
                customer.id,
                invoice_settings={"default_payment_method": payment_method_id}
            )
            
            # Create Stripe subscription
            stripe_subscription = await stripe.Subscription.create(
                customer=customer.id,
                items=[{"price": settings.STRIPE_PRICE_IDS[tier]}],
                expand=["latest_invoice.payment_intent"]
            )
            
            # Create subscription record
            subscription = await self.create(
                db,
                data={
                    "user_id": user_id,
                    "tier": tier,
                    "stripe_subscription_id": stripe_subscription.id,
                    "stripe_customer_id": customer.id,
                    "status": stripe_subscription.status,
                    "current_period_start": datetime.fromtimestamp(stripe_subscription.current_period_start),
                    "current_period_end": datetime.fromtimestamp(stripe_subscription.current_period_end),
                    "trial_start": datetime.fromtimestamp(stripe_subscription.trial_start) if stripe_subscription.trial_start else None,
                    "trial_end": datetime.fromtimestamp(stripe_subscription.trial_end) if stripe_subscription.trial_end else None
                }
            )
            
            return subscription
        except StripeError as e:
            logger.error("Stripe error in subscription creation", exc_info=e)
            raise PaymentError(str(e))
        except Exception as e:
            logger.error("Error in subscription creation", exc_info=e)
            raise

    async def cancel_subscription(
        self,
        db: Session = Depends(get_db),
        *,
        user_id: UUID
    ) -> Subscription:
        """
        Cancel a subscription.
        
        Args:
            db: Database session
            user_id: User's ID
        """
        try:
            subscription = await self.get_active_subscription(db, user_id=user_id)
            if not subscription:
                raise NotFoundException("No active subscription found")
            
            # Cancel Stripe subscription
            stripe_subscription = await stripe.Subscription.delete(
                subscription.stripe_subscription_id
            )
            
            # Update subscription record
            return await self.update(
                db,
                id=subscription.id,
                data={
                    "status": stripe_subscription.status,
                    "canceled_at": datetime.utcnow()
                }
            )
        except StripeError as e:
            logger.error("Stripe error in subscription cancellation", exc_info=e)
            raise PaymentError(str(e))
        except Exception as e:
            logger.error("Error in subscription cancellation", exc_info=e)
            raise

    async def update_subscription(
        self,
        db: Session = Depends(get_db),
        *,
        user_id: UUID,
        new_tier: SubscriptionTier
    ) -> Subscription:
        """
        Update subscription tier.
        
        Args:
            db: Database session
            user_id: User's ID
            new_tier: New subscription tier
        """
        try:
            subscription = await self.get_active_subscription(db, user_id=user_id)
            if not subscription:
                raise NotFoundException("No active subscription found")
            
            # Update Stripe subscription
            stripe_subscription = await stripe.Subscription.modify(
                subscription.stripe_subscription_id,
                items=[{
                    "id": subscription.stripe_subscription_id,
                    "price": settings.STRIPE_PRICE_IDS[new_tier]
                }],
                proration_behavior="always_invoice"
            )
            
            # Update subscription record
            return await self.update(
                db,
                id=subscription.id,
                data={
                    "tier": new_tier,
                    "current_period_start": datetime.fromtimestamp(stripe_subscription.current_period_start),
                    "current_period_end": datetime.fromtimestamp(stripe_subscription.current_period_end)
                }
            )
        except StripeError as e:
            logger.error("Stripe error in subscription update", exc_info=e)
            raise PaymentError(str(e))
        except Exception as e:
            logger.error("Error in subscription update", exc_info=e)
            raise

    async def get_active_subscription(
        self,
        db: Session = Depends(get_db),
        *,
        user_id: UUID
    ) -> Optional[Subscription]:
        """
        Get user's active subscription.
        
        Args:
            db: Database session
            user_id: User's ID
        """
        try:
            return await self.repository.get_active_subscription(db, user_id=user_id)
        except Exception as e:
            logger.error("Error getting active subscription", exc_info=e)
            raise

    async def handle_webhook(
        self,
        db: Session = Depends(get_db),
        *,
        event: StripeWebhookEvent
    ) -> None:
        """
        Handle Stripe webhook events.
        
        Args:
            db: Database session
            event: Stripe webhook event
        """
        try:
            # Verify webhook signature
            stripe.Webhook.construct_event(
                event.payload,
                event.signature,
                settings.STRIPE_WEBHOOK_SECRET
            )
            
            # Handle different event types
            if event.type == "customer.subscription.updated":
                await self._handle_subscription_updated(db, event.data)
            elif event.type == "customer.subscription.deleted":
                await self._handle_subscription_deleted(db, event.data)
            elif event.type == "invoice.payment_failed":
                await self._handle_payment_failed(db, event.data)
        except StripeError as e:
            logger.error("Stripe error in webhook handling", exc_info=e)
            raise StripeWebhookError(str(e))
        except Exception as e:
            logger.error("Error in webhook handling", exc_info=e)
            raise

    async def _get_or_create_customer(
        self,
        db: Session,
        user_id: UUID
    ) -> stripe.Customer:
        """Get or create Stripe customer for user."""
        try:
            # Check existing subscription for customer ID
            subscription = await self.repository.get_latest_subscription(
                db, user_id=user_id
            )
            if subscription and subscription.stripe_customer_id:
                return await stripe.Customer.retrieve(subscription.stripe_customer_id)
            
            # Create new customer
            user = await self.user_service.get(db, id=user_id)
            customer = await stripe.Customer.create(
                email=user.email,
                name=user.full_name,
                metadata={"user_id": str(user_id)}
            )
            
            return customer
        except Exception as e:
            logger.error("Error in customer creation", exc_info=e)
            raise

    async def _handle_subscription_updated(
        self,
        db: Session,
        data: Dict[str, Any]
    ) -> None:
        """Handle subscription updated webhook."""
        subscription = await self.repository.get_by_stripe_id(
            db, stripe_id=data["subscription"]
        )
        if subscription:
            await self.update(
                db,
                id=subscription.id,
                data={
                    "status": data["status"],
                    "current_period_start": datetime.fromtimestamp(data["current_period_start"]),
                    "current_period_end": datetime.fromtimestamp(data["current_period_end"])
                }
            )

    async def _handle_subscription_deleted(
        self,
        db: Session,
        data: Dict[str, Any]
    ) -> None:
        """Handle subscription deleted webhook."""
        subscription = await self.repository.get_by_stripe_id(
            db, stripe_id=data["subscription"]
        )
        if subscription:
            await self.update(
                db,
                id=subscription.id,
                data={
                    "status": "canceled",
                    "canceled_at": datetime.utcnow()
                }
            )

    async def _handle_payment_failed(
        self,
        db: Session,
        data: Dict[str, Any]
    ) -> None:
        """Handle payment failed webhook."""
        subscription = await self.repository.get_by_stripe_id(
            db, stripe_id=data["subscription"]
        )
        if subscription:
            await self.update(
                db,
                id=subscription.id,
                data={"status": "past_due"}
            ) 