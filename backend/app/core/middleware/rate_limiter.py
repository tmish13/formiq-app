"""Rate limiting middleware for API protection."""
import time
from typing import Callable, Dict, List, Optional, Set, Tuple, Union

from fastapi import Request, Response, status
from redis.asyncio.client import Redis
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.logging import get_logger
from app.core.exceptions import RateLimitExceededException

logger = get_logger(__name__)

class MemoryRateLimiter:
    """In-memory rate limiter used as fallback when Redis is unavailable."""
    
    def __init__(self):
        """Initialize the memory rate limiter."""
        self.requests: Dict[str, List[float]] = {}
        self.last_cleanup = time.time()
        self.cleanup_interval = 60  # Cleanup every minute
    
    async def increment(self, key: str, window: int) -> Tuple[int, int]:
        """
        Increment request count for a key within a time window.
        
        Args:
            key: The rate limit key
            window: Time window in seconds
            
        Returns:
            Tuple of (current count, window)
        """
        now = time.time()
        
        # Periodic cleanup to prevent memory leaks
        if now - self.last_cleanup > self.cleanup_interval:
            self._cleanup()
            self.last_cleanup = now
        
        # Initialize key if not exists
        if key not in self.requests:
            self.requests[key] = []
        
        # Clean old requests outside window
        cutoff = now - window
        self.requests[key] = [t for t in self.requests[key] if t > cutoff]
        
        # Add current request
        self.requests[key].append(now)
        
        return len(self.requests[key]), window
    
    def _cleanup(self) -> None:
        """Clean up old rate limit data to prevent memory leaks."""
        now = time.time()
        keys_to_delete = []
        
        for key, timestamps in self.requests.items():
            # Keep only requests from the last 10 minutes
            cutoff = now - 600  # 10 minutes
            new_timestamps = [t for t in timestamps if t > cutoff]
            
            if new_timestamps:
                self.requests[key] = new_timestamps
            else:
                keys_to_delete.append(key)
        
        # Delete empty keys
        for key in keys_to_delete:
            del self.requests[key]


