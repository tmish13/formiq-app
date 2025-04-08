"""Timing middleware for measuring request processing time."""
import time
from typing import Callable, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

class TimingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for measuring and logging request processing time.
    
    This middleware adds an X-Response-Time header to all responses
    and optionally logs slow requests for performance monitoring.
    """
    
    def __init__(
        self,
        app,
        *,
        slow_request_threshold: int = 1000,  # ms
        log_all_timings: bool = False,
        exclude_paths: Optional[list] = None,
    ):
        """
        Initialize the timing middleware.
        
        Args:
            app: The FastAPI application
            slow_request_threshold: Threshold in ms to log slow requests
            log_all_timings: Whether to log timing for all requests
            exclude_paths: List of paths to exclude from timing
        """
        super().__init__(app)
        self.slow_request_threshold = slow_request_threshold
        self.log_all_timings = log_all_timings
        self.exclude_paths = exclude_paths or []
        
        logger.info(
            f"Timing middleware initialized with slow threshold {slow_request_threshold}ms"
        )
    
    def _should_time(self, request: Request) -> bool:
        """
        Determine if timing should be applied to this request.
        
        Args:
            request: The incoming request
            
        Returns:
            Boolean indicating if timing should be applied
        """
        path = request.url.path
        
        # Skip timing for excluded paths
        for excluded in self.exclude_paths:
            if path.startswith(excluded):
                return False
        
        return True
    
    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        """
        Process a request and measure its timing.
        
        Args:
            request: The incoming request
            call_next: The next middleware or route handler
            
        Returns:
            Response from the next handler with timing headers
        """
        # Skip timing if not applicable
        if not self._should_time(request):
            return await call_next(request)
        
        start_time = time.time()
        
        # Process the request
        response = await call_next(request)
        
        # Calculate processing time
        process_time = time.time() - start_time
        process_time_ms = round(process_time * 1000, 2)
        
        # Add timing header
        response.headers["X-Response-Time"] = f"{process_time_ms}ms"
        
        # Log slow requests
        if process_time_ms > self.slow_request_threshold:
            logger.warning(
                f"Slow request detected: {request.method} {request.url.path} "
                f"took {process_time_ms}ms",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "process_time_ms": process_time_ms,
                    "client_ip": request.client.host if request.client else "unknown",
                }
            )
        elif self.log_all_timings and settings.DEBUG:
            logger.debug(
                f"Request timing: {request.method} {request.url.path} "
                f"took {process_time_ms}ms"
            )
        
        return response 