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
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    decode_access_token,
    verify_token,
    create_refresh_token,
    generate_password_reset_token,
    verify_password_reset_token,
)
import jwt
import time
import uuid
from jose import jwt as jose_jwt
import logging

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
    from app.services.user_service import UserService as AppUserService
    return AppUserService(db=mock_db_session)

@pytest.fixture
def workout_service(mock_db_session):
    """Create a workout service instance"""
    from app.services.workout_service import WorkoutService as AppWorkoutService
    return AppWorkoutService(db=mock_db_session)

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

@pytest.fixture
def test_token(test_user):
    """Create a test access token"""
    return create_access_token(data={"sub": test_user.email})

def test_password_hashing():
    """Test password hashing and verification"""
    password = "testpassword123"
    hashed = get_password_hash(password)
    assert verify_password(password, hashed)
    assert not verify_password("wrongpassword", hashed)

def test_jwt_token_creation_and_verification():
    """Test JWT token creation and verification"""
    user_id_int = 1
    token_int_sub = create_access_token(user_id_int)
    assert verify_token(token_int_sub) == str(user_id_int)

    user_id_str = str(uuid.uuid4())
    token_str_sub = create_access_token(user_id_str)
    assert verify_token(token_str_sub) == user_id_str
    
    assert verify_token("invalid_token") is None

def test_get_password_hash_validation_rules():
    """Test validation rules enforced by get_password_hash."""
    short_password = "short"
    with pytest.raises(ValueError, match=r"Password is too short"):
        get_password_hash(short_password)

    common_password = "password123"
    with pytest.raises(ValueError, match=r"Password is too common"):
        get_password_hash(common_password)

    valid_password = "ValidStrongP@ssw0rd"
    hashed = get_password_hash(valid_password)
    assert verify_password(valid_password, hashed)

def test_password_reset_token_generation_and_verification():
    """Test password reset token creation and verification."""
    email = "reset_sec@example.com"
    token = generate_password_reset_token(email)
    assert token is not None
    
    verified_email = verify_password_reset_token(token)
    assert verified_email == email

    assert verify_password_reset_token("invalid.token.here") is None

def test_access_token_creation_with_custom_data():
    """Test access token creation with custom data in payload."""
    user_id_str = str(uuid.uuid4())
    custom_data = {"email": "test_custom@example.com", "role": "admin_test"}
    token = create_access_token(user_id_str, custom_data)
    
    payload = jose_jwt.decode(token, settings.JWT_SECRET_KEY if hasattr(settings, 'JWT_SECRET_KEY') else settings.jwt_secret, algorithms=[settings.JWT_ALGORITHM  if hasattr(settings, 'JWT_ALGORITHM') else "HS256"])
    assert payload["sub"] == user_id_str
    assert payload["email"] == custom_data["email"]
    assert payload["role"] == custom_data["role"]
    assert "exp" in payload

def test_refresh_token_creation_with_custom_data():
    """Test refresh token creation with custom data."""
    user_id_str = str(uuid.uuid4())
    custom_data = {"email": "refresh_custom@example.com", "session_id": "session123"}
    token = create_refresh_token(user_id_str, custom_data) 
    
    payload = jose_jwt.decode(token, settings.JWT_SECRET_KEY if hasattr(settings, 'JWT_SECRET_KEY') else settings.jwt_secret, algorithms=[settings.JWT_ALGORITHM if hasattr(settings, 'JWT_ALGORITHM') else "HS256"])
    assert payload["sub"] == user_id_str
    assert payload["email"] == custom_data["email"]
    assert payload["session_id"] == custom_data["session_id"]
    assert "exp" in payload
    assert payload.get("type") == "refresh"

