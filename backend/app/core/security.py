"""
Security utilities module.

This module provides functions for handling security-related operations
such as token generation, authentication, login attempt tracking, and token blacklisting.
Password hashing and pwned password checks are handled by app.core.password.
"""
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Union, Tuple
from jose import jwt, JWTError
import secrets
import uuid # For UUID generation
from uuid import UUID as UUID_type # For type hinting

from fastapi import Depends, HTTPException, status, Request, Response
from fastapi.security import OAuth2PasswordBearer
from redis import Redis

from app.core.config import settings
from app.core.logging import get_logger
# Removed: from app.core.validators import validate_password as validate_password_strength
# Removed: import hashlib, httpx, asyncio, time, json (json still needed for track_login_attempt)
import time # Still needed for track_login_attempt
import json # Still needed for track_login_attempt

# Import password functions from app.core.password
from app.core.password import verify_password, get_password_hash

# Removed: from app.core.token import verify_token, decode_token (all token logic here now)
# Remove 'from app.api import deps' from the top of the file

# Removed: pwd_context (now in app.core.password)

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

# JWT algorithm - Ensure JWT_ALGORITHM is used consistently, not ALGORITHM directly sometimes
ALGORITHM = settings.JWT_ALGORITHM # This is fine, but use settings.JWT_ALGORITHM directly in jwt.encode/decode

# Login attempt tracking for throttling (remains)
LOGIN_ATTEMPT_KEY_PREFIX = "login_attempt:"
LOGIN_ATTEMPT_KEY_TTL = settings.LOGIN_ATTEMPT_LOCKOUT_TIME * 2 # Use setting
MAX_ATTEMPTS = settings.LOGIN_MAX_ATTEMPTS # Use setting
LOCKOUT_TIME = settings.LOGIN_ATTEMPT_LOCKOUT_TIME  # Use setting

# Removed: PWNED_PASSWORD_CACHE, PWNED_CACHE_TTL_SECONDS, PWNED_PASSWORD_KEY_PREFIX (moved to password.py)

# Token blacklist functions using Redis (remains)
BLACKLIST_PREFIX = "blacklist_token:"

# --- Core JWT Creation & Decoding ---

def _create_jwt(
    subject: Union[str, UUID_type],
    expires_delta: timedelta,
    token_type: str,
    additional_claims: Optional[Dict[str, Any]] = None
) -> str:
    """
    Internal helper to create a JWT.
    Args:
        subject: The subject of the token.
        expires_delta: Lifespan of the token.
        token_type: Type of the token (e.g., "access", "refresh").
        additional_claims: Any other data to include in the token payload.
    Returns:
        The encoded JWT.
    """
    now = datetime.utcnow()
    expire = now + expires_delta
    
    to_encode: Dict[str, Any] = {
        "exp": expire,
        "sub": str(subject),
        "iat": now,
        "type": token_type,
        "jti": secrets.token_hex(16)  # Unique token identifier
    }
    
    if additional_claims:
        to_encode.update(additional_claims)
        
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

def _decode_jwt_payload(token: str) -> Optional[Dict[str, Any]]:
    """
    Internal helper to decode a JWT and return its payload.
    Handles JWT errors and returns None on failure.
    Does NOT check token type or blacklist.
    """
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError as e:
        logger.debug(f"JWT decoding error: {e}", exc_info=True)
        return None

# --- Public-Facing Token Creation Functions ---

