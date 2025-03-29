import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from app.services.user import UserService, UserError
from app.models.user import User
from app.models.subscription import Subscription
from sqlalchemy.orm import Session
from app.core.exceptions import ValidationError, NotFoundError, AuthenticationError
from app.core.security import get_password_hash, verify_password, create_access_token
from app.core.config import settings

@pytest.fixture
def mock_db_session():
    """Create a mock database session"""
    session = Mock(spec=Session)
    session.query.return_value.filter.return_value.first.return_value = None
    session.add = Mock()
    session.commit = Mock()
    return session

@pytest.fixture
def user_service(mock_db_session):
    """Create a user service instance"""
    return UserService(db=mock_db_session)

@pytest.fixture
def test_user():
    """Create a test user"""
    return User(
        id=1,
        email="test@example.com",
        username="testuser",
        hashed_password=get_password_hash("testpassword"),
        is_active=True,
        is_verified=True,
        subscription_tier="PRO",
        created_at=datetime.now()
    )

def test_create_user(user_service, mock_db_session):
    """Test creating a new user"""
    user_data = {
        "email": "new@example.com",
        "username": "newuser",
        "password": "newpassword",
        "subscription_tier": "FREE"
    }
    
    user = user_service.create_user(**user_data)
    
    assert user.email == user_data["email"]
    assert user.username == user_data["username"]
    assert verify_password(user_data["password"], user.hashed_password)
    assert user.subscription_tier == user_data["subscription_tier"]
    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called_once()

def test_get_user_by_id(user_service, test_user, mock_db_session):
    """Test retrieving a user by ID"""
    mock_db_session.query.return_value.filter.return_value.first.return_value = test_user
    
    user = user_service.get_user_by_id(user_id=1)
    
    assert user.id == test_user.id
    assert user.email == test_user.email
    assert user.username == test_user.username

def test_get_user_by_email(user_service, test_user, mock_db_session):
    """Test retrieving a user by email"""
    mock_db_session.query.return_value.filter.return_value.first.return_value = test_user
    
    user = user_service.get_user_by_email(email="test@example.com")
    
    assert user.id == test_user.id
    assert user.email == test_user.email
    assert user.username == test_user.username

def test_get_user_by_username(user_service, test_user, mock_db_session):
    """Test retrieving a user by username"""
    mock_db_session.query.return_value.filter.return_value.first.return_value = test_user
    
    user = user_service.get_user_by_username(username="testuser")
    
    assert user.id == test_user.id
    assert user.email == test_user.email
    assert user.username == test_user.username

def test_authenticate_user(user_service, test_user, mock_db_session):
    """Test user authentication"""
    mock_db_session.query.return_value.filter.return_value.first.return_value = test_user
    
    user = user_service.authenticate_user(
        email="test@example.com",
        password="testpassword"
    )
    
    assert user.id == test_user.id
    assert user.email == test_user.email
    assert user.username == test_user.username

def test_authenticate_user_invalid_password(user_service, test_user, mock_db_session):
    """Test authentication with invalid password"""
    mock_db_session.query.return_value.filter.return_value.first.return_value = test_user
    
    with pytest.raises(AuthenticationError):
        user_service.authenticate_user(
            email="test@example.com",
            password="wrongpassword"
        )

def test_update_user(user_service, test_user, mock_db_session):
    """Test updating user information"""
    mock_db_session.query.return_value.filter.return_value.first.return_value = test_user
    
    update_data = {
        "username": "updateduser",
        "email": "updated@example.com"
    }
    
    updated_user = user_service.update_user(
        user_id=1,
        **update_data
    )
    
    assert updated_user.username == update_data["username"]
    assert updated_user.email == update_data["email"]
    mock_db_session.commit.assert_called_once()

def test_change_password(user_service, test_user, mock_db_session):
    """Test changing user password"""
    mock_db_session.query.return_value.filter.return_value.first.return_value = test_user
    
    new_password = "newpassword123"
    user_service.change_password(
        user_id=1,
        current_password="testpassword",
        new_password=new_password
    )
    
    assert verify_password(new_password, test_user.hashed_password)
    mock_db_session.commit.assert_called_once()

def test_change_password_invalid_current(user_service, test_user, mock_db_session):
    """Test changing password with invalid current password"""
    mock_db_session.query.return_value.filter.return_value.first.return_value = test_user
    
    with pytest.raises(AuthenticationError):
        user_service.change_password(
            user_id=1,
            current_password="wrongpassword",
            new_password="newpassword123"
        )

