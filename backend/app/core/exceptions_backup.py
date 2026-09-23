from typing import Any, Dict, List, Optional, Union
from fastapi import HTTPException, status
from app.core.logging import get_logger
from http import HTTPStatus

logger = get_logger(__name__)

class BaseAPIException(Exception):
    """Base exception class for API errors.
    
    Attributes:
        message (str): Human readable error description
        error_code (str): Machine readable error code
        status_code (int): HTTP status code
        details (Optional[Dict[str, Any]]): Additional error details
    """
    def __init__(
        self,
        message: str,
        error_code: str,
        status_code: int = HTTPStatus.INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary format."""
        return {
            "error": {
                "message": self.message,
                "code": self.error_code,
                "details": self.details
            }
        }

class ValidationError(BaseAPIException):
    """Raised when request validation fails."""
    def __init__(
        self,
        message: str = "Invalid request data",
        error_code: str = "VALIDATION_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=HTTPStatus.BAD_REQUEST,
            details=details
        )

class AuthenticationError(BaseAPIException):
    """Raised when authentication fails."""
    def __init__(
        self,
        message: str = "Authentication failed",
        error_code: str = "AUTHENTICATION_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=HTTPStatus.UNAUTHORIZED,
            details=details
        )

class AuthorizationError(BaseAPIException):
    """Raised when user lacks required permissions."""
    def __init__(
        self,
        message: str = "Permission denied",
        error_code: str = "AUTHORIZATION_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=HTTPStatus.FORBIDDEN,
            details=details
        )

class ResourceNotFoundError(BaseAPIException):
    """Raised when requested resource is not found."""
    def __init__(
        self,
        message: str = "Resource not found",
        error_code: str = "RESOURCE_NOT_FOUND",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=HTTPStatus.NOT_FOUND,
            details=details
        )

class BusinessError(BaseAPIException):
    """Raised when a business rule is violated."""
    def __init__(
        self,
        message: str = "Business rule violation",
        error_code: str = "BUSINESS_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            details=details
        )

class RateLimitError(BaseAPIException):
    """Raised when rate limit is exceeded."""
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        error_code: str = "RATE_LIMIT_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=HTTPStatus.TOO_MANY_REQUESTS,
            details=details
        )

class DatabaseError(BaseAPIException):
    """Raised when database operations fail."""
    def __init__(
        self,
        message: str = "Database operation failed",
        error_code: str = "DATABASE_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            details=details
        )

class ConfigurationError(BaseAPIException):
    """Raised when there are configuration issues."""
    def __init__(
        self,
        message: str = "Configuration error",
        error_code: str = "CONFIGURATION_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            details=details
        )

class ExternalServiceError(BaseAPIException):
    """Raised when external service calls fail."""
    def __init__(
        self,
        message: str = "External service error",
        error_code: str = "EXTERNAL_SERVICE_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=HTTPStatus.BAD_GATEWAY,
            details=details
        )

# Authentication Errors
class InvalidCredentialsError(AuthenticationError):
    """Raised when credentials are invalid."""
    def __init__(self, message: str = "Invalid credentials provided"):
        super().__init__(message=message, error_code="INVALID_CREDENTIALS")

class TokenExpiredError(AuthenticationError):
    """Raised when authentication token has expired."""
    def __init__(self, message: str = "Authentication token has expired"):
        super().__init__(
            message=message,
            error_code="TOKEN_EXPIRED",
            details={"should_refresh": True}
        )

# Authorization Errors
class InsufficientPermissionsError(AuthorizationError):
    """Raised when user lacks required permissions."""
    def __init__(
        self,
        message: str = "Insufficient permissions",
        required_permissions: Optional[List[str]] = None
    ):
        details = {"required_permissions": required_permissions} if required_permissions else None
        super().__init__(message=message, error_code="INSUFFICIENT_PERMISSIONS", details=details)

# Validation Errors
class InvalidInputError(ValidationError):
    """Raised when input data is invalid."""
    def __init__(
        self,
        message: str = "Invalid input data",
        field_errors: Optional[Dict[str, List[str]]] = None
    ):
        super().__init__(message=message, field_errors=field_errors, error_code="INVALID_INPUT")

# Resource Errors
class ResourceError(BaseAPIException):
    """Base class for resource-related errors."""
    def __init__(
        self,
        message: str,
        resource_type: str,
        resource_id: Optional[Union[str, int]] = None,
        error_code: str = "RESOURCE_ERROR"
    ):
        details = {
            "resource_type": resource_type,
            "resource_id": resource_id
        } if resource_id else {"resource_type": resource_type}
        
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=HTTPStatus.NOT_FOUND,
            details=details
        )

class ResourceNotFoundError(ResourceError):
    """Raised when a requested resource is not found."""
    def __init__(
        self,
        resource_type: str,
        resource_id: Optional[Union[str, int]] = None
    ):
        message = f"{resource_type} not found"
        if resource_id:
            message = f"{resource_type} with id {resource_id} not found"
        super().__init__(
            message=message,
            resource_type=resource_type,
            resource_id=resource_id,
            error_code="RESOURCE_NOT_FOUND"
        )

# Service Errors
class ServiceError(BaseAPIException):
    """Base class for service-related errors."""
    def __init__(
        self,
        message: str,
        service_name: str,
        is_temporary: bool = True,
        retry_after: Optional[int] = None,
        error_code: str = "SERVICE_ERROR"
    ):
        details = {"service": service_name, "is_temporary": is_temporary}
        if retry_after is not None:
            details["retry_after"] = retry_after
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=HTTPStatus.SERVICE_UNAVAILABLE if is_temporary else HTTPStatus.INTERNAL_SERVER_ERROR,
            details=details
        )

class DatabaseError(ServiceError):
    """Raised when a database operation fails."""
    def __init__(
        self,
        message: str = "Database operation failed",
        is_temporary: bool = True,
        retry_after: Optional[int] = 30
    ):
        super().__init__(
            message=message,
            service_name="database",
            is_temporary=is_temporary,
            retry_after=retry_after,
            error_code="DATABASE_ERROR"
        )

class CacheError(ServiceError):
    """Raised when a cache operation fails."""
    def __init__(
        self,
        message: str = "Cache operation failed",
        is_temporary: bool = True,
        retry_after: Optional[int] = 5
    ):
        super().__init__(
            message=message,
            service_name="cache",
            is_temporary=is_temporary,
            retry_after=retry_after,
            error_code="CACHE_ERROR"
        )

# Rate Limiting Errors
class RateLimitError(BaseAPIException):
    """Raised when rate limit is exceeded."""
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: int = 60,
        limit: Optional[int] = None,
        window: Optional[int] = None
    ):
        details = {
            "retry_after": retry_after,
            "limit": limit,
            "window": window
        }
        super().__init__(
            message=message,
            error_code="RATE_LIMIT_EXCEEDED",
            status_code=HTTPStatus.TOO_MANY_REQUESTS,
            details=details
        )

# Business Logic Errors
class InvalidStateError(BusinessError):
    """Raised when an operation is invalid in the current state."""
    def __init__(
        self,
        message: str,
        current_state: str,
        expected_state: Optional[str] = None
    ):
        details = {
            "current_state": current_state,
            "expected_state": expected_state
        } if expected_state else {"current_state": current_state}
        super().__init__(
            message=message,
            error_code="INVALID_STATE",
            details=details
        )

# System Errors
class SystemError(BaseAPIException):
    """Base class for system-level errors."""
    def __init__(
        self,
        message: str,
        error_code: str = "SYSTEM_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            details=details
        )

class ApplicationException(Exception):
    """Base exception for all application-specific exceptions."""
    
    def __init__(
        self,
        message: str,
        status_code: int = HTTPStatus.INTERNAL_SERVER_ERROR,
        error_code: str = "internal_error",
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API response."""
        result = {
            "error": self.error_code,
            "message": self.message,
        }
        
        if self.details:
            result["details"] = self.details
            
        return result


class AuthenticationException(ApplicationException):
    """Raised when authentication fails."""
    
    def __init__(
        self,
        message: str = "Authentication failed",
        error_code: str = "authentication_error",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=HTTPStatus.UNAUTHORIZED,
            error_code=error_code,
            details=details
        )


class PermissionDeniedException(ApplicationException):
    """Raised when user doesn't have permission to perform an action."""
    
    def __init__(
        self,
        message: str = "Permission denied",
        error_code: str = "permission_denied",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=HTTPStatus.FORBIDDEN,
            error_code=error_code,
            details=details
        )


class ValidationException(BaseAPIException):
    """Exception raised when validation fails."""
    def __init__(
        self,
        message: str = "Validation error",
        error_code: str = "VALIDATION_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=HTTPStatus.BAD_REQUEST,
            details=details
        )


class ResourceNotFoundException(ApplicationException):
    """Raised when requested resource is not found."""
    
    def __init__(
        self,
        message: str = "Resource not found",
        error_code: str = "not_found",
        resource_type: Optional[str] = None,
        resource_id: Optional[Union[str, int]] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        if resource_type:
            details["resource_type"] = resource_type
        if resource_id:
            details["resource_id"] = resource_id
            
        super().__init__(
            message=message,
            status_code=HTTPStatus.NOT_FOUND,
            error_code=error_code,
            details=details
        )


class ConflictException(ApplicationException):
    """Raised when there's a conflict with the current state of the resource."""
    
    def __init__(
        self,
        message: str = "Resource conflict",
        error_code: str = "conflict",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=HTTPStatus.CONFLICT,
            error_code=error_code,
            details=details
        )


class RateLimitExceededException(ApplicationException):
    """Raised when rate limit is exceeded."""
    
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        error_code: str = "rate_limit_exceeded",
        retry_after: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        if retry_after:
            details["retry_after"] = retry_after
            
        super().__init__(
            message=message,
            status_code=HTTPStatus.TOO_MANY_REQUESTS,
            error_code=error_code,
            details=details
        )


class ServiceUnavailableException(ApplicationException):
    """Raised when a service is unavailable."""
    
    def __init__(
        self,
        message: str = "Service unavailable",
        error_code: str = "service_unavailable",
        service_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        if service_name:
            details["service"] = service_name
            
        super().__init__(
            message=message,
            status_code=HTTPStatus.SERVICE_UNAVAILABLE,
            error_code=error_code,
            details=details
        )


class DatabaseException(ApplicationException):
    """Raised when a database operation fails."""
    
    def __init__(
        self,
        message: str = "Database operation failed",
        error_code: str = "database_error",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            error_code=error_code,
            details=details
        )


class ConfigurationException(ApplicationException):
    """Raised when there's a configuration issue."""
    
    def __init__(
        self,
        message: str = "Configuration error",
        error_code: str = "configuration_error",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            error_code=error_code,
            details=details
        )


def http_exception_handler(status_code: int, message: str, headers: Optional[Dict[str, str]] = None) -> HTTPException:
    """Create a FastAPI HTTPException with consistent format.
    
    Args:
        status_code: HTTP status code
        message: Error message
        headers: Optional response headers
        
    Returns:
        HTTPException: FastAPI exception
    """
    return HTTPException(
        status_code=status_code,
        detail={"message": message},
        headers=headers
    )

class AppException(HTTPException):
    """Base application exception."""
    def __init__(
        self,
        message: str,
        code: str,
        status_code: int = HTTPStatus.INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(status_code=status_code, detail=message)
        self.message = message
        self.code = code
        self.details = details or {}
        logger.error(f"Application error: {message}", extra={"code": code, "status_code": status_code})

class NotFoundError(AppException):
    """Raised when a resource is not found."""
    def __init__(self, message: str = "Resource not found"):
        super().__init__(
            message=message,
            code="NOT_FOUND",
            status_code=HTTPStatus.NOT_FOUND
        )

class ValidationError(AppException):
    """Raised when validation fails."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            details=details
        )

class AuthenticationError(AppException):
    """Raised when authentication fails."""
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            message=message,
            code="AUTHENTICATION_ERROR",
            status_code=HTTPStatus.UNAUTHORIZED
        )

class AuthorizationError(AppException):
    """Raised when authorization fails."""
    def __init__(self, message: str = "Not authorized"):
        super().__init__(
            message=message,
            code="AUTHORIZATION_ERROR",
            status_code=HTTPStatus.FORBIDDEN
        )

class ConflictError(AppException):
    """Raised when there's a conflict."""
    def __init__(self, message: str = "Resource already exists"):
        super().__init__(
            message=message,
            code="CONFLICT",
            status_code=HTTPStatus.CONFLICT
        )

class RateLimitError(AppException):
    """Raised when rate limit is exceeded."""
    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(
            message=message,
            code="RATE_LIMIT_EXCEEDED",
            status_code=HTTPStatus.TOO_MANY_REQUESTS
        )

class ServiceUnavailableError(AppException):
    """Raised when a service is unavailable."""
    def __init__(self, message: str = "Service temporarily unavailable"):
        super().__init__(
            message=message,
            code="SERVICE_UNAVAILABLE",
            status_code=HTTPStatus.SERVICE_UNAVAILABLE
        )

class AuthorizationException(AppException):
    """Exception for authorization errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="AUTHORIZATION_ERROR",
            status_code=HTTPStatus.FORBIDDEN,
            details=details
        )

class DatabaseError(AppException):
    """Exception for database-related errors."""
    
    def __init__(
        self,
        message: str = "Database error occurred",
        details: Optional[Dict[str, Any]] = None,
        status_code: int = HTTPStatus.INTERNAL_SERVER_ERROR
    ):
        super().__init__(
            message=message,
            code="DATABASE_ERROR",
            status_code=status_code,
            details=details
        )

class CacheException(AppException):
    """Exception for cache errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="CACHE_ERROR",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            details=details
        )

class ExternalServiceException(AppException):
    """Exception for external service errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="EXTERNAL_SERVICE_ERROR",
            status_code=HTTPStatus.BAD_GATEWAY,
            details=details
        )

class PaymentError(AppException):
    """Exception for payment-related errors."""
    
    def __init__(
        self,
        message: str = "Payment error occurred",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            code="PAYMENT_ERROR",
            status_code=HTTPStatus.BAD_REQUEST,
            details=details
        )

class ProcessingError(AppException):
    """Exception for video processing errors."""
    
    def __init__(
        self,
        message: str = "Video processing error occurred",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            code="PROCESSING_ERROR",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            details=details
        )

class ServiceError(AppException):
    """Base exception for service-level errors."""
    def __init__(self, message: str, code: str = "SERVICE_ERROR", status_code: int = HTTPStatus.INTERNAL_SERVER_ERROR):
        super().__init__(message, code, status_code)

class RateLimitException(HTTPException):
    """Exception raised when rate limit is exceeded."""
    def __init__(self, detail: str = "Rate limit exceeded", details: Optional[Dict[str, Any]] = None):
        super().__init__(status_code=HTTPStatus.TOO_MANY_REQUESTS, detail=detail)
        self.details = details or {}

class ValidationException(HTTPException):
    """Exception raised for validation errors."""
    
    def __init__(self, message: str = "Validation error", details: Optional[Dict[str, Any]] = None):
        """Initialize validation exception with message and optional details.
        
        Args:
            message: Error message
            details: Additional error details
        """
        super().__init__(status_code=400, detail=message)
        self.details = details or {}

"""Custom exceptions."""
from fastapi import HTTPException, status

class UserAlreadyExists(HTTPException):
    """Raised when user already exists."""
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )

class InvalidCredentials(HTTPException):
    """Raised when credentials are invalid."""
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail
        )

class UserNotFound(HTTPException):
    """Raised when user is not found."""
    def __init__(self, detail: str = "User not found"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail
        )

class TokenExpired(HTTPException):
    """Raised when token has expired."""
    def __init__(self, detail: str = "Token has expired"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail
        )

class InvalidToken(HTTPException):
    """Raised when token is invalid."""
    def __init__(self, detail: str = "Invalid token"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail
        )

class VideoProcessingError(ProcessingError):
    """Exception for video processing errors."""
    
    def __init__(
        self,
        message: str = "Video processing error occurred",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            code="VIDEO_PROCESSING_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details
        )

class VideoValidationError(ValidationError):
    """Exception for video validation errors."""
    
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            details=details
        )

class VideoFormatError(VideoValidationError):
    """Exception for invalid video format."""
    
    def __init__(
        self,
        message: str = "Invalid video format",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            details=details
        )

class VideoSizeError(VideoValidationError):
    """Exception for video size exceeding limits."""
    
    def __init__(
        self,
        message: str = "Video size exceeds maximum allowed",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            details=details
        )

class VideoDurationError(VideoValidationError):
    """Exception for video duration exceeding limits."""
    
    def __init__(
        self,
        message: str = "Video duration exceeds maximum allowed",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            details=details
        )

class PoseDetectionError(VideoProcessingError):
    """Exception for pose detection failures."""
    
    def __init__(
        self,
        message: str = "Failed to detect pose in video",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            details=details
        )

class ExerciseIdentificationError(VideoProcessingError):
    """Exception for exercise identification failures."""
    
    def __init__(
        self,
        message: str = "Failed to identify exercise type",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            details=details
        )

class FormAnalysisError(VideoProcessingError):
    """Exception for form analysis failures."""
    
    def __init__(
        self,
        message: str = "Failed to analyze exercise form",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            details=details
        )

class FeedbackVideoError(VideoProcessingError):
    """Exception for feedback video generation failures."""
    
    def __init__(
        self,
        message: str = "Failed to generate feedback video",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            details=details
        )

class StorageError(AppException):
    """Exception for storage-related errors."""
    
    def __init__(
        self,
        message: str = "Storage error occurred",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            code="STORAGE_ERROR",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            details=details
        )

class FileUploadError(StorageError):
    """Exception for file upload failures."""
    
    def __init__(
        self,
        message: str = "Failed to upload file",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            details=details
        )

class FileDownloadError(StorageError):
    """Exception for file download failures."""
    
    def __init__(
        self,
        message: str = "Failed to download file",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            details=details
        )

class FileDeleteError(StorageError):
    """Exception for file deletion failures."""
    
    def __init__(
        self,
        message: str = "Failed to delete file",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            details=details
        )

class NotFoundException(AppException):
    """Exception raised when a resource is not found."""
    def __init__(self, detail: str = "Resource not found"):
        super().__init__(status_code=HTTPStatus.NOT_FOUND, detail=detail)

class AuthenticationException(AppException):
    """Exception raised for authentication errors."""
    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(status_code=HTTPStatus.UNAUTHORIZED, detail=detail)

class AuthorizationException(AppException):
    """Exception raised for authorization errors."""
    def __init__(self, detail: str = "Not authorized"):
        super().__init__(status_code=HTTPStatus.FORBIDDEN, detail=detail)

class DatabaseException(AppException):
    """Exception raised for database errors."""
    def __init__(self, detail: str = "Database error"):
        super().__init__(status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=detail)

class VideoProcessingError(AppException):
    """Base class for video processing errors."""
    def __init__(self, detail: str = "Video processing error"):
        super().__init__(status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=detail)

class VideoValidationError(ValidationException):
    """Base class for video validation errors."""
    def __init__(self, detail: str = "Video validation error"):
        super().__init__(detail=detail)

class VideoFormatError(VideoValidationError):
    """Exception raised for invalid video format."""
    def __init__(self, detail: str = "Invalid video format"):
        super().__init__(detail=detail)

class VideoSizeError(VideoValidationError):
    """Exception raised for invalid video size."""
    def __init__(self, detail: str = "Invalid video size"):
        super().__init__(detail=detail)

class VideoDurationError(VideoValidationError):
    """Exception raised for invalid video duration."""
    def __init__(self, detail: str = "Invalid video duration"):
        super().__init__(detail=detail)

class PoseDetectionError(VideoProcessingError):
    """Exception raised when pose detection fails."""
    def __init__(self, detail: str = "Pose detection failed"):
        super().__init__(detail=detail)

class ExerciseIdentificationError(VideoProcessingError):
    """Exception raised when exercise identification fails."""
    def __init__(self, detail: str = "Exercise identification failed"):
        super().__init__(detail=detail)

class FormAnalysisError(VideoProcessingError):
    """Exception raised when form analysis fails."""
    def __init__(self, detail: str = "Form analysis failed"):
        super().__init__(detail=detail)

class FeedbackVideoError(VideoProcessingError):
    """Exception raised when feedback video generation fails."""
    def __init__(self, detail: str = "Feedback video generation failed"):
        super().__init__(detail=detail)

class StorageError(AppException):
    """Exception for storage-related errors."""
    
    def __init__(
        self,
        message: str = "Storage error occurred",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            code="STORAGE_ERROR",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            details=details
        )

class FileUploadError(StorageError):
    """Exception for file upload failures."""
    
    def __init__(
        self,
        message: str = "Failed to upload file",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            details=details
        )

class FileDownloadError(StorageError):
    """Exception for file download failures."""
    
    def __init__(
        self,
        message: str = "Failed to download file",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            details=details
        )

class FileDeleteError(StorageError):
    """Exception for file deletion failures."""
    
    def __init__(
        self,
        message: str = "Failed to delete file",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            details=details
        )

class NotFoundException(HTTPException):
    """Not found exception."""

    def __init__(self, detail: str = "Not found"):
        """Initialize exception."""
        super().__init__(status_code=HTTPStatus.NOT_FOUND, detail=detail)

class UnauthorizedException(HTTPException):
    """Unauthorized exception."""

    def __init__(self, detail: str = "Unauthorized"):
        """Initialize exception."""
        super().__init__(
            status_code=HTTPStatus.UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )

class ForbiddenException(HTTPException):
    """Forbidden exception."""

    def __init__(self, detail: str = "Forbidden"):
        """Initialize exception."""
        super().__init__(status_code=HTTPStatus.FORBIDDEN, detail=detail)

class BadRequestException(HTTPException):
    """Bad request exception."""

    def __init__(self, detail: str = "Bad request"):
        """Initialize exception."""
        super().__init__(status_code=HTTPStatus.BAD_REQUEST, detail=detail)

"""Core exceptions module."""
from typing import Any, Dict, Optional


class BaseAPIException(Exception):
    """Base exception for all API errors."""
    
    def __init__(
        self,
        message: str,
        status_code: int = HTTPStatus.INTERNAL_SERVER_ERROR,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(message)
        logger.error(
            f"Application error: {message}",
            extra={
                "code": error_code,
                "status_code": status_code,
                "details": details
            }
        )


class AuthenticationException(BaseAPIException):
    """Raised when authentication fails."""
    
    def __init__(
        self,
        message: str = "Authentication failed",
        error_code: str = "AUTH_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=HTTPStatus.UNAUTHORIZED,
            error_code=error_code,
            details=details
        )


class PermissionDeniedException(BaseAPIException):
    """Raised when user doesn't have required permissions."""
    
    def __init__(
        self,
        message: str = "Permission denied",
        error_code: str = "PERMISSION_DENIED",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=HTTPStatus.FORBIDDEN,
            error_code=error_code,
            details=details
        )


class ValidationException(BaseAPIException):
    """Validation error exception."""
    def __init__(
        self,
        message: str = "Validation error",
        error_code: str = "VALIDATION_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=HTTPStatus.BAD_REQUEST,
            details=details
        )


class NotFoundException(BaseAPIException):
    """Raised when a requested resource is not found."""
    
    def __init__(
        self,
        message: str = "Resource not found",
        error_code: str = "NOT_FOUND",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=HTTPStatus.NOT_FOUND,
            error_code=error_code,
            details=details
        )


class ConflictException(BaseAPIException):
    """Raised when there's a conflict with existing data."""
    
    def __init__(
        self,
        message: str = "Resource conflict",
        error_code: str = "CONFLICT",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=HTTPStatus.CONFLICT,
            error_code=error_code,
            details=details
        )


class RateLimitException(BaseAPIException):
    """Raised when rate limit is exceeded."""
    
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        error_code: str = "RATE_LIMIT",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=HTTPStatus.TOO_MANY_REQUESTS,
            error_code=error_code,
            details=details
        )


class ServiceUnavailableException(BaseAPIException):
    """Raised when a required service is unavailable."""
    
    def __init__(
        self,
        message: str = "Service unavailable",
        error_code: str = "SERVICE_UNAVAILABLE",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=HTTPStatus.SERVICE_UNAVAILABLE,
            error_code=error_code,
            details=details
        )


class DatabaseException(BaseAPIException):
    """Exception for database-related errors."""
    
    def __init__(
        self,
        message: str = "Database error occurred",
        details: Optional[Dict[str, Any]] = None,
        status_code: int = HTTPStatus.INTERNAL_SERVER_ERROR
    ):
        super().__init__(
            message=message,
            status_code=status_code,
            error_code="DATABASE_ERROR",
            details=details
        )


class CacheException(BaseAPIException):
    """Exception for cache errors."""
    
    def __init__(
        self,
        message: str = "Cache error occurred",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            error_code="CACHE_ERROR",
            details=details
        )


class ExternalServiceException(BaseAPIException):
    """Exception for external service errors."""
    
    def __init__(
        self,
        message: str = "External service error",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=HTTPStatus.BAD_GATEWAY,
            error_code="EXTERNAL_SERVICE_ERROR",
            details=details
        )


class VideoProcessingException(BaseAPIException):
    """Base exception for errors related to video processing operations."""
    def __init__(
        self,
        message: str = "Video processing error",
        error_code: str = "VIDEO_PROCESSING_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR, # Or UNPROCESSABLE_ENTITY
            details=details
        )


class VideoReadError(VideoProcessingException): # New class
    """Raised when a video file cannot be read or accessed.""" # New class
    def __init__( # New class
        self, # New class
        message: str = "Failed to read or access video file", # New class
        details: Optional[Dict[str, Any]] = None # New class
    ): # New class
        super().__init__( # New class
            message=message, # New class
            error_code="VIDEO_READ_ERROR", # New class
            details=details # New class
        ) # New class


class VideoValidationException(ValidationException):
    """Base exception for errors during video validation."""
    def __init__(
        self,
        message: str = "Video validation error",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code="VIDEO_VALIDATION_ERROR",
            details=details
        )


class StorageException(BaseAPIException):
    """Exception for storage-related errors."""
    
    def __init__(
        self,
        message: str = "Storage error occurred",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            error_code="STORAGE_ERROR",
            details=details
        )


# Specific Video Processing Exceptions
class PoseDetectionException(VideoProcessingException):
    """Exception for pose detection failures."""
    def __init__(self, message: str = "Failed to detect pose in video", details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, error_code="POSE_DETECTION_ERROR", details=details)

class ExerciseIdentificationException(VideoProcessingException):
    """Exception for exercise identification failures."""
    def __init__(self, message: str = "Failed to identify exercise type", details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, error_code="EXERCISE_IDENTIFICATION_ERROR", details=details)

class FormAnalysisException(VideoProcessingException):
    """Exception for form analysis failures."""
    def __init__(self, message: str = "Failed to analyze exercise form", details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, error_code="FORM_ANALYSIS_ERROR", details=details)

# Specific Video Validation Exceptions
class VideoFormatException(VideoValidationException):
    """Exception for invalid video format."""
    def __init__(self, message: str = "Invalid video format", details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, details={"error_type": "format", **details} if details else {"error_type": "format"})

class VideoSizeException(VideoValidationException):
    """Exception for video size exceeding limits."""
    def __init__(self, message: str = "Video size exceeds maximum allowed", details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, details={"error_type": "size", **details} if details else {"error_type": "size"})

class VideoDurationException(VideoValidationException):
    """Exception for video duration exceeding limits."""
    def __init__(self, message: str = "Video duration exceeds maximum allowed", details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, details={"error_type": "duration", **details} if details else {"error_type": "duration"})

# Specific Storage Exceptions
class FileUploadException(StorageException):
    """Exception for file upload failures."""
    def __init__(self, message: str = "Failed to upload file", details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, details={"operation": "upload", **details} if details else {"operation": "upload"})

class FileDownloadException(StorageException):
    """Exception for file download failures."""
    def __init__(self, message: str = "Failed to download file", details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, details={"operation": "download", **details} if details else {"operation": "download"})

class FileDeleteException(StorageException):
    """Exception for file deletion failures."""
    def __init__(self, message: str = "Failed to delete file", details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, details={"operation": "delete", **details} if details else {"operation": "delete"})

class EmailError(ApplicationException):
    """Exception raised for email-related errors."""
    def __init__(
        self,
        message: str,
        error_code: str = "EMAIL_ERROR",
        status_code: int = HTTPStatus.INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=status_code,
            details=details
        )

class ServerErrorException(AppException):
    """Generic server error."""
    def __init__(self, message: str = "An unexpected server error occurred", details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, code="SERVER_ERROR", status_code=HTTPStatus.INTERNAL_SERVER_ERROR, details=details)

class StripeWebhookError(PaymentError):
    """Raised when Stripe webhook processing fails."""
    def __init__(
        self,
        message: str = "Stripe webhook processing failed",
        error_code: str = "STRIPE_WEBHOOK_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=HTTPStatus.BAD_REQUEST,
            details=details
        )

class VideoProcessingError(Exception):
    """Base exception for video processing errors."""
    pass

class VideoValidationError(VideoProcessingError):
    """Exception raised for video validation failures."""
    pass

class VideoReadError(VideoProcessingError):
    """Exception raised when a video file cannot be read or opened."""
    pass 