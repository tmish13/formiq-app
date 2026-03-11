import pytest
from datetime import datetime, timedelta
from app.services.subscription import SubscriptionService, SubscriptionError
from app.models.enums import SubscriptionTier
from app.models.user import User
from app.models.subscription import Subscription
from sqlalchemy.orm import Session
from unittest.mock import Mock, patch, MagicMock
import stripe
from app.core.config import settings
from app.core.exceptions import ValidationError, PaymentError

@pytest.fixture
def mock_stripe():
    with patch('app.services.subscription.stripe') as mock:
        # Mock Customer
        mock_customer = MagicMock()
        mock_customer.id = "cus_123"
        mock.Customer.create.return_value = mock_customer

        # Mock Subscription
        mock_subscription = MagicMock()
        mock_subscription.id = "sub_123"
        mock_subscription.status = "active"
        mock_subscription.current_period_start = int(datetime.now().timestamp())
        mock_subscription.current_period_end = int((datetime.now() + timedelta(days=30)).timestamp())
        mock_subscription.cancel_at_period_end = False
        mock.Subscription.create.return_value = mock_subscription
        mock.Subscription.modify.return_value = mock_subscription
        mock.Subscription.retrieve.return_value = mock_subscription
        mock.Subscription.delete.return_value = mock_subscription

        yield mock

@pytest.fixture
def mock_db_session():
    """Create a mock database session"""
    session = Mock(spec=Session)
    session.query.return_value.filter.return_value.first.return_value = None
    session.add = Mock()
    session.commit = Mock()
    return session

@pytest.fixture
def subscription_service(mock_db_session, mock_stripe):
    """Create a subscription service instance"""
    return SubscriptionService(db=mock_db_session)

@pytest.fixture
def test_user(mock_db_session):
    """Create a test user"""
    user = User(
        id=1,
        email="test@example.com",
        username="testuser",
        subscription_tier=SubscriptionTier.FREE
    )
    mock_db_session.add(user)
    mock_db_session.commit()
    mock_db_session.refresh(user)
    return user

@pytest.fixture
def test_subscription(mock_db_session, test_user):
    subscription = Subscription(
        user_id=test_user.id,
        stripe_subscription_id="sub_123",
        stripe_customer_id="cus_123",
        status="active",
        current_period_start=datetime.now(),
        current_period_end=datetime.now() + timedelta(days=30),
        cancel_at_period_end=False
    )
    mock_db_session.add(subscription)
    mock_db_session.commit()
    mock_db_session.refresh(subscription)
    return subscription

def test_create_subscription_free_tier(subscription_service, test_user, mock_db_session):
    """Test creating a free subscription"""
    subscription = subscription_service.create_subscription(
        user=test_user,
        tier=SubscriptionTier.FREE
    )
    
    assert subscription.tier == SubscriptionTier.FREE
    assert subscription.user_id == test_user.id
    assert subscription.stripe_subscription_id is None
    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called_once()

def test_create_subscription_paid_tier(subscription_service, test_user, mock_stripe):
    """Test creating a paid subscription"""
    subscription = subscription_service.create_subscription(
        user=test_user,
        tier=SubscriptionTier.PRO,
        payment_method_id="pm_test123"
    )
    
    assert subscription.tier == SubscriptionTier.PRO
    assert subscription.stripe_subscription_id == "sub_test123"
    mock_stripe["subscription"].create.assert_called_once()

def test_create_subscription_invalid_tier(subscription_service, test_user):
    """Test creating a subscription with invalid tier"""
    with pytest.raises(InvalidTierError):
        subscription_service.create_subscription(
            user=test_user,
            tier="invalid_tier"
        )

def test_upgrade_subscription(subscription_service, test_user, mock_stripe):
    """Test upgrading a subscription"""
    # Setup initial subscription
    test_user.subscription_tier = SubscriptionTier.FREE
    test_user.stripe_customer_id = "cus_test123"
    
    # Upgrade to PRO
    subscription = subscription_service.upgrade_subscription(
        user=test_user,
        new_tier=SubscriptionTier.PRO,
        payment_method_id="pm_test123"
    )
    
    assert subscription.tier == SubscriptionTier.PRO
    assert subscription.stripe_subscription_id == "sub_test123"
    mock_stripe["subscription"].create.assert_called_once()

def test_downgrade_subscription(subscription_service, test_user, mock_stripe):
    """Test downgrading a subscription"""
    # Setup initial subscription
    test_user.subscription_tier = SubscriptionTier.PRO
    test_user.stripe_customer_id = "cus_test123"
    mock_stripe["subscription"].retrieve.return_value = {"id": "sub_test123"}
    
    subscription = subscription_service.downgrade_subscription(
        user=test_user,
        new_tier=SubscriptionTier.FREE
    )
    
    assert subscription.tier == SubscriptionTier.FREE
    assert subscription.stripe_subscription_id is None
    mock_stripe["subscription"].delete.assert_called_once()

