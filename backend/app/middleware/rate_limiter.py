from typing import Optional, Any
from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from redis import Redis, RedisError
from app.core.logger import logger
import time
from app.core.exceptions import RateLimitException
from prometheus_client import Counter, Histogram

# Prometheus metrics
RATE_LIMIT_EXCEEDED = Counter(
    'rate_limit_exceeded_total',
    'Number of requests that exceeded rate limit',
    ['client_ip']
)

RATE_LIMIT_LATENCY = Histogram(
    'rate_limit_latency_seconds',
    'Time spent processing rate limit checks',
    ['client_ip']
)

class RateLimiter(BaseHTTPMiddleware):
    def __init__(
        self,
        app: ASGIApp,
        redis_client: Redis,
        requests_per_minute: int = 100,
        burst_size: int = 200
    ):
        super().__init__(app)
        self.redis_client = redis_client
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size
        self.window_size = 60  # 1 minute window

    async def dispatch(
        self, request: Request, call_next: Any
    ) -> Any:
        # Skip rate limiting for certain paths
        if request.url.path in ["/api/v1/health", "/api/v1/metrics"]:
            return await call_next(request)

        client_ip = request.client.host
        key = f"rate_limit:{client_ip}"
        
        with RATE_LIMIT_LATENCY.labels(client_ip=client_ip).time():
            try:
                # Use Redis pipeline for atomic operations
                pipe = self.redis_client.pipeline()
                pipe.get(key)
                pipe.incr(key)
                pipe.expire(key, self.window_size)
                current, new_count, _ = pipe.execute()
                
                current_count = int(new_count or 0)
                
                # Log rate limit status
                logger.info(
                    "rate_limit_check",
                    client_ip=client_ip,
                    current_count=current_count,
                    limit=self.requests_per_minute,
                    burst=self.burst_size
                )
                
                if current_count > self.burst_size:
                    RATE_LIMIT_EXCEEDED.labels(client_ip=client_ip).inc()
                    logger.warning(
                        "rate_limit_exceeded",
                        client_ip=client_ip,
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
                    error=str(e)
                )
                # On unexpected errors, allow the request to proceed
                return await call_next(request) 