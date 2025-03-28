"""
Stripe utility module for handling payment and subscription operations.
This module provides functions to interact with the Stripe API for customer management,
checkout sessions, and subscription handling.
"""

from datetime import datetime
from typing import Dict, Any, Optional

import stripe
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ..config import settings
from ..models import User, SubscriptionTier

# Configure Stripe API key
stripe.api_key = settings.STRIPE_SECRET_KEY

# Subscription price IDs
SUBSCRIPTION_PRICES = {
    "basic": settings.STRIPE_BASIC_PRICE_ID,
    "premium": settings.STRIPE_PREMIUM_PRICE_ID,
}

async def create_customer(email: str, name: Optional[str] = None) -> Dict[str, Any]:
    """
    Create a new Stripe customer.
    
    Args:
        email: Customer's email address
        name: Optional customer name
        
    Returns:
        Dict containing the created customer information
        
    Raises:
        HTTPException: If customer creation fails
    """
    try:
        customer = stripe.Customer.create(
            email=email,
            name=name,
            metadata={"source": "formiq_app"}
        )
        return customer
    except stripe.error.StripeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error creating Stripe customer: {str(exc)}"
        ) from exc

async def create_checkout_session(
    customer_id: str,
    price_id: str,
    success_url: str,
    cancel_url: str
) -> Dict[str, Any]:
    """
    Create a Stripe checkout session for subscription.
    
    Args:
        customer_id: Stripe customer ID
        price_id: Stripe price ID for the subscription
        success_url: URL to redirect after successful payment
        cancel_url: URL to redirect after cancelled payment
        
    Returns:
        Dict containing the checkout session information
        
    Raises:
        HTTPException: If session creation fails
    """
    try:
        checkout_session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            line_items=[
                {
                    "price": price_id,
                    "quantity": 1,
                },
            ],
            mode="subscription",
            success_url=success_url,
            cancel_url=cancel_url,
        )
        return checkout_session
    except stripe.error.StripeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error creating checkout session: {str(exc)}"
        ) from exc

async def handle_subscription_event(event_data: Dict[str, Any], session: Session) -> Dict[str, Any]:
    """
    Handle Stripe subscription events.
    
    Args:
        event_data: Webhook event data from Stripe
        session: Database session
        
    Returns:
        Dict containing the status and message of the operation
    """
    event_type = event_data["type"]
    event_object = event_data["data"]["object"]
    
    # Handle subscription created or updated
    if event_type in ["customer.subscription.created", "customer.subscription.updated"]:
        subscription = event_object
        customer_id = subscription["customer"]
        subscription_status = subscription["status"]
        
        # Find the user with this customer ID
        user = session.query(User).filter(User.stripe_customer_id == customer_id).first()
        if not user:
            return {"status": "error", "message": "User not found"}
        
        # Get the subscription item's price ID to determine tier
        if subscription["items"]["data"]:
            price_id = subscription["items"]["data"][0]["price"]["id"]
            
            # Determine subscription tier from price ID
            tier = None
            for key, value in SUBSCRIPTION_PRICES.items():
                if value == price_id:
                    tier = key
            
            if tier:
                # Calculate end date
                current_period_end = subscription["current_period_end"]
                end_date = datetime.fromtimestamp(current_period_end)
                
                # Update user subscription
                user.subscription_tier = SubscriptionTier(tier)
                user.subscription_end_date = end_date
                user.stripe_subscription_id = subscription["id"]
                session.commit()
                
                return {
                    "status": "success",
                    "message": f"Subscription {subscription_status} for user {user.email}"
                }
    
    # Handle subscription cancelled
    elif event_type == "customer.subscription.deleted":
        subscription = event_object
        customer_id = subscription["customer"]
        
        # Find the user with this customer ID
        user = session.query(User).filter(User.stripe_customer_id == customer_id).first()
        if not user:
            return {"status": "error", "message": "User not found"}
        
        # Downgrade to free tier
        user.subscription_tier = SubscriptionTier.FREE
        user.subscription_end_date = None
        user.stripe_subscription_id = None
        session.commit()
        
        return {
            "status": "success",
            "message": f"Subscription cancelled for user {user.email}"
        }
    
    return {"status": "ignored", "message": f"Event {event_type} not handled"} 