def test_cancel_subscription(subscription_service, test_user, mock_stripe):
    """Test canceling a subscription"""
    # Setup subscription
    test_user.subscription_tier = SubscriptionTier.PRO
    test_user.stripe_customer_id = "cus_test123"
    mock_stripe["subscription"].retrieve.return_value = {"id": "sub_test123"}
    
    subscription_service.cancel_subscription(user=test_user)
    
    assert test_user.subscription_tier == SubscriptionTier.FREE
    mock_stripe["subscription"].delete.assert_called_once()

def test_check_subscription_status_active(subscription_service, test_user):
    """Test checking active subscription status"""
    test_user.subscription_tier = SubscriptionTier.PRO
    test_user.subscription_end_date = datetime.now() + timedelta(days=30)
    
    status = subscription_service.check_subscription_status(user=test_user)
    assert status.is_active is True
    assert status.days_remaining == 30

def test_check_subscription_status_expired(subscription_service, test_user):
    """Test checking expired subscription status"""
    test_user.subscription_tier = SubscriptionTier.PRO
    test_user.subscription_end_date = datetime.now() - timedelta(days=1)
    
    status = subscription_service.check_subscription_status(user=test_user)
    assert status.is_active is False
    assert status.days_remaining == -1

def test_handle_webhook_subscription_updated(subscription_service, mock_db_session):
    """Test handling subscription updated webhook"""
    event_data = {
        "type": "customer.subscription.updated",
        "data": {
            "object": {
                "id": "sub_test123",
                "customer": "cus_test123",
                "status": "active",
                "current_period_end": int((datetime.now() + timedelta(days=30)).timestamp())
            }
        }
    }
    
    subscription_service.handle_webhook(event_data)
    mock_db_session.commit.assert_called_once()

def test_handle_webhook_subscription_deleted(subscription_service, mock_db_session):
    """Test handling subscription deleted webhook"""
    event_data = {
        "type": "customer.subscription.deleted",
        "data": {
            "object": {
                "id": "sub_test123",
                "customer": "cus_test123"
            }
        }
    }
    
    subscription_service.handle_webhook(event_data)
    mock_db_session.commit.assert_called_once()

def test_get_subscription_usage(subscription_service, test_user):
    """Test getting subscription usage"""
    test_user.subscription_tier = SubscriptionTier.PRO
    
    usage = subscription_service.get_subscription_usage(user=test_user)
    assert isinstance(usage.form_checks_remaining, int)
    assert isinstance(usage.total_form_checks, int)

def test_validate_subscription_limits(subscription_service, test_user):
    """Test validating subscription limits"""
    test_user.subscription_tier = SubscriptionTier.FREE
    
    # Should raise error when limit exceeded
    with pytest.raises(SubscriptionError):
        subscription_service.validate_subscription_limits(
            user=test_user,
            action="form_check",
            current_count=10  # Assuming FREE tier limit is less than 10
        )

def test_handle_payment_failure(subscription_service, test_user, mock_stripe):
    """Test handling payment failure"""
    test_user.subscription_tier = SubscriptionTier.PRO
    test_user.stripe_customer_id = "cus_test123"
    
    mock_stripe["subscription"].retrieve.return_value = {
        "id": "sub_test123",
        "status": "past_due"
    }
    
    with pytest.raises(SubscriptionError):
        subscription_service.handle_payment_failure(user=test_user)
    
    assert test_user.subscription_tier == SubscriptionTier.FREE

def test_reactivate_subscription(subscription_service, test_user, mock_stripe):
    """Test reactivating a subscription"""
    test_user.subscription_tier = SubscriptionTier.FREE
    test_user.stripe_customer_id = "cus_test123"
    
    subscription = subscription_service.reactivate_subscription(
        user=test_user,
        tier=SubscriptionTier.PRO,
        payment_method_id="pm_test123"
    )
    
    assert subscription.tier == SubscriptionTier.PRO
    assert subscription.stripe_subscription_id == "sub_test123"
    mock_stripe["subscription"].create.assert_called_once()

def test_create_subscription(subscription_service, test_user, mock_stripe):
    """Test creating a new subscription."""
    price_id = "price_123"
    payment_method_id = "pm_123"

    subscription = subscription_service.create_subscription(
        user=test_user,
        price_id=price_id,
        payment_method_id=payment_method_id
    )

    assert subscription.user_id == test_user.id
    assert subscription.stripe_subscription_id == "sub_123"
    assert subscription.stripe_customer_id == "cus_123"
    assert subscription.status == "active"
    assert not subscription.cancel_at_period_end

    # Verify Stripe API calls
    mock_stripe.Customer.create.assert_called_once_with(
        email=test_user.email,
        metadata={"user_id": test_user.id}
    )
    mock_stripe.Subscription.create.assert_called_once()

