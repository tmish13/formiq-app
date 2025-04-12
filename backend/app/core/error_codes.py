"""Error code registry for consistent error handling."""
from enum import Enum
from typing import Dict, Optional


class ErrorCode(str, Enum):
    """Enumeration of all possible error codes."""
    
    # Authentication Errors (1xxx)
    AUTHENTICATION_FAILED = "AUTH_001"
    INVALID_CREDENTIALS = "AUTH_002"
    TOKEN_EXPIRED = "AUTH_003"
    INVALID_TOKEN = "AUTH_004"
    ACCOUNT_INACTIVE = "AUTH_005"
    ACCOUNT_LOCKED = "AUTH_006"
    
    # Authorization Errors (2xxx)
    PERMISSION_DENIED = "AUTH_201"
    INSUFFICIENT_PRIVILEGES = "AUTH_202"
    SUBSCRIPTION_REQUIRED = "AUTH_203"
    
    # Validation Errors (3xxx)
    VALIDATION_ERROR = "VAL_301"
    INVALID_INPUT = "VAL_302"
    MISSING_REQUIRED_FIELD = "VAL_303"
    INVALID_FORMAT = "VAL_304"
    
    # Resource Errors (4xxx)
    RESOURCE_NOT_FOUND = "RES_401"
    RESOURCE_EXISTS = "RES_402"
    RESOURCE_CONFLICT = "RES_403"
    
    # Rate Limiting Errors (5xxx)
    RATE_LIMIT_EXCEEDED = "RATE_501"
    TOO_MANY_REQUESTS = "RATE_502"
    
    # Service Errors (6xxx)
    SERVICE_UNAVAILABLE = "SVC_601"
    EXTERNAL_SERVICE_ERROR = "SVC_602"
    DATABASE_ERROR = "SVC_603"
    
    # File Operation Errors (7xxx)
    FILE_TOO_LARGE = "FILE_701"
    INVALID_FILE_TYPE = "FILE_702"
    FILE_UPLOAD_FAILED = "FILE_703"
    
    # General Errors (9xxx)
    INTERNAL_SERVER_ERROR = "GEN_901"
    UNKNOWN_ERROR = "GEN_902"


class ErrorCategory(str, Enum):
    """Categories of errors for grouping and reporting."""
    
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    VALIDATION = "validation"
    RESOURCE = "resource"
    RATE_LIMIT = "rate_limit"
    SERVICE = "service"
    FILE = "file"
    GENERAL = "general"


ERROR_CODE_MESSAGES: Dict[ErrorCode, str] = {
    # Authentication
    ErrorCode.AUTHENTICATION_FAILED: "Authentication failed",
    ErrorCode.INVALID_CREDENTIALS: "Invalid email or password",
    ErrorCode.TOKEN_EXPIRED: "Authentication token has expired",
    ErrorCode.INVALID_TOKEN: "Invalid authentication token",
    ErrorCode.ACCOUNT_INACTIVE: "Account is inactive",
    ErrorCode.ACCOUNT_LOCKED: "Account has been locked",
    
    # Authorization
    ErrorCode.PERMISSION_DENIED: "Permission denied",
    ErrorCode.INSUFFICIENT_PRIVILEGES: "Insufficient privileges for this operation",
    ErrorCode.SUBSCRIPTION_REQUIRED: "Active subscription required",
    
    # Validation
    ErrorCode.VALIDATION_ERROR: "Validation error occurred",
    ErrorCode.INVALID_INPUT: "Invalid input data",
    ErrorCode.MISSING_REQUIRED_FIELD: "Required field is missing",
    ErrorCode.INVALID_FORMAT: "Invalid data format",
    
    # Resource
    ErrorCode.RESOURCE_NOT_FOUND: "Requested resource not found",
    ErrorCode.RESOURCE_EXISTS: "Resource already exists",
    ErrorCode.RESOURCE_CONFLICT: "Resource conflict",
    
    # Rate Limiting
    ErrorCode.RATE_LIMIT_EXCEEDED: "Rate limit exceeded",
    ErrorCode.TOO_MANY_REQUESTS: "Too many requests",
    
    # Service
    ErrorCode.SERVICE_UNAVAILABLE: "Service is currently unavailable",
    ErrorCode.EXTERNAL_SERVICE_ERROR: "External service error",
    ErrorCode.DATABASE_ERROR: "Database operation failed",
    
    # File Operations
    ErrorCode.FILE_TOO_LARGE: "File size exceeds maximum limit",
    ErrorCode.INVALID_FILE_TYPE: "Invalid file type",
    ErrorCode.FILE_UPLOAD_FAILED: "File upload failed",
    
    # General
    ErrorCode.INTERNAL_SERVER_ERROR: "Internal server error",
    ErrorCode.UNKNOWN_ERROR: "An unknown error occurred"
}


def get_error_message(code: ErrorCode, default: Optional[str] = None) -> str:
    """Get the standard error message for an error code.
    
    Args:
        code: The error code
        default: Default message if code not found
        
    Returns:
        The standard error message for the code
    """
    return ERROR_CODE_MESSAGES.get(code, default or "An error occurred") 