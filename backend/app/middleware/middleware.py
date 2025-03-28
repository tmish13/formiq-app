from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import time
from typing import Optional, Dict, Any
import json
from app.core.logging import get_logger
from app.core.monitoring import track_request, record_error_metrics
from app.core.cache import cache_service
from app.core.config import settings
import re

logger = get_logger(__name__)

class FormIQMiddleware(BaseHTTPMiddleware):
    """Consolidated middleware for FormIQ application."""
    
    def __init__(self, app):
        super().__init__(app)
        self.rate_limit_requests = settings.RATE_LIMIT_REQUESTS
        self.rate_limit_burst = settings.RATE_LIMIT_BURST
        self.rate_limit_window = 60  # 1 minute
        self.rate_limit_burst_window = 300  # 5 minutes
        
        # Security headers
        self.security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "camera=(), microphone=(), geolocation=()"
        }
        
        # Request validation patterns
        self.validation_patterns = {
            "email": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
            "password": r"^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{8,}$",
            "username": r"^[a-zA-Z0-9_-]{3,20}$"
        }
    
    async def dispatch(self, request: Request, call_next):
        # Start timing
        start_time = time.time()
        
        try:
            # 1. Request Logging
            await self._log_request(request)
            
            # 2. Rate Limiting
            if not await self._check_rate_limit(request):
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many requests"}
                )
            
            # 3. Request Validation
            if not await self._validate_request(request):
                return JSONResponse(
                    status_code=400,
                    content={"detail": "Invalid request data"}
                )
            
            # 4. Process Request
            response = await call_next(request)
            
            # 5. Add Security Headers
            response = await self._add_security_headers(response)
            
            # 6. Track Metrics
            duration = time.time() - start_time
            track_request(
                method=request.method,
                endpoint=request.url.path,
                status=response.status_code,
                duration=duration
            )
            
            # 7. Log Response
            await self._log_response(request, response, duration)
            
            return response
            
        except Exception as e:
            # Log error and track metrics
            duration = time.time() - start_time
            await self._handle_error(request, e, duration)
            raise
    
    async def _log_request(self, request: Request):
        """Log incoming request details."""
        logger.info(
            "incoming_request",
            method=request.method,
            path=request.url.path,
            client_host=request.client.host,
            query_params=dict(request.query_params),
            headers=dict(request.headers)
        )
    
    async def _check_rate_limit(self, request: Request) -> bool:
        """Check if request is within rate limits."""
        client_ip = request.client.host
        endpoint = request.url.path
        
        # Standard rate limit
        key = f"rate_limit:{client_ip}:{endpoint}"
        current = await cache_service.get(key)
        
        if current and int(current) >= self.rate_limit_requests:
            logger.warning(
                "rate_limit_exceeded",
                client_ip=client_ip,
                endpoint=endpoint,
                current=current
            )
            return False
        
        # Burst rate limit
        burst_key = f"rate_limit:burst:{client_ip}:{endpoint}"
        burst_current = await cache_service.get(burst_key)
        
        if burst_current and int(burst_current) >= self.rate_limit_burst:
            logger.warning(
                "burst_rate_limit_exceeded",
                client_ip=client_ip,
                endpoint=endpoint,
                current=burst_current
            )
            return False
        
        # Update counters
        await cache_service.incr(key, expire=self.rate_limit_window)
        await cache_service.incr(burst_key, expire=self.rate_limit_burst_window)
        
        return True
    
    async def _validate_request(self, request: Request) -> bool:
        """Validate request data against patterns."""
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.json()
                return self._validate_data(body)
            except json.JSONDecodeError:
                return False
        return True
    
    def _validate_data(self, data: Dict[str, Any]) -> bool:
        """Validate data against patterns."""
        for field, pattern in self.validation_patterns.items():
            if field in data and not re.match(pattern, str(data[field])):
                logger.warning(
                    "validation_failed",
                    field=field,
                    value=data[field]
                )
                return False
        return True
    
    async def _add_security_headers(self, response: Response) -> Response:
        """Add security headers to response."""
        for header, value in self.security_headers.items():
            response.headers[header] = value
        return response
    
    async def _log_response(self, request: Request, response: Response, duration: float):
        """Log response details."""
        logger.info(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration=duration
        )
    
    async def _handle_error(self, request: Request, error: Exception, duration: float):
        """Handle and log errors."""
        error_type = type(error).__name__
        logger.error(
            "request_error",
            method=request.method,
            path=request.url.path,
            error=str(error),
            error_type=error_type,
            duration=duration
        )
        record_error_metrics(
            method=request.method,
            endpoint=request.url.path,
            error_type=error_type
        ) 