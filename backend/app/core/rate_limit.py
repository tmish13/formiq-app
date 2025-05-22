"""Rate limiting functionality specific to email sending."""
from typing import Dict, Optional, Tuple, Callable, Any
from datetime import datetime, timedelta
# Removed: from fastapi import HTTPException, Request, Response, status
# Removed: from functools import wraps
import time
from redis.asyncio import Redis
from app.core.logging import get_logger
from app.core.config import settings
# Keep this if email functions use it -> No, we will use cache_service
# from app.core.cache import get_redis
from app.core.cache import cache_service # Use the global cache_service instance
from app.core.exceptions import RateLimitExceededException # Moved local import to top

logger = get_logger(__name__)

# Removed RateLimitExceeded Exception (use one from core.exceptions or middleware if needed elsewhere)

# Removed RedisRateLimiter Class

# Removed rate_limit Decorator Function

# Removed init_rate_limit Function

# --- Keep Email Rate Limiting Functionality Below --- #

# Email rate limit configurations
EMAIL_RATE_LIMITS = {
    "verification": {
        "limit": settings.EMAIL_VERIFICATION_RATE_LIMIT or 3,     # Emails per window
        "window": settings.EMAIL_VERIFICATION_WINDOW or 3600  # Window in seconds (e.g., 1 hour)
    },
    "password_reset": {
        "limit": settings.EMAIL_PASSWORD_RESET_RATE_LIMIT or 3,
        "window": settings.EMAIL_PASSWORD_RESET_WINDOW or 3600
    },
    "notification": {
        "limit": settings.EMAIL_NOTIFICATION_RATE_LIMIT or 100,
        "window": settings.EMAIL_NOTIFICATION_WINDOW or 3600 
    }
}

async def increment_rate_limit(key: str, window: int, limit: int) -> Tuple[int, float, bool]:
    """Atomically increments the rate limit counter for a key.
    
    Uses Redis INCR and EXPIRE for efficiency.
    
    Args:
        key: The specific rate limit key (e.g., "email:verify:user@example.com")
        window: The time window in seconds.
        limit: The maximum number of allowed requests in the window.
        
    Returns:
        Tuple containing:
            - count: The current count after incrementing.
            - ttl: The remaining time-to-live for the key in seconds (approx).
            - allowed: Boolean indicating if the limit was exceeded before incrementing.
                     (Note: The increment happens regardless)
    """
    try:
        if not cache_service.available or not cache_service.redis_client:
            logger.warning(f"Redis unavailable for rate limiting key {key}. Failing open.")
            return 1, float(window), True # Fail open

        redis = cache_service.redis_client
        # Use pipeline for atomic operations
        pipe = redis.pipeline()
        
        # Increment the counter
        pipe.incr(key)
        # Set expiration only if the key is new (count is 1)
        # Alternatively, just set expire on every increment - simpler, slightly more overhead.
        pipe.expire(key, window)
        # Get the TTL
        pipe.ttl(key)
        
        results = await pipe.execute()
        count = results[0]
        # expire_result = results[1] # Result of expire command
        ttl = results[2]
        
        # Check if limit was exceeded *before* this increment
        allowed = (count -1) < limit
        
        return count, float(ttl) if ttl >= 0 else float(window), allowed
        
    except Exception as e:
        logger.error(f"Redis error during rate limit increment for key {key}: {str(e)}", exc_info=True)
        # Fail open - assume allowed if Redis fails
        return 1, float(window), True 

async def get_rate_limit_info(key: str) -> Dict[str, Any]:
    """Gets the current count and TTL for a rate limit key."""
    try:
        if not cache_service.available or not cache_service.redis_client:
            logger.warning(f"Redis unavailable for getting rate limit info for key {key}.")
            return {
                "key": key, "count": 0, "ttl": 0.0, "reset_in": 0,
                "reset_timestamp": int(time.time()), "error": "Redis unavailable"
            }

        redis = cache_service.redis_client
        pipe = redis.pipeline()
        pipe.get(key)
        pipe.ttl(key)
        results = await pipe.execute()
        
        count = int(results[0] or 0)
        ttl = float(results[1]) if results[1] >= 0 else 0.0 # TTL is -2 if key doesn't exist, -1 if no expiry
        
        return {
            "key": key,
            "count": count,
            "ttl": ttl,
            "reset_in": int(ttl) if ttl > 0 else 0,
            "reset_timestamp": int(time.time() + ttl) if ttl > 0 else int(time.time())
        }
        
    except Exception as e:
        logger.error(f"Redis error getting rate limit info for key {key}: {str(e)}", exc_info=True)
        return {
            "key": key,
            "count": 0,
            "ttl": 0.0,
            "reset_in": 0,
            "reset_timestamp": int(time.time()),
            "error": str(e)
        }

async def check_email_rate_limit(email: str, email_type: str) -> None:
    """Checks and increments the rate limit for sending a specific type of email.
    
    Raises:
        HTTPException(429) if the rate limit is exceeded.
    """
    if email_type not in EMAIL_RATE_LIMITS:
        logger.warning(f"Attempted to check rate limit for unknown email type: {email_type}")
        return # Or raise an error? For now, allow unknown types.

    config = EMAIL_RATE_LIMITS[email_type]
    limit = config["limit"]
    window = config["window"]
    key = f"rate_limit:email:{email_type}:{email.lower()}"

    count, ttl, allowed = await increment_rate_limit(key, window, limit)

    if not allowed:
        logger.warning(f"Email rate limit exceeded for {email_type} to {email}. Count: {count}/{limit}")
        retry_after = int(ttl) if ttl > 0 else window
        # Raise the specific exception defined in middleware/exceptions
        # from app.core.exceptions import RateLimitExceededException # Local import moved to top
        raise RateLimitExceededException(retry_after=retry_after, detail=f"Too many {email_type.replace('_', ' ')} emails sent. Try again later.")

    logger.debug(f"Email rate limit check passed for {email_type} to {email}. Count: {count}/{limit}") 