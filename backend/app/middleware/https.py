"""HTTPS enforcement middleware for production environments."""
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.datastructures import URL
from starlette.status import HTTP_301_MOVED_PERMANENTLY
from typing import Callable, Optional

from app.core.config import settings


class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    """
    Middleware to redirect HTTP requests to HTTPS.
    
    This middleware checks for the following in order:
    1. X-Forwarded-Proto header (common with reverse proxies)
    2. Forwarded header (standardized version)
    3. The URL scheme
    
    If the request is determined to be HTTP and the environment is production,
    a redirect to HTTPS is issued.
    """
    
    def __init__(self, app, https_domain: Optional[str] = None):
        """Initialize the middleware.
        
        Args:
            app: The FastAPI application
            https_domain: Optional domain to use for redirects
        """
        super().__init__(app)
        self.https_domain = https_domain
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process the request and redirect if needed.
        
        Args:
            request: The incoming request
            call_next: The next middleware or route handler
            
        Returns:
            Response: Either a redirect response or the original response
        """
        # Only enforce HTTPS in production
        if settings.ENVIRONMENT.lower() != "production":
            return await call_next(request)
        
        # Skip HTTPS enforcement for health check endpoints
        if request.url.path in ["/health", "/api/v1/health"]:
            return await call_next(request)
        
        # Check X-Forwarded-Proto header first (common with AWS ALB, Nginx, etc.)
        forwarded_proto = request.headers.get("X-Forwarded-Proto")
        if forwarded_proto and forwarded_proto.lower() == "http":
            return self._redirect_to_https(request)
        
        # Check Forwarded header (standardized)
        forwarded = request.headers.get("Forwarded")
        if forwarded and "proto=http" in forwarded.lower():
            return self._redirect_to_https(request)
        
        # Check URL scheme directly (less common in production with proxies)
        if request.url.scheme == "http":
            return self._redirect_to_https(request)
        
        return await call_next(request)
    
    def _redirect_to_https(self, request: Request) -> Response:
        """Create a redirect response to HTTPS.
        
        Args:
            request: The incoming HTTP request
            
        Returns:
            Response: A 301 redirect to the HTTPS version of the URL
        """
        # Create the HTTPS URL
        url = URL(
            scheme="https",
            host=self.https_domain or request.url.hostname or settings.APP_DOMAIN,
            port=443 if not self.https_domain else None,
            path=request.url.path,
            query=request.url.query,
        )
        
        # Return a 301 permanent redirect
        return Response(
            status_code=HTTP_301_MOVED_PERMANENTLY,
            headers={"Location": str(url)},
            content="Redirecting to HTTPS"
        ) 