"""Core request validation middleware."""
from typing import Optional, Dict, Any, List, Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.exceptions import ValidationException
from app.core.logging import get_logger
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

logger = get_logger(__name__)

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
            "/api/v1/health", # Assuming health check path
            # "/api/v1/metrics", # If you have a metrics endpoint
            "/docs",
            "/redoc",
            "/openapi.json"
        ]
    
    def _load_custom_validators(self) -> Dict[str, List[Callable]]: # Type hint for callable list
        """Load custom validators from configuration."""
        # This needs a more robust way to load callables if defined by string in settings
        return getattr(settings, 'CUSTOM_VALIDATORS', {}) 
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Process the request and validate it."""
        endpoint = request.url.path
        
        if self._should_skip_validation(request):
            return await call_next(request)
        
        with VALIDATION_LATENCY.labels(endpoint=endpoint).time():
            try:
                if not self._validate_content_length(request):
                    self._log_validation_error('content_length', endpoint)
                    raise ValidationException(
                        "Request body too large",
                        details={
                            "max_size": f"{self.max_content_length} bytes",
                            "current_size": request.headers.get("content-length", "N/A")
                        }
                    )
                
                if not self._validate_content_type(request):
                    self._log_validation_error('content_type', endpoint)
                    raise ValidationException(
                        "Invalid content type",
                        details={
                            "allowed_types": list(self.allowed_content_types),
                            "received_type": request.headers.get("content-type", "N/A")
                        }
                    )
                
                if self._is_json_request(request):
                    try:
                        # Read body once and store for potential re-use by endpoint
                        # This is important because request.json() consumes the stream.
                        # FastAPI typically handles this for Pydantic models, but 
                        # if we validate here, we need to be careful.
                        # A common pattern is to replace request.json() with a memoized version
                        # or store the body on request.state if needed by endpoint AND Pydantic.
                        # For now, assume if Pydantic is used, it will re-read or this middleware
                        # is primarily for non-Pydantic or pre-Pydantic checks.
                        body = await request.json()
                        request.state.json_body = body # Store for potential re-use
                        if not self._validate_json_body(body, endpoint): # Pass endpoint for context
                            self._log_validation_error('json_body', endpoint)
                            raise ValidationException(
                                "Invalid JSON body structure or content",
                                details={"error": "Custom JSON validation failed"}
                            )
                    except json.JSONDecodeError as e:
                        self._log_validation_error('json_decode', endpoint)
                        raise ValidationException(
                            "Invalid JSON body: Not valid JSON",
                            details={"error": str(e)}
                        )
                
                if self._should_apply_custom_validation(request):
                    await self._apply_custom_validation(request)
                
                return await call_next(request)
                
            except ValidationException: # Re-raise our specific exception
                raise
            except Exception as e: # Catch other unexpected errors during validation
                self._log_validation_error('unexpected_validation_phase', endpoint)
                logger.error(f"Unexpected error during request validation: {str(e)}", exc_info=True)
                raise ValidationException(
                    "Unexpected error during request validation",
                    details={"error": str(e)}
                )
    
    def _should_skip_validation(self, request: Request) -> bool:
        """Check if validation should be skipped for this request."""
        return any(request.url.path.startswith(path) for path in self.skip_paths)
    
    def _validate_content_length(self, request: Request) -> bool:
        """Validate the content length of the request."""
        content_length_str = request.headers.get("content-length")
        if not content_length_str:
            # For chunked encoding or if endpoint expects no body, this might be fine
            # However, if a body is expected but no content-length, it's ambiguous.
            # For now, allow if no content-length. Strict checking could be added.
            return True 
        
        try:
            length = int(content_length_str)
            return length <= self.max_content_length
        except ValueError:
            logger.warning(f"Invalid Content-Length header: {content_length_str}")
            return False # Invalid content length format
    
    def _validate_content_type(self, request: Request) -> bool:
        """Validate the content type of the request."""
        content_type = request.headers.get("content-type", "")
        if not content_type and (request.method in ["POST", "PUT", "PATCH"]):
             # If there's a body expected, content-type should be present.
             # This check can be more nuanced based on whether body is actually present.
             # For now, if method implies body, content-type is needed.
             # logger.warning(f"Missing Content-Type for {request.method} to {request.url.path}")
             # return False # Stricter check
             return True # Relaxed: allow if no body is actually sent, or let endpoint handle

        if content_type.startswith("multipart/form-data"):
            return "boundary=" in content_type.lower()
        
        return any(
            content_type.lower().startswith(allowed_type.lower())
            for allowed_type in self.allowed_content_types
        )
    
    def _is_json_request(self, request: Request) -> bool:
        """Check if the request is a JSON request."""
        content_type = request.headers.get("content-type", "")
        return content_type.lower().startswith("application/json")
    
    def _validate_json_body(self, body: Dict[Any, Any], endpoint: str) -> bool:
        """Validate the structure of the JSON body. Placeholder for custom rules."""
        # Example: if endpoint == "/api/v1/specific_endpoint":
        # if not isinstance(body.get("my_field"), str):
        # return False
        return True
    
    def _should_apply_custom_validation(self, request: Request) -> bool:
        """Check if custom validation should be applied."""
        path = request.url.path
        return path in self.custom_validators
    
    async def _apply_custom_validation(self, request: Request):
        """Apply custom validation rules loaded from settings."""
        path = request.url.path
        validators_for_path = self.custom_validators[path]
        body = await request.state.json_body if hasattr(request.state, "json_body") else await request.json()
        
        for validator_config in validators_for_path: # Assuming validators_for_path is a list of configs
            # This part needs to be more robust: how are validators defined/loaded?
            # If they are strings, they need to be imported. If callables, they can be called.
            # E.g., validator_func = import_string(validator_config["function"])
            # await validator_func(request, body, **validator_config.get("params", {}))
            pass # Placeholder for actual custom validator execution
    
    def _log_validation_error(self, error_type: str, endpoint: str):
        """Log validation error and update metrics."""
        VALIDATION_ERRORS.labels(
            error_type=error_type,
            endpoint=endpoint
        ).inc()
        
        logger.warning(
            f"Request validation error: {error_type} for endpoint {endpoint}"
        ) 