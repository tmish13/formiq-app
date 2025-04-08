"""Rate limiting middleware for API rate control."""
import time
from fastapi import Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Dict, Callable, Tuple, Optional, Set
import hashlib
import json
from datetime import datetime

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

class RateLimitExceeded(Exception):
    """Exception raised when rate limit is exceeded."""
    pass

class MemoryStore:
    """In-memory store for rate limiting data."""
    
    def __init__(self):
        """Initialize the memory store."""
        self.data: Dict[str, Tuple[int, float]] = {}  # key -> (count, reset_time)
        self.last_cleanup = time.time()
        
    async def increment(self, key: str, window: float, max_requests: int) -> Tuple[int, float, bool]:
        """Increment the counter for a key.
        
        Args:
            key: The rate limit key
            window: The time window in seconds
            max_requests: The maximum number of requests allowed
            
        Returns:
            Tuple[int, float, bool]: (current count, reset time, exceeded)
        """
        now = time.time()
        
        # Cleanup old entries every 60 seconds
        if now - self.last_cleanup > 60:
            self._cleanup()
            self.last_cleanup = now
        
        # Get or create entry
        count, reset_time = self.data.get(key, (0, now + window))
        
        # Reset if window expired
        if now > reset_time:
            count = 0
            reset_time = now + window
        
        # Increment counter
        count += 1
        
        # Store updated values
        self.data[key] = (count, reset_time)
        
        # Check if limit exceeded
        exceeded = count > max_requests
        
        return count, reset_time, exceeded
    
    def _cleanup(self):
        """Remove expired entries."""
        now = time.time()
        keys_to_remove = []
        
        for key, (_, reset_time) in self.data.items():
            if now > reset_time:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.data[key]

