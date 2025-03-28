from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from app.core.logger import logger
from typing import Any

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Any
    ) -> Any:
        response = await call_next(request)
        
        # Security Headers
        headers = {
            # Prevent clickjacking
            "X-Frame-Options": "DENY",
            # Enable XSS protection
            "X-XSS-Protection": "1; mode=block",
            # Prevent MIME type sniffing
            "X-Content-Type-Options": "nosniff",
            # Referrer policy
            "Referrer-Policy": "strict-origin-when-cross-origin",
            # Content Security Policy
            "Content-Security-Policy": (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self' data:; "
                "connect-src 'self' https:; "
                "frame-ancestors 'none';"
            ),
            # HSTS (uncomment in production)
            # "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            # Permissions Policy
            "Permissions-Policy": (
                "accelerometer=(), "
                "camera=(), "
                "geolocation=(), "
                "gyroscope=(), "
                "magnetometer=(), "
                "microphone=(), "
                "payment=(), "
                "usb=()"
            )
        }
        
        # Add headers to response
        for header, value in headers.items():
            response.headers[header] = value
            
        return response

# Create middleware instance
security_headers_middleware = SecurityHeadersMiddleware 