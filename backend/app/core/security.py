"""Security module."""
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Union
from jose import jwt, JWTError
from passlib.context import CryptContext
import secrets
import hashlib
import base64
import re
import time
import httpx
import asyncio
from app.core.config import settings
from app.core.logging import logger
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from uuid import UUID
from app.core.validators import validate_password as validate_password_strength
import uuid
from fastapi import Request
from app.services.user_service import get_user_service
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.password import verify_password
from app.core.token import verify_token, decode_token

# Password hashing context with stronger settings
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12,  # Increased from default 10
    bcrypt__default_rounds=12
)

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

# JWT algorithm
ALGORITHM = settings.JWT_ALGORITHM

# Login attempt tracking for throttling
LOGIN_ATTEMPT_CACHE = {}
MAX_ATTEMPTS = 5
LOCKOUT_TIME = 300  # seconds (5 minutes)

# Recent breach detection cache
PWNED_PASSWORD_CACHE = {}
PWNED_CACHE_TTL = 86400  # 24 hours

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
        
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
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
def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Args:
        password: Plain text password
    
    Returns:
        str: Hashed password
        
    Raises:
        ValueError: If password doesn't meet security requirements
    """
    # Validate password strength
    validate_password_strength(password)
    
    # Check if password has been exposed in data breaches (optional/async)
    # This is done asynchronously so we don't block
    asyncio.create_task(is_password_pwned(password))
    
    # Hash and return
    return pwd_context.hash(password)

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

def create_password_reset_token(email: str) -> str:
    """
    Create password reset token.
    
    Args:
        email: User email
        
    Returns:
        JWT token string
    """
    expire = datetime.utcnow() + timedelta(hours=settings.PASSWORD_RESET_TOKEN_EXPIRE_HOURS)
    to_encode = {
        "exp": expire,
        "sub": email,
        "type": "reset",
        "jti": secrets.token_hex(16)
    }
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

def generate_password_reset_token(email: str) -> str:
    """
    Generate a password reset token.
    
    Args:
        email: User's email address
        
    Returns:
        str: Password reset token
    """
    delta = timedelta(hours=settings.PASSWORD_RESET_TOKEN_EXPIRE_HOURS)
    now = datetime.utcnow()
    expires = now + delta
    exp = expires.timestamp()
    encoded_jwt = jwt.encode(
        {"exp": exp, "nbf": now, "sub": email, "type": "password_reset"},
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )
    return encoded_jwt

def track_login_attempt(username: str, success: bool) -> bool:
    """
    Track login attempts to prevent brute force attacks.
    
    Args:
        username: Username or email attempting to login
        success: Whether the login was successful
        
    Returns:
        bool: True if account is locked, False otherwise
    """
    now = time.time()
    
    # If successful login, clear any failed attempts
    if success:
        if username in LOGIN_ATTEMPT_CACHE:
            del LOGIN_ATTEMPT_CACHE[username]
        return False
    
    # Get current attempts or initialize new record
    record = LOGIN_ATTEMPT_CACHE.get(username, {"attempts": 0, "first_attempt": now, "locked_until": 0})
    
    # Check if account is currently locked
    if record["locked_until"] > now:
        # Extend lockout time with each additional attempt during lockout
        record["locked_until"] = now + LOCKOUT_TIME
        LOGIN_ATTEMPT_CACHE[username] = record
        return True
    
    # Reset if it's been more than the lockout time since first attempt
    if now - record["first_attempt"] > LOCKOUT_TIME:
        record = {"attempts": 0, "first_attempt": now, "locked_until": 0}
    
    # Increment attempts
    record["attempts"] += 1
    
    # Lock account if max attempts reached
    if record["attempts"] >= MAX_ATTEMPTS:
        record["locked_until"] = now + LOCKOUT_TIME
        logger.warning(f"Account locked due to too many failed attempts: {username}")
    
    # Update cache
    LOGIN_ATTEMPT_CACHE[username] = record
    
    return record["locked_until"] > now

async def is_password_pwned(password: str) -> bool:
    """
    Check if a password has been exposed in data breaches using the 'Have I Been Pwned' API.
    Uses k-anonymity to protect the password value.
    
    Args:
        password: Password to check
        
    Returns:
        bool: True if password found in breaches, False otherwise
    """
    if not settings.CHECK_PASSWORD_BREACH:
        return False
        
    try:
        # Hash the password with SHA-1
        password_hash = hashlib.sha1(password.encode('utf-8')).hexdigest().upper()
        prefix, suffix = password_hash[:5], password_hash[5:]
        
        # Check cache first to reduce API calls
        cache_key = prefix
        cache_entry = PWNED_PASSWORD_CACHE.get(cache_key)
        
        if cache_entry and (time.time() - cache_entry["timestamp"] < PWNED_CACHE_TTL):
            # Use cached result if available and fresh
            return suffix in cache_entry["suffixes"]
            
        # Make API request
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.pwnedpasswords.com/range/{prefix}",
                headers={"User-Agent": "FormIQ-Security-Check"}
            )
            
            if response.status_code != 200:
                logger.warning(f"Error checking password breach: Status {response.status_code}")
                return False
                
            # Store all suffixes in cache
            result_text = response.text
            lines = result_text.splitlines()
            suffixes = {line.split(':')[0]: int(line.split(':')[1]) for line in lines}
            
            # Update cache
            PWNED_PASSWORD_CACHE[cache_key] = {
                "timestamp": time.time(),
                "suffixes": suffixes
            }
            
            # Check if password hash suffix is in results
            if suffix in suffixes:
                # Password found in breach database
                logger.warning("Password was found in breach database and should not be used")
                return True
                
        return False
    except Exception as e:
        logger.error(f"Error checking password breach: {str(e)}")
        return False

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
        algorithm=settings.ALGORITHM
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
            algorithms=[settings.ALGORITHM]
        )
        
        # Check token type
        if payload.get("type") != "email_verification":
            return None
            
        return payload["sub"]
    except jwt.JWTError:
        return None

def create_session_token(user_id: UUID, device_info: Optional[Dict[str, Any]] = None) -> str:
    """Create a session token.
    
    Args:
        user_id: User ID
        device_info: Optional device information
        
    Returns:
        str: Session token
    """
    now = datetime.utcnow()
    session_id = str(uuid.uuid4())
    
    to_encode = {
        "exp": now + timedelta(days=settings.SESSION_EXPIRE_DAYS),
        "nbf": now,
        "iat": now,
        "sub": str(user_id),
        "sid": session_id,
        "type": "session",
        "device": device_info or {}
    }
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    
    return encoded_jwt

def verify_session_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify a session token and return the decoded payload.
    
    Args:
        token: The session token to verify
        
    Returns:
        The decoded token payload if valid, None otherwise
        
    The payload contains:
        - user_id: The ID of the user
        - session_id: The ID of the session
        - exp: The expiration timestamp
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        # Verify required claims
        if not all(k in payload for k in ["user_id", "session_id", "exp"]):
            return None
            
        return payload
    except JWTError:
        return None

def create_refresh_token(user_id: UUID, session_id: str) -> str:
    """Create a refresh token.
    
    Args:
        user_id: User ID
        session_id: Session ID
        
    Returns:
        str: Refresh token
    """
    now = datetime.utcnow()
    
    to_encode = {
        "exp": now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        "nbf": now,
        "iat": now,
        "sub": str(user_id),
        "sid": session_id,
        "type": "refresh"
    }
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    
    return encoded_jwt

def verify_refresh_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify a refresh token.
    
    Args:
        token: Refresh token to verify
        
    Returns:
        Optional[Dict[str, Any]]: Token data if valid, None otherwise
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        
        # Check token type
        if payload.get("type") != "refresh":
            return None
            
        return {
            "user_id": UUID(payload["sub"]),
            "session_id": payload["sid"],
            "issued_at": datetime.fromtimestamp(payload["iat"]),
            "expires_at": datetime.fromtimestamp(payload["exp"])
        }
    except (jwt.JWTError, ValueError):
        return None

def get_device_info(request: Request) -> Dict[str, Any]:
    """Get device information from request.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Dict[str, Any]: Device information
    """
    return {
        "ip": request.client.host,
        "user_agent": request.headers.get("user-agent"),
        "platform": request.headers.get("sec-ch-ua-platform"),
        "mobile": request.headers.get("sec-ch-ua-mobile"),
        "timestamp": datetime.utcnow().isoformat()
    }

def create_jwt_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create a JWT token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt

def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create an access token."""
    return create_jwt_token(
        data=data,
        expires_delta=expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )

def create_refresh_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create a refresh token."""
    return create_jwt_token(
        data=data,
        expires_delta=expires_delta or timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )

def decode_jwt_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT token."""
    try:
        decoded_token = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return decoded_token
    except JWTError as e:
        raise ValueError(f"Invalid token: {str(e)}")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
    user_service = Depends(get_user_service)
):
    """
    Get current user from access token.
    
    Args:
        token: JWT access token
        db: Database session
        user_service: User service instance
        
    Returns:
        User: Current user
        
    Raises:
        HTTPException: If token is invalid or user not found
    """
    from app.models.user import User  # Import at function level to avoid circular import
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = decode_token(token)
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    user = await user_service.get_by_id(user_id)
    if user is None:
        raise credentials_exception
        
    return user

async def get_current_active_user(
    current_user = Depends(get_current_user)
):
    """
    Get current active user.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User: Current active user
        
    Raises:
        HTTPException: If user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user 