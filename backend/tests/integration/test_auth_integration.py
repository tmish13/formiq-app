"""Integration tests for authentication functionality."""
import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.models.user import User
from app.services.auth import AuthService
from app.services.user_service import UserService
from app.services.session_service import SessionService
from app.core.security import get_password_hash
from app.db.session import get_db

@pytest.fixture
def test_client():
    return TestClient(app)

@pytest.fixture
def db_session():
    """Create a fresh database session for each test."""
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()

@pytest.fixture
def user_service(db_session):
    return UserService(db_session)

@pytest.fixture
def session_service(db_session):
    return SessionService(db_session)

@pytest.fixture
def auth_service(db_session, user_service, session_service):
    return AuthService(db_session, user_service, session_service)

@pytest.fixture
def test_user(db_session):
    """Create a test user in the database."""
    user = User(
        email="test@example.com",
        hashed_password=get_password_hash("testpassword123"),
        full_name="Test User",
        is_active=True,
        is_verified=False
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.mark.asyncio
async def test_user_registration_flow(test_client, db_session):
    """Test the complete user registration flow."""
    # Register new user
    response = test_client.post(
        "/api/v1/auth/register",
        json={
            "email": "newuser@example.com",
            "password": "newpassword123",
            "confirm_password": "newpassword123",
            "full_name": "New User"
        }
    )
    assert response.status_code == 201
    user_data = response.json()
    assert user_data["email"] == "newuser@example.com"
    assert user_data["full_name"] == "New User"
    assert not user_data["is_verified"]

    # Verify user exists in database
    user = db_session.query(User).filter(User.email == "newuser@example.com").first()
    assert user is not None
    assert user.email == "newuser@example.com"
    assert user.full_name == "New User"
    assert not user.is_verified

@pytest.mark.asyncio
async def test_login_flow(test_client, test_user):
    """Test the login flow with valid credentials."""
    # Login with valid credentials
    response = test_client.post(
        "/api/v1/auth/login",
        data={
            "username": "test@example.com",
            "password": "testpassword123"
        }
    )
    assert response.status_code == 200
    token_data = response.json()
    assert "access_token" in token_data
    assert "refresh_token" in token_data
    assert token_data["token_type"] == "bearer"
    assert "session_id" in token_data

    # Verify token works
    response = test_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token_data['access_token']}"}
    )
    assert response.status_code == 200
    user_data = response.json()
    assert user_data["email"] == "test@example.com"
    assert user_data["full_name"] == "Test User"

@pytest.mark.asyncio
async def test_login_invalid_credentials(test_client):
    """Test login with invalid credentials."""
    response = test_client.post(
        "/api/v1/auth/login",
        data={
            "username": "test@example.com",
            "password": "wrongpassword"
        }
    )
    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["detail"]

@pytest.mark.asyncio
async def test_password_reset_flow(test_client, test_user):
    """Test the complete password reset flow."""
    # Request password reset
    response = test_client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": "test@example.com"}
    )
    assert response.status_code == 202

    # Get reset token from database (in real app, this would be sent via email)
    # For testing, we'll simulate having the token
    reset_token = "test_reset_token"  # In real app, this would be a proper JWT token

    # Reset password with token
    response = test_client.post(
        "/api/v1/auth/password-reset/verify",
        json={
            "token": reset_token,
            "new_password": "newpassword123"
        }
    )
    assert response.status_code == 200

    # Verify can login with new password
    response = test_client.post(
        "/api/v1/auth/login",
        data={
            "username": "test@example.com",
            "password": "newpassword123"
        }
    )
    assert response.status_code == 200
    assert "access_token" in response.json()

@pytest.mark.asyncio
async def test_email_verification_flow(test_client, test_user):
    """Test the email verification flow."""
    # Request verification email
    response = test_client.post(
        "/api/v1/auth/verify-email/send",
        headers={"Authorization": f"Bearer {test_user.create_access_token()}"}
    )
    assert response.status_code == 202

    # Get verification token (in real app, this would be sent via email)
    # For testing, we'll simulate having the token
    verification_token = "test_verification_token"  # In real app, this would be a proper JWT token

    # Verify email with token
    response = test_client.get(
        f"/api/v1/auth/verify-email/{verification_token}"
    )
    assert response.status_code == 200

    # Verify user is now marked as verified
    response = test_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {test_user.create_access_token()}"}
    )
    assert response.status_code == 200
    assert response.json()["is_verified"] is True

@pytest.mark.asyncio
async def test_token_refresh_flow(test_client, test_user):
    """Test the token refresh flow."""
    # First login to get tokens
    response = test_client.post(
        "/api/v1/auth/login",
        data={
            "username": "test@example.com",
            "password": "testpassword123"
        }
    )
    assert response.status_code == 200
    tokens = response.json()

    # Refresh token
    response = test_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]}
    )
    assert response.status_code == 200
    new_tokens = response.json()
    assert "access_token" in new_tokens
    assert "refresh_token" in new_tokens
    assert new_tokens["access_token"] != tokens["access_token"]

    # Verify new access token works
    response = test_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {new_tokens['access_token']}"}
    )
    assert response.status_code == 200
    assert response.json()["email"] == "test@example.com"

@pytest.mark.asyncio
async def test_logout_flow(test_client, test_user):
    """Test the logout flow."""
    # First login to get tokens
    response = test_client.post(
        "/api/v1/auth/login",
        data={
            "username": "test@example.com",
            "password": "testpassword123"
        }
    )
    assert response.status_code == 200
    tokens = response.json()

    # Logout
    response = test_client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert response.status_code == 200

    # Verify token is no longer valid
    response = test_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_logout_all_devices_flow(test_client, test_user):
    """Test logging out from all devices."""
    # First login to get tokens
    response = test_client.post(
        "/api/v1/auth/login",
        data={
            "username": "test@example.com",
            "password": "testpassword123"
        }
    )
    assert response.status_code == 200
    tokens = response.json()

    # Logout from all devices
    response = test_client.post(
        "/api/v1/auth/logout-all",
        headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert response.status_code == 200

    # Verify token is no longer valid
    response = test_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert response.status_code == 401

    # Verify refresh token is also invalid
    response = test_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]}
    )
    assert response.status_code == 401 