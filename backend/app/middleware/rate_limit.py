from fastapi import Request, Response
from fastapi.responses import JSONResponse
from app.core.cache import cache_service
from app.core.config import settings
from app.core.exceptions import RateLimitError
from app.core.logging import get_logger
import time

logger = get_logger(__name__)

class RateLimitMiddleware:
    """Middleware for rate limiting requests."""
    
    def __init__(self, requests_per_minute: int = 60, burst_size: int = 100):
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size
        self.window_size = 60  # 1 minute window

    async def __call__(self, request: Request, call_next):
        """Process the request and apply rate limiting."""
        # Skip rate limiting for certain paths
        if request.url.path in settings.RATE_LIMIT_EXEMPT_PATHS:
            return await call_next(request)

        client_ip = request.client.host
        key = f"rate_limit:{client_ip}"
        
        try:
            # Get current request count
            current_count = await cache_service.get(key)
            current_count = int(current_count) if current_count else 0

            # Check if rate limit exceeded
            if current_count >= self.burst_size:
                logger.warning(
                    f"Rate limit exceeded for IP: {client_ip}",
                    extra={"path": request.url.path}
                )
                raise RateLimitError(
                    message="Rate limit exceeded",
                    code="RATE_LIMIT_EXCEEDED",
                    status_code=429
                )

            # Increment request count
            if current_count == 0:
                # First request in window, set expiry
                await cache_service.set(
                    key,
                    "1",
                    expire=self.window_size
                )
            else:
                # Increment existing count
                await cache_service.incr(key)

            # Process request
            response = await call_next(request)
            
            # Add rate limit headers
            response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
            response.headers["X-RateLimit-Remaining"] = str(
                self.burst_size - (current_count + 1)
            )
            response.headers["X-RateLimit-Reset"] = str(
                int(time.time()) + self.window_size
            )
            
            return response

        except Exception as e:
            logger.error(
                f"Rate limiting error: {str(e)}",
                extra={"path": request.url.path, "client_ip": client_ip}
            )
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Rate limiting error",
                    "code": "RATE_LIMIT_ERROR",
                    "details": str(e)
                }
            ) 