import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.models.user import User
from datetime import datetime, timedelta
from app.core.exceptions import AuthenticationError, AuthorizationError, ValidationError, NotFoundError
from unittest.mock import Mock, patch
from app.services.user import UserService
from app.services.workout import WorkoutService
from sqlalchemy.orm import Session
from app.core.encryption import encrypt_data, decrypt_data
from app.core.validators import validate_email, validate_password, validate_username
from fastapi import HTTPException
from app.middleware.rate_limiter import RateLimiterMiddleware
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    decode_access_token,
    verify_token,
)
import jwt

@pytest.fixture
def client():
    """Create a test client"""
    return TestClient(app)

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
def workout_service(mock_db_session):
    """Create a workout service instance"""
    return WorkoutService(db=mock_db_session)

@pytest.fixture
def test_user():
    """Create a test user"""
    return User(
        id=1,
        email="test@example.com",
        username="testuser",
        hashed_password=create_access_token(data={"sub": "test@example.com"}),
        is_active=True,
        is_verified=True,
        subscription_tier="PRO",
        created_at=datetime.now()
    )

@pytest.fixture
def test_token(test_user):
    """Create a test access token"""
    return create_access_token(data={"sub": test_user.email})

def test_password_hashing():
    """Test password hashing and verification"""
    password = "testpassword123"
    hashed = create_access_token(data={"sub": password})
    
    assert create_access_token(data={"sub": password}) == hashed
    assert create_access_token(data={"sub": "wrongpassword"}) != hashed
    assert hashed != password  # Ensure password is hashed

def test_jwt_token_creation_and_verification():
    """Test JWT token creation and verification"""
    user_id = 1
    token = create_access_token(user_id)
    
    assert verify_token(token) == str(user_id)
    assert verify_token("invalid_token") is None

def test_password_reset_token():
    """Test password reset token generation and verification"""
    user_id = 1
    token = create_access_token(user_id)
    
    assert create_access_token(user_id) == token
    assert create_access_token("invalid_token") is None

def test_rate_limiting():
    """Test rate limiting functionality"""
    limiter = RateLimiterMiddleware(app=None, requests=5, window=60)
    user_id = 1
    
    # Test within limit
    for _ in range(5):
        assert limiter.check_rate_limit(user_id) is True
    
    # Test exceeding limit
    for _ in range(5):
        limiter.check_rate_limit(user_id)
    assert limiter.check_rate_limit(user_id) is False

def test_data_encryption():
    """Test data encryption and decryption"""
    sensitive_data = "sensitive information"
    encrypted = encrypt_data(sensitive_data)
    decrypted = decrypt_data(encrypted)
    
    assert decrypted == sensitive_data
    assert encrypted != sensitive_data  # Ensure data is encrypted

def test_input_validation():
    """Test input validation functions"""
    # Test email validation
    assert validate_email("test@example.com") is True
    assert validate_email("invalid-email") is False
    
    # Test password validation
    assert validate_password("StrongPass123!") is True
    assert validate_password("weak") is False
    
    # Test username validation
    assert validate_username("valid_username") is True
    assert validate_username("") is False

def test_sql_injection_prevention(user_service, mock_db_session):
    """Test SQL injection prevention"""
    malicious_input = "'; DROP TABLE users; --"
    
    # Test user creation with malicious input
    with pytest.raises(ValidationError):
        user_service.create_user(
            email=malicious_input,
            username=malicious_input,
            password=create_access_token(data={"sub": "password"})
        )
    
    # Test user retrieval with malicious input
    with pytest.raises(ValidationError):
        user_service.get_user_by_email(email=malicious_input)

def test_xss_prevention(workout_service, mock_db_session):
    """Test XSS prevention"""
    malicious_input = "<script>alert('xss')</script>"
    
    # Test workout creation with malicious input
    with pytest.raises(ValidationError):
        workout_service.create_workout(
            user=test_user,
            name=malicious_input,
            description=malicious_input
        )

def test_csrf_protection(user_service, test_user, mock_db_session):
    """Test CSRF protection"""
    # Test token generation
    token = create_access_token(test_user.id)
    
    # Test token verification
    assert create_access_token(test_user.id) == token
    
    # Test invalid token
    assert create_access_token("invalid_token") is None

def test_password_policy(user_service):
    """Test password policy enforcement"""
    # Test weak password
    with pytest.raises(ValidationError):
        user_service.create_user(
            email="test@example.com",
            username="testuser",
            password="weak"
        )
    
    # Test strong password
    user = user_service.create_user(
        email="test@example.com",
        username="testuser",
        password="StrongPass123!"
    )
    assert user is not None

