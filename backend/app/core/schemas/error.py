"""Error response schemas."""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class ErrorDetail(BaseModel):
    """Detailed error information."""
    
    field: Optional[str] = Field(None, description="Field that caused the error")
    code: str = Field(..., description="Error code for this specific error")
    message: str = Field(..., description="Detailed error message")


class ErrorResponse(BaseModel):
    """Standardized error response format."""
    
    status_code: int = Field(..., description="HTTP status code")
    error_code: str = Field(..., description="Application-specific error code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[List[ErrorDetail]] = Field(None, description="List of detailed errors")
    request_id: Optional[str] = Field(None, description="Request ID for tracking")
    timestamp: str = Field(..., description="ISO formatted timestamp of the error")
    path: Optional[str] = Field(None, description="Request path where the error occurred")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status_code": 400,
                "error_code": "VALIDATION_ERROR",
                "message": "Invalid input data",
                "details": [
                    {
                        "field": "email",
                        "code": "invalid_email",
                        "message": "Invalid email format"
                    }
                ],
                "request_id": "req-123-456",
                "timestamp": "2024-03-14T12:00:00Z",
                "path": "/api/v1/users"
            }
        }
    ) 