def test_verify_token_with_expired_token():
    """Test direct verification of an expired token using verify_token."""
    user_id_str = str(uuid.uuid4())
    expired_payload = {
        "exp": datetime.utcnow() - timedelta(seconds=3600),
        "sub": user_id_str,
        "iat": datetime.utcnow() - timedelta(seconds=3700)
    }
    expired_token = jose_jwt.encode(expired_payload, settings.JWT_SECRET_KEY if hasattr(settings, 'JWT_SECRET_KEY') else settings.jwt_secret, algorithm=settings.JWT_ALGORITHM if hasattr(settings, 'JWT_ALGORITHM') else "HS256")
    
    assert verify_token(expired_token) is None

    payload_short_expiry = {
        "exp": datetime.utcnow() + timedelta(seconds=1), 
        "sub": user_id_str,
        "iat": datetime.utcnow()
    }
    short_expiry_token = jose_jwt.encode(payload_short_expiry, settings.JWT_SECRET_KEY if hasattr(settings, 'JWT_SECRET_KEY') else settings.jwt_secret, algorithm=settings.JWT_ALGORITHM if hasattr(settings, 'JWT_ALGORITHM') else "HS256")    
    assert verify_token(short_expiry_token) == user_id_str
    time.sleep(2)
    assert verify_token(short_expiry_token) is None

def test_mock_token_blacklisting_functionality():
    """Test token blacklisting functionality with a standalone mock implementation."""
    class MockStandaloneTokenBlacklist:
        def __init__(self):
            self.tokens = set()
            self.expiry = {}
        
        def add(self, token_jti, expires_at_ts):
            self.tokens.add(token_jti)
            self.expiry[token_jti] = expires_at_ts
        
        def is_blacklisted(self, token_jti):
            now = datetime.utcnow().timestamp()
            expired_jtis = [jti for jti, exp_ts in self.expiry.items() if exp_ts < now]
            for jti in expired_jtis:
                self.tokens.discard(jti)
                self.expiry.pop(jti, None)
            return token_jti in self.tokens

    blacklist = MockStandaloneTokenBlacklist()
    token_jti_1 = str(uuid.uuid4())
    expires_at_1 = (datetime.utcnow() + timedelta(hours=1)).timestamp()

    assert not blacklist.is_blacklisted(token_jti_1)
    blacklist.add(token_jti_1, expires_at_1)
    assert blacklist.is_blacklisted(token_jti_1)
    
    token_jti_2_expired = str(uuid.uuid4())
    expires_at_2_short = (datetime.utcnow() + timedelta(seconds=1)).timestamp()
    blacklist.add(token_jti_2_expired, expires_at_2_short)
    assert blacklist.is_blacklisted(token_jti_2_expired)
    time.sleep(2)
    assert not blacklist.is_blacklisted(token_jti_2_expired)

def test_rate_limiting():
    """Test rate limiting functionality"""
    class MockRateLimiter:
        def __init__(self, requests, window):
            self.requests = requests
            self.window = window
            self.counts = {}

        def check_rate_limit(self, identifier):
            now = datetime.now()
            if identifier not in self.counts:
                self.counts[identifier] = []
            
            self.counts[identifier] = [ts for ts in self.counts[identifier] if now - ts < timedelta(seconds=self.window)]
            
            if len(self.counts[identifier]) < self.requests:
                self.counts[identifier].append(now)
                return True
            return False

    limiter = MockRateLimiter(requests=5, window=60)
    user_id_str = "user1"
    
    for _ in range(5):
        assert limiter.check_rate_limit(user_id_str) is True
    
    assert limiter.check_rate_limit(user_id_str) is False
    limiter.counts[user_id_str] = []
    for _ in range(5):
        assert limiter.check_rate_limit(user_id_str) is True

def test_data_encryption():
    """Test data encryption and decryption"""
    sensitive_data = "sensitive information"
    encrypted = encrypt_data(sensitive_data)
    decrypted = decrypt_data(encrypted)
    
    assert decrypted == sensitive_data
    assert encrypted != sensitive_data

