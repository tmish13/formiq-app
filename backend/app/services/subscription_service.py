"""Subscription service implementation with Stripe integration."""
from typing import Optional, List, Dict, Any, Union
from uuid import UUID
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from stripe.error import StripeError
from app.core.exceptions import (
    ValidationError,
    NotFoundException,
    PaymentError,
    StripeWebhookError
)
from app.core.logging import get_logger
from app.core.stripe.client import stripe_client as stripe
from app.core.config import Settings, settings
from app.models.subscription import Subscription
from app.models.user import User as DBUser
from app.models.enums import SubscriptionTier
from app.schemas.subscription import (
    SubscriptionResponse,
    SubscriptionCreate,
    SubscriptionUpdate
)
from app.services.base_service import BaseService
from app.core.db_deps import get_async_db
from app.core.config import settings, Settings
from app.core.database import SessionLocal
from fastapi import Depends
from sqlalchemy.orm import Session
from typing import Generator

# Initialize logger
logger = get_logger(__name__)

class SubscriptionService(BaseService[Subscription, SubscriptionCreate, SubscriptionUpdate]):
    """
    Subscription service with Stripe integration.
    
    Features:
    - Subscription creation and management
    - Stripe payment processing
    - Webhook handling
    - Tier management
    - Usage tracking
    """
    
    def __init__(self, db: Union[AsyncSession, Session], app_settings: Settings):
        super().__init__(db=db, settings=app_settings, model=Subscription)

    # --- Integrated Repository Methods (now async using self.db) ---

    async def _get_active_subscription_async(self, user_id: UUID) -> Optional[Subscription]:
        """Get user's active subscription asynchronously."""
        stmt = select(self.model).filter(
            and_(
                self.model.user_id == user_id,
                self.model.status.in_(["active", "trialing"]),
                or_( # Ensuring that current_period_end or trial_end is in the future
                    self.model.current_period_end > datetime.utcnow(),
                    self.model.trial_end > datetime.utcnow() 
                )
            )
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def _get_by_stripe_id_async(self, stripe_id: str) -> Optional[Subscription]:
        """Get subscription by Stripe subscription ID asynchronously."""
        stmt = select(self.model).filter(self.model.stripe_subscription_id == stripe_id)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def _get_latest_subscription_async(self, user_id: UUID) -> Optional[Subscription]:
        """Get user's latest subscription asynchronously, typically the most recently created."""
        stmt = select(self.model).filter(self.model.user_id == user_id).order_by(self.model.created_at.desc())
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def _count_user_subscriptions_this_month_async(self, user_id: UUID) -> int: # Example custom query
        """Count user's new subscriptions created in current month."""
        start_of_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        stmt = select(func.count(self.model.id)).filter(
            and_(
                self.model.user_id == user_id,
                self.model.created_at >= start_of_month
            )
        ).select_from(self.model) # Ensure select_from if model is not first in select() for count
        result = await self.db.execute(stmt)
        count = result.scalar_one_or_none()
        return count if count is not None else 0

    # --- Service Methods Refactored ---

    async def create_subscription_async(
        self,
        user_id: UUID,
        tier: SubscriptionTier,
        payment_method_id: str
    ) -> SubscriptionResponse:
        """Create a new subscription asynchronously."""
        try:
            existing = await self._get_active_subscription_async(user_id=user_id)
            if existing:
                raise ValidationError("User already has an active subscription")
            
            customer = await self._get_or_create_stripe_customer_async(user_id)
            
            await stripe.PaymentMethod.attach(payment_method_id, customer=customer.id)
            await stripe.Customer.modify(customer.id, invoice_settings={"default_payment_method": payment_method_id})
            
            stripe_price_id = self.settings.STRIPE_PRICE_IDS.get(tier.value)
            if not stripe_price_id:
                raise ValueError(f"Stripe price ID not configured for tier: {tier.value}")

            stripe_subscription = await stripe.Subscription.create(
                customer=customer.id,
                items=[{"price": stripe_price_id}],
                expand=["latest_invoice.payment_intent"]
            )
            
            subscription_data = {
                    "user_id": user_id,
                "tier": tier.value,
                    "stripe_subscription_id": stripe_subscription.id,
                    "stripe_customer_id": customer.id,
                    "status": stripe_subscription.status,
                    "current_period_start": datetime.fromtimestamp(stripe_subscription.current_period_start),
                    "current_period_end": datetime.fromtimestamp(stripe_subscription.current_period_end),
                    "trial_start": datetime.fromtimestamp(stripe_subscription.trial_start) if stripe_subscription.trial_start else None,
                "trial_end": datetime.fromtimestamp(stripe_subscription.trial_end) if stripe_subscription.trial_end else None,
                }
            created_db_subscription = await super().create_async(obj_in=subscription_data)
            return SubscriptionResponse.from_orm(created_db_subscription)
            
        except StripeError as e:
            logger.error("Stripe error in subscription creation", exc_info=True, extra={"user_id": user_id, "tier": tier.value})
            raise PaymentError(str(e))
        except Exception as e:
            logger.error("Error in subscription creation", exc_info=True, extra={"user_id": user_id, "tier": tier.value})
            raise # Re-raise after logging

    async def cancel_subscription_async(self, user_id: UUID) -> SubscriptionResponse:
        """Cancel a subscription asynchronously."""
        try:
            subscription = await self._get_active_subscription_async(user_id=user_id)
            if not subscription:
                raise NotFoundException("No active subscription found for user")
            
            stripe_subscription_obj = await stripe.Subscription.delete(subscription.stripe_subscription_id) # API returns subscription obj on delete
            
            update_data = {
                "status": stripe_subscription_obj.status, # Should be 'canceled'
                "canceled_at": datetime.utcnow(), # Explicitly set cancel time
                # Stripe might set current_period_end to cancellation time or keep original.
                # If Stripe sets it, we can use that:
                # "current_period_end": datetime.fromtimestamp(stripe_subscription_obj.current_period_end)
            }
            updated_db_subscription = await super().update_async(db_obj=subscription, obj_in=update_data)
            return SubscriptionResponse.from_orm(updated_db_subscription)

        except StripeError as e:
            logger.error("Stripe error in subscription cancellation", exc_info=True, extra={"user_id": user_id})
            raise PaymentError(str(e))
        except Exception as e:
            logger.error("Error in subscription cancellation", exc_info=True, extra={"user_id": user_id})
            raise

    async def update_subscription_tier_async(
        self,
        user_id: UUID,
        new_tier: SubscriptionTier
    ) -> SubscriptionResponse:
        """Update subscription tier asynchronously."""
        try:
            subscription = await self._get_active_subscription_async(user_id=user_id)
            if not subscription:
                raise NotFoundException("No active subscription found for user to update")
            
            stripe_sub = await stripe.Subscription.retrieve(subscription.stripe_subscription_id)
            if not stripe_sub or not stripe_sub.items or not stripe_sub.items.data:
                raise PaymentError("Could not retrieve Stripe subscription items.")
            stripe_subscription_item_id = stripe_sub.items.data[0].id

            new_stripe_price_id = self.settings.STRIPE_PRICE_IDS.get(new_tier.value)
            if not new_stripe_price_id:
                raise ValueError(f"Stripe price ID not configured for new tier: {new_tier.value}")

            updated_stripe_subscription = await stripe.Subscription.modify(
                subscription.stripe_subscription_id,
                items=[{
                    "id": stripe_subscription_item_id,
                    "price": new_stripe_price_id
                }],
                proration_behavior="always_invoice",
                expand=["latest_invoice.payment_intent"]
            )
            
            update_data = {
                "tier": new_tier.value,
                "status": updated_stripe_subscription.status,
                "current_period_start": datetime.fromtimestamp(updated_stripe_subscription.current_period_start),
                "current_period_end": datetime.fromtimestamp(updated_stripe_subscription.current_period_end),
            }
            updated_db_subscription = await super().update_async(db_obj=subscription, obj_in=update_data)
            return SubscriptionResponse.from_orm(updated_db_subscription)

        except StripeError as e:
            logger.error("Stripe error in subscription update", exc_info=True, extra={"user_id": user_id, "new_tier": new_tier.value})
            raise PaymentError(str(e))
        except Exception as e:
            logger.error("Error in subscription update", exc_info=True, extra={"user_id": user_id, "new_tier": new_tier.value})
            raise

    async def handle_stripe_webhook_async(self, event_payload: str, stripe_signature: str) -> None:
        """Handle Stripe webhook events asynchronously."""
        try:
            event = stripe.Webhook.construct_event(
                payload=event_payload, sig_header=stripe_signature, secret=self.settings.STRIPE_WEBHOOK_SECRET
            )
        except ValueError as e:
            logger.error("Webhook error: Invalid payload", exc_info=True)
            raise StripeWebhookError(f"Invalid payload: {str(e)}")
        except stripe.error.SignatureVerificationError as e:
            logger.error("Webhook error: Invalid signature", exc_info=True)
            raise StripeWebhookError(f"Invalid signature: {str(e)}")
        except Exception as e:
            logger.error(f"Webhook construction error: {str(e)}", exc_info=True)
            raise StripeWebhookError(f"Could not construct webhook event: {str(e)}")

        event_data = event.data.object
        event_type = event.type
        logger.info(f"Received Stripe webhook: {event_type}", extra={"stripe_event_id": event.id})

        if event_type == "customer.subscription.updated":
            await self._handle_subscription_updated_async(event_data)
        elif event_type == "customer.subscription.deleted":
            await self._handle_subscription_deleted_async(event_data)
        elif event_type == "invoice.payment_failed":
            await self._handle_payment_failed_async(event_data)
        # ... other event handlers
        else:
            logger.info(f"Unhandled Stripe event type: {event_type}")
        return

    async def _get_or_create_stripe_customer_async(self, user_id: UUID) -> stripe.Customer:
        """Get existing Stripe customer or create a new one asynchronously."""
        latest_sub = await self._get_latest_subscription_async(user_id)
        if latest_sub and latest_sub.stripe_customer_id:
            try:
                customer = await stripe.Customer.retrieve(latest_sub.stripe_customer_id)
                if customer and not getattr(customer, 'deleted', False): # Check if customer is not deleted
                    return customer
            except StripeError as e:
                logger.warning(f"Failed to retrieve Stripe customer {latest_sub.stripe_customer_id} for user {user_id}: {e}. Will create a new one.")

        user_stmt = select(DBUser.email, DBUser.full_name).where(DBUser.id == user_id)
        user_result = await self.db.execute(user_stmt)
        user_details = user_result.first()
        
        if not user_details:
            raise NotFoundException(f"User {user_id} not found for Stripe customer creation.")

        customer_data = {
            "email": user_details.email,
            "name": user_details.full_name if user_details.full_name else user_details.email,
            "metadata": {"app_user_id": str(user_id)}
        }
        stripe_customer = await stripe.Customer.create(**customer_data)
        
        # Consider if stripe_customer_id should be updated on the user model or if new subscriptions always pick it up.
        logger.info(f"Created Stripe customer {stripe_customer.id} for user {user_id}")
        return stripe_customer

    async def _handle_subscription_updated_async(self, data: Dict[str, Any]) -> None:
        """Handle 'customer.subscription.updated' webhook event asynchronously."""
        stripe_subscription_id = data.get("id")
        if not stripe_subscription_id:
            logger.error("Webhook customer.subscription.updated: Missing subscription ID in event data.")
            return

        subscription = await self._get_by_stripe_id_async(stripe_subscription_id)
        if not subscription:
            # This could be a new subscription initiated from Stripe's side or after a local DB issue.
            # Decide on business logic: create a new local subscription record or log/ignore.
            # For now, log and return if no matching local subscription.
            logger.warning(f"Webhook customer.subscription.updated: No local subscription found for stripe_id {stripe_subscription_id}. Event data: {data}")
            # Optionally, you could create one:
            # user_id = data.get("metadata", {}).get("app_user_id") # If you store app_user_id in Stripe metadata
            # if user_id:
            #    create_data = { ... map data from webhook to local model ... }
            #    await super().create_async(obj_in=create_data)
            return

        # Determine tier from price_id - this is crucial and needs robust mapping
        tier_value = None
        try:
            price_id = data.get("items", {}).get("data", [{}])[0].get("price", {}).get("id")
            if price_id:
                # Reverse lookup from settings.STRIPE_PRICE_IDS
                for tier_enum_val, s_price_id in self.settings.STRIPE_PRICE_IDS.items():
                    if s_price_id == price_id:
                        tier_value = tier_enum_val # tier_enum_val should match SubscriptionTier enum values
                        break
            if not tier_value:
                 logger.warning(f"Webhook: Could not determine tier for price_id {price_id} in subscription update for {stripe_subscription_id}")

        except (IndexError, KeyError, AttributeError) as e:
            logger.error(f"Error parsing tier from webhook data for {stripe_subscription_id}: {e}. Data: {data.get('items')}")


        update_data = {
            "status": data.get("status"),
            "current_period_start": datetime.fromtimestamp(data.get("current_period_start")) if data.get("current_period_start") else None,
            "current_period_end": datetime.fromtimestamp(data.get("current_period_end")) if data.get("current_period_end") else None,
            "trial_start": datetime.fromtimestamp(data.get("trial_start")) if data.get("trial_start") else None,
            "trial_end": datetime.fromtimestamp(data.get("trial_end")) if data.get("trial_end") else None,
            "canceled_at": datetime.fromtimestamp(data.get("canceled_at")) if data.get("canceled_at") else None,
        }
        if tier_value: # Only update tier if successfully determined
            update_data["tier"] = tier_value

        update_data_filtered = {k: v for k, v in update_data.items() if v is not None or k == 'trial_start' or k == 'trial_end' or k == 'canceled_at'} # Allow explicit None for date fields

        await super().update_async(db_obj=subscription, obj_in=update_data_filtered)
        logger.info(f"Webhook: Subscription {subscription.id} (Stripe: {stripe_subscription_id}) updated. Status: {update_data.get('status')}, Tier: {tier_value}")

    async def _handle_subscription_deleted_async(self, data: Dict[str, Any]) -> None:
        """Handle 'customer.subscription.deleted' (cancellation) webhook event asynchronously."""
        stripe_subscription_id = data.get("id")
        if not stripe_subscription_id:
            logger.error("Webhook customer.subscription.deleted: Missing subscription ID.")
            return

        subscription = await self._get_by_stripe_id_async(stripe_subscription_id)
        if not subscription:
            logger.warning(f"Webhook customer.subscription.deleted: No subscription found for stripe_id {stripe_subscription_id}")
            return

        update_data = {
            "status": data.get("status", "canceled"), # Stripe sends 'canceled'
            "canceled_at": datetime.fromtimestamp(data.get("canceled_at")) if data.get("canceled_at") else datetime.utcnow(),
            # current_period_end might also be relevant from data.get("current_period_end")
        }
        await super().update_async(db_obj=subscription, obj_in=update_data)
        logger.info(f"Webhook: Subscription {subscription.id} (Stripe: {stripe_subscription_id}) updated for deletion. Status: {update_data['status']}.")

    async def _handle_payment_failed_async(self, data: Dict[str, Any]) -> None:
        """Handle 'invoice.payment_failed' webhook event asynchronously."""
        stripe_subscription_id = data.get("subscription") 
        if not stripe_subscription_id:
            logger.warning(f"Webhook invoice.payment_failed: Missing subscription_id. Invoice data: {data}")
            return
            
        subscription = await self._get_by_stripe_id_async(stripe_subscription_id)
        if not subscription:
            logger.warning(f"Webhook invoice.payment_failed: No subscription found for stripe_id {stripe_subscription_id}")
            return
        
        # The 'data' object for invoice.payment_failed is an Invoice object.
        # The subscription status is what we generally care about.
        stripe_subscription_obj = await stripe.Subscription.retrieve(stripe_subscription_id)
        new_status_from_stripe = stripe_subscription_obj.status # e.g., 'active', 'past_due', 'unpaid', 'canceled'

        update_data = {"status": new_status_from_stripe}
        await super().update_async(db_obj=subscription, obj_in=update_data)
        logger.info(f"Webhook: Payment failed for subscription {subscription.id} (Stripe: {stripe_subscription_id}). Status updated to {new_status_from_stripe}.")
        # Optionally, trigger notifications or other business logic for payment failure.

# Synchronous session provider for get_subscription_service
def get_sync_db_session() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_subscription_service(
    db: Session = Depends(get_sync_db_session), # Use the local sync session provider
    app_settings: Settings = Depends(lambda: settings)
) -> SubscriptionService:
    logger.warning("Instantiating SubscriptionService with a synchronous DB session. Most methods are async and will error if DB ops are attempted without running an event loop.")
    return SubscriptionService(db=db, app_settings=app_settings)

async def get_async_subscription_service(
    db: AsyncSession = Depends(get_async_db),
    app_settings: Settings = Depends(lambda: settings)
) -> SubscriptionService:
    return SubscriptionService(db=db, app_settings=app_settings) 