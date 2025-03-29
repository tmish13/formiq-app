from typing import Optional, Any, Dict
from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from redis import Redis, RedisError
from app.core.logging import logger
import time
from app.core.exceptions import RateLimitException
from prometheus_client import Counter, Histogram, Gauge

# Prometheus metrics
RATE_LIMIT_EXCEEDED = Counter(
    'rate_limit_exceeded_total',
    'Number of requests that exceeded rate limit',
    ['client_ip', 'endpoint']
)

RATE_LIMIT_LATENCY = Histogram(
    'rate_limit_latency_seconds',
    'Time spent processing rate limit checks',
    ['client_ip', 'endpoint']
)

RATE_LIMIT_REQUESTS = Gauge(
    'rate_limit_requests_current',
    'Current number of requests in the window',
    ['client_ip', 'endpoint']
)

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

        # Get rate limit rules for the endpoint
        rules = self._get_rate_limit_rules(request)
        
        # Apply custom rules if they exist
        if rules:
            return await self._apply_custom_rules(request, rules, call_next)
        
        return await self._apply_default_rules(request, call_next)

    def _should_skip_rate_limit(self, request: Request) -> bool:
        """Check if rate limiting should be skipped for this request."""
        return any(request.url.path.startswith(path) for path in self.skip_paths)

    def _get_rate_limit_rules(self, request: Request) -> Optional[Dict[str, int]]:
        """Get rate limit rules for the endpoint."""
        path = request.url.path
        return self.custom_rules.get(path)

    async def _apply_custom_rules(
        self,
        request: Request,
        rules: Dict[str, int],
        call_next: Any
    ) -> Any:
        """Apply custom rate limit rules for the endpoint."""
        client_ip = request.client.host
        endpoint = request.url.path
        key = f"rate_limit:{client_ip}:{endpoint}"
        
        limit = rules.get('limit', self.requests_per_minute)
        burst = rules.get('burst', self.burst_size)
        window = rules.get('window', self.window_size)
        
        with RATE_LIMIT_LATENCY.labels(
            client_ip=client_ip,
            endpoint=endpoint
        ).time():
            try:
                # Use Redis pipeline for atomic operations
                pipe = self.redis_client.pipeline()
                pipe.get(key)
                pipe.incr(key)
                pipe.expire(key, window)
                current, new_count, _ = pipe.execute()
                
                current_count = int(new_count or 0)
                RATE_LIMIT_REQUESTS.labels(
                    client_ip=client_ip,
                    endpoint=endpoint
                ).set(current_count)
                
                if current_count > burst:
                    RATE_LIMIT_EXCEEDED.labels(
                        client_ip=client_ip,
                        endpoint=endpoint
                    ).inc()
                    
                    logger.warning(
                        "rate_limit_exceeded",
                        client_ip=client_ip,
                        endpoint=endpoint,
                        count=current_count,
                        limit=burst
                    )
                    
                    raise HTTPException(
                        status_code=429,
                        detail={
                            "error": "Too many requests",
                            "retry_after": window,
                            "limit": limit,
                            "burst": burst
                        }
                    )
                
                return await call_next(request)
                
            except RedisError as e:
                logger.error(
                    "rate_limit_redis_error",
                    client_ip=client_ip,
                    endpoint=endpoint,
                    error=str(e)
                )
                # On Redis errors, allow the request to proceed
                return await call_next(request)
            except HTTPException:
                raise
            except Exception as e:
                logger.error(
                    "rate_limit_unexpected_error",
                    client_ip=client_ip,
                    endpoint=endpoint,
                    error=str(e)
                )
                # On unexpected errors, allow the request to proceed
                return await call_next(request)

    async def _apply_default_rules(self, request: Request, call_next: Any) -> Any:
        """Apply default rate limit rules."""
        client_ip = request.client.host
        endpoint = request.url.path
        key = f"rate_limit:{client_ip}:{endpoint}"
        
        with RATE_LIMIT_LATENCY.labels(
            client_ip=client_ip,
            endpoint=endpoint
        ).time():
            try:
                # Use Redis pipeline for atomic operations
                pipe = self.redis_client.pipeline()
                pipe.get(key)
                pipe.incr(key)
                pipe.expire(key, self.window_size)
                current, new_count, _ = pipe.execute()
                
                current_count = int(new_count or 0)
                RATE_LIMIT_REQUESTS.labels(
                    client_ip=client_ip,
                    endpoint=endpoint
                ).set(current_count)
                
                if current_count > self.burst_size:
                    RATE_LIMIT_EXCEEDED.labels(
                        client_ip=client_ip,
                        endpoint=endpoint
                    ).inc()
                    
                    logger.warning(
                        "rate_limit_exceeded",
                        client_ip=client_ip,
                        endpoint=endpoint,
                        count=current_count,
                        limit=self.burst_size
                    )
                    
                    raise HTTPException(
                        status_code=429,
                        detail={
                            "error": "Too many requests",
                            "retry_after": self.window_size,
                            "limit": self.requests_per_minute,
                            "burst": self.burst_size
                        }
                    )
                
                return await call_next(request)
                
            except RedisError as e:
                logger.error(
                    "rate_limit_redis_error",
                    client_ip=client_ip,
                    endpoint=endpoint,
                    error=str(e)
                )
                # On Redis errors, allow the request to proceed
                return await call_next(request)
            except HTTPException:
                raise
            except Exception as e:
                logger.error(
                    "rate_limit_unexpected_error",
                    client_ip=client_ip,
                    endpoint=endpoint,
                    error=str(e)
                )
                # On unexpected errors, allow the request to proceed
                return await call_next(request) 