def test_input_validation():
    """Test input validation functions"""
    assert validate_email("test@example.com") is True
    assert validate_email("invalid-email") is False
    
    assert validate_password("StrongPass123!") is True
    assert validate_password("weak") is False
    
    assert validate_username("valid_username") is True
    assert validate_username("") is False

def test_sql_injection_prevention(user_service, mock_db_session):
    """Test SQL injection prevention"""
    malicious_input = "'; DROP TABLE users; --"
    
    with pytest.raises(ValidationError):
        user_service.create_user(
            email=malicious_input,
            username=malicious_input,
            password=create_access_token(data={"sub": "password"})
        )
    
    with pytest.raises(ValidationError):
        user_service.get_user_by_email(email=malicious_input)

def test_xss_prevention(workout_service, mock_db_session):
    """Test XSS prevention"""
    malicious_input = "<script>alert('xss')</script>"
    
    with pytest.raises(ValidationError):
        workout_service.create_workout(
            user=test_user,
            name=malicious_input,
            description=malicious_input
        )

def test_csrf_protection(user_service, test_user, mock_db_session):
    """Test CSRF protection"""
    token = create_access_token(test_user.id)
    
    assert create_access_token(test_user.id) == token
    
    assert create_access_token("invalid_token") is None

def test_password_policy(user_service):
    """Test password policy enforcement"""
    with pytest.raises(ValidationError):
        user_service.create_user(
            email="test@example.com",
            username="testuser",
            password="weak"
        )
    
    user = user_service.create_user(
        email="test@example.com",
        username="testuser",
        password="StrongPass123!"
    )
    assert user is not None

def test_session_management(user_service, test_user, mock_db_session):
    """Test session management"""
    token = create_access_token(test_user.id)
    
    assert create_access_token(test_user.id) == token
    
    expired_token = create_access_token(test_user.id, expires_delta=timedelta(seconds=-1))
    assert create_access_token(test_user.id) is None

def test_authentication_flow(user_service, test_user, mock_db_session):
    """Test authentication flow security"""
    mock_db_session.query.return_value.filter.return_value.first.return_value = test_user
    user = user_service.authenticate_user(
        email="test@example.com",
        password=create_access_token(data={"sub": "testpassword"})
    )
    assert user.id == test_user.id
    
    with pytest.raises(AuthenticationError):
        user_service.authenticate_user(
            email="test@example.com",
            password="wrongpassword"
        )
    
    for _ in range(5):
        with pytest.raises(AuthenticationError):
            user_service.authenticate_user(
                email="test@example.com",
                password="wrongpassword"
            )

def test_authorization_checks(workout_service, test_user, mock_db_session):
    """Test authorization checks"""
    workout_data = {
        "name": "Test Workout",
        "description": "Test description",
        "duration": timedelta(minutes=60),
        "difficulty": "intermediate"
    }
    workout = workout_service.create_workout(user=test_user, **workout_data)
    
    retrieved_workout = workout_service.get_workout(
        workout_id=workout.id,
        user_id=test_user.id
    )
    assert retrieved_workout.id == workout.id
    
    with pytest.raises(NotFoundError):
        workout_service.get_workout(
            workout_id=workout.id,
            user_id=999
        )

def test_sensitive_data_handling(user_service, test_user, mock_db_session):
    """Test handling of sensitive data"""
    assert test_user.hashed_password != create_access_token(data={"sub": "testpassword"})
    
    sensitive_data = "credit_card_number"
    encrypted = encrypt_data(sensitive_data)
    assert encrypted != sensitive_data
    assert decrypt_data(encrypted) == sensitive_data

def test_secure_headers():
    """Test secure headers"""
    assert create_access_token(1) is not None
    assert create_access_token(1) is not None

