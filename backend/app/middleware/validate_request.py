from typing import Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.exceptions import ValidationException
from app.core.logger import logger
from app.core.config import settings

class ValidateRequestMiddleware(BaseHTTPMiddleware):
    """Middleware to validate request body size and content type."""
    
    def __init__(self, app):
        super().__init__(app)
        self.max_content_length = settings.MAX_CONTENT_LENGTH
        self.allowed_content_types = {
            "application/json",
            "application/x-www-form-urlencoded",
            "multipart/form-data",
        }
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Process the request and validate it."""
        # Skip validation for certain paths
        if self._should_skip_validation(request):
            return await call_next(request)
        
        # Validate content length
        if not self._validate_content_length(request):
            logger.warning(
                "request_too_large",
                content_length=request.headers.get("content-length"),
                max_length=self.max_content_length
            )
            raise ValidationException(
                "Request body too large",
                details={
                    "max_size": self.max_content_length,
                    "current_size": request.headers.get("content-length")
                }
            )
        
        # Validate content type
        if not self._validate_content_type(request):
            logger.warning(
                "invalid_content_type",
                content_type=request.headers.get("content-type")
            )
            raise ValidationException(
                "Invalid content type",
                details={
                    "allowed_types": list(self.allowed_content_types),
                    "received_type": request.headers.get("content-type")
                }
            )
        
        # Validate request body if it's JSON
        if self._is_json_request(request):
            try:
                body = await request.json()
                if not self._validate_json_body(body):
                    raise ValidationException(
                        "Invalid JSON body",
                        details={"error": "Invalid JSON structure"}
                    )
            except Exception as e:
                logger.warning(
                    "invalid_json_body",
                    error=str(e)
                )
                raise ValidationException(
                    "Invalid JSON body",
                    details={"error": str(e)}
                )
        
        return await call_next(request)
    
    def _should_skip_validation(self, request: Request) -> bool:
        """Check if validation should be skipped for this request."""
        skip_paths = [
            "/api/v1/health",
            "/api/v1/metrics",
            "/docs",
            "/redoc",
            "/openapi.json"
        ]
        return any(request.url.path.startswith(path) for path in skip_paths)
    
    def _validate_content_length(self, request: Request) -> bool:
        """Validate the content length of the request."""
        content_length = request.headers.get("content-length")
        if not content_length:
            return True  # No content length header, skip validation
        
        try:
            length = int(content_length)
            return length <= self.max_content_length
        except ValueError:
            return False
    
    def _validate_content_type(self, request: Request) -> bool:
        """Validate the content type of the request."""
        content_type = request.headers.get("content-type", "")
        
        # For multipart/form-data, check if it has a boundary
        if content_type.startswith("multipart/form-data"):
            return "boundary=" in content_type
        
        # For other content types, check if they're in the allowed list
        return any(
            content_type.startswith(allowed_type)
            for allowed_type in self.allowed_content_types
        )
    
    def _is_json_request(self, request: Request) -> bool:
        """Check if the request is a JSON request."""
        content_type = request.headers.get("content-type", "")
        return content_type.startswith("application/json")
    
    def _validate_json_body(self, body: dict) -> bool:
        """Validate the structure of the JSON body."""
        # Add custom validation rules here
        # For example, check for required fields, data types, etc.
        return True 