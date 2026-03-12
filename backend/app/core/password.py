"""Password utilities module."""
from passlib.context import CryptContext
from app.core.validators import validate_password as validate_password_strength
import asyncio
import hashlib
# import time # No longer needed directly here
# import json # No longer needed directly here
# from redis import Redis # No longer needed directly here
from app.core.config import settings
from app.core.logging import get_logger
import httpx

logger = get_logger(__name__)

# Password hashing context with stronger settings
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=settings.BCRYPT_ROUNDS,
    bcrypt__default_rounds=settings.BCRYPT_ROUNDS
)

# Pwned password check constants - Caching removed for now, can be added back with async redis
# PWNED_CACHE_TTL_SECONDS = 86400
# PWNED_PASSWORD_KEY_PREFIX = "pwned_password_cache:"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify that a plain password matches a hashed password.
    
    Args:
        plain_password: Plain text password
        hashed_password: Hashed password
    
    Returns:
        bool: True if passwords match, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)

async def is_password_pwned(password: str) -> bool:
    """
    Check if a password has been exposed in data breaches using the 'Have I Been Pwned' API (k-anonymity).
    Args:
        password: Password to check.
    Returns:
        bool: True if password found in breaches, False otherwise.
    """
    if not settings.CHECK_PASSWORD_BREACH:
        logger.info("Password breach check is disabled via settings.CHECK_PASSWORD_BREACH.")
        return False
        
    api_request_prefix_for_logging = "unknown_prefix"
    try:
        password_hash = hashlib.sha1(password.encode('utf-8')).hexdigest().upper()
        prefix, suffix = password_hash[:5], password_hash[5:]
        api_request_prefix_for_logging = prefix
        
        # Removed Redis caching logic for now to simplify async refactor
        # Caching can be re-introduced using an async Redis client if this function
        # is called with one, or by a dedicated caching layer.

        async with httpx.AsyncClient(timeout=settings.HIBP_TIMEOUT_SECONDS) as client:
            response = await client.get(
                f"https://api.pwnedpasswords.com/range/{prefix}",
                headers={"User-Agent": settings.HIBP_USER_AGENT}
            )
            
            if response.status_code != 200:
                logger.warning(f"HIBP API error for prefix {prefix}: Status {response.status_code}, Response: {response.text[:200]}")
                return False # Fail open (not pwned) if API error
                
            result_text = response.text
            # Check if the suffix is in any of the lines returned
            if any(line.startswith(suffix) for line in result_text.splitlines()):
                logger.warning(f"Password with SHA1 prefix {prefix} found in HIBP breach database (suffix matched).")
                return True
                
        return False
    except httpx.TimeoutException:
        logger.warning(f"HIBP API call timed out for prefix {api_request_prefix_for_logging}. Assuming password not pwned.")
        return False
    except httpx.RequestError as e:
        logger.error(f"HIBP API request error for prefix {api_request_prefix_for_logging}: {e}", exc_info=True)
        return False
    except Exception as e:
        logger.error(f"General error in is_password_pwned for prefix {api_request_prefix_for_logging}: {e}", exc_info=True)
        return False

def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt.
    Validates strength before hashing.
    Args:
        password: Plain text password
    Returns:
        str: Hashed password
    Raises:
        ValueError: If password doesn't meet security requirements.
    """
    validate_password_strength(password)
    return pwd_context.hash(password)