def test_create_subscription_existing_customer(subscription_service, test_user, mock_stripe):
    """Test creating a subscription for user with existing Stripe customer."""
    test_user.stripe_customer_id = "cus_existing"
    price_id = "price_123"

    subscription = subscription_service.create_subscription(
        user=test_user,
        price_id=price_id
    )

    assert subscription.stripe_customer_id == "cus_existing"
    mock_stripe.Customer.create.assert_not_called()

def test_create_subscription_stripe_error(subscription_service, test_user, mock_stripe):
    """Test handling of Stripe API errors during subscription creation."""
    mock_stripe.Subscription.create.side_effect = stripe.error.StripeError("API Error")
    price_id = "price_123"

    with pytest.raises(PaymentError):
        subscription_service.create_subscription(
            user=test_user,
            price_id=price_id
        )

def test_get_subscription(subscription_service, test_subscription):
    """Test retrieving a subscription by ID."""
    subscription = subscription_service.get_subscription(test_subscription.id)
    assert subscription.id == test_subscription.id

def test_get_subscription_not_found(subscription_service):
    """Test retrieving a non-existent subscription."""
    with pytest.raises(ValidationError):
        subscription_service.get_subscription(999)

def test_get_user_subscription(subscription_service, test_subscription):
    """Test getting active subscription for a user."""
    subscription = subscription_service.get_user_subscription(test_subscription.user_id)
    assert subscription.id == test_subscription.id

def test_get_user_subscription_no_active(subscription_service, test_user):
    """Test getting subscription when user has no active subscription."""
    subscription = subscription_service.get_user_subscription(test_user.id)
    assert subscription is None

def test_update_subscription(subscription_service, test_subscription, mock_stripe):
    """Test updating subscription details."""
    price_id = "price_new"
    cancel_at_period_end = True

    subscription = subscription_service.update_subscription(
        subscription=test_subscription,
        price_id=price_id,
        cancel_at_period_end=cancel_at_period_end
    )

    assert subscription.cancel_at_period_end == cancel_at_period_end
    mock_stripe.Subscription.modify.assert_called()

def test_update_subscription_stripe_error(subscription_service, test_subscription, mock_stripe):
    """Test handling of Stripe API errors during subscription update."""
    mock_stripe.Subscription.modify.side_effect = stripe.error.StripeError("API Error")

    with pytest.raises(PaymentError):
        subscription_service.update_subscription(
            subscription=test_subscription,
            price_id="price_new"
        )

def test_cancel_subscription(subscription_service, test_subscription, mock_stripe):
    """Test canceling a subscription."""
    subscription = subscription_service.cancel_subscription(test_subscription)
    assert subscription.status == "canceled"
    mock_stripe.Subscription.delete.assert_called_once()

def test_cancel_subscription_stripe_error(subscription_service, test_subscription, mock_stripe):
    """Test handling of Stripe API errors during subscription cancellation."""
    mock_stripe.Subscription.delete.side_effect = stripe.error.StripeError("API Error")

    with pytest.raises(PaymentError):
        subscription_service.cancel_subscription(test_subscription)

def test_handle_webhook_event(subscription_service, test_subscription):
    """Test handling Stripe webhook events."""
    event = {
        "type": "customer.subscription.updated",
        "data": {
            "object": {
                "id": test_subscription.stripe_subscription_id,
                "status": "past_due",
                "current_period_end": int((datetime.now() + timedelta(days=15)).timestamp()),
                "cancel_at_period_end": True
            }
        }
    }

    subscription_service.handle_webhook_event(event)
    
    # Refresh subscription from database
    subscription = subscription_service.get_subscription(test_subscription.id)
    assert subscription.status == "past_due"
    assert subscription.cancel_at_period_end

def test_get_subscription_usage(subscription_service, test_subscription, mock_stripe):
    """Test getting subscription usage metrics."""
    usage = subscription_service.get_subscription_usage(test_subscription)
    
    assert "current_period_start" in usage
    assert "current_period_end" in usage
    assert "status" in usage
    assert "cancel_at_period_end" in usage
    assert "latest_invoice" in usage

def test_get_subscription_usage_stripe_error(subscription_service, test_subscription, mock_stripe):
    """Test handling of Stripe API errors when getting subscription usage."""
    mock_stripe.Subscription.retrieve.side_effect = stripe.error.StripeError("API Error")

    with pytest.raises(PaymentError):
        subscription_service.get_subscription_usage(test_subscription) 