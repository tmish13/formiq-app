import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from app.services.user import UserService
from app.models.user import User
from app.models.subscription import Subscription
from sqlalchemy.orm import Session
from app.core.exceptions import ValidationError, NotFoundError, AuthenticationError
from app.core.security import get_password_hash, verify_password, create_access_token
from app.core.config import settings
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from app.schemas.user import UserCreate, UserUpdate
from app.core.exceptions import NotFoundException

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
    """Return a UserService instance with a mock db session."""
    return UserService(mock_db_session)

def configure_for_async_test(user_service, mock_db_session):
    """Configure the user service and db session for async testing."""
    user_service.set_async_mode(True)
    
    # Mock async database methods
    mock_db_session.commit = AsyncMock()
    mock_db_session.rollback = AsyncMock()
    mock_db_session.refresh = AsyncMock()
    
    return user_service

@pytest.fixture
def test_user():
    """Create a test user"""
    return User(
        id=1,
        email="test@example.com",
        username="testuser",
        hashed_password=get_password_hash("TestPassword123!", validate=False),
        is_active=True,
        is_verified=True,
        subscription_tier="PRO",
        created_at=datetime.now()
    )

def test_create_user(user_service, mock_db_session):
    """Test creating a new user"""
    # Mock the get_password_hash function to bypass validation
    with patch('app.services.user.get_password_hash') as mock_hash:
        mock_hash.return_value = "hashed_password"
        
        user_data = {
            "email": "new@example.com",
            "username": "newuser",
            "password": "Complex%P4ssw0rd$789",
            "subscription_tier": "FREE"
        }
        
        user = user_service.create_user(**user_data)
        
        assert user.email == user_data["email"]
        assert user.username == user_data["username"]
        assert user.hashed_password == "hashed_password"
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
        password="TestPassword123!"
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
            password="WrongPassword123!"
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
    
    new_password = "NewPassword456!"
    user_service.change_password(
        user_id=1,
        current_password="TestPassword123!",
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
            current_password="WrongPassword123!",
            new_password="NewPassword456!"
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
    
    start_date = datetime.now()
    end_date = start_date + timedelta(days=30)
    
    updated_user = user_service.update_subscription(
        user_id=1,
        tier="PREMIUM",
        start_date=start_date,
        end_date=end_date,
        status="active",
        stripe_subscription_id="sub_123456",
        stripe_customer_id="cus_123456"
    )
    
    assert updated_user.subscription_tier == "PREMIUM"
    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called_once()
    mock_db_session.refresh.assert_called_once_with(test_user)

@pytest.mark.asyncio
async def test_update_subscription_async(user_service, test_user, mock_db_session):
    """Test updating user subscription asynchronously"""
    # Configure for async testing
    configure_for_async_test(user_service, mock_db_session)
    
    # Mock the repository's async method
    user_service.repository = Mock()
    user_service.repository.get_by_id_async = AsyncMock()
    user_service.repository.get_by_id_async.return_value = test_user
    
    start_date = datetime.now()
    end_date = start_date + timedelta(days=30)
    
    updated_user = await user_service.update_subscription_async(
        user_id=1,
        tier="PREMIUM",
        start_date=start_date,
        end_date=end_date,
        status="active",
        stripe_subscription_id="sub_123456",
        stripe_customer_id="cus_123456"
    )
    
    assert updated_user is not None
    assert test_user.subscription_tier == "PREMIUM"
    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called_once()
    mock_db_session.refresh.assert_called_once_with(test_user)

@pytest.mark.asyncio
async def test_create_user_async(user_service, mock_db_session):
    """Test creating a new user asynchronously"""
    # Configure for async testing
    configure_for_async_test(user_service, mock_db_session)
    
    # Mock the async database query
    mock_execute = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_execute.return_value = mock_result
    mock_db_session.execute = mock_execute
    
    # Mock the get_password_hash function to bypass validation
    with patch('app.services.user.get_password_hash') as mock_hash:
        mock_hash.return_value = "hashed_password"
        
        user_data = {
            "email": "new_async@example.com",
            "username": "newasyncuser",
            "password": "Complex%P4ssw0rd$789",
            "subscription_tier": "FREE"
        }
        
        user = await user_service.create_user_async(**user_data)
        
        assert user.email == user_data["email"]
        assert user.username == user_data["username"]
        assert user.hashed_password == "hashed_password"
        assert user.subscription_tier == user_data["subscription_tier"]
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()
        mock_db_session.refresh.assert_called_once()

def test_validate_user_data(user_service):
    """Test user data validation"""
    # Test invalid email
    with pytest.raises(ValidationError):
        user_service.create_user(
            email="invalid-email",
            username="testuser",
            password="TestPassword123!"
        )
    
    # Test invalid username
    with pytest.raises(ValidationError):
        user_service.create_user(
            email="test@example.com",
            username="",  # Empty username
            password="TestPassword123!"
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
        
    # Test invalid stripe subscription ID format
    with pytest.raises(ValidationError):
        user_service.update_subscription(
            user_id=1,
            tier="PRO",
            stripe_subscription_id="invalid_id"  # Should start with sub_
        )
        
    # Test invalid stripe customer ID format
    with pytest.raises(ValidationError):
        user_service.update_subscription(
            user_id=1,
            tier="PRO",
            stripe_customer_id="invalid_id"  # Should start with cus_
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

# Minimal db_session fixture for these tests if not provided globally.
# This is a simplified version. A robust test setup would use a test DB.
@pytest.fixture
def db_session_for_user_service(tmp_path) -> Session:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.db.base import Base # Ensure your Base for models is imported

    # Use a temporary SQLite DB for each test function if this fixture is function-scoped
    # or for the module if module-scoped.
    db_file = tmp_path / "test_user_service.db"
    engine = create_engine(f"sqlite:///{db_file}")
    Base.metadata.create_all(engine) # Create tables
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(engine) # Clean up tables
        # db_file.unlink() # Remove the temp DB file

@pytest.mark.asyncio
async def test_user_creation(db_session_for_user_service: Session):
    """Test user creation with validation."""
    user_service = UserService(db_session_for_user_service)
    user_data = UserCreate(
        email="test_creation@example.com", # Unique email for this test
        password="StrongPass123!",
        full_name="Test User Create",
        username="testcreateuser" # Added username as it's often required
    )
    
    user = await user_service.create_user(user_data)
    assert user.email == "test_creation@example.com"
    assert user.full_name == "Test User Create"
    assert user.username == "testcreateuser"
    
    # Test duplicate email
    with pytest.raises(ValidationError): # Or IntegrityError from DB driver depending on service impl.
        await user_service.create_user(user_data)

@pytest.mark.asyncio
async def test_user_update(db_session_for_user_service: Session):
    """Test user update operations."""
    user_service = UserService(db_session_for_user_service)
    
    # Create test user
    user_data_orig = UserCreate(
        email="update_test@example.com", # Unique email
        password="StrongPass123!",
        full_name="Update User Original",
        username="updateuserorig" # Added username
    )
    user = await user_service.create_user(user_data_orig)
    
    # Update user
    update_data = UserUpdate(
        full_name="Updated Name For Test",
        email="updated_email@example.com" # Example of updating email
        # password="NewPass123!" # Updating password might be a separate method or require current pass
    )
    updated_user = await user_service.update_user(user_id=user.id, user_in=update_data)
    assert updated_user.full_name == "Updated Name For Test"
    assert updated_user.email == "updated_email@example.com"
    # If password was updated, add verification for it, e.g. by trying to authenticate.

@pytest.mark.asyncio
async def test_user_deletion(db_session_for_user_service: Session):
    """Test user deletion."""
    user_service = UserService(db_session_for_user_service)
    
    user_data_del = UserCreate(
        email="delete_test@example.com", # Unique email
        password="StrongPass123!",
        full_name="Delete User Test",
        username="deleteusertest" # Added username
    )
    user = await user_service.create_user(user_data_del)
    
    await user_service.delete_user(user_id=user.id)
    
    # Verify user is deleted by trying to get them
    with pytest.raises(NotFoundException):
        await user_service.get_user_by_id(user_id=user.id) # Assuming get_user_by_id exists 