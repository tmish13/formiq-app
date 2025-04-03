"""Security module."""
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Union
from jose import jwt, JWTError
from passlib.context import CryptContext
from app.core.config import settings
from app.core.logging import logger
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from uuid import UUID

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

ALGORITHM = "HS256"

# Token related functions
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
    
    to_encode = {"exp": expire, "sub": str(subject)}
    
    # Add additional data if provided
    if isinstance(data, dict):
        to_encode.update(data)
        
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

def create_refresh_token(
    subject: Union[str, Any], 
    expires_delta: Optional[timedelta] = None,
    data: Optional[Dict[str, Any]] = None
) -> str:
    """
    Create refresh token.
    
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
        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode = {"exp": expire, "sub": str(subject)}
    
    # Add additional data if provided
    if isinstance(data, dict):
        to_encode.update(data)
        
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
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
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return payload["sub"]
    except JWTError:
        return None

# Password related functions
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Get password hash."""
    validate_password(password)
    return pwd_context.hash(password)

def validate_password(password: str) -> bool:
    """
    Validate password strength.
    
    Args:
        password: Password to validate
        
    Returns:
        True if password is valid
        
    Raises:
        ValueError: If password does not meet security requirements
    """
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")
    
    if not any(c.isupper() for c in password):
        raise ValueError("Password must contain at least one uppercase letter")
    
    if not any(c.islower() for c in password):
        raise ValueError("Password must contain at least one lowercase letter")
    
    if not any(c.isdigit() for c in password):
        raise ValueError("Password must contain at least one number")
    
    if not any(c in "!@#$%^&*()_-+=[]{}|;:'\",.<>/?`~" for c in password):
        raise ValueError("Password must contain at least one special character")
    
    return True

# Security utility functions
# Token blacklist implementation
class TokenBlacklist:
    """Token blacklist implementation."""
    
    def __init__(self):
        """Initialize token blacklist."""
        self.tokens = set()
        self.expiry = {}
    
    def add(self, token: str, expires_in: int = None) -> None:
        """
        Add a token to the blacklist.
        
        Args:
            token: JWT token to blacklist
            expires_in: Optional time to keep the token in the blacklist (seconds)
        """
        self.tokens.add(token)
        
        # If expires_in is not provided, try to extract expiration from token
        if expires_in is None:
            try:
                payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM], options={"verify_signature": True})
                if "exp" in payload:
                    self.expiry[token] = payload["exp"]
                    return
            except JWTError:
                logger.error(f"Failed to decode token for blacklisting: {token[:10]}...")
        
        # Default: expire after 24 hours
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in or 86400)
        self.expiry[token] = expires_at.timestamp()
    
    def is_blacklisted(self, token: str) -> bool:
        """
        Check if a token is blacklisted.
        
        Args:
            token: JWT token to check
            
        Returns:
            True if token is blacklisted
        """
        # Clean expired tokens from blacklist
        now = datetime.utcnow().timestamp()
        expired_tokens = [t for t, exp in self.expiry.items() if exp < now]
        for t in expired_tokens:
            self.tokens.discard(t)
            self.expiry.pop(t, None)
        
        result = token in self.tokens
        return result
    
    def clear(self) -> None:
        """Clear the blacklist."""
        self.tokens.clear()
        self.expiry.clear()

# Create a global instance for token blacklisting
token_blacklist = TokenBlacklist()

def blacklist_token(token: str, expires_in: int = None) -> None:
    """
    Add a token to the blacklist.
    
    Args:
        token: JWT token to blacklist
        expires_in: Optional time to keep the token in the blacklist (seconds)
    """
    token_blacklist.add(token, expires_in)

def is_token_blacklisted(token: str) -> bool:
    """
    Check if a token is blacklisted.
    
    Args:
        token: JWT token to check
        
    Returns:
        True if token is blacklisted
    """
    return token_blacklist.is_blacklisted(token)

def generate_password_reset_token(email: str) -> str:
    """
    Generate a password reset token.
    
    Args:
        email: User email
        
    Returns:
        Password reset token
    """
    expires = datetime.utcnow() + timedelta(hours=24)
    to_encode = {"exp": expires, "sub": email, "type": "reset"}
    return jwt.encode(
        to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM
    )

def verify_password_reset_token(token: str) -> Optional[str]:
    """
    Verify a password reset token.
    
    Args:
        token: Password reset token
        
    Returns:
        Email if token is valid, None otherwise
    """
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
        if payload.get("type") != "reset":
            return None
        return payload["sub"]
    except JWTError:
        return None

def decode_access_token(token: str) -> dict:
    """
    Decode and verify an access token.
    
    Args:
        token: JWT token to decode
        
    Returns:
        Token payload if valid
        
    Raises:
        HTTPException: If token is invalid
    """
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) 