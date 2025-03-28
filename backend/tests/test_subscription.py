import pytest
from datetime import datetime, timedelta
from ..services.subscription import (
    SubscriptionService,
    SubscriptionTier,
    SubscriptionError,
    InvalidTierError,
    ExpiredSubscriptionError
)
from ..models.user import User
from ..models.subscription import Subscription
from sqlalchemy.orm import Session
from unittest.mock import Mock, patch
import stripe

@pytest.fixture
def mock_stripe():
    """Mock Stripe API responses"""
    with patch('stripe.Customer') as mock_customer, \
         patch('stripe.Subscription') as mock_subscription, \
         patch('stripe.Price') as mock_price:
        
        mock_customer.create.return_value = {"id": "cus_test123"}
        mock_customer.retrieve.return_value = {"id": "cus_test123"}
        
        mock_subscription.create.return_value = {
            "id": "sub_test123",
            "status": "active",
            "current_period_end": int((datetime.now() + timedelta(days=30)).timestamp())
        }
        
        mock_price.retrieve.return_value = {"id": "price_test123"}
        
        yield {
            "customer": mock_customer,
            "subscription": mock_subscription,
            "price": mock_price
        }

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
def test_user():
    """Create a test user"""
    return User(
        id=1,
        email="test@example.com",
        username="testuser",
        subscription_tier=SubscriptionTier.FREE
    )

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