def test_verify_user(user_service, test_user, mock_db_session):
    """Test user verification"""
    test_user.is_verified = False
    mock_db_session.query.return_value.filter.return_value.first.return_value = test_user
    
    user_service.verify_user(user_id=1)
    
    assert test_user.is_verified is True
    mock_db_session.commit.assert_called_once()

def test_deactivate_user(user_service, test_user, mock_db_session):
    """Test user deactivation"""
    mock_db_session.query.return_value.filter.return_value.first.return_value = test_user
    
    user_service.deactivate_user(user_id=1)
    
    assert test_user.is_active is False
    mock_db_session.commit.assert_called_once()

def test_activate_user(user_service, test_user, mock_db_session):
    """Test user activation"""
    test_user.is_active = False
    mock_db_session.query.return_value.filter.return_value.first.return_value = test_user
    
    user_service.activate_user(user_id=1)
    
    assert test_user.is_active is True
    mock_db_session.commit.assert_called_once()

def test_update_subscription(user_service, test_user, mock_db_session):
    """Test updating user subscription"""
    mock_db_session.query.return_value.filter.return_value.first.return_value = test_user
    
    subscription_data = {
        "tier": "PREMIUM",
        "start_date": datetime.now(),
        "end_date": datetime.now() + timedelta(days=30)
    }
    
    user_service.update_subscription(
        user_id=1,
        **subscription_data
    )
    
    assert test_user.subscription_tier == subscription_data["tier"]
    assert test_user.subscription_start_date == subscription_data["start_date"]
    assert test_user.subscription_end_date == subscription_data["end_date"]
    mock_db_session.commit.assert_called_once()

def test_validate_user_data(user_service):
    """Test user data validation"""
    # Test invalid email
    with pytest.raises(ValidationError):
        user_service.create_user(
            email="invalid-email",
            username="testuser",
            password="testpassword"
        )
    
    # Test invalid username
    with pytest.raises(ValidationError):
        user_service.create_user(
            email="test@example.com",
            username="",  # Empty username
            password="testpassword"
        )
    
    # Test invalid password
    with pytest.raises(ValidationError):
        user_service.create_user(
            email="test@example.com",
            username="testuser",
            password="123"  # Too short password
        )

def test_validate_subscription_data(user_service):
    """Test subscription data validation"""
    # Test invalid subscription tier
    with pytest.raises(ValidationError):
        user_service.update_subscription(
            user_id=1,
            tier="INVALID_TIER"
        )
    
    # Test invalid date range
    with pytest.raises(ValidationError):
        user_service.update_subscription(
            user_id=1,
            tier="PRO",
            start_date=datetime.now(),
            end_date=datetime.now() - timedelta(days=1)  # End date before start date
        )

def test_get_user_stats(user_service, test_user, mock_db_session):
    """Test retrieving user statistics"""
    mock_db_session.query.return_value.filter.return_value.first.return_value = test_user
    
    stats = user_service.get_user_stats(user_id=1)
    
    assert isinstance(stats, dict)
    assert "total_workouts" in stats
    assert "completed_workouts" in stats
    assert "total_exercises" in stats
    assert "average_duration" in stats

def test_reset_password(user_service, test_user, mock_db_session):
    """Test password reset functionality"""
    mock_db_session.query.return_value.filter.return_value.first.return_value = test_user
    
    reset_token = user_service.generate_password_reset_token(user_id=1)
    
    assert reset_token is not None
    assert test_user.password_reset_token is not None
    assert test_user.password_reset_expires is not None
    mock_db_session.commit.assert_called_once()

def test_verify_password_reset_token(user_service, test_user, mock_db_session):
    """Test password reset token verification"""
    mock_db_session.query.return_value.filter.return_value.first.return_value = test_user
    
    reset_token = user_service.generate_password_reset_token(user_id=1)
    is_valid = user_service.verify_password_reset_token(
        user_id=1,
        token=reset_token
    )
    
    assert is_valid is True

def test_verify_password_reset_token_invalid(user_service, test_user, mock_db_session):
    """Test password reset token verification with invalid token"""
    mock_db_session.query.return_value.filter.return_value.first.return_value = test_user
    
    is_valid = user_service.verify_password_reset_token(
        user_id=1,
        token="invalid_token"
    )
    
    assert is_valid is False 