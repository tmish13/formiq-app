"""Common schema models used across the application."""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class Message(BaseModel):
    """Basic message response model."""
    message: str = Field(..., description="Response message")


class ErrorDetail(BaseModel):
    """Detailed error information."""
    loc: List[str] = Field(default_factory=list, description="Error location")
    msg: str = Field(..., description="Error message")
    type: str = Field(..., description="Error type")


class ErrorResponse(BaseModel):
    """Standard error response model."""
    detail: List[ErrorDetail] = Field(..., description="List of error details")
    status_code: int = Field(..., description="HTTP status code")
    error: str = Field(..., description="Error type")


class ValidationError(BaseModel):
    """Validation error response model."""
    detail: List[ErrorDetail]


class PaginationParams(BaseModel):
    """Common pagination parameters."""
    page: int = Field(default=1, ge=1, description="Page number")
    per_page: int = Field(default=10, ge=1, le=100, description="Items per page")
    

class PaginatedResponse(BaseModel):
    """Base model for paginated responses."""
    items: List[Any]
    total: int
    page: int
    per_page: int
    pages: int
    has_next: bool
    has_prev: bool 