class RedisStore:
    """Redis-based store for rate limiting data."""
    
    def __init__(self):
        """Initialize the Redis store."""
        self.redis = None
    
    async def _get_redis(self):
        """Get Redis connection lazily."""
        if self.redis is None:
            from app.core.redis import get_redis
            self.redis = await get_redis()
        return self.redis
    
    async def increment(self, key: str, window: float, max_requests: int) -> Tuple[int, float, bool]:
        """Increment the counter for a key.
        
        Args:
            key: The rate limit key
            window: The time window in seconds
            max_requests: The maximum number of requests allowed
            
        Returns:
            Tuple[int, float, bool]: (current count, reset time, exceeded)
        """
        redis = await self._get_redis()
        now = time.time()
        reset_time = now + window
        
        # Use Redis pipeline for atomic operations
        pipeline = redis.pipeline()
        
        # Check if key exists
        pipeline.exists(f"ratelimit:{key}")
        # Get current count
        pipeline.get(f"ratelimit:{key}")
        # Get TTL
        pipeline.ttl(f"ratelimit:{key}")
        
        exists, count, ttl = await pipeline.execute()
        
        # If key doesn't exist or TTL is negative (expired)
        if not exists or ttl < 0:
            count = 1
            # Set key with expiration
            await redis.set(f"ratelimit:{key}", count, ex=int(window))
            return count, reset_time, False
        
        # Increment counter
        count = await redis.incr(f"ratelimit:{key}")
        
        # Get remaining TTL for reset time
        remaining_ttl = await redis.ttl(f"ratelimit:{key}")
        reset_time = now + remaining_ttl
        
        # Check if limit exceeded
        exceeded = count > max_requests
        
        return count, reset_time, exceeded

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware for API rate limiting.
    
    This middleware enforces rate limits on API requests based on:
    - Client IP address
    - Authenticated user ID
    - Endpoint path
    
    Different endpoints can have different rate limits, and rate limit
    information is included in response headers.
    """
    
    def __init__(self, app):
        """Initialize the middleware.
        
        Args:
            app: The FastAPI application
        """
        super().__init__(app)
        
        # Set up storage backend
        storage = getattr(settings, "RATE_LIMIT_STORAGE", "memory")
        if storage == "redis" and hasattr(settings, "REDIS_HOST"):
            self.store = RedisStore()
        else:
            self.store = MemoryStore()
        
        # Default rate limits
        self.default_requests = getattr(settings, "RATE_LIMIT_DEFAULT_REQUESTS", 100)
        self.default_burst = getattr(settings, "RATE_LIMIT_DEFAULT_BURST", 200)
        self.token_requests = getattr(settings, "RATE_LIMIT_TOKEN_REQUESTS", 50)
        
        # Endpoints with custom rate limits
        self.custom_limits = {
            "/api/v1/auth/login": (5, 15),  # 5 requests per minute, burst of 15
            "/api/v1/auth/register": (3, 10),  # 3 requests per minute, burst of 10
            "/api/v1/form-checks/analyze": (10, 30),  # 10 requests per minute, burst of 30
        }
        
        # Endpoints excluded from rate limiting
        self.excluded_paths: Set[str] = {
            "/health",
            "/api/v1/health",
            "/api/docs",
            "/api/redoc",
            "/api/openapi.json",
        }
        
        # Window time in seconds (1 minute)
        self.window = 60
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process the request and apply rate limiting.
        
        Args:
            request: The incoming request
            call_next: The next middleware or route handler
            
        Returns:
            Response: The response
        """
        # Skip rate limiting for excluded paths
        if request.url.path in self.excluded_paths:
            return await call_next(request)
        
        # Get rate limit key
        key = self._get_rate_limit_key(request)
        
        # Get custom rate limits for the endpoint if available
        requests_limit, burst_limit = self._get_limits_for_endpoint(request.url.path)
        
        try:
            # Increment counter and check limit
            count, reset_time, exceeded = await self.store.increment(key, self.window, requests_limit)
            
            # If exceeded but under burst limit, allow but log
            if exceeded and count <= burst_limit:
                logger.warning(f"Rate limit soft exceeded: {count}/{requests_limit} for {key}")
                exceeded = False
            
            # If exceeds burst limit, block request
            if exceeded:
                logger.warning(f"Rate limit hard exceeded: {count}/{burst_limit} for {key}")
                return self._rate_limit_response(count, requests_limit, reset_time)
            
            # Process request normally
            response = await call_next(request)
            
            # Add rate limit headers
            response.headers["X-RateLimit-Limit"] = str(requests_limit)
            response.headers["X-RateLimit-Remaining"] = str(max(0, requests_limit - count))
            response.headers["X-RateLimit-Reset"] = str(int(reset_time))
            
            return response
            
        except Exception as e:
            # Log error and let request through if rate limiting fails
            logger.error(f"Rate limiting error: {str(e)}", exc_info=True)
            return await call_next(request)
    
    def _get_rate_limit_key(self, request: Request) -> str:
        """Generate a rate limit key for the request.
        
        Args:
            request: The incoming request
            
        Returns:
            str: The rate limit key
        """
        # Get client IP
        client_ip = self._get_client_ip(request)
        
        # Get user ID if authenticated
        user_id = self._get_user_id(request)
        
        # Create key components
        key_parts = {
            "ip": client_ip,
            "user_id": user_id,
            "path": request.url.path,
            "method": request.method,
        }
        
        # Create deterministic key
        key_json = json.dumps(key_parts, sort_keys=True)
        return hashlib.sha256(key_json.encode()).hexdigest()
    
    def _get_client_ip(self, request: Request) -> str:
        """Get the client IP address.
        
        Args:
            request: The incoming request
            
        Returns:
            str: The client IP address
        """
        # Try X-Forwarded-For first
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Get first IP in the list
            return forwarded_for.split(",")[0].strip()
        
        # Fall back to client.host
        return request.client.host if request.client else "unknown"
    
    def _get_user_id(self, request: Request) -> Optional[str]:
        """Get the authenticated user ID if available.
        
        Args:
            request: The incoming request
            
        Returns:
            Optional[str]: The user ID or None
        """
        try:
            # This requires setting user in auth middleware
            user = getattr(request.state, "user", None)
            if user and hasattr(user, "id"):
                return str(user.id)
        except Exception:
            pass
        
        return None
    
    def _get_limits_for_endpoint(self, path: str) -> Tuple[int, int]:
        """Get rate limits for the endpoint.
        
        Args:
            path: The request path
            
        Returns:
            Tuple[int, int]: (requests limit, burst limit)
        """
        # Check for custom limits
        if path in self.custom_limits:
            return self.custom_limits[path]
        
        # Check if token endpoint
        if "/token" in path or "/auth/" in path:
            return self.token_requests, self.token_requests * 2
        
        # Default limits
        return self.default_requests, self.default_burst
    
    def _rate_limit_response(self, count: int, limit: int, reset_time: float) -> Response:
        """Create rate limit exceeded response.
        
        Args:
            count: Current request count
            limit: Rate limit
            reset_time: When the rate limit resets
            
        Returns:
            Response: 429 Too Many Requests response
        """
        reset_seconds = int(reset_time - time.time())
        body = {
            "detail": "Too many requests",
            "limit": limit,
            "current": count,
            "reset_in_seconds": max(0, reset_seconds),
            "reset_at": datetime.fromtimestamp(reset_time).isoformat(),
        }
        
        response = Response(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content=json.dumps(body),
            media_type="application/json",
        )
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = "0"
        response.headers["X-RateLimit-Reset"] = str(int(reset_time))
        response.headers["Retry-After"] = str(max(0, reset_seconds))
        
        return response 