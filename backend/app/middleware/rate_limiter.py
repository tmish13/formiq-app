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
        window_size: int = 60,
        custom_rules: Optional[Dict[str, Dict[str, int]]] = None,
        skip_paths: Optional[list] = None
    ):
        super().__init__(app)
        self.redis_client = redis_client
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size
        self.window_size = window_size  # Default to 1 minute window
        
        # Default custom rules for 1,000 user capacity
        default_rules = {
            # Auth endpoints - limit login attempts
            "/api/v1/auth/login": {"requests": 5, "burst": 10, "window": 60},
            "/api/v1/auth/register": {"requests": 3, "burst": 5, "window": 60},
            "/api/v1/auth/refresh": {"requests": 10, "burst": 20, "window": 60},
            
            # User profile - moderate limits
            "/api/v1/users/me": {"requests": 60, "burst": 100, "window": 60},
            "/api/v1/users/profile": {"requests": 40, "burst": 80, "window": 60},
            
            # Form check uploads - stricter limits due to resource intensity
            "/api/v1/form-checks": {"requests": 10, "burst": 20, "window": 60},
            
            # Form check analysis - very strict limits due to high resource usage
            "/api/v1/form-checks/*/analyze": {"requests": 5, "burst": 10, "window": 120},
            
            # Feedback endpoints - moderate limits
            "/api/v1/form-checks/*/feedback": {"requests": 20, "burst": 40, "window": 60},
            
            # Exercise and workout endpoints - higher limits
            "/api/v1/exercises": {"requests": 100, "burst": 200, "window": 60},
            "/api/v1/workouts": {"requests": 60, "burst": 120, "window": 60},
        }
        
        # Merge provided custom rules with defaults
        self.custom_rules = {**default_rules, **(custom_rules or {})}
        
        self.skip_paths = skip_paths or [
            "/api/v1/health",
            "/api/v1/metrics",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/v1/auth/verify"  # Allow email verification without limits
        ]
        
        logger.info(f"Rate limiter initialized with default limit of {requests_per_minute}/minute")

    async def dispatch(self, request: Request, call_next: Any) -> Any:
        start_time = time.time()
        
        # Skip rate limiting for certain paths
        if self._should_skip_rate_limit(request):
            return await call_next(request)

        # Get client IP and endpoint
        client_ip = self._get_client_ip(request)
        endpoint = request.url.path
        method = request.method
        
        # Find matching rule - allow for wildcard paths
        rule_key, rule = self._find_matching_rule(endpoint)
        
        # Get rate limit parameters from matching rule or use defaults
        requests_limit = rule.get("requests", self.requests_per_minute)
        burst_limit = rule.get("burst", self.burst_size)
        window = rule.get("window", self.window_size)
        
        # Create Redis keys for standard and burst windows
        # Standard is for normal rate limiting, burst is for surge protection
        standard_key = f"rate_limit:{client_ip}:{method}:{rule_key}"
        burst_key = f"rate_limit:burst:{client_ip}:{method}:{rule_key}"
        
        try:
            # Check if client is already blocked (temporary blacklist)
            blacklist_key = f"rate_limit:blacklist:{client_ip}"
            is_blacklisted = await self.redis_client.get(blacklist_key)
            
            if is_blacklisted:
                block_time = await self.redis_client.ttl(blacklist_key)
                logger.warning(f"Blocked request from blacklisted IP: {client_ip}, remaining: {block_time}s")
                return self._rate_limit_response(block_time)
            
            # Use Redis pipeline for atomic operations
            pipeline = self.redis_client.pipeline()
            
            # Increment and get counts for both windows
            pipeline.incr(standard_key)
            pipeline.ttl(standard_key)
            pipeline.incr(burst_key)
            pipeline.ttl(burst_key)
            
            # Execute pipeline
            results = await pipeline.execute()
            standard_count, standard_ttl, burst_count, burst_ttl = results
            
            # Set expiry if keys are new
            if standard_ttl < 0:
                await self.redis_client.expire(standard_key, window)
            
            if burst_ttl < 0:
                # Burst window is typically 5x the standard window
                await self.redis_client.expire(burst_key, window * 5)
            
            # Update metrics
            RATE_LIMIT_REQUESTS.labels(
                client_ip=client_ip,
                endpoint=rule_key
            ).set(standard_count)
            
            # Check if burst limit exceeded (severe overuse)
            if burst_count > burst_limit * 2:
                # Temporarily blacklist client for excessive usage (5 minutes)
                blacklist_time = 300  # 5 minutes
                await self.redis_client.set(blacklist_key, 1, expire=blacklist_time)
                
                RATE_LIMIT_EXCEEDED.labels(path=rule_key).inc()
                
                logger.warning(
                    f"Client blacklisted for excessive requests: {client_ip} - {endpoint} - {burst_count}/{burst_limit}"
                )
                
                return self._rate_limit_response(blacklist_time)
            
            # Check standard rate limit
            if standard_count > requests_limit:
                RATE_LIMIT_EXCEEDED.labels(path=rule_key).inc()
                
                logger.info(
                    f"Rate limit exceeded: {client_ip} - {endpoint} - {standard_count}/{requests_limit}"
                )
                
                # Get remaining time in window
                remaining = standard_ttl if standard_ttl > 0 else window
                return self._rate_limit_response(remaining)
            
            # Process request
            with RATE_LIMIT_LATENCY.labels(path=rule_key).time():
                response = await call_next(request)
                
                # Add rate limit headers
                response.headers["X-RateLimit-Limit"] = str(requests_limit)
                response.headers["X-RateLimit-Remaining"] = str(max(0, requests_limit - standard_count))
                response.headers["X-RateLimit-Reset"] = str(int(time.time()) + standard_ttl if standard_ttl > 0 else window)
                
                # Add performance tracking header in development
                if request.app.state.settings.ENVIRONMENT in ["development", "staging"]:
                    processing_time = time.time() - start_time
                    response.headers["X-Processing-Time"] = f"{processing_time:.4f}"
                
                return response
                
        except Exception as e:
            logger.error(f"Rate limiter error: {str(e)}", exc_info=True)
            # On unexpected errors, allow the request to proceed
            return await call_next(request)

    def _get_client_ip(self, request: Request) -> str:
        """Extract the client IP with proper proxy handling."""
        # Try X-Forwarded-For first (for clients behind proxies)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Get the first IP in the chain (client's real IP)
            return forwarded_for.split(",")[0].strip()
        
        # Fallback to direct client IP
        return request.client.host if request.client else "unknown"

    def _find_matching_rule(self, endpoint: str) -> tuple:
        """Find the most specific rule matching the endpoint."""
        # First try direct match
        if endpoint in self.custom_rules:
            return endpoint, self.custom_rules[endpoint]
        
        # Then try wildcard matches
        for rule_path, rule in self.custom_rules.items():
            if "*" in rule_path:
                # Convert rule path to regex pattern
                pattern = rule_path.replace("*", ".*")
                if endpoint.startswith(pattern.split("*")[0]):
                    return rule_path, rule
        
        # Default rule
        return "default", {
            "requests": self.requests_per_minute, 
            "burst": self.burst_size,
            "window": self.window_size
        }

    def _should_skip_rate_limit(self, request: Request) -> bool:
        """Check if rate limiting should be skipped for this request."""
        # Skip based on path
        if any(request.url.path.startswith(path) for path in self.skip_paths):
            return True
        
        # Skip for internal maintenance calls with secret header
        secret_header = request.headers.get("X-Internal-Key")
        if secret_header and secret_header == request.app.state.settings.SECRET_KEY[:32]:
            return True
            
        return False
        
    def _rate_limit_response(self, retry_after: int) -> Response:
        """Create a standardized rate limit exceeded response."""
        return JSONResponse(
            status_code=429,
            content={
                "detail": "Rate limit exceeded. Please try again later.",
                "type": "rate_limit_exceeded"
            },
            headers={
                "Retry-After": str(retry_after),
                "X-RateLimit-Reset": str(int(time.time()) + retry_after)
            }
        ) 