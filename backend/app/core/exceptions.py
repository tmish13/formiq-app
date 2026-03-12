"""
FormIQ Backend Exception Hierarchy

Clean, minimal exception hierarchy based on actual usage patterns.
Provides consistent error codes and HTTP status mapping for API responses.
"""

from typing import Any, Dict, Optional
from http import HTTPStatus
from fastapi import HTTPException
from app.core.logging import get_logger

logger = get_logger(__name__)

# =============================================================================
# Base Exception Classes
# =============================================================================

class FormIQException(Exception):
    """
    Base exception for all FormIQ application errors.
    
    Provides consistent error structure with HTTP status codes and error codes
    that map cleanly to API responses.
    """
    
    def __init__(
        self,
        message: str,
        error_code: str,
        status_code: int = HTTPStatus.INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)
        
        # Log all application errors for monitoring
        logger.error(
            f"FormIQ error: {message}",
            extra={
                "error_code": error_code,
                "status_code": status_code,
                "details": details
            }
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for JSON API responses."""
        result = {
            "error": {
                "code": self.error_code,
                "message": self.message,
                "status": self.status_code
            }
        }
        if self.details:
            result["error"]["details"] = self.details
        return result
    
    def to_http_exception(self) -> HTTPException:
        """Convert to FastAPI HTTPException for API responses."""
        return HTTPException(
            status_code=self.status_code,
            detail=self.to_dict()["error"]
        )

# =============================================================================
# Authentication & Authorization Exceptions  
# =============================================================================

class AuthenticationException(FormIQException):
    """Authentication failed - invalid credentials, expired tokens, etc."""
    
    def __init__(
        self,
        message: str = "Authentication failed",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_ERROR",
            status_code=HTTPStatus.UNAUTHORIZED,
            details=details
        )

class PermissionDeniedException(FormIQException):
    """User lacks required permissions for the requested operation."""
    
    def __init__(
        self,
        message: str = "Permission denied",
        required_permissions: Optional[list] = None
    ):
        details = {"required_permissions": required_permissions} if required_permissions else None
        super().__init__(
            message=message,
            error_code="PERMISSION_DENIED",
            status_code=HTTPStatus.FORBIDDEN,
            details=details
        )

# =============================================================================
# Validation & Input Exceptions
# =============================================================================

class ValidationException(FormIQException):
    """Invalid input data, failed validation rules."""

    def __init__(
        self,
        message: str = "Validation error",
        field_errors: Optional[Dict[str, list]] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        d = details or ({"field_errors": field_errors} if field_errors else None)
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=HTTPStatus.BAD_REQUEST,
            details=d
        )

# =============================================================================
# Resource Management Exceptions
# =============================================================================

class NotFoundException(FormIQException):
    """Requested resource was not found."""
    
    def __init__(
        self,
        message: str = "Resource not found",
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None
    ):
        details = {}
        if resource_type:
            details["resource_type"] = resource_type
        if resource_id:
            details["resource_id"] = resource_id
        
        super().__init__(
            message=message,
            error_code="NOT_FOUND",
            status_code=HTTPStatus.NOT_FOUND,
            details=details or None
        )

class ConflictException(FormIQException):
    """Resource already exists or conflicts with current state."""
    
    def __init__(
        self,
        message: str = "Resource conflict",
        conflicting_field: Optional[str] = None
    ):
        details = {"conflicting_field": conflicting_field} if conflicting_field else None
        super().__init__(
            message=message,
            error_code="CONFLICT",
            status_code=HTTPStatus.CONFLICT,
            details=details
        )

# =============================================================================
# Video Processing Exceptions
# =============================================================================

class VideoProcessingError(FormIQException):
    """Base class for all video processing related errors."""
    
    def __init__(
        self,
        message: str = "Video processing failed",
        processing_stage: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        if processing_stage:
            details = details or {}
            details["processing_stage"] = processing_stage
            
        super().__init__(
            message=message,
            error_code="VIDEO_PROCESSING_ERROR",
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            details=details
        )

class VideoValidationError(VideoProcessingError):
    """Video file validation failed (format, size, duration, etc.)."""
    
    def __init__(
        self,
        message: str,
        validation_type: str,
        expected_value: Optional[Any] = None,
        actual_value: Optional[Any] = None
    ):
        details = {"validation_type": validation_type}
        if expected_value is not None:
            details["expected"] = expected_value
        if actual_value is not None:
            details["actual"] = actual_value
            
        super().__init__(
            message=message,
            processing_stage="validation",
            details=details
        )

class VideoReadError(VideoProcessingError):
    """Video file reading or decoding failed."""
    
    def __init__(
        self,
        message: str = "Failed to read video file",
        codec_info: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        if codec_info:
            details = details or {}
            details["codec_info"] = codec_info
            
        super().__init__(
            message=message,
            processing_stage="video_reading",
            details=details
        )

# =============================================================================
# Storage & File Exceptions
# =============================================================================

class StorageError(FormIQException):
    """File storage operations failed (S3, local filesystem, etc.)."""
    
    def __init__(
        self,
        message: str = "Storage operation failed",
        operation: Optional[str] = None,
        file_path: Optional[str] = None
    ):
        details = {}
        if operation:
            details["operation"] = operation
        if file_path:
            details["file_path"] = file_path
            
        super().__init__(
            message=message,
            error_code="STORAGE_ERROR",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            details=details or None
        )

# =============================================================================
# Service & External System Exceptions
# =============================================================================

class ServiceError(FormIQException):
    """Generic service-level error for internal service failures."""
    
    def __init__(
        self,
        message: str = "Service error occurred",
        service_name: Optional[str] = None,
        is_retryable: bool = True
    ):
        details = {
            "service_name": service_name,
            "is_retryable": is_retryable
        } if service_name else {"is_retryable": is_retryable}
        
        super().__init__(
            message=message,
            error_code="SERVICE_ERROR",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            details=details
        )

class ExternalServiceError(FormIQException):
    """External service unavailable or returned an error (OpenAI, S3, etc.)."""
    
    def __init__(
        self,
        message: str = "External service error",
        service_name: Optional[str] = None,
        is_temporary: bool = True,
        retry_after: Optional[int] = None
    ):
        details = {
            "service_name": service_name,
            "is_temporary": is_temporary
        }
        if retry_after:
            details["retry_after_seconds"] = retry_after
            
        status_code = HTTPStatus.SERVICE_UNAVAILABLE if is_temporary else HTTPStatus.BAD_GATEWAY
        
        super().__init__(
            message=message,
            error_code="EXTERNAL_SERVICE_ERROR",
            status_code=status_code,
            details=details
        )

# =============================================================================
# AI/ML Processing Exceptions
# =============================================================================

class AIServiceError(ServiceError):
    """AI/ML model processing failed."""
    
    def __init__(
        self,
        message: str = "AI processing failed",
        model_type: Optional[str] = None,
        confidence_score: Optional[float] = None
    ):
        details = {}
        if model_type:
            details["model_type"] = model_type
        if confidence_score is not None:
            details["confidence_score"] = confidence_score
            
        super().__init__(
            message=message,
            service_name="ai_service",
            is_retryable=True
        )
        self.error_code = "AI_SERVICE_ERROR"
        if details:
            self.details.update(details)

# =============================================================================
# System & Infrastructure Exceptions
# =============================================================================

class ServerErrorException(FormIQException):
    """Generic server error for unexpected system failures."""
    
    def __init__(
        self,
        message: str = "Internal server error",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code="SERVER_ERROR",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            details=details
        )

class DatabaseException(FormIQException):
    """Database operation failed."""
    
    def __init__(
        self,
        message: str = "Database operation failed",
        operation: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        if operation:
            details = details or {}
            details["operation"] = operation
            
        super().__init__(
            message=message,
            error_code="DATABASE_ERROR",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            details=details
        )

class EmailError(ExternalServiceError):
    """Email service operation failed."""
    
    def __init__(
        self,
        message: str = "Email operation failed",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            service_name="email_service",
            is_temporary=True,
            retry_after=60
        )
        if details:
            self.details.update(details)

class ProcessingError(FormIQException):
    """Generic processing error (e.g. pose estimation)."""

    def __init__(
        self,
        message: str = "Processing failed",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code="PROCESSING_ERROR",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            details=details
        )


class RateLimitExceededException(FormIQException):
    """Rate limit exceeded."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
        detail: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        msg = detail or message
        d = details or {}
        if retry_after is not None:
            d["retry_after"] = retry_after
        super().__init__(
            message=msg,
            error_code="RATE_LIMIT_EXCEEDED",
            status_code=HTTPStatus.TOO_MANY_REQUESTS,
            details=d
        )
        self.retry_after = retry_after


# =============================================================================
# Convenience Aliases for Backward Compatibility
# =============================================================================

# These aliases maintain compatibility with existing code
# while gradually migrating to the new hierarchy

AuthenticationError = AuthenticationException
AuthorizationException = PermissionDeniedException
AuthorizationError = PermissionDeniedException
NotFoundError = NotFoundException
ResourceNotFoundError = NotFoundException
ValidationError = ValidationException
AppException = FormIQException
BusinessError = FormIQException
RateLimitException = FormIQException  # Alias for middleware imports


class PaymentError(ExternalServiceError):
    """Payment/billing operation failed (e.g. Stripe)."""

    def __init__(
        self,
        message: str = "Payment operation failed",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            service_name="stripe",
            is_temporary=True,
            retry_after=30
        )
        if details:
            self.details.update(details)


class StripeWebhookError(ExternalServiceError):
    """Stripe webhook processing failed."""

    def __init__(
        self,
        message: str = "Stripe webhook error",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            service_name="stripe",
            is_temporary=False,
            retry_after=None
        )
        if details:
            self.details.update(details)

# =============================================================================
# Exception Handler Utilities
# =============================================================================

def create_error_response(
    error_code: str,
    message: str,
    status_code: int = HTTPStatus.INTERNAL_SERVER_ERROR,
    details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create a standardized error response dictionary.
    
    Use this for cases where you need to return an error response
    without raising an exception.
    """
    response = {
        "error": {
            "code": error_code,
            "message": message,
            "status": status_code
        }
    }
    if details:
        response["error"]["details"] = details
    return response