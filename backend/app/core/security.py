from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Union
from jose import jwt
from passlib.context import CryptContext
from app.core.config import settings
from app.core.logging import logger

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Token related functions
def create_access_token(
    subject: Union[str, Any], 
    expires_delta: Optional[timedelta] = None, 
    scopes: Optional[list] = None,
    claims: Optional[Dict[str, Any]] = None
) -> str:
    """
    Create a JWT access token.
    
    Args:
        subject: Subject of the token (usually user ID)
        expires_delta: Optional expiration time
        scopes: Optional list of permission scopes
        claims: Optional additional claims
        
    Returns:
        Encoded JWT token
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode = {"exp": expire, "sub": str(subject)}
    
    if scopes:
        to_encode["scopes"] = scopes
    
    if claims:
        to_encode.update(claims)
    
    try:
        encoded_jwt = jwt.encode(
            to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
        )
        return encoded_jwt
    except Exception as e:
        logger.error("token_creation_failed", error=str(e))
        raise

def verify_token(token: str) -> Dict[str, Any]:
    """
    Verify and decode a JWT token.
    
    Args:
        token: JWT token to verify
        
    Returns:
        Decoded token payload
    """
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        return payload
    except jwt.JWTError as e:
        logger.error("token_verification_failed", error=str(e))
        raise
    except Exception as e:
        logger.error("token_verification_error", error=str(e))
        raise

# Password related functions
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hash.
    
    Args:
        plain_password: Password in plain text
        hashed_password: Hashed password
        
    Returns:
        True if password matches hash
    """
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """
    Hash a password.
    
    Args:
        password: Password in plain text
        
    Returns:
        Hashed password
    """
    return pwd_context.hash(password)

# Security utility functions
def is_token_blacklisted(token: str) -> bool:
    """
    Check if a token is blacklisted.
    
    Args:
        token: JWT token to check
        
    Returns:
        True if token is blacklisted
    """
    # Implement token blacklist check using Redis or DB
    return False

def blacklist_token(token: str, expires_in: int = None) -> None:
    """
    Add a token to the blacklist.
    
    Args:
        token: JWT token to blacklist
        expires_in: Optional time to keep the token in the blacklist
    """
    # Implement token blacklisting using Redis or DB
    pass

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
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
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
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        if payload.get("type") != "reset":
            return None
        return payload["sub"]
    except jwt.JWTError:
        return None 