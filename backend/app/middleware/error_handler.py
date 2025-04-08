from typing import Any, Callable, Dict, Optional, Type
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp, Message, Receive, Scope, Send
from app.core.exceptions import (
    AppException,
    AuthenticationException,
    ValidationException,
    NotFoundException,
    RateLimitException,
    AuthorizationError,
    AuthenticationError,
    ServiceError
)
from fastapi.exceptions import RequestValidationError, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from redis import RedisError
from app.core.logging import logger
import traceback
import json
import time
from datetime import datetime

# Custom error response structure
def error_response(
    status_code: int,
    error_type: str,
    message: str,
    details: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None,
    code: Optional[str] = None
) -> Dict[str, Any]:
    """Create a consistent error response structure."""
    response = {
        "error": {
            "status_code": status_code,
            "type": error_type,
            "message": message,
        }
    }
    
    if code:
        response["error"]["code"] = code
    
    if details:
        response["error"]["details"] = details
    
    if request_id:
        response["request_id"] = request_id
        
    return response

class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Enhanced error handler middleware with consistent error responses."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Any]
    ) -> Response:
        """Handle errors in request processing with improved logging and consistent responses."""
        # Generate a unique request ID if not already present
        request_id = request.headers.get("X-Request-ID", f"{int(time.time() * 1000)}")
        start_time = time.time()
        
        # Attach request ID to the request state for later use
        request.state.request_id = request_id
        
        # Log basic request information
        path = request.url.path
        method = request.method
        
        try:
            # Process the request
            response = await call_next(request)
            
            # Calculate request duration
            duration_ms = round((time.time() - start_time) * 1000, 2)
            
            # Add request ID to response headers if not already set
            if "X-Request-ID" not in response.headers:
                response.headers["X-Request-ID"] = request_id
                
            return response
            
        except AppException as e:
            # Handle generic app exceptions
            logger.error(
                f"Application error: {str(e)}",
                extra={
                    "request_id": request_id,
                    "path": path,
                    "method": method,
                    "status_code": e.status_code,
                    "error_code": getattr(e, "code", None),
                    "details": getattr(e, "details", {})
                }
            )
            
            return JSONResponse(
                status_code=e.status_code,
                content=error_response(
                    status_code=e.status_code,
                    error_type="application_error",
                    message=str(e),
                    details=getattr(e, "details", {}),
                    request_id=request_id,
                    code=getattr(e, "code", None)
                ),
                headers={"X-Request-ID": request_id}
            )
            
        except (AuthenticationException, AuthenticationError) as e:
            # Handle authentication errors
            logger.warning(
                f"Authentication error: {str(e)}",
                extra={
                    "request_id": request_id,
                    "path": path,
                    "method": method
                }
            )
            
            return JSONResponse(
                status_code=401,
                content=error_response(
                    status_code=401,
                    error_type="authentication_error",
                    message=str(e),
                    request_id=request_id,
                    code="AUTHENTICATION_FAILED"
                ),
                headers={"X-Request-ID": request_id}
            )
            
        except (ValidationException, RequestValidationError) as e:
            # Handle validation errors
            if isinstance(e, RequestValidationError):
                details = e.errors()
                error_msg = "Validation error"
            else:
                details = getattr(e, "details", {})
                error_msg = str(e)
                
            logger.warning(
                f"Validation error: {error_msg}",
                extra={
                    "request_id": request_id,
                    "path": path,
                    "method": method,
                    "details": details
                }
            )
            
            return JSONResponse(
                status_code=422,
                content=error_response(
                    status_code=422,
                    error_type="validation_error",
                    message=error_msg,
                    details=details,
                    request_id=request_id,
                    code="VALIDATION_ERROR"
                ),
                headers={"X-Request-ID": request_id}
            )
            
        except (NotFoundException, HTTPException) as e:
            # Handle not found and other HTTP exceptions
            status_code = 404 if isinstance(e, NotFoundException) else getattr(e, "status_code", 500)
            
            logger.warning(
                f"HTTP error: {str(e)}",
                extra={
                    "request_id": request_id,
                    "path": path,
                    "method": method,
                    "status_code": status_code
                }
            )
            
            return JSONResponse(
                status_code=status_code,
                content=error_response(
                    status_code=status_code,
                    error_type="http_error",
                    message=str(e),
                    request_id=request_id,
                    code=f"HTTP_{status_code}"
                ),
                headers={"X-Request-ID": request_id}
            )
            
        except RateLimitException as e:
            # Handle rate limiting errors
            logger.warning(
                f"Rate limit exceeded: {str(e)}",
                extra={
                    "request_id": request_id,
                    "path": path,
                    "method": method
                }
            )
            
            return JSONResponse(
                status_code=429,
                content=error_response(
                    status_code=429,
                    error_type="rate_limit_error",
                    message=str(e),
                    request_id=request_id,
                    code="RATE_LIMIT_EXCEEDED"
                ),
                headers={
                    "X-Request-ID": request_id,
                    "Retry-After": "60"  # Suggest retry after 60 seconds
                }
            )
            
        except SQLAlchemyError as e:
            # Handle database errors
            error_message = "Database error occurred"
            
            logger.error(
                f"Database error: {str(e)}",
                extra={
                    "request_id": request_id,
                    "path": path,
                    "method": method,
                    "error": str(e)
                },
                exc_info=True
            )
            
            return JSONResponse(
                status_code=500,
                content=error_response(
                    status_code=500,
                    error_type="database_error",
                    message=error_message,
                    details={"error": str(e)} if not getattr(request, "is_production", False) else {},
                    request_id=request_id,
                    code="DATABASE_ERROR"
                ),
                headers={"X-Request-ID": request_id}
            )
            
        except RedisError as e:
            # Handle Redis errors
            error_message = "Cache service temporarily unavailable"
            
            logger.error(
                f"Redis error: {str(e)}",
                extra={
                    "request_id": request_id,
                    "path": path,
                    "method": method,
                    "error": str(e)
                }
            )
            
            return JSONResponse(
                status_code=503,
                content=error_response(
                    status_code=503,
                    error_type="service_unavailable",
                    message=error_message,
                    request_id=request_id,
                    code="CACHE_SERVICE_ERROR"
                ),
                headers={"X-Request-ID": request_id}
            )
            
        except Exception as e:
            # Handle all other unexpected errors
            logger.error(
                f"Unexpected error: {str(e)}",
                extra={
                    "request_id": request_id,
                    "path": path,
                    "method": method,
                    "error_type": type(e).__name__
                },
                exc_info=True
            )
            
            # Generic error message for production
            error_message = "Internal server error"
            
            # Only include detailed error info in non-production environments
            details = None
            if not getattr(request, "is_production", False):
                details = {
                    "error_type": type(e).__name__,
                    "error": str(e)
                }
            
            return JSONResponse(
                status_code=500,
                content=error_response(
                    status_code=500,
                    error_type="internal_error",
                    message=error_message,
                    details=details,
                    request_id=request_id,
                    code="INTERNAL_SERVER_ERROR"
                ),
                headers={"X-Request-ID": request_id}
            )