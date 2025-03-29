"""Stripe client configuration and initialization."""
import stripe
from app.core.config import settings
from app.core.logging import get_logger

# Initialize logger
logger = get_logger(__name__)

# Configure Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY
stripe.api_version = "2023-10-16"  # Use latest stable version

# Export configured client
stripe_client = stripe

def verify_webhook_signature(payload: bytes, sig_header: str, secret: str) -> bool:
    """
    Verify Stripe webhook signature.
    
    Args:
        payload: Raw request body
        sig_header: Stripe signature header
        secret: Webhook signing secret
        
    Returns:
        bool: True if signature is valid
        
    Raises:
        StripeError: If signature verification fails
    """
    try:
        stripe.Webhook.construct_event(
            payload=payload,
            sig_header=sig_header,
            secret=secret
        )
        return True
    except stripe.error.SignatureVerificationError as e:
        logger.error("Webhook signature verification failed", exc_info=e)
        return False
    except Exception as e:
        logger.error("Error verifying webhook signature", exc_info=e)
        return False 