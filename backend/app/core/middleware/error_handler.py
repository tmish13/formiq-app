"""Global error handler middleware for FastAPI application."""
import logging
import traceback
from typing import Callable, Dict, Any, Optional

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.core.exceptions import BaseAPIException
from app.core.error_utils import (
    handle_validation_error,
    handle_database_error,
    convert_http_exception
)
from app.core.monitoring import track_error

logger = logging.getLogger(__name__)

class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Global error handler middleware that catches and formats all exceptions."""
    
    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        """Process the request and handle any errors that occur."""
        try:
            return await call_next(request)
            
        except BaseAPIException as exc:
            # Handle our custom exceptions
            track_error(
                error_type=type(exc).__name__,
                error_code=exc.error_code,
                is_operational=True
            )
            
            if exc.is_critical:
                logger.critical(
                    f"Critical error occurred: {exc.message}",
                    extra={
                        "error_code": exc.error_code,
                        "details": exc.details,
                        "path": request.url.path
                    }
                )
            
            headers = exc.headers or {}
            if exc.retry_after:
                headers["Retry-After"] = str(exc.retry_after)
                
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "error": {
                        "type": type(exc).__name__,
                        "code": exc.error_code,
                        "message": exc.message,
                        "details": exc.details
                    }
                },
                headers=headers
            )
            
        except PydanticValidationError as exc:
            # Convert Pydantic validation errors
            api_error = handle_validation_error(exc)
            track_error(
                error_type="ValidationError",
                error_code="VALIDATION_ERROR",
                is_operational=True
            )
            return JSONResponse(
                status_code=api_error.status_code,
                content={
                    "error": {
                        "type": "ValidationError",
                        "code": "VALIDATION_ERROR",
                        "message": api_error.message,
                        "details": api_error.details
                    }
                }
            )
            
        except SQLAlchemyError as exc:
            # Convert database errors
            api_error = handle_database_error(exc, request.url.path)
            track_error(
                error_type="DatabaseError",
                error_code=api_error.error_code,
                is_operational=True
            )
            return JSONResponse(
                status_code=api_error.status_code,
                content={
                    "error": {
                        "type": "DatabaseError",
                        "code": api_error.error_code,
                        "message": api_error.message,
                        "details": api_error.details
                    }
                }
            )
            
        except Exception as exc:
            # Handle unexpected errors
            error_id = track_error(
                error_type=type(exc).__name__,
                error_code="INTERNAL_SERVER_ERROR",
                is_operational=False
            )
            
            # Log detailed error information
            logger.error(
                f"Unexpected error occurred: {str(exc)}",
                extra={
                    "error_id": error_id,
                    "path": request.url.path,
                    "method": request.method,
                    "client_host": request.client.host,
                    "traceback": traceback.format_exc()
                }
            )
            
            return JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "type": "InternalServerError",
                        "code": "INTERNAL_SERVER_ERROR",
                        "message": "An unexpected error occurred",
                        "error_id": error_id
                    }
                }
            ) 