class EnhancedRateLimiter(BaseHTTPMiddleware):
    """
    Enhanced rate limiting middleware with Redis-based distributed limiting.
    
    Features:
    - Redis-based rate limiting for distributed deployment
    - Memory-based fallback for when Redis is unavailable
    - Configurable rate limits per endpoint
    - Support for API key and user-based rate limiting
    - Customizable response headers
    """
    
    def __init__(
        self,
        app,
        redis_client: Optional[Redis] = None,
        requests_per_minute: int = settings.RATE_LIMIT_REQUESTS,
        burst_size: int = settings.RATE_LIMIT_BURST,
        window_size: int = settings.RATE_LIMIT_WINDOW,
        exclude_paths: Optional[List[str]] = None,
        endpoint_limits: Optional[Dict[str, int]] = None,
    ):
        """
        Initialize the rate limiter.
        
        Args:
            app: The FastAPI application
            redis_client: Redis client for distributed rate limiting
            requests_per_minute: Default requests allowed per minute
            burst_size: Maximum burst allowed
            window_size: Time window in seconds
            exclude_paths: List of paths to exclude from rate limiting
            endpoint_limits: Dictionary of endpoint-specific rate limits
        """
        super().__init__(app)
        self.redis = redis_client
        self.default_limit = requests_per_minute
        self.burst_size = burst_size
        self.window_size = window_size
        self.exclude_paths = exclude_paths or []
        self.endpoint_limits = endpoint_limits or {}
        self.memory_limiter = MemoryRateLimiter()
        
        # Cache of limit by path
        self.path_limit_cache: Dict[str, int] = {}
        
        logger.info(
            f"Rate limiter initialized with default {requests_per_minute} "
            f"requests per minute, window {window_size}s, burst {burst_size}"
        )
    
    def _should_limit(self, request: Request) -> bool:
        """
        Determine if rate limiting should be applied to this request.
        
        Args:
            request: The incoming request
            
        Returns:
            Boolean indicating if rate limiting should be applied
        """
        # Skip rate limiting for excluded paths
        path = request.url.path
        for excluded in self.exclude_paths:
            if path.startswith(excluded):
                return False
        
        # Always rate limit non-GET methods
        if request.method != "GET":
            return True
        
        # Don't rate limit health check endpoints 
        if "health" in path:
            return False
        
        return True
    
    def _get_limit_for_path(self, path: str) -> int:
        """
        Get rate limit for a specific path.
        
        Args:
            path: The request path
            
        Returns:
            Rate limit for the path
        """
        # Check cache first
        if path in self.path_limit_cache:
            return self.path_limit_cache[path]
        
        # Check endpoint-specific limits
        for pattern, limit in self.endpoint_limits.items():
            if path.startswith(pattern):
                self.path_limit_cache[path] = limit
                return limit
        
        # Default limit
        self.path_limit_cache[path] = self.default_limit
        return self.default_limit
    
    def _get_rate_limit_key(self, request: Request) -> str:
        """
        Generate a rate limit key based on client identity.
        
        Args:
            request: The incoming request
            
        Returns:
            Rate limit key
        """
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        
        # Get path for endpoint-specific limiting
        path = request.url.path
        
        # Check for API key or user identity
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return f"rate:api:{api_key}:{path}"
        
        # Try to get user ID from session
        user_id = None
        if hasattr(request.state, "user_id"):
            user_id = request.state.user_id
        
        if user_id:
            return f"rate:user:{user_id}:{path}"
        
        # Fallback to IP-based limiting
        return f"rate:ip:{client_ip}:{path}"
    
    async def _increment_redis(
        self, key: str, window: int
    ) -> Tuple[int, int]:
        """
        Increment request count in Redis within a sliding window.
        
        Args:
            key: The rate limit key
            window: Time window in seconds
            
        Returns:
            Tuple of (current count, window)
        """
        pipe = self.redis.pipeline()
        now = int(time.time())
        window_key = f"{key}:{now // window}"
        
        try:
            # Increment the counter for current window
            await pipe.incr(window_key)
            # Set expiration if not already set
            await pipe.expire(window_key, window * 2)
            
            # Get counts from current and previous window
            prev_window_key = f"{key}:{(now // window) - 1}"
            curr_count = await self.redis.get(window_key)
            prev_count = await self.redis.get(prev_window_key)
            
            # Calculate weighted count based on sliding window
            curr_count = int(curr_count or 0)
            prev_count = int(prev_count or 0)
            
            # Calculate position in current window (0.0 to 1.0)
            window_position = (now % window) / window
            
            # Calculate weighted count
            weighted_count = int(prev_count * (1 - window_position) + curr_count)
            
            return weighted_count, window
            
        except Exception as e:
            # Log error and fallback to memory-based limiter
            logger.error(f"Redis rate limiting failed: {str(e)}")
            return await self.memory_limiter.increment(key, window)
    
    async def _check_rate_limit(
        self, request: Request
    ) -> Tuple[bool, int, int, int]:
        """
        Check if a request exceeds the rate limit.
        
        Args:
            request: The incoming request
            
        Returns:
            Tuple of (is_allowed, current, limit, reset)
        """
        path = request.url.path
        limit = self._get_limit_for_path(path)
        key = self._get_rate_limit_key(request)
        window = self.window_size
        
        # Use Redis if available, otherwise fall back to memory
        if self.redis:
            try:
                current, _ = await self._increment_redis(key, window)
            except Exception as e:
                logger.error(f"Redis rate limiting failed: {str(e)}")
                current, _ = await self.memory_limiter.increment(key, window)
        else:
            current, _ = await self.memory_limiter.increment(key, window)
        
        # Allow burst up to burst_size
        max_allowed = min(limit, self.burst_size)
        is_allowed = current <= max_allowed
        
        # Calculate reset time
        reset = int(time.time()) + window
        
        return is_allowed, current, max_allowed, reset
    
    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        """
        Process a request applying rate limiting.
        
        Args:
            request: The incoming request
            call_next: The next middleware or route handler
            
        Returns:
            Response from the next handler or rate limit exceeded response
        """
        # Skip rate limiting if not applicable
        if not self._should_limit(request):
            return await call_next(request)
        
        # Check rate limit
        is_allowed, current, limit, reset = await self._check_rate_limit(request)
        
        # If rate limit exceeded, return 429 response
        if not is_allowed:
            logger.warning(
                f"Rate limit exceeded for {request.url.path}",
                extra={
                    "client_ip": request.client.host if request.client else "unknown",
                    "current": current,
                    "limit": limit,
                    "path": request.url.path,
                }
            )
            
            # Create response with appropriate headers
            headers = {
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(reset),
                "Retry-After": str(reset - int(time.time())),
            }
            
            raise RateLimitExceededException(
                message="Rate limit exceeded",
                retry_after=reset - int(time.time()),
                details={
                    "limit": limit,
                    "current": current,
                    "reset": reset,
                }
            )
        
        # Process the request
        response = await call_next(request)
        
        # Add rate limit headers to response
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(max(0, limit - current))
        response.headers["X-RateLimit-Reset"] = str(reset)
        
        return response 