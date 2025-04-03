from typing import Any, Dict, Optional
from fastapi import HTTPException, status
from app.core.logging import logger

class AppException(HTTPException):
    """Base application exception."""
    def __init__(
        self,
        message: str,
        code: str,
        status_code: int = 500,
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
            status_code=status.HTTP_404_NOT_FOUND
        )

class ValidationError(AppException):
    """Raised when validation fails."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details
        )

class AuthenticationError(AppException):
    """Raised when authentication fails."""
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            message=message,
            code="AUTHENTICATION_ERROR",
            status_code=status.HTTP_401_UNAUTHORIZED
        )

class AuthorizationError(AppException):
    """Raised when authorization fails."""
    def __init__(self, message: str = "Not authorized"):
        super().__init__(
            message=message,
            code="AUTHORIZATION_ERROR",
            status_code=status.HTTP_403_FORBIDDEN
        )

class ConflictError(AppException):
    """Raised when there's a conflict."""
    def __init__(self, message: str = "Resource already exists"):
        super().__init__(
            message=message,
            code="CONFLICT",
            status_code=status.HTTP_409_CONFLICT
        )

class RateLimitError(AppException):
    """Raised when rate limit is exceeded."""
    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(
            message=message,
            code="RATE_LIMIT_EXCEEDED",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS
        )

class ServiceUnavailableError(AppException):
    """Raised when a service is unavailable."""
    def __init__(self, message: str = "Service temporarily unavailable"):
        super().__init__(
            message=message,
            code="SERVICE_UNAVAILABLE",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )

class AuthorizationException(AppException):
    """Exception for authorization errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="AUTHORIZATION_ERROR",
            status_code=status.HTTP_403_FORBIDDEN,
            details=details
        )

class DatabaseError(AppException):
    """Exception for database-related errors."""
    
    def __init__(
        self,
        message: str = "Database error occurred",
        details: Optional[Dict[str, Any]] = None,
        status_code: int = 500
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
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details
        )

class ExternalServiceException(AppException):
    """Exception for external service errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="EXTERNAL_SERVICE_ERROR",
            status_code=status.HTTP_502_BAD_GATEWAY,
            details=details
        )

class ConfigurationException(AppException):
    """Exception for configuration errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="CONFIGURATION_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
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
            status_code=400,
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
            status_code=500,
            details=details
        )

class ServiceError(AppException):
    """Base exception for service-level errors."""
    def __init__(self, message: str, code: str = "SERVICE_ERROR", status_code: int = 500):
        super().__init__(message, code, status_code)

class RateLimitException(HTTPException):
    """Exception raised when rate limit is exceeded."""
    def __init__(self, detail: str = "Rate limit exceeded", details: Optional[Dict[str, Any]] = None):
        super().__init__(status_code=429, detail=detail)
        self.details = details or {}

class ValidationException(HTTPException):
    """Exception raised for validation errors."""
    def __init__(self, detail: str = "Validation error", details: Optional[Dict[str, Any]] = None):
        super().__init__(status_code=422, detail=detail)
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
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
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
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)

class AuthenticationException(AppException):
    """Exception raised for authentication errors."""
    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)

class AuthorizationException(AppException):
    """Exception raised for authorization errors."""
    def __init__(self, detail: str = "Not authorized"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)

class DatabaseException(AppException):
    """Exception raised for database errors."""
    def __init__(self, detail: str = "Database error"):
        super().__init__(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)

class VideoProcessingError(AppException):
    """Base class for video processing errors."""
    def __init__(self, detail: str = "Video processing error"):
        super().__init__(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)

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
    """Base class for storage errors."""
    def __init__(self, detail: str = "Storage error"):
        super().__init__(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)

class FileUploadError(StorageError):
    """Exception raised when file upload fails."""
    def __init__(self, detail: str = "File upload failed"):
        super().__init__(detail=detail)

class FileDownloadError(StorageError):
    """Exception raised when file download fails."""
    def __init__(self, detail: str = "File download failed"):
        super().__init__(detail=detail)

class FileDeleteError(StorageError):
    """Exception raised when file deletion fails."""
    def __init__(self, detail: str = "File deletion failed"):
        super().__init__(detail=detail)

class NotFoundException(HTTPException):
    """Not found exception."""

    def __init__(self, detail: str = "Not found"):
        """Initialize exception."""
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)

class UnauthorizedException(HTTPException):
    """Unauthorized exception."""

    def __init__(self, detail: str = "Unauthorized"):
        """Initialize exception."""
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )

class ForbiddenException(HTTPException):
    """Forbidden exception."""

    def __init__(self, detail: str = "Forbidden"):
        """Initialize exception."""
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)

class BadRequestException(HTTPException):
    """Bad request exception."""

    def __init__(self, detail: str = "Bad request"):
        """Initialize exception."""
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

class StorageError(Exception):
    """Storage error exception."""

    def __init__(self, message: str = "Storage error"):
        """Initialize exception."""
        super().__init__(message) 