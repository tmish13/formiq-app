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

# Prometheus metrics
RATE_LIMIT_EXCEEDED = Counter(
    "rate_limit_exceeded_total",
    "Total number of rate limit exceeded events",
    ["path"]
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
    def __init__(
        self,
        app: ASGIApp,
        redis_client: Redis,
        requests_per_minute: int = 100,
        burst_size: int = 200,
        custom_rules: Optional[Dict[str, Dict[str, int]]] = None,
        skip_paths: Optional[list] = None
    ):
        super().__init__(app)
        self.redis_client = redis_client
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size
        self.window_size = 60  # 1 minute window
        self.custom_rules = custom_rules or {}
        self.skip_paths = skip_paths or [
            "/api/v1/health",
            "/api/v1/metrics",
            "/docs",
            "/redoc",
            "/openapi.json"
        ]

    async def dispatch(self, request: Request, call_next: Any) -> Any:
        # Skip rate limiting for certain paths
        if self._should_skip_rate_limit(request):
            return await call_next(request)

        # Get client IP and endpoint
        client_ip = request.client.host if request.client else "unknown"
        endpoint = request.url.path

        # Get rate limit rules for this endpoint
        rules = self.custom_rules.get(endpoint, {})
        requests_limit = rules.get("requests", self.requests_per_minute)
        burst_limit = rules.get("burst", self.burst_size)

        # Get current count
        key = f"rate_limit:{client_ip}:{endpoint}"
        
        try:
            # Use Redis pipeline for atomic operations
            count = await self.redis_client.incr(key)
            if count == 1:
                await self.redis_client.expire(key, self.window_size)
            
            # Update metrics
            RATE_LIMIT_REQUESTS.labels(
                client_ip=client_ip,
                endpoint=endpoint
            ).set(count)
            
            # Check limit
            if count > burst_limit:
                RATE_LIMIT_EXCEEDED.labels(
                    client_ip=client_ip,
                    endpoint=endpoint
                ).inc()
                
                logger.warning(
                    "rate_limit_exceeded",
                    extra={
                        "client_ip": client_ip,
                        "endpoint": endpoint,
                        "count": count,
                        "limit": burst_limit
                    }
                )
                
                raise RateLimitException(
                    detail={
                        "error": "Too many requests",
                        "retry_after": self.window_size,
                        "limit": burst_limit
                    }
                )
            
            # Process request
            with RATE_LIMIT_LATENCY.labels(
                client_ip=client_ip,
                endpoint=endpoint
            ).time():
                response = await call_next(request)
                
                # Add rate limit headers
                response.headers["X-RateLimit-Limit"] = str(requests_limit)
                response.headers["X-RateLimit-Remaining"] = str(max(0, burst_limit - count))
                response.headers["X-RateLimit-Reset"] = str(int(time.time()) + self.window_size)
                
                return response
                
        except RateLimitException:
            raise
        except Exception as e:
            logger.error(
                "rate_limit_error",
                extra={
                    "client_ip": client_ip,
                    "endpoint": endpoint,
                    "error": str(e)
                }
            )
            # On unexpected errors, allow the request to proceed
            return await call_next(request)

    def _should_skip_rate_limit(self, request: Request) -> bool:
        """Check if rate limiting should be skipped for this request."""
        return any(request.url.path.startswith(path) for path in self.skip_paths) 