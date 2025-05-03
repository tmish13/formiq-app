"""Rate limiting functionality for API endpoints."""
from typing import Dict, Optional, Tuple, Callable, Any
from datetime import datetime, timedelta
from fastapi import HTTPException, Request, Response
from functools import wraps
import time
from redis.asyncio import Redis
from app.core.logging import get_logger
from app.core.config import settings
from app.core.cache import get_redis

logger = get_logger(__name__)

class RateLimitExceeded(HTTPException):
    """Exception raised when rate limit is exceeded."""
    def __init__(self, retry_after: int):
        super().__init__(
            status_code=429,
            detail="Too many requests",
            headers={
                "Retry-After": str(retry_after),
                "X-RateLimit-Reset": str(int(time.time()) + retry_after)
            }
        )

class RedisRateLimiter:
    """Redis-based rate limiter for API endpoints."""
    
    def __init__(self, redis_client: Optional[Redis] = None):
        """Initialize rate limiter with Redis client."""
        self.redis = redis_client
        self.default_limit = settings.RATE_LIMIT_REQUESTS
        self.default_window = settings.RATE_LIMIT_WINDOW
        self.default_burst = settings.RATE_LIMIT_BURST
        
        # Default rate limits for different endpoint types
        self.endpoint_limits = {
            # Auth endpoints
            "auth": {
                "limit": 5,
                "burst": 10,
                "window": 60
            },
            # Form check analysis (resource intensive)
            "analysis": {
                "limit": 10,
                "burst": 20,
                "window": 120
            },
            # Video upload endpoints
            "upload": {
                "limit": 20,
                "burst": 40,
                "window": 60
            },
            # Standard API endpoints
            "api": {
                "limit": 60,
                "burst": 120,
                "window": 60
            }
        }
    
    async def get_redis(self) -> Redis:
        """Get Redis client, creating if necessary."""
        if not self.redis:
            self.redis = await get_redis()
        return self.redis

    async def check_rate_limit(
        self,
        key: str,
        limit: int,
        window: int,
        burst: Optional[int] = None
    ) -> Tuple[bool, int, int]:
        """Check if rate limit is exceeded for a key.
        
        Args:
            key: Rate limit key
            limit: Number of requests allowed
            window: Time window in seconds
            burst: Burst limit (optional)
            
        Returns:
            Tuple[bool, int, int]: (is_allowed, current_count, retry_after)
        """
        redis = await self.get_redis()
        now = int(time.time())
        window_key = f"{key}:{now // window}"
        
        try:
            # Use pipeline for atomic operations
            pipe = redis.pipeline()
            
            # Increment counter for current window
            pipe.incr(window_key)
            pipe.expire(window_key, window * 2)  # Keep an extra window for sliding window calc
            
            # Get counts from current and previous windows
            prev_key = f"{key}:{(now // window) - 1}"
            pipe.get(prev_key)
            
            # Execute pipeline
            current_count, _, prev_count = await pipe.execute()
            prev_count = int(prev_count or 0)
            
            # Calculate position in current window (0 to 1)
            window_position = (now % window) / window
            
            # Calculate weighted count for sliding window
            weighted_count = int(
                prev_count * (1 - window_position) +
                current_count * window_position
            )
            
            # Check burst limit first if specified
            if burst and weighted_count > burst:
                logger.warning(f"Burst limit exceeded for {key}: {weighted_count}/{burst}")
                return False, weighted_count, window
            
            # Check normal limit
            is_allowed = weighted_count <= limit
            retry_after = window - (now % window) if not is_allowed else 0
            
            return is_allowed, weighted_count, retry_after
            
        except Exception as e:
            logger.error(f"Redis rate limit error: {str(e)}")
            # Default to allowing request on Redis failure
            return True, 0, 0

def rate_limit(
    limit: Optional[int] = None,
    window: Optional[int] = None,
    burst: Optional[int] = None,
    key_func: Optional[Callable[[Request], str]] = None
):
    """Decorator for rate limiting FastAPI routes.
    
    Args:
        limit: Requests allowed per window
        window: Time window in seconds
        burst: Maximum burst allowed
        key_func: Function to generate rate limit key from request
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # Get request object
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if not request:
                logger.error("No request object found in route arguments")
                return await func(*args, **kwargs)
            
            # Get rate limiter instance
            limiter = RedisRateLimiter()
            
            # Generate rate limit key
            if key_func:
                key = key_func(request)
            else:
                # Default to IP-based limiting
                client_ip = request.headers.get("X-Forwarded-For", request.client.host)
                endpoint = request.url.path
                key = f"rate_limit:{client_ip}:{endpoint}"
            
            # Get limits (use defaults if not specified)
            endpoint_type = (
                "auth" if "/auth/" in request.url.path
                else "analysis" if "/analyze" in request.url.path
                else "upload" if "/upload" in request.url.path
                else "api"
            )
            
            default_limits = limiter.endpoint_limits[endpoint_type]
            actual_limit = limit or default_limits["limit"]
            actual_window = window or default_limits["window"]
            actual_burst = burst or default_limits["burst"]
            
            # Check rate limit
            is_allowed, count, retry_after = await limiter.check_rate_limit(
                key,
                actual_limit,
                actual_window,
                actual_burst
            )
            
            if not is_allowed:
                raise RateLimitExceeded(retry_after)
            
            # Execute route handler
            response = await func(*args, **kwargs)
            
            # Add rate limit headers to response
            if isinstance(response, Response):
                response.headers["X-RateLimit-Limit"] = str(actual_limit)
                response.headers["X-RateLimit-Remaining"] = str(max(0, actual_limit - count))
                response.headers["X-RateLimit-Reset"] = str(int(time.time()) + actual_window)
            
            return response
            
        return wrapper
    return decorator 

async def init_rate_limit():
    """Initialize rate limiting at application startup.
    
    This function sets up the rate limiting system and ensures
    all required resources are available.
    """
    from app.core.logging import get_logger
    from app.core.config import settings
    
    logger = get_logger(__name__)
    logger.info("Initializing rate limiting system")
    
    # Initialize rate limiter based on environment
    try:
        if settings.RATE_LIMIT_ENABLED:
            # Use Redis for rate limiting if available
            from app.core.cache import cache_service
            
            if cache_service.available:
                logger.info("Using Redis for rate limiting storage")
            else:
                logger.warning("Redis unavailable - using in-memory rate limiting")
                
            logger.info(f"Rate limiting enabled: {settings.RATE_LIMIT_REQUESTS} requests per {settings.RATE_LIMIT_WINDOW} seconds")
        else:
            logger.info("Rate limiting disabled")
            
    except Exception as e:
        logger.error(f"Failed to initialize rate limiting: {str(e)}")
        # Don't raise error to prevent application startup failure
        # Application can still function without rate limiting 