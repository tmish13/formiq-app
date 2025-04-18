from typing import Optional, Any, Dict, Callable
from fastapi import Request, Response, HTTPException, FastAPI
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from redis import Redis, RedisError
from app.core.logging import logger
import time
from app.core.exceptions import RateLimitException
from prometheus_client import Counter, Histogram, Gauge
from app.core.cache import CacheService
from fastapi.responses import JSONResponse
import logging
from app.core.config import settings
from app.core.redis import get_redis

# Prometheus metrics
RATE_LIMIT_EXCEEDED = Counter(
    'rate_limit_exceeded_counter',  # Changed metric name to avoid conflicts
    'Number of requests that exceeded rate limit',
    ['endpoint']
)

RATE_LIMIT_REMAINING = Gauge(
    'rate_limit_remaining_gauge',  # Changed metric name to avoid conflicts
    'Number of requests remaining before rate limit',
    ['endpoint']
)

RATE_LIMIT_LATENCY = Histogram(
    "rate_limit_latency_seconds",
    "Rate limiter latency in seconds",
    ["path"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1]
)

RATE_LIMIT_REQUESTS = Gauge(
    'rate_limit_requests_current',
    'Current number of requests in the window',
    ['client_ip', 'endpoint']
)

logger = logging.getLogger(__name__)

class RateLimiterMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, redis_client: CacheService, requests_per_minute: int = 60):
        super().__init__(app)
        self.redis_client = redis_client
        self.requests_per_minute = requests_per_minute
        self.window = 60  # 1 minute window

    def _should_skip_rate_limit(self, request: Request) -> bool:
        """Check if request should bypass rate limiting"""
        # Skip rate limiting for specific paths
        if request.url.path in ["/docs", "/redoc", "/openapi.json"]:
            return True
        
        # Check for bypass header or query param
        bypass_header = request.headers.get("X-Rate-Limit-Bypass")
        bypass_param = request.query_params.get("bypass_rate_limit")
        
        return bool(bypass_header or bypass_param)

    async def _get_client_identifier(self, request: Request) -> str:
        """Get unique identifier for the client"""
        # Use X-Forwarded-For header if available, otherwise use client host or default
        client_ip = request.headers.get("X-Forwarded-For")
        if not client_ip:
            client_ip = request.client.host if request.client else "127.0.0.1"
        return f"rate_limit:{client_ip}"

    async def check_rate_limit(self, request: Request) -> bool:
        """Check if rate limit is exceeded for the client"""
        if self._should_skip_rate_limit(request):
            return False

        client_id = await self._get_client_identifier(request)
        current_count = await self.redis_client.get(client_id) or 0

        if current_count >= self.requests_per_minute:
            return True

        await self.redis_client.set(client_id, current_count + 1, expire=self.window)
        return False

    async def dispatch(self, request: Request, call_next) -> Response:
        """Handle the request and apply rate limiting"""
        try:
            is_rate_limited = await self.check_rate_limit(request)
            if is_rate_limited:
                raise RateLimitException()

            response = await call_next(request)
            return response

        except RateLimitException as e:
            # Re-raise the exception to be handled by FastAPI's exception handlers
            raise
        except Exception as e:
            logger.error(f"Error in rate limiter middleware: {str(e)}")
            # Let FastAPI handle the error
            raise

class EnhancedRateLimiter(BaseHTTPMiddleware):
    """Enhanced rate limiter middleware with Redis backend."""

    def __init__(
        self,
        app: ASGIApp,
        limit: int = settings.RATE_LIMIT_PER_MINUTE,
        window: int = 60,
        redis_prefix: str = "rate_limit:",
        exclude_paths: Optional[list] = None
    ):
        """Initialize rate limiter.
        
        Args:
            app: ASGI application
            limit: Maximum number of requests per window
            window: Time window in seconds
            redis_prefix: Prefix for Redis keys
            exclude_paths: List of paths to exclude from rate limiting
        """
        super().__init__(app)
        self.limit = limit
        self.window = window
        self.redis_prefix = redis_prefix
        self.exclude_paths = exclude_paths or []
        self.redis = get_redis()

    async def dispatch(
        self,
        request: Request,
        call_next: Any
    ) -> Response:
        """Process request through rate limiter.
        
        Args:
            request: FastAPI request
            call_next: Next middleware in chain
            
        Returns:
            Response
        """
        # Skip rate limiting for excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)

        # Get client IP
        client_ip = request.client.host
        
        # Create Redis key
        key = f"{self.redis_prefix}{request.url.path}:{client_ip}"
        
        # Get current count and window start
        pipe = self.redis.pipeline()
        pipe.get(key)
        pipe.ttl(key)
        current, ttl = await pipe.execute()
        
        # If no current record or TTL expired
        if current is None or ttl < 0:
            pipe = self.redis.pipeline()
            pipe.setex(key, self.window, 1)
            pipe.execute()
            
            # Update metrics
            RATE_LIMIT_REMAINING.labels(endpoint=request.url.path).set(self.limit - 1)
            
            return await call_next(request)
            
        # Convert to int
        current = int(current)
        
        # Check if limit exceeded
        if current >= self.limit:
            # Update metrics
            RATE_LIMIT_EXCEEDED.labels(endpoint=request.url.path).inc()
            RATE_LIMIT_REMAINING.labels(endpoint=request.url.path).set(0)
            
            # Log rate limit exceeded
            logger.warning(
                f"Rate limit exceeded for {client_ip} on {request.url.path}",
                extra={
                    "client_ip": client_ip,
                    "path": request.url.path,
                    "limit": self.limit,
                    "window": self.window
                }
            )
            
            # Return rate limit exceeded response
            return Response(
                content="Rate limit exceeded",
                status_code=429,
                headers={
                    "Retry-After": str(ttl),
                    "X-RateLimit-Limit": str(self.limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time()) + ttl)
                }
            )
            
        # Increment counter
        pipe = self.redis.pipeline()
        pipe.incr(key)
        pipe.execute()
        
        # Update metrics
        remaining = self.limit - (current + 1)
        RATE_LIMIT_REMAINING.labels(endpoint=request.url.path).set(remaining)
        
        # Add rate limit headers
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(time.time()) + ttl)
        
        return response 