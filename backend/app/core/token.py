"""Token utilities module."""
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Union
from jose import jwt, JWTError
import secrets
from app.core.config import settings

# JWT algorithm
ALGORITHM = settings.JWT_ALGORITHM

def create_access_token(
    subject: Union[str, Any], 
    expires_delta: Optional[timedelta] = None,
    data: Optional[Dict[str, Any]] = None
) -> str:
    """
    Create access token.
    
    Args:
        subject: User ID or subject identifier
        expires_delta: Optional expiration time override
        data: Additional data to encode in the token
        
    Returns:
        JWT token string
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # Add standard claims
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "iat": datetime.utcnow(),
        "jti": secrets.token_hex(16)  # Add unique token ID for potential revocation
    }
    
    # Add additional data if provided
    if isinstance(data, dict):
        to_encode.update(data)
        
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(
    subject: Union[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create refresh token with longer validity.
    
    Args:
        subject: User ID or subject identifier
        expires_delta: Optional expiration time override
        
    Returns:
        JWT refresh token string
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "type": "refresh",
        "iat": datetime.utcnow(),
        "jti": secrets.token_hex(16)
    }
    
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> Optional[str]:
    """
    Verify token and return user ID.
    
    Args:
        token: JWT token to verify
        
    Returns:
        User ID if token is valid, None otherwise
    """
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM])
        return payload["sub"]
    except JWTError:
        return None

def decode_token(token: str) -> Dict[str, Any]:
    """
    Decode and verify a token.
    
    Args:
        token: JWT token to decode
        
    Returns:
        Token payload if valid
        
    Raises:
        JWTError: If token is invalid
    """
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM])

def create_email_verification_token(email: str) -> str:
    """Create email verification token.
    
    Args:
        email: Email to create token for
        
    Returns:
        str: JWT token containing email
    """
    delta = timedelta(hours=24)  # Token valid for 24 hours
    now = datetime.utcnow()
    expires = now + delta
    
    to_encode = {
        "exp": expires,
        "nbf": now,
        "sub": email,
        "type": "email_verification"
    }
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=ALGORITHM
    )
    
    return encoded_jwt

def verify_email_token(token: str) -> Optional[str]:
    """Verify email verification token.
    
    Args:
        token: Token to verify
        
    Returns:
        Optional[str]: Email if token is valid, None otherwise
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[ALGORITHM]
        )
        
        # Check token type
        if payload.get("type") != "email_verification":
            return None
            
        return payload["sub"]
    except JWTError:
        return None 