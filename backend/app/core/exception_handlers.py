"""
FastAPI Exception Handlers for FormIQ Backend

Provides consistent error response formatting across all API endpoints.
Maps FormIQ exceptions to standardized JSON responses.
"""

from typing import Any, Dict, Union
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError, HTTPException
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import FormIQException
from app.core.logging import get_logger

logger = get_logger(__name__)

def setup_exception_handlers(app: FastAPI) -> None:
    """
    Register all exception handlers for the FastAPI application.
    
    This should be called during application initialization.
    """
    
    @app.exception_handler(FormIQException)
    async def formiq_exception_handler(request: Request, exc: FormIQException) -> JSONResponse:
        """Handle all FormIQ custom exceptions with consistent formatting."""
        logger.error(
            f"FormIQ exception: {exc.message}",
            extra={
                "path": request.url.path,
                "method": request.method,
                "error_code": exc.error_code,
                "status_code": exc.status_code,
                "details": exc.details
            }
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_dict()["error"]
        )
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        """Handle FastAPI HTTPExceptions with consistent formatting."""
        logger.warning(
            f"HTTP exception: {exc.detail}",
            extra={
                "path": request.url.path,
                "method": request.method,
                "status_code": exc.status_code
            }
        )
        
        # If detail is already a dict (from our exceptions), use it directly
        if isinstance(exc.detail, dict):
            content = exc.detail
        else:
            content = {
                "code": "HTTP_ERROR",
                "message": str(exc.detail),
                "status": exc.status_code
            }
        
        # Forward the exception's headers. Without this every header an endpoint
        # attaches to an HTTPException was dropped on the floor: Retry-After on a
        # 503 (upload backpressure, G-36), WWW-Authenticate on a 401.
        return JSONResponse(
            status_code=exc.status_code,
            content=content,
            headers=getattr(exc, "headers", None) or None,
        )
    
    @app.exception_handler(StarletteHTTPException)
    async def starlette_http_exception_handler(
        request: Request, 
        exc: StarletteHTTPException
    ) -> JSONResponse:
        """Handle Starlette HTTP exceptions (fallback for lower-level errors)."""
        logger.warning(
            f"Starlette HTTP exception: {exc.detail}",
            extra={
                "path": request.url.path,
                "method": request.method,
                "status_code": exc.status_code
            }
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": "HTTP_ERROR",
                "message": str(exc.detail,
            headers=getattr(exc, "headers", None) or None,
        ),
                "status": exc.status_code
            }
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, 
        exc: RequestValidationError
    ) -> JSONResponse:
        """Handle Pydantic validation errors from request parsing."""
        logger.warning(
            f"Request validation failed: {exc.errors()}",
            extra={
                "path": request.url.path,
                "method": request.method,
                "validation_errors": exc.errors()
            }
        )
        
        # Extract field-specific errors for better API responses
        field_errors = {}
        for error in exc.errors():
            field_path = " -> ".join(str(loc) for loc in error["loc"][1:])  # Skip 'body'
            if field_path in field_errors:
                field_errors[field_path].append(error["msg"])
            else:
                field_errors[field_path] = [error["msg"]]
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "status": status.HTTP_422_UNPROCESSABLE_ENTITY,
                "details": {
                    "field_errors": field_errors
                }
            }
        )
    
    @app.exception_handler(IntegrityError)
    async def database_integrity_exception_handler(
        request: Request, 
        exc: IntegrityError
    ) -> JSONResponse:
        """Handle database integrity constraint violations."""
        logger.error(
            f"Database integrity error: {exc.orig}",
            extra={
                "path": request.url.path,
                "method": request.method,
                "db_error": str(exc.orig)
            }
        )
        
        # Try to extract meaningful constraint information
        error_detail = str(exc.orig)
        if "UNIQUE constraint failed" in error_detail:
            message = "Resource already exists"
            code = "RESOURCE_CONFLICT"
            status_code = status.HTTP_409_CONFLICT
        elif "FOREIGN KEY constraint failed" in error_detail:
            message = "Referenced resource not found"
            code = "REFERENCE_ERROR"
            status_code = status.HTTP_400_BAD_REQUEST
        else:
            message = "Database constraint violation"
            code = "DATABASE_ERROR"
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        
        return JSONResponse(
            status_code=status_code,
            content={
                "code": code,
                "message": message,
                "status": status_code,
                "details": {
                    "constraint_type": "integrity",
                    "database_error": error_detail
                }
            }
        )
    
    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """
        Handle any unexpected exceptions that aren't caught by other handlers.
        
        This is our safety net to ensure all errors return consistent JSON responses
        rather than HTML error pages.
        """
        logger.error(
            f"Unhandled exception: {exc}",
            extra={
                "path": request.url.path,
                "method": request.method,
                "exception_type": type(exc).__name__,
                "exception_str": str(exc)
            },
            exc_info=True  # Include full stack trace in logs
        )
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "status": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "details": {
                    "error_type": type(exc).__name__,
                    # In production, don't expose internal error details
                    "debug_message": str(exc) if app.debug else None
                }
            }
        )

def create_error_response(
    code: str,
    message: str,
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    details: Dict[str, Any] = None
) -> JSONResponse:
    """
    Create a standardized error response.
    
    Use this utility function in endpoints where you need to return
    an error response directly without raising an exception.
    """
    content = {
        "code": code,
        "message": message,
        "status": status_code
    }
    if details:
        content["details"] = details
    
    return JSONResponse(
        status_code=status_code,
        content=content
    )