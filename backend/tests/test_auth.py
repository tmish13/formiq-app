from fastapi.testclient import TestClient
from ..main import app
import pytest
from ..database import Base, get_db
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
from fastapi import HTTPException
from jose import jwt
from ..auth import (
    create_access_token,
    verify_password,
    get_password_hash,
    get_current_user,
    authenticate_user,
)
from ..config import settings
from ..models import User

# Test database setup
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

@pytest.fixture
def test_client():
    Base.metadata.create_all(bind=engine)
    yield TestClient(app)
    Base.metadata.drop_all(bind=engine)

def test_register_user(test_client):
    response = test_client.post(
        "/auth/register",
        json={
            "email": "test@example.com",
            "username": "testuser",
            "password": "Test123!@#"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["email"] == "test@example.com"

def test_login_user(test_client):
    # First register a user
    test_client.post(
        "/auth/register",
        json={
            "email": "test@example.com",
            "username": "testuser",
            "password": "Test123!@#"
        }
    )
    
    # Then try to login
    response = test_client.post(
        "/auth/login",
        json={
            "email": "test@example.com",
            "password": "Test123!@#"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_password_hashing():
    password = "testpassword"
    hashed = get_password_hash(password)
    
    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("wrongpassword", hashed) is False

def test_create_access_token():
    data = {"sub": "1", "email": "test@example.com"}
    token = create_access_token(data)
    
    decoded = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    assert decoded["sub"] == data["sub"]
    assert decoded["email"] == data["email"]
    assert "exp" in decoded

def test_create_access_token_with_expiry():
    data = {"sub": "1", "email": "test@example.com"}
    expires_delta = timedelta(minutes=15)
    token = create_access_token(data, expires_delta)
    
    decoded = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    assert decoded["exp"] - decoded["iat"] == int(expires_delta.total_seconds())

def test_expired_token():
    data = {"sub": "1", "email": "test@example.com"}
    expires_delta = timedelta(minutes=-1)  # Token that expired 1 minute ago
    token = create_access_token(data, expires_delta)
    
    with pytest.raises(jwt.ExpiredSignatureError):
        jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])

@pytest.fixture
def test_user_with_password():
    db = next(get_db())
    hashed_password = get_password_hash("testpassword")
    user = User(
        email="test@example.com",
        username="testuser",
        hashed_password=hashed_password,
        subscription_tier="basic",
        subscription_end_date=datetime.now() + timedelta(days=30),
        is_email_verified=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    yield user
    db.delete(user)
    db.commit()
    db.close()

def test_authenticate_user(test_user_with_password):
    db = next(get_db())
    user = authenticate_user(db, "test@example.com", "testpassword")
    assert user is not None
    assert user.email == "test@example.com"

    # Test with wrong password
    user = authenticate_user(db, "test@example.com", "wrongpassword")
    assert user is None

    # Test with non-existent user
    user = authenticate_user(db, "nonexistent@example.com", "testpassword")
    assert user is None

    db.close()

def test_get_current_user(test_user_with_password):
    db = next(get_db())
    
    # Create valid token
    token = create_access_token(
        {"sub": str(test_user_with_password.id), "email": test_user_with_password.email}
    )
    
    # Test with valid token
    user = get_current_user(db, token)
    assert user is not None
    assert user.email == test_user_with_password.email

    # Test with invalid token
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(db, "invalid_token")
    assert exc_info.value.status_code == 401

    # Test with non-existent user
    token = create_access_token({"sub": "999", "email": "nonexistent@example.com"})
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(db, token)
    assert exc_info.value.status_code == 404

    db.close()

def test_token_without_sub():
    token = create_access_token({"email": "test@example.com"})  # Missing sub
    db = next(get_db())
    
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(db, token)
    assert exc_info.value.status_code == 401
    
    db.close()

def test_token_without_email():
    token = create_access_token({"sub": "1"})  # Missing email
    db = next(get_db())
    
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(db, token)
    assert exc_info.value.status_code == 401
    
    db.close()

def test_password_validation():
    # Test minimum length
    short_password = "short"
    with pytest.raises(ValueError):
        get_password_hash(short_password)

    # Test common passwords
    common_password = "password123"
    with pytest.raises(ValueError):
        get_password_hash(common_password)

    # Test valid password
    valid_password = "StrongP@ssw0rd"
    hashed = get_password_hash(valid_password)
    assert verify_password(valid_password, hashed)

def test_subscription_validation(test_user_with_password):
    db = next(get_db())
    
    # Update user to have expired subscription
    test_user_with_password.subscription_end_date = datetime.now() - timedelta(days=1)
    db.commit()
    
    # Create token
    token = create_access_token(
        {"sub": str(test_user_with_password.id), "email": test_user_with_password.email}
    )
    
    # Test access with expired subscription
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(db, token, required_subscription="pro")
    assert exc_info.value.status_code == 403
    
    db.close()

def test_email_verification(test_user_with_password):
    db = next(get_db())
    
    # Update user to have unverified email
    test_user_with_password.is_email_verified = False
    db.commit()
    
    # Create token
    token = create_access_token(
        {"sub": str(test_user_with_password.id), "email": test_user_with_password.email}
    )
    
    # Test access with unverified email
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(db, token, require_verification=True)
    assert exc_info.value.status_code == 403
    
    db.close() 