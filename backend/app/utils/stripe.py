import stripe
from typing import Optional, Dict, Any
from app.core.config import settings
from app.core.logging import get_logger

# Initialize logger
logger = get_logger(__name__)

stripe.api_key = settings.STRIPE_SECRET_KEY

class StripeService:
    @staticmethod
    async def create_customer(email: str, name: Optional[str] = None) -> Dict[str, Any]:
        try:
            customer = stripe.Customer.create(
                email=email,
                name=name
            )
            return customer
        except stripe.error.StripeError as e:
            logger.error(f"Stripe customer creation failed: {str(e)}")
            raise

    @staticmethod
    async def create_subscription(
        customer_id: str,
        price_id: str,
        payment_method_id: Optional[str] = None
    ) -> Dict[str, Any]:
        try:
            if payment_method_id:
                # Attach payment method to customer
                stripe.PaymentMethod.attach(
                    payment_method_id,
                    customer=customer_id
                )
                # Set as default payment method
                stripe.Customer.modify(
                    customer_id,
                    invoice_settings={
                        "default_payment_method": payment_method_id
                    }
                )

            # Create subscription
            subscription = stripe.Subscription.create(
                customer=customer_id,
                items=[{"price": price_id}],
                payment_behavior="default_incomplete",
                payment_settings={"save_default_payment_method": "on_subscription"},
                expand=["latest_invoice.payment_intent"]
            )
            return subscription
        except stripe.error.StripeError as e:
            logger.error(f"Stripe subscription creation failed: {str(e)}")
            raise

    @staticmethod
    async def cancel_subscription(subscription_id: str) -> Dict[str, Any]:
        try:
            subscription = stripe.Subscription.delete(subscription_id)
            return subscription
        except stripe.error.StripeError as e:
            logger.error(f"Stripe subscription cancellation failed: {str(e)}")
            raise

    @staticmethod
    async def get_subscription(subscription_id: str) -> Dict[str, Any]:
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            return subscription
        except stripe.error.StripeError as e:
            logger.error(f"Stripe subscription retrieval failed: {str(e)}")
            raise

    @staticmethod
    async def update_subscription(
        subscription_id: str,
        price_id: str
    ) -> Dict[str, Any]:
        try:
            subscription = stripe.Subscription.modify(
                subscription_id,
                items=[{
                    "id": subscription_id,
                    "price": price_id
                }]
            )
            return subscription
        except stripe.error.StripeError as e:
            logger.error(f"Stripe subscription update failed: {str(e)}")
            raise

    @staticmethod
    async def create_checkout_session(
        customer_id: str,
        price_id: str,
        success_url: str,
        cancel_url: str
    ) -> Dict[str, Any]:
        try:
            session = stripe.checkout.Session.create(
                customer=customer_id,
                payment_method_types=["card"],
                line_items=[{
                    "price": price_id,
                    "quantity": 1,
                }],
                mode="subscription",
                success_url=success_url,
                cancel_url=cancel_url,
            )
            return session
        except stripe.error.StripeError as e:
            logger.error(f"Stripe checkout session creation failed: {str(e)}")
            raise

    @staticmethod
    async def create_portal_session(customer_id: str, return_url: str) -> Dict[str, Any]:
        try:
            session = stripe.billing_portal.Session.create(
                customer=customer_id,
                return_url=return_url,
            )
            return session
        except stripe.error.StripeError as e:
            logger.error(f"Stripe portal session creation failed: {str(e)}")
            raise 