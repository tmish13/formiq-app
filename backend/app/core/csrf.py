from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
import secrets
import time
from typing import Optional, Dict, Any
from app.core.config import settings

# Constants
CSRF_TOKEN_BYTES = 32
CSRF_HEADER_NAME = "X-CSRF-Token"
CSRF_COOKIE_NAME = "csrf_token"
CSRF_TOKEN_EXPIRY = 3600  # 1 hour in seconds

class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    """Middleware for CSRF protection with HttpOnly cookie-based authentication."""
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Process the request and validate CSRF tokens for unsafe methods."""
        # Only validate POST, PUT, PATCH, DELETE requests
        if request.method not in ["GET", "HEAD", "OPTIONS"]:
            # CSRF validation 
            valid = await validate_csrf_token(request)
            if not valid:
                return Response(
                    content="CSRF token validation failed",
                    status_code=status.HTTP_403_FORBIDDEN,
                )
        
        # Process the request
        response = await call_next(request)
        
        # Generate a new CSRF token for each response
        if not request.url.path.endswith("/csrf-token"):  # Avoid duplicating token if this is the token endpoint
            csrf_token = generate_csrf_token()
            response.set_cookie(
                key=CSRF_COOKIE_NAME,
                value=csrf_token,
                httponly=False,  # Must be accessible from JS
                secure=settings.COOKIE_SECURE,
                samesite="lax",
                max_age=CSRF_TOKEN_EXPIRY
            )
        
        return response

def generate_csrf_token() -> str:
    """Generate a random CSRF token."""
    return secrets.token_hex(CSRF_TOKEN_BYTES)

async def validate_csrf_token(request: Request) -> bool:
    """Validate the CSRF token from the request header against the cookie."""
    # Get the token from header
    header_token = request.headers.get(CSRF_HEADER_NAME)
    if not header_token:
        return False
    
    # Get the token from cookie
    cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
    if not cookie_token:
        return False
    
    # Compare tokens
    return header_token == cookie_token

async def get_csrf_token(request: Request) -> Optional[str]:
    """Get the CSRF token from the request cookie."""
    return request.cookies.get(CSRF_COOKIE_NAME) 