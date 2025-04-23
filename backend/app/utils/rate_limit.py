"""Rate limiting utility module."""
from functools import wraps
from typing import Callable, Optional
import time

from fastapi import HTTPException, Request
from redis import Redis
from app.core.config import settings

redis_client: Optional[Redis] = None

def get_redis() -> Redis:
    """Get Redis client instance.
    
    Returns:
        Redis client instance
    """
    global redis_client
    if redis_client is None:
        redis_client = Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD,
            decode_responses=True
        )
    return redis_client

def rate_limit(limit: int, window: int) -> Callable:
    """Rate limit decorator.
    
    Args:
        limit: Maximum number of requests allowed within the window
        window: Time window in seconds
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get request object from kwargs
            request: Request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            if not request:
                for arg in kwargs.values():
                    if isinstance(arg, Request):
                        request = arg
                        break
            
            if not request:
                raise HTTPException(
                    status_code=500,
                    detail="Could not get request object for rate limiting"
                )
            
            # Get client IP
            client_ip = request.client.host
            
            # Create Redis key
            key = f"rate_limit:{func.__name__}:{client_ip}"
            
            # Get Redis client
            redis = get_redis()
            
            # Get current count
            current = redis.get(key)
            
            if current is None:
                # First request, set to 1 with expiry
                redis.setex(key, window, 1)
            else:
                current = int(current)
                if current >= limit:
                    # Rate limit exceeded
                    ttl = redis.ttl(key)
                    raise HTTPException(
                        status_code=429,
                        detail={
                            "error": "Rate limit exceeded",
                            "limit": limit,
                            "window": window,
                            "retry_after": ttl
                        }
                    )
                # Increment counter
                redis.incr(key)
            
            # Execute the function
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator 