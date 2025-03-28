"""
Stripe utility module for handling payment and subscription operations.
This module provides functions for managing Stripe customers, subscriptions, and webhook events.
"""

import datetime
from typing import Dict, Any, Optional
import stripe
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.user import User
from app.models.subscription import SubscriptionTier
from app.core.logging import get_logger

logger = get_logger(__name__)

# Configure Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY

# Subscription price IDs
SUBSCRIPTION_PRICES = {
    SubscriptionTier.BASIC: settings.STRIPE_BASIC_PRICE_ID,
    SubscriptionTier.PRO: settings.STRIPE_PRO_PRICE_ID,
    SubscriptionTier.ENTERPRISE: settings.STRIPE_ENTERPRISE_PRICE_ID
}

async def create_customer(user: User, db: Session) -> str:
    """Create a new Stripe customer for a user."""
    try:
        # Create customer in Stripe
        customer = stripe.Customer.create(
            email=user.email,
            name=f"{user.first_name} {user.last_name}",
            metadata={
                "user_id": str(user.id)
            }
        )
        
        # Update user with Stripe customer ID
        user.stripe_customer_id = customer.id
        db.commit()
        
        logger.info(f"Created Stripe customer for user {user.id}")
        return customer.id
        
    except stripe.error.StripeError as e:
        logger.error(f"Failed to create Stripe customer for user {user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create payment account"
        )

async def create_checkout_session(
    user: User,
    price_id: str,
    success_url: str,
    cancel_url: str
) -> Dict[str, Any]:
    """Create a Stripe checkout session for subscription."""
    try:
        # Get or create Stripe customer
        if not user.stripe_customer_id:
            await create_customer(user, db)
        
        # Create checkout session
        session = stripe.checkout.Session.create(
            customer=user.stripe_customer_id,
            payment_method_types=["card"],
            line_items=[{
                "price": price_id,
                "quantity": 1,
            }],
            mode="subscription",
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                "user_id": str(user.id)
            }
        )
        
        logger.info(f"Created checkout session for user {user.id}")
        return {
            "session_id": session.id,
            "url": session.url
        }
        
    except stripe.error.StripeError as e:
        logger.error(f"Failed to create checkout session for user {user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create checkout session"
        )

async def handle_subscription_event(event: Dict[str, Any], db: Session) -> None:
    """Handle Stripe subscription events."""
    try:
        event_type = event["type"]
        data = event["data"]["object"]
        
        if event_type == "customer.subscription.created":
            # Handle new subscription
            user_id = data["metadata"]["user_id"]
            user = db.query(User).filter(User.id == user_id).first()
            
            if user:
                # Update user subscription
                user.subscription_status = "active"
                user.subscription_tier = data["items"]["data"][0]["price"]["metadata"]["tier"]
                user.subscription_start_date = datetime.datetime.fromtimestamp(data["current_period_start"])
                user.subscription_end_date = datetime.datetime.fromtimestamp(data["current_period_end"])
                db.commit()
                
                logger.info(f"Updated subscription for user {user_id}")
        
        elif event_type == "customer.subscription.updated":
            # Handle subscription update
            user_id = data["metadata"]["user_id"]
            user = db.query(User).filter(User.id == user_id).first()
            
            if user:
                # Update user subscription
                user.subscription_status = data["status"]
                user.subscription_tier = data["items"]["data"][0]["price"]["metadata"]["tier"]
                user.subscription_end_date = datetime.datetime.fromtimestamp(data["current_period_end"])
                db.commit()
                
                logger.info(f"Updated subscription for user {user_id}")
        
        elif event_type == "customer.subscription.deleted":
            # Handle subscription cancellation
            user_id = data["metadata"]["user_id"]
            user = db.query(User).filter(User.id == user_id).first()
            
            if user:
                # Update user subscription
                user.subscription_status = "cancelled"
                user.subscription_end_date = datetime.datetime.fromtimestamp(data["canceled_at"])
                db.commit()
                
                logger.info(f"Cancelled subscription for user {user_id}")
        
    except Exception as e:
        logger.error(f"Failed to handle subscription event: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process subscription event"
        ) 