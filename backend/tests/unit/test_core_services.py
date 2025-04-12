import pytest
from fastapi import HTTPException
from app.core.security import verify_password, get_password_hash
from app.core.config import settings
from app.services.user_service import UserService
from app.services.auth_service import AuthService
from app.schemas.user import UserCreate, UserUpdate
from app.core.exceptions import (
    NotFoundException,
    ValidationError,
    AuthenticationError
)

def test_password_hashing():
    """Test password hashing and verification."""
    password = "testpassword123"
    hashed = get_password_hash(password)
    assert verify_password(password, hashed)
    assert not verify_password("wrongpassword", hashed)

@pytest.mark.asyncio
async def test_user_creation(db_session):
    """Test user creation with validation."""
    user_service = UserService(db_session)
    user_data = UserCreate(
        email="test@example.com",
        password="StrongPass123!",
        full_name="Test User"
    )
    
    user = await user_service.create_user(user_data)
    assert user.email == "test@example.com"
    assert user.full_name == "Test User"
    
    # Test duplicate email
    with pytest.raises(ValidationError):
        await user_service.create_user(user_data)

@pytest.mark.asyncio
async def test_user_authentication(db_session):
    """Test user authentication flow."""
    auth_service = AuthService(db_session)
    user_service = UserService(db_session)
    
    # Create test user
    user_data = UserCreate(
        email="auth@example.com",
        password="StrongPass123!",
        full_name="Auth User"
    )
    user = await user_service.create_user(user_data)
    
    # Test successful authentication
    token = await auth_service.authenticate_user(
        email="auth@example.com",
        password="StrongPass123!"
    )
    assert token is not None
    assert "access_token" in token
    
    # Test failed authentication
    with pytest.raises(AuthenticationError):
        await auth_service.authenticate_user(
            email="auth@example.com",
            password="WrongPass123!"
        )

@pytest.mark.asyncio
async def test_user_update(db_session):
    """Test user update operations."""
    user_service = UserService(db_session)
    
    # Create test user
    user_data = UserCreate(
        email="update@example.com",
        password="StrongPass123!",
        full_name="Update User"
    )
    user = await user_service.create_user(user_data)
    
    # Update user
    update_data = UserUpdate(
        full_name="Updated Name",
        password="NewPass123!"
    )
    updated_user = await user_service.update_user(user.id, update_data)
    assert updated_user.full_name == "Updated Name"
    
    # Verify new password works
    auth_service = AuthService(db_session)
    token = await auth_service.authenticate_user(
        email="update@example.com",
        password="NewPass123!"
    )
    assert token is not None

@pytest.mark.asyncio
async def test_user_deletion(db_session):
    """Test user deletion."""
    user_service = UserService(db_session)
    
    # Create test user
    user_data = UserCreate(
        email="delete@example.com",
        password="StrongPass123!",
        full_name="Delete User"
    )
    user = await user_service.create_user(user_data)
    
    # Delete user
    await user_service.delete_user(user.id)
    
    # Verify user is deleted
    with pytest.raises(NotFoundException):
        await user_service.get_user(user.id)

@pytest.mark.asyncio
async def test_token_validation(db_session):
    """Test token validation and refresh."""
    auth_service = AuthService(db_session)
    user_service = UserService(db_session)
    
    # Create test user
    user_data = UserCreate(
        email="token@example.com",
        password="StrongPass123!",
        full_name="Token User"
    )
    user = await user_service.create_user(user_data)
    
    # Get tokens
    tokens = await auth_service.authenticate_user(
        email="token@example.com",
        password="StrongPass123!"
    )
    
    # Validate access token
    user_id = await auth_service.validate_token(tokens["access_token"])
    assert user_id == user.id
    
    # Test invalid token
    with pytest.raises(AuthenticationError):
        await auth_service.validate_token("invalid_token")

@pytest.mark.asyncio
async def test_rate_limiting(db_session):
    """Test rate limiting functionality."""
    auth_service = AuthService(db_session)
    
    # Test rate limiting for login attempts
    for _ in range(settings.MAX_LOGIN_ATTEMPTS):
        with pytest.raises(AuthenticationError):
            await auth_service.authenticate_user(
                email="ratelimit@example.com",
                password="WrongPass123!"
            )
    
    # Next attempt should raise rate limit error
    with pytest.raises(HTTPException) as exc_info:
        await auth_service.authenticate_user(
            email="ratelimit@example.com",
            password="WrongPass123!"
        )
    assert exc_info.value.status_code == 429 