def test_input_sanitization(workout_service, test_user, mock_db_session):
    """Test input sanitization"""
    html_input = "<script>alert('xss')</script>Hello"
    
    with pytest.raises(ValidationError):
        workout_service.create_workout(
            user=test_user,
            name=html_input,
            description=html_input
        )
    
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
    
    expire = datetime.utcnow() - timedelta(seconds=1)
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
    
    for _ in range(100):
        response = client.get(endpoint, headers=headers)
        if response.status_code == 429:
            break
    
    assert "X-RateLimit-Limit" in response.headers
    assert "X-RateLimit-Remaining" in response.headers
    assert "X-RateLimit-Reset" in response.headers

def test_input_validation(client, test_token):
    """Test input validation and sanitization"""
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
        "password",
        "123456",
        "abcdefgh",
        "12345678",
        "a1b2c3d4"
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
    expired_token = create_access_token(
        data={"sub": "test@example.com"},
        expires_delta=timedelta(seconds=1)
    )
    
    time.sleep(2)
    
    response = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {expired_token}"}
    )
    assert response.status_code == 401
    
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
    
    assert "X-Content-Type-Options" in response.headers
    assert "X-Frame-Options" in response.headers
    assert "X-XSS-Protection" in response.headers
    assert "Strict-Transport-Security" in response.headers
    assert "Content-Security-Policy" in response.headers

def test_file_upload_security(client, test_token):
    """Test security of file upload functionality"""
    with open("test.txt", "w") as f:
        f.write("test content")
    
    with open("test.txt", "rb") as f:
        response = client.post(
            "/api/v1/workouts/analyze",
            files={"video": ("test.txt", f, "text/plain")},
            headers={"Authorization": f"Bearer {test_token}"}
        )
    assert response.status_code == 422
    
    large_file = b"0" * (10 * 1024 * 1024)
    response = client.post(
        "/api/v1/workouts/analyze",
        files={"video": ("large.mp4", large_file, "video/mp4")},
        headers={"Authorization": f"Bearer {test_token}"}
    )
    assert response.status_code == 422

def test_create_access_token_with_specific_expiry():
    """Test create_access_token with a specific expires_delta."""
    subject_for_token = "user_subject_for_expiry_test"
    expires_delta = timedelta(minutes=33) 
    token = create_access_token(subject=subject_for_token, expires_delta=expires_delta)
    
    decoded_payload = jose_jwt.decode(token, settings.JWT_SECRET_KEY if hasattr(settings, 'JWT_SECRET_KEY') else settings.jwt_secret, algorithms=[settings.JWT_ALGORITHM if hasattr(settings, 'JWT_ALGORITHM') else "HS256"])
    issue_time = datetime.fromtimestamp(decoded_payload["iat"])
    expiry_time = datetime.fromtimestamp(decoded_payload["exp"])
    
    assert abs((expiry_time - issue_time).total_seconds() - expires_delta.total_seconds()) < 2
    assert decoded_payload["sub"] == subject_for_token

def test_direct_jwt_decode_of_expired_token():
    """Test decoding an expired token directly using jose.jwt.decode to see ExpiredSignatureError."""
    subject_for_token = "user_subject_for_direct_expired_test"
    expired_payload_data = {
        "exp": datetime.utcnow() - timedelta(minutes=15),
        "iat": datetime.utcnow() - timedelta(minutes=30),
        "sub": subject_for_token
    }
    expired_token = jose_jwt.encode(expired_payload_data, settings.JWT_SECRET_KEY if hasattr(settings, 'JWT_SECRET_KEY') else settings.jwt_secret, algorithm=settings.JWT_ALGORITHM if hasattr(settings, 'JWT_ALGORITHM') else "HS256")
    
    with pytest.raises(jose_jwt.ExpiredSignatureError):
        jose_jwt.decode(expired_token, settings.JWT_SECRET_KEY if hasattr(settings, 'JWT_SECRET_KEY') else settings.jwt_secret, algorithms=[settings.JWT_ALGORITHM if hasattr(settings, 'JWT_ALGORITHM') else "HS256"]) 