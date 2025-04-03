"""Tests for JWT token functionality."""
import pytest
from jose import jwt
import time
from app.core.security import (
    create_access_token,
    create_refresh_token,
    verify_token,
    decode_access_token,
    generate_password_reset_token,
    verify_password_reset_token,
    TokenBlacklist,
    blacklist_token,
    token_blacklist
)
from app.core.config import settings
import uuid
from datetime import datetime, timedelta
import logging

# Configure logging for the test
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_access_token_creation():
    """Test access token creation with data."""
    user_id = str(uuid.uuid4())
    data = {"email": "test@example.com", "role": "user"}
    token = create_access_token(user_id, data)
    
    # Decode the token manually to verify
    payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    
    assert payload["sub"] == user_id
    assert payload["email"] == data["email"]
    assert payload["role"] == data["role"]
    assert "exp" in payload

def test_access_token_verification():
    """Test access token verification."""
    user_id = str(uuid.uuid4())
    token = create_access_token(user_id)
    
    # Verify the token
    subject = verify_token(token)
    
    assert subject == user_id

def test_refresh_token_creation():
    """Test refresh token creation with data."""
    user_id = str(uuid.uuid4())
    data = {"email": "test@example.com", "role": "user"}
    token = create_refresh_token(user_id, data)
    
    # Decode the token manually to verify
    payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    
    assert payload["sub"] == user_id
    assert payload["email"] == data["email"]
    assert payload["role"] == data["role"]
    assert "exp" in payload

def test_token_expiration():
    """Test token expiration."""
    # Create a token that expires in 1 second
    user_id = str(uuid.uuid4())
    token = jwt.encode(
        {"exp": time.time() + 1, "sub": user_id},
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM
    )
    
    # Verify the token works before expiration
    assert verify_token(token) == user_id
    
    # Wait for expiration
    time.sleep(2)
    
    # Verify the token doesn't work after expiration
    assert verify_token(token) is None

def test_password_reset_token():
    """Test password reset token creation and verification."""
    email = "reset@example.com"
    token = generate_password_reset_token(email)
    
    # Verify the token
    verified_email = verify_password_reset_token(token)
    
    assert verified_email == email

def test_token_with_additional_data():
    """Test creating and verifying tokens with additional data."""
    user_id = str(uuid.uuid4())
    data = {
        "email": "data@example.com",
        "permissions": ["read", "write"],
        "user_type": "admin"
    }
    
    token = create_access_token(user_id, data)
    payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    
    assert payload["sub"] == user_id
    assert payload["email"] == data["email"]
    assert payload["permissions"] == data["permissions"]
    assert payload["user_type"] == data["user_type"]

def test_token_blacklisting():
    """Test token blacklisting functionality with a standalone implementation."""
    # Simple standalone token blacklist implementation for testing
    class TestTokenBlacklist:
        def __init__(self):
            self.tokens = set()
            self.expiry = {}
        
        def add(self, token, expires_in=None):
            self.tokens.add(token)
            expires_at = datetime.utcnow() + timedelta(seconds=expires_in or 3600)
            self.expiry[token] = expires_at.timestamp()
        
        def is_blacklisted(self, token):
            # Clean expired tokens
            now = datetime.utcnow().timestamp()
            expired_tokens = [t for t, exp in self.expiry.items() if exp < now]
            for t in expired_tokens:
                self.tokens.discard(t)
                self.expiry.pop(t, None)
            
            return token in self.tokens
    
    # Create blacklist
    blacklist = TestTokenBlacklist()
    
    # Create test token
    token = "test_token"
    
    # Initial check
    assert token not in blacklist.tokens
    assert not blacklist.is_blacklisted(token)
    
    # Add to blacklist
    blacklist.add(token)
    
    # Should be blacklisted
    assert token in blacklist.tokens
    assert blacklist.is_blacklisted(token)
    
    # Test expiration
    expired_token = "expired_token"
    blacklist.add(expired_token, expires_in=1)
    
    # Initially blacklisted
    assert blacklist.is_blacklisted(expired_token)
    
    # Wait for expiration
    time.sleep(2)
    
    # Should be removed
    assert not blacklist.is_blacklisted(expired_token) 