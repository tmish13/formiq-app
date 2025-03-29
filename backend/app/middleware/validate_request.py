from typing import Optional, Dict, Any, List
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.exceptions import ValidationException
from app.core.logging import logger
from app.core.config import settings
from prometheus_client import Counter, Histogram
import json

# Prometheus metrics
VALIDATION_ERRORS = Counter(
    'request_validation_errors_total',
    'Total number of request validation errors',
    ['error_type', 'endpoint']
)

VALIDATION_LATENCY = Histogram(
    'request_validation_latency_seconds',
    'Time spent validating requests',
    ['endpoint']
)

class EnhancedValidateRequestMiddleware(BaseHTTPMiddleware):
    """Enhanced middleware to validate request body size and content type."""
    
    def __init__(self, app):
        super().__init__(app)
        self.max_content_length = settings.MAX_CONTENT_LENGTH
        self.allowed_content_types = {
            "application/json",
            "application/x-www-form-urlencoded",
            "multipart/form-data",
        }
        self.custom_validators = self._load_custom_validators()
        self.skip_paths = [
            "/api/v1/health",
            "/api/v1/metrics",
            "/docs",
            "/redoc",
            "/openapi.json"
        ]
    
    def _load_custom_validators(self) -> Dict[str, Dict[str, Any]]:
        """Load custom validators from configuration."""
        return getattr(settings, 'CUSTOM_VALIDATORS', {})
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Process the request and validate it."""
        endpoint = request.url.path
        
        # Skip validation for certain paths
        if self._should_skip_validation(request):
            return await call_next(request)
        
        with VALIDATION_LATENCY.labels(endpoint=endpoint).time():
            try:
                # Validate content length
                if not self._validate_content_length(request):
                    self._log_validation_error('content_length', endpoint)
                    raise ValidationException(
                        "Request body too large",
                        details={
                            "max_size": self.max_content_length,
                            "current_size": request.headers.get("content-length")
                        }
                    )
                
                # Validate content type
                if not self._validate_content_type(request):
                    self._log_validation_error('content_type', endpoint)
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
                            self._log_validation_error('json_body', endpoint)
                            raise ValidationException(
                                "Invalid JSON body",
                                details={"error": "Invalid JSON structure"}
                            )
                    except json.JSONDecodeError as e:
                        self._log_validation_error('json_decode', endpoint)
                        raise ValidationException(
                            "Invalid JSON body",
                            details={"error": str(e)}
                        )
                
                # Apply custom validation rules
                if self._should_apply_custom_validation(request):
                    await self._apply_custom_validation(request)
                
                return await call_next(request)
                
            except ValidationException:
                raise
            except Exception as e:
                self._log_validation_error('unexpected', endpoint)
                raise ValidationException(
                    "Validation error",
                    details={"error": str(e)}
                )
    
    def _should_skip_validation(self, request: Request) -> bool:
        """Check if validation should be skipped for this request."""
        return any(request.url.path.startswith(path) for path in self.skip_paths)
    
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
    
    def _should_apply_custom_validation(self, request: Request) -> bool:
        """Check if custom validation should be applied."""
        path = request.url.path
        return path in self.custom_validators
    
    async def _apply_custom_validation(self, request: Request):
        """Apply custom validation rules."""
        path = request.url.path
        validators = self.custom_validators[path]
        
        for validator in validators:
            try:
                await validator(request)
            except Exception as e:
                self._log_validation_error('custom_validation', path)
                raise ValidationException(
                    "Custom validation failed",
                    details={"error": str(e)}
                )
    
    def _log_validation_error(self, error_type: str, endpoint: str):
        """Log validation error and update metrics."""
        VALIDATION_ERRORS.labels(
            error_type=error_type,
            endpoint=endpoint
        ).inc()
        
        logger.warning(
            "validation_error",
            error_type=error_type,
            endpoint=endpoint
        ) 