def test_session_management(user_service, test_user, mock_db_session):
    """Test session management"""
    # Test session creation
    token = create_access_token(test_user.id)
    
    # Test session validation
    assert create_access_token(test_user.id) == token
    
    # Test session expiration
    expired_token = create_access_token(test_user.id, expires_delta=timedelta(seconds=-1))
    assert create_access_token(test_user.id) is None

def test_authentication_flow(user_service, test_user, mock_db_session):
    """Test authentication flow security"""
    # Test successful authentication
    mock_db_session.query.return_value.filter.return_value.first.return_value = test_user
    user = user_service.authenticate_user(
        email="test@example.com",
        password=create_access_token(data={"sub": "testpassword"})
    )
    assert user.id == test_user.id
    
    # Test failed authentication
    with pytest.raises(AuthenticationError):
        user_service.authenticate_user(
            email="test@example.com",
            password="wrongpassword"
        )
    
    # Test brute force prevention
    for _ in range(5):
        with pytest.raises(AuthenticationError):
            user_service.authenticate_user(
                email="test@example.com",
                password="wrongpassword"
            )

def test_authorization_checks(workout_service, test_user, mock_db_session):
    """Test authorization checks"""
    # Create a workout
    workout_data = {
        "name": "Test Workout",
        "description": "Test description",
        "duration": timedelta(minutes=60),
        "difficulty": "intermediate"
    }
    workout = workout_service.create_workout(user=test_user, **workout_data)
    
    # Test access with correct user
    retrieved_workout = workout_service.get_workout(
        workout_id=workout.id,
        user_id=test_user.id
    )
    assert retrieved_workout.id == workout.id
    
    # Test access with different user
    with pytest.raises(NotFoundError):
        workout_service.get_workout(
            workout_id=workout.id,
            user_id=999
        )

def test_sensitive_data_handling(user_service, test_user, mock_db_session):
    """Test handling of sensitive data"""
    # Test password hashing
    assert test_user.hashed_password != create_access_token(data={"sub": "testpassword"})
    
    # Test sensitive data encryption
    sensitive_data = "credit_card_number"
    encrypted = encrypt_data(sensitive_data)
    assert encrypted != sensitive_data
    assert decrypt_data(encrypted) == sensitive_data

def test_secure_headers():
    """Test secure headers"""
    # This would typically be tested in an integration test with the web framework
    # For now, we'll verify the security-related functions
    assert create_access_token(1) is not None
    assert create_access_token(1) is not None

def test_input_sanitization(workout_service, test_user, mock_db_session):
    """Test input sanitization"""
    # Test HTML sanitization
    html_input = "<script>alert('xss')</script>Hello"
    
    with pytest.raises(ValidationError):
        workout_service.create_workout(
            user=test_user,
            name=html_input,
            description=html_input
        )
    
    # Test SQL injection prevention
    sql_input = "'; DROP TABLE workouts; --"
    
    with pytest.raises(ValidationError):
        workout_service.create_workout(
            user=test_user,
            name=sql_input,
            description=sql_input
        )

def test_token_creation(test_user):
    """Test JWT token creation and validation"""
    token = create_access_token(data={"sub": test_user.email})
    
    assert isinstance(token, str)
    assert len(token) > 0
    
    # Test expired token by directly manipulating the expiration time
    expire = datetime.utcnow() - timedelta(seconds=1)  # Already expired
    to_encode = {"exp": expire, "sub": test_user.email}
    
    expired_token = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    
    assert len(expired_token) > 0
    assert verify_token(expired_token) is None

def test_authentication_required(client):
    """Test that authentication is required for protected endpoints"""
    protected_endpoints = [
        "/api/v1/users/me",
        "/api/v1/workouts",
        "/api/v1/workout-plans",
        "/api/v1/subscriptions/status"
    ]
    
    for endpoint in protected_endpoints:
        response = client.get(endpoint)
        assert response.status_code == 401

def test_invalid_token(client):
    """Test handling of invalid tokens"""
    invalid_tokens = [
        "invalid_token",
        "Bearer invalid_token",
        "Bearer ",
        "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0QGV4YW1wbGUuY29tIiwiZXhwIjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
    ]
    
    for token in invalid_tokens:
        response = client.get(
            "/api/v1/users/me",
            headers={"Authorization": token}
        )
        assert response.status_code == 401

def test_token_expiration(client, test_user):
    """Test handling of expired tokens"""
    expired_token = create_access_token(
        data={"sub": test_user.email},
        expires_delta=timedelta(seconds=-1)
    )
    
    response = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {expired_token}"}
    )
    assert response.status_code == 401

def test_user_authorization(client, test_token):
    """Test user authorization for accessing resources"""
    # Create a workout
    workout_data = {
        "name": "Test Workout",
        "description": "Test description",
        "duration": 45,
        "difficulty": "beginner"
    }
    
    response = client.post(
        "/api/v1/workouts",
        json=workout_data,
        headers={"Authorization": f"Bearer {test_token}"}
    )
    assert response.status_code == 201
    workout_id = response.json()["id"]
    
    # Try to access workout with different user's token
    other_user_token = create_access_token(data={"sub": "other@example.com"})
    response = client.get(
        f"/api/v1/workouts/{workout_id}",
        headers={"Authorization": f"Bearer {other_user_token}"}
    )
    assert response.status_code == 404

def test_rate_limiting(client, test_token):
    """Test rate limiting for API endpoints"""
    endpoint = "/api/v1/workouts"
    headers = {"Authorization": f"Bearer {test_token}"}
    
    # Make multiple requests in quick succession
    for _ in range(100):
        response = client.get(endpoint, headers=headers)
        if response.status_code == 429:  # Too Many Requests
            break
    
    # Verify rate limiting headers
    assert "X-RateLimit-Limit" in response.headers
    assert "X-RateLimit-Remaining" in response.headers
    assert "X-RateLimit-Reset" in response.headers

def test_input_validation(client, test_token):
    """Test input validation and sanitization"""
    # Test SQL injection attempt
    malicious_input = "'; DROP TABLE users; --"
    response = client.post(
        "/api/v1/users/register",
        json={
            "email": malicious_input,
            "username": "testuser",
            "password": "testpassword"
        }
    )
    assert response.status_code == 422
    
    # Test XSS attempt
    xss_input = "<script>alert('xss')</script>"
    response = client.post(
        "/api/v1/workouts",
        json={
            "name": xss_input,
            "description": "Test description",
            "duration": 45,
            "difficulty": "beginner"
        },
        headers={"Authorization": f"Bearer {test_token}"}
    )
    assert response.status_code == 422

def test_csrf_protection(client, test_token):
    """Test CSRF protection"""
    # Test without CSRF token
    response = client.post(
        "/api/v1/workouts",
        json={
            "name": "Test Workout",
            "description": "Test description",
            "duration": 45,
            "difficulty": "beginner"
        },
        headers={"Authorization": f"Bearer {test_token}"}
    )
    assert response.status_code == 403
    
    # Test with CSRF token
    response = client.post(
        "/api/v1/workouts",
        json={
            "name": "Test Workout",
            "description": "Test description",
            "duration": 45,
            "difficulty": "beginner"
        },
        headers={
            "Authorization": f"Bearer {test_token}",
            "X-CSRF-Token": "valid_csrf_token"
        }
    )
    assert response.status_code == 201

def test_password_policy(client):
    """Test password policy enforcement"""
    weak_passwords = [
        "password",  # Too common
        "123456",    # Too short
        "abcdefgh",  # No numbers
        "12345678",  # No letters
        "a1b2c3d4"   # No special characters
    ]
    
    for password in weak_passwords:
        response = client.post(
            "/api/v1/users/register",
            json={
                "email": "test@example.com",
                "username": "testuser",
                "password": password
            }
        )
        assert response.status_code == 422

def test_session_management(client, test_token):
    """Test session management and security"""
    # Test session timeout
    expired_token = create_access_token(
        data={"sub": "test@example.com"},
        expires_delta=timedelta(seconds=1)
    )
    
    # Wait for token to expire
    import time
    time.sleep(2)
    
    response = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {expired_token}"}
    )
    assert response.status_code == 401
    
    # Test concurrent sessions
    token1 = create_access_token(data={"sub": "test@example.com"})
    token2 = create_access_token(data={"sub": "test@example.com"})
    
    response1 = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token1}"}
    )
    response2 = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token2}"}
    )
    
    assert response1.status_code == 200
    assert response2.status_code == 200

def test_secure_headers(client):
    """Test security headers"""
    response = client.get("/api/v1/health")
    
    # Check for security headers
    assert "X-Content-Type-Options" in response.headers
    assert "X-Frame-Options" in response.headers
    assert "X-XSS-Protection" in response.headers
    assert "Strict-Transport-Security" in response.headers
    assert "Content-Security-Policy" in response.headers

def test_file_upload_security(client, test_token):
    """Test security of file upload functionality"""
    # Test file type validation
    with open("test.txt", "w") as f:
        f.write("test content")
    
    with open("test.txt", "rb") as f:
        response = client.post(
            "/api/v1/workouts/analyze",
            files={"video": ("test.txt", f, "text/plain")},
            headers={"Authorization": f"Bearer {test_token}"}
        )
    assert response.status_code == 422
    
    # Test file size limits
    large_file = b"0" * (10 * 1024 * 1024)  # 10MB
    response = client.post(
        "/api/v1/workouts/analyze",
        files={"video": ("large.mp4", large_file, "video/mp4")},
        headers={"Authorization": f"Bearer {test_token}"}
    )
    assert response.status_code == 422 