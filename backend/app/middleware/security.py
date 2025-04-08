"""Security headers middleware for API responses."""
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable, Dict, Optional

from app.core.config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to HTTP responses.
    
    This middleware adds various security headers to API responses 
    to protect against common web vulnerabilities:
    
    - Strict-Transport-Security (HSTS): Forces HTTPS usage
    - X-Frame-Options: Prevents clickjacking attacks
    - X-XSS-Protection: Helps prevent XSS attacks
    - X-Content-Type-Options: Prevents MIME type confusion attacks
    - Content-Security-Policy: Restricts resource loading
    - Referrer-Policy: Controls referrer information
    - Feature-Policy: Restricts browser features
    """
    
    def __init__(self, app, hsts_seconds: Optional[int] = None):
        """Initialize the middleware.
        
        Args:
            app: The FastAPI application
            hsts_seconds: Optional HSTS max-age value
        """
        super().__init__(app)
        self.hsts_seconds = hsts_seconds or settings.SECURITY_HSTS_SECONDS
        self.is_production = settings.ENVIRONMENT.lower() == "production"
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process the request and add security headers to the response.
        
        Args:
            request: The incoming request
            call_next: The next middleware or route handler
            
        Returns:
            Response: The response with added security headers
        """
        # Process the request normally
        response = await call_next(request)
        
        # Add security headers
        if self.is_production:
            # Only add HSTS in production and only on HTTPS connections
            is_https = (
                request.headers.get("X-Forwarded-Proto") == "https" or
                request.url.scheme == "https"
            )
            if is_https:
                response.headers["Strict-Transport-Security"] = self._get_hsts_value()
            
            # Add other security headers
            response.headers.update(self._get_security_headers())
        
        return response
    
    def _get_hsts_value(self) -> str:
        """Generate the HSTS header value.
        
        Returns:
            str: The Strict-Transport-Security header value
        """
        value = f"max-age={self.hsts_seconds}"
        
        if settings.SECURITY_HSTS_INCLUDE_SUBDOMAINS:
            value += "; includeSubDomains"
        
        return value
    
    def _get_security_headers(self) -> Dict[str, str]:
        """Generate security headers based on settings.
        
        Returns:
            Dict[str, str]: Dictionary of security headers
        """
        headers = {}
        
        # Prevent clickjacking
        if settings.SECURITY_FRAME_DENY:
            headers["X-Frame-Options"] = "DENY"
        
        # Prevent XSS
        if settings.SECURITY_XSS_PROTECTION:
            headers["X-XSS-Protection"] = "1; mode=block"
        
        # Prevent MIME type confusion
        if settings.SECURITY_CONTENT_TYPE_NOSNIFF:
            headers["X-Content-Type-Options"] = "nosniff"
        
        # Content Security Policy
        if hasattr(settings, "SECURITY_CONTENT_SECURITY_POLICY"):
            headers["Content-Security-Policy"] = settings.SECURITY_CONTENT_SECURITY_POLICY
        
        # Referrer Policy
        headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Feature Policy to restrict browser features
        headers["Feature-Policy"] = (
            "camera 'none'; microphone 'none'; geolocation 'none'; "
            "accelerometer 'none'; autoplay 'none'; payment 'none'"
        )
        
        return headers 