def create_access_token(
    subject: Union[str, UUID_type], 
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create a JWT access token."""
    delta = expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return _create_jwt(subject=subject, expires_delta=delta, token_type="access")

def create_refresh_token(
    subject: Union[str, UUID_type],
    session_id: Optional[str] = None, # session_id is specific to some refresh token uses
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create a JWT refresh token."""
    delta = expires_delta or timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    additional_claims = {}
    if session_id:
        additional_claims["sid"] = session_id
    return _create_jwt(subject=subject, expires_delta=delta, token_type="refresh", additional_claims=additional_claims if additional_claims else None)

def create_password_reset_token(
    email: str, 
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create a password reset token."""
    delta = expires_delta or timedelta(hours=settings.PASSWORD_RESET_TOKEN_EXPIRE_HOURS)
    return _create_jwt(subject=email, expires_delta=delta, token_type="password_reset")

def create_email_verification_token(
    email: str, 
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create an email verification token."""
    # Ensure SECRET_KEY is used if that was the specific intention for this token, otherwise default JWT_SECRET.
    # For consistency, all tokens should ideally use JWT_SECRET. Assuming this is the case.
    delta = expires_delta or timedelta(hours=settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS) # Needs setting
    return _create_jwt(subject=email, expires_delta=delta, token_type="email_verification")

def create_session_token(
    user_id: Union[str, UUID_type],
    device_info: Optional[Dict[str, Any]] = None,
    session_id: Optional[str] = None, # Allow passing session_id for consistency, or generate if None
    expires_delta: Optional[timedelta] = None
) -> Tuple[str, str]:
    """
    Create a session token and its associated session ID.
    Returns:
        Tuple[str, str]: (encoded_session_token, session_id_used_in_token)
    """
    sid = session_id or str(uuid.uuid4())
    delta = expires_delta or timedelta(days=settings.SESSION_EXPIRE_DAYS) # Needs setting
    additional_claims = {
        "sid": sid,
        "device": device_info or {}
    }
    token = _create_jwt(subject=str(user_id), expires_delta=delta, token_type="session", additional_claims=additional_claims)
    return token, sid

# --- Token Verification & Payload Retrieval Functions ---

def verify_token_payload(
    token: str,
    redis_client: Redis,
    expected_token_type: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Verifies a JWT token against blacklist, decodes it, and optionally checks its type.
    Args:
        token: The JWT token.
        redis_client: Redis client for blacklist check.
        expected_token_type: If provided, the 'type' claim in token must match.
    Returns:
        The token payload if valid and not blacklisted, otherwise None.
    """
    if is_token_blacklisted(token, redis_client):
        logger.debug(f"Token is blacklisted: {token[:20]}...")
        return None
        
    payload = _decode_jwt_payload(token)
    if not payload:
        return None

    if expected_token_type and payload.get("type") != expected_token_type:
        logger.debug(f"Token type mismatch. Expected '{expected_token_type}', got '{payload.get('type')}'")
        return None
        
    return payload

def verify_password_reset_token_and_get_email(token: str, redis_client: Redis) -> Optional[str]:
    """Verifies password reset token and returns the email if valid."""
    payload = verify_token_payload(token, redis_client, expected_token_type="password_reset")
    return payload["sub"] if payload and "sub" in payload else None

def verify_email_verification_token_and_get_email(token: str, redis_client: Redis) -> Optional[str]:
    """Verifies email verification token and returns the email if valid."""
    payload = verify_token_payload(token, redis_client, expected_token_type="email_verification")
    return payload["sub"] if payload and "sub" in payload else None

def verify_session_token_and_get_payload(token: str, redis_client: Redis) -> Optional[Dict[str, Any]]:
    """Verifies session token and returns its payload if valid."""
    payload = verify_token_payload(token, redis_client, expected_token_type="session")
    if payload and all(k in payload for k in ["sub", "sid", "exp"]): # 'sub' is user_id
        return payload
    logger.debug("Session token missing required claims (sub, sid, exp) or invalid.")
    return None

# --- FastAPI Dependency for Current User ---
# Moved to app.core.auth_utils.py to avoid circular import

# --- Token Blacklisting (remains) ---
def blacklist_token(token: str, redis_client: Redis, expires_in_seconds: Optional[int] = None) -> None:
    # ... (existing code, ensure JWT_SECRET and ALGORITHM are settings.JWT_SECRET, settings.JWT_ALGORITHM)
    # Minor adjustment: use settings.JWT_ALGORITHM directly instead of ALGORITHM global for decode
    key = f"{BLACKLIST_PREFIX}{token}"
    expiry_seconds_to_use = expires_in_seconds

    if expiry_seconds_to_use is None:
        try:
            # Use verify_exp=False to decode even if expired, just to get the 'exp' claim
            payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM], options={"verify_signature": True, "verify_exp": False})
            if "exp" in payload:
                token_exp_timestamp = payload["exp"]
                current_timestamp = datetime.utcnow().timestamp()
                remaining_time = int(token_exp_timestamp - current_timestamp)
                
                # Blacklist for at least the remaining time + buffer, or a default if already expired.
                # Ensure it's blacklisted for a minimum duration even if remaining_time is short.
                min_blacklist_duration = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60 // 2 # e.g., half of access token life
                
                if remaining_time > 0:
                    expiry_seconds_to_use = max(remaining_time + 60, min_blacklist_duration) # Add 60s buffer
                else: 
                    expiry_seconds_to_use = min_blacklist_duration
            else: # No 'exp' claim, use default
                expiry_seconds_to_use = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        except JWTError:
            logger.warning(f"Could not decode token to get expiry for blacklist: {token[:20]}... Defaulting expiry.")
            expiry_seconds_to_use = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    elif expiry_seconds_to_use <= 0:
         logger.warning(f"Non-positive expires_in_seconds provided for blacklist: {expiry_seconds_to_use}. Defaulting expiry.")
         expiry_seconds_to_use = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60

    try:
        redis_client.setex(key, expiry_seconds_to_use, "blacklisted")
        logger.info(f"Token blacklisted in Redis: {token[:20]}... for {expiry_seconds_to_use}s")
    except Exception as e:
        logger.error(f"Failed to blacklist token in Redis: {token[:20]}... - {e}", exc_info=True)


def is_token_blacklisted(token: str, redis_client: Redis) -> bool:
    # ... (existing code, ensure no issues)
    key = f"{BLACKLIST_PREFIX}{token}"
    try:
        return redis_client.exists(key) > 0
    except Exception as e:
        logger.error(f"Failed to check token blacklist in Redis: {token[:20]}... - {e}", exc_info=True)
        # Fail-safe consideration: If Redis is down, should we deny all tokens or allow?
        # Current: allow (returns False if not confirmed blacklisted).
        # For higher security, if Redis check fails, could return True (treat as blacklisted).
        return False 

# --- Login Attempt Throttling (remains) ---
def track_login_attempt(username: str, success: bool, redis_client: Redis) -> bool:
    # ... (existing code - ensure settings are used for MAX_ATTEMPTS, LOCKOUT_TIME, LOGIN_ATTEMPT_KEY_TTL)
    now = time.time()
    redis_key = f"{LOGIN_ATTEMPT_KEY_PREFIX}{username}"

    if success:
        try:
            redis_client.delete(redis_key)
        except Exception as e:
            logger.error(f"Failed to delete login attempt key from Redis for {username}: {e}", exc_info=True)
        return False

    record_str = None
    try:
        record_str = redis_client.get(redis_key)
    except Exception as e:
        logger.error(f"Failed to get login attempt key from Redis for {username}: {e}", exc_info=True)
        return False 

    if record_str:
        try:
            record = json.loads(record_str)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse login attempt record from Redis for {username}. Resetting.", exc_info=True)
            record = {"attempts": 0, "first_attempt": now, "locked_until": 0.0}
    else:
        record = {"attempts": 0, "first_attempt": now, "locked_until": 0.0}

    if float(record.get("locked_until", 0.0)) > now:
        record["locked_until"] = now + LOCKOUT_TIME # Use settings.LOGIN_ATTEMPT_LOCKOUT_TIME
        try:
            # TTL should be LOGIN_ATTEMPT_KEY_TTL from settings
            redis_client.setex(redis_key, settings.LOGIN_ATTEMPT_KEY_TTL_SECONDS, json.dumps(record)) 
        except Exception as e:
            logger.error(f"Failed to update locked_until in Redis for {username}: {e}", exc_info=True)
        return True
    
    if (now - float(record.get("first_attempt", now))) > LOCKOUT_TIME: # Use settings.LOGIN_ATTEMPT_LOCKOUT_TIME
        record = {"attempts": 0, "first_attempt": now, "locked_until": 0.0}
    
    record["attempts"] = record.get("attempts", 0) + 1
    record["first_attempt"] = record.get("first_attempt", now) 
    
    if record["attempts"] >= MAX_ATTEMPTS: # Use settings.LOGIN_MAX_ATTEMPTS
        record["locked_until"] = now + LOCKOUT_TIME # Use settings.LOGIN_ATTEMPT_LOCKOUT_TIME
        logger.warning(f"Account locked due to too many failed login attempts (Redis): {username}")
    
    try:
        # TTL should be LOGIN_ATTEMPT_KEY_TTL from settings
        redis_client.setex(redis_key, settings.LOGIN_ATTEMPT_KEY_TTL_SECONDS, json.dumps(record))
    except Exception as e:
        logger.error(f"Failed to set login attempt data in Redis for {username}: {e}", exc_info=True)

    return float(record.get("locked_until", 0.0)) > now

# --- Helper: Create Token Response DTO (remains, uses new token functions) ---
def create_token_response(
    user_id: Union[str, UUID_type], 
    session_id_for_refresh: Optional[str] = None, # To be included in refresh token if session-bound
    user_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create access and refresh tokens and return them in the response.
    """
    access_token = create_access_token(subject=user_id)
    # If session_id_for_refresh is provided, the refresh token can be tied to that session
    refresh_token = create_refresh_token(subject=user_id, session_id=session_id_for_refresh) 
    
    result = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user_id": str(user_id), # Ensure user_id is string in response
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }
    
    if user_data:
        result["user"] = user_data
        
    return result

# --- Utility: Get Device Info (remains) ---
def get_device_info(request: Request) -> Dict[str, Any]:
    # ... (existing code)
    return {
        "ip": request.client.host if request.client else "unknown",
        "user_agent": request.headers.get("user-agent", "unknown"),
        "platform": request.headers.get("sec-ch-ua-platform", "unknown"),
        "mobile": request.headers.get("sec-ch-ua-mobile", "unknown"), # e.g. "?1" for true, "?0" for false
        "timestamp": datetime.utcnow().isoformat()
    }


# --- Security Initialization (remains, review content) ---
def init_security():
    """Initialize security systems at application startup.
    This function validates security configurations.
    Password context is now in app.core.password.
    """
    # from app.core.logging import get_logger # Already imported
    # from app.core.config import settings # Already imported
    # import secrets # Already imported
    
    logger = get_logger(__name__)
    logger.info("Initializing security systems (token, blacklist, throttling config)")
    
    try:
        # Validate required security settings for JWT
        if not settings.JWT_SECRET or len(settings.JWT_SECRET) < 32:
            logger.warning("JWT_SECRET is too short or not set - security risk!")
            if settings.ENVIRONMENT == "production":
                raise ValueError("JWT_SECRET must be at least 32 characters in production")
        
        # SECRET_KEY is often used for other things like CSRF, session cookies (non-JWT)
        # If it's also used for some JWTs (like email verification in old code), ensure it's strong.
        # The refactor aims to use JWT_SECRET for all JWTs.
        if not settings.SECRET_KEY or len(settings.SECRET_KEY) < 32:
            logger.warning("SECRET_KEY is too short or not set - security risk for non-JWT secrets!")
            # No direct production raise here unless specifically used for critical JWTs not covered by JWT_SECRET
        
        # Validate encryption key (used for data at rest, not tokens)
        # This is still relevant if app uses Fernet for other encryption.
        from cryptography.fernet import Fernet
        try:
            if settings.ENCRYPTION_KEY:
                Fernet(settings.ENCRYPTION_KEY.encode()) # Fernet key must be bytes
                logger.info("Encryption key validated")
            else:
                # This might be acceptable if no direct data encryption using Fernet is done by this app
                logger.info("ENCRYPTION_KEY not set. No general data encryption via Fernet configured.")
                # If production requires it for some feature, that feature should check.
        except Exception as e:
            logger.error(f"Invalid ENCRYPTION_KEY: {str(e)}. Fernet encryption will fail.")
            if settings.ENVIRONMENT == "production" and settings.REQUIRE_ENCRYPTION_KEY_IN_PROD: # New hypothetical setting
                 raise ValueError(f"ENCRYPTION_KEY is invalid or not set but required in production: {e}")
        
        if settings.ENVIRONMENT == "production":
            if settings.DEBUG:
                logger.warning("DEBUG mode is enabled in production - security risk!")
            
            # Ensure BACKEND_CORS_ORIGINS is used, not CORS_ORIGINS directly if they differ
            if not settings.BACKEND_CORS_ORIGINS or "*" in settings.BACKEND_CORS_ORIGINS:
                logger.warning("CORS is configured to allow all origins (*) in production - security risk!")
        
        logger.info("Security systems configuration validated successfully.")
    except Exception as e:
        logger.error(f"Security initialization validation failed: {str(e)}", exc_info=True)
        if settings.ENVIRONMENT == "production":
            # For critical validation failures, re-raise to stop startup
            if isinstance(e, ValueError) and ("JWT_SECRET" in str(e) or ("ENCRYPTION_KEY" in str(e) and settings.REQUIRE_ENCRYPTION_KEY_IN_PROD)):
                raise
        # In dev/test, allow continuation with warnings for non-critical issues.

# Ensure all necessary settings are present in config.py:
# settings.BCRYPT_ROUNDS (e.g., 12)
# settings.HIBP_TIMEOUT_SECONDS (e.g., 10.0)
# settings.HIBP_USER_AGENT (e.g., "FormIQ-Security-Check/1.0")
# settings.LOGIN_ATTEMPT_LOCKOUT_TIME (e.g., 300)
# settings.LOGIN_MAX_ATTEMPTS (e.g., 5)
# settings.LOGIN_ATTEMPT_KEY_TTL_SECONDS (e.g., settings.LOGIN_ATTEMPT_LOCKOUT_TIME * 2)
# settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS (e.g., 24)
# settings.SESSION_EXPIRE_DAYS (e.g., 7)
# settings.REQUIRE_ENCRYPTION_KEY_IN_PROD (e.g., False, or True if app uses Fernet encryption critically)

# Removed old token functions:
# - create_access_token (old version with subject, data - the problematic one)
# - create_refresh_token (old version with subject, data)
# - decode_token (old generic one)
# - verify_password_reset_token (old one, replaced by verify_password_reset_token_and_get_email)
# - create_password_reset_token (old one - generate_password_reset_token was also a duplicate)
# - generate_password_reset_token
# - decode_access_token (old one raising HTTPException, replaced by get_current_user_payload)
# - create_email_verification_token (old one, replaced by new one)
# - verify_email_token (old one, replaced by verify_email_verification_token_and_get_email)
# - create_session_token (old one, new one returns tuple with session_id)
# - verify_session_token (old one, replaced by verify_session_token_and_get_payload)
# - create_refresh_token (old versions, new one is consolidated)
# - verify_refresh_token (old one, replaced by verify_token_payload(..., type="refresh"))
# - create_jwt_token (old generic one)
# - decode_jwt_token (old generic one)

# Removed password functions (moved or using app.core.password):
# - verify_password
# - get_password_hash
# - is_password_pwned (and its constants)

# Removed: create_token_response (old version, replaced by new one)
# Removed: create_email_verification_token (old version, replaced by new one)
# Removed: verify_email_token (old version, replaced by new one)
# Removed: create_session_token (old version, new one returns tuple with session_id)
# Removed: verify_session_token (old version, replaced by new one)
# Removed: create_refresh_token (old versions, new one is consolidated)
# Removed: verify_refresh_token (old version, replaced by new one)
# Removed: get_device_info (old version, replaced by new one)
# Removed: create_jwt_token (old generic one)
# Removed: decode_jwt_token (old generic one)
# Removed: init_security (old version, replaced by new one) 

verify_password_reset_token = verify_password_reset_token_and_get_email 