"""Utility functions for error handling."""
from typing import Any, Dict, List, Optional, Type, TypeVar
from fastapi import HTTPException
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.exc import SQLAlchemyError
from app.core.exceptions import (
    ValidationError,
    DatabaseError,
    BusinessError,
    ResourceNotFoundError
)

T = TypeVar('T')

def handle_validation_error(error: PydanticValidationError) -> ValidationError:
    """Convert Pydantic validation error to our custom ValidationError."""
    errors = []
    for err in error.errors():
        errors.append({
            "field": ".".join(str(x) for x in err["loc"]),
            "message": err["msg"],
            "code": err["type"]
        })
    return ValidationError(message="Validation error", details=errors)

def handle_database_error(error: SQLAlchemyError, operation: str) -> DatabaseError:
    """Convert SQLAlchemy error to our custom DatabaseError."""
    error_message = str(error)
    error_type = type(error).__name__
    
    # Map common database errors to user-friendly messages
    if "duplicate key" in error_message.lower():
        return DatabaseError(
            message="A record with this data already exists",
            error_code="DB_DUPLICATE_KEY",
            details={"operation": operation}
        )
    elif "foreign key" in error_message.lower():
        return DatabaseError(
            message="Referenced record does not exist",
            error_code="DB_FOREIGN_KEY_ERROR",
            details={"operation": operation}
        )
    
    return DatabaseError(
        message=f"Database error during {operation}",
        error_code="DB_ERROR",
        details={"error_type": error_type}
    )

def validate_resource_exists(
    resource: Optional[T],
    resource_type: str,
    resource_id: Any
) -> T:
    """Validate that a resource exists and return it."""
    if not resource:
        raise ResourceNotFoundError(
            message=f"{resource_type} not found",
            details={"id": str(resource_id)}
        )
    return resource

def validate_business_condition(
    condition: bool,
    message: str,
    error_code: str,
    details: Optional[Dict[str, Any]] = None
) -> None:
    """Validate a business rule condition."""
    if not condition:
        raise BusinessError(
            message=message,
            error_code=error_code,
            details=details
        )

def convert_http_exception(exc: HTTPException) -> BusinessError:
    """Convert FastAPI HTTPException to our custom BusinessError."""
    return BusinessError(
        message=exc.detail,
        status_code=exc.status_code,
        error_code="HTTP_ERROR",
        headers=exc.headers
    ) 