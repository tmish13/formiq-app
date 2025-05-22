"""Core error handling middleware."""
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
from app.core.logging import get_logger
from app.core.config import settings
import traceback
import time

logger = get_logger(__name__)

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
    response_payload = {
        "error": {
            "status_code": status_code,
            "type": error_type,
            "message": message,
        }
    }
    if code:
        response_payload["error"]["code"] = code
    if details:
        response_payload["error"]["details"] = details
    if request_id:
        response_payload["request_id"] = request_id
    return response_payload

class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Enhanced error handler middleware with consistent error responses."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Any]
    ) -> Response:
        """Handle errors in request processing with improved logging and consistent responses."""
        request_id = request.headers.get("X-Request-ID", f"{int(time.time() * 1000)}")
        request.state.request_id = request_id
        path = request.url.path
        method = request.method

        try:
            response = await call_next(request)
            if "X-Request-ID" not in response.headers:
                response.headers["X-Request-ID"] = request_id
            return response

        except AppException as e:
            logger.error(
                f"Application error: {str(e)}",
                extra={
                    "request_id": request_id, "path": path, "method": method,
                    "status_code": e.status_code, "error_code": getattr(e, "code", None),
                    "details": getattr(e, "details", {})
                }
            )
            return JSONResponse(
                status_code=e.status_code,
                content=error_response(
                    status_code=e.status_code, error_type="application_error", message=str(e),
                    details=getattr(e, "details", {}), request_id=request_id, code=getattr(e, "code", None)
                ),
                headers={"X-Request-ID": request_id}
            )

        except (AuthenticationException, AuthenticationError) as e:
            logger.warning(f"Authentication error: {str(e)}", extra={"request_id": request_id, "path": path, "method": method})
            return JSONResponse(
                status_code=401,
                content=error_response(
                    status_code=401, error_type="authentication_error", message=str(e),
                    request_id=request_id, code="AUTHENTICATION_FAILED"
                ),
                headers={"X-Request-ID": request_id}
            )

        except (ValidationException, RequestValidationError) as e:
            details = e.errors() if isinstance(e, RequestValidationError) else getattr(e, "details", {})
            error_msg = "Validation error" if isinstance(e, RequestValidationError) else str(e)
            logger.warning(f"Validation error: {error_msg}", extra={"request_id": request_id, "path": path, "method": method, "details": details})
            return JSONResponse(
                status_code=422,
                content=error_response(
                    status_code=422, error_type="validation_error", message=error_msg,
                    details=details, request_id=request_id, code="VALIDATION_ERROR"
                ),
                headers={"X-Request-ID": request_id}
            )

        except HTTPException as e: # Catch FastAPI's HTTPException
            logger.warning(f"HTTP error: {str(e.detail)}", extra={"request_id": request_id, "path": path, "method": method, "status_code": e.status_code})
            return JSONResponse(
                status_code=e.status_code,
                content=error_response(
                    status_code=e.status_code, error_type="http_error", message=str(e.detail),
                    request_id=request_id, code=f"HTTP_{e.status_code}"
                ),
                headers={"X-Request-ID": request_id, **e.headers} # Preserve original headers like Retry-After
            )

        except NotFoundException as e: # Specific custom NotFound
            logger.warning(f"Resource not found: {str(e)}", extra={"request_id": request_id, "path": path, "method": method, "status_code": 404})
            return JSONResponse(
                status_code=404,
                content=error_response(
                    status_code=404, error_type="not_found_error", message=str(e),
                    request_id=request_id, code="NOT_FOUND"
                ),
                headers={"X-Request-ID": request_id}
            )

        except RateLimitException as e: # Specific custom RateLimit
            logger.warning(f"Rate limit exceeded: {str(e)}", extra={"request_id": request_id, "path": path, "method": method})
            retry_after = getattr(e, 'retry_after', "60") # Default if not set
            if hasattr(e, "headers") and e.headers and "Retry-After" in e.headers:
                retry_after = e.headers["Retry-After"]

            return JSONResponse(
                status_code=429,
                content=error_response(
                    status_code=429, error_type="rate_limit_error", message=str(e),
                    request_id=request_id, code="RATE_LIMIT_EXCEEDED"
                ),
                headers={"X-Request-ID": request_id, "Retry-After": str(retry_after)}
            )

        except SQLAlchemyError as e:
            error_message = "Database error occurred"
            logger.error(f"Database error: {str(e)}", extra={"request_id": request_id, "path": path, "method": method, "error": str(e)}, exc_info=True)
            return JSONResponse(
                status_code=500,
                content=error_response(
                    status_code=500, error_type="database_error", message=error_message,
                    details={"error": str(e)} if settings.ENVIRONMENT != "production" else {}, # Avoid leaking details in prod
                    request_id=request_id, code="DATABASE_ERROR"
                ),
                headers={"X-Request-ID": request_id}
            )

        except RedisError as e:
            error_message = "Cache service error"
            logger.critical(f"Redis error: {str(e)}", extra={"request_id": request_id, "path": path, "method": method, "error": str(e)}, exc_info=True)
            return JSONResponse(
                status_code=503, # Service Unavailable
                content=error_response(
                    status_code=503, error_type="cache_error", message=error_message,
                    request_id=request_id, code="CACHE_ERROR"
                ),
                headers={"X-Request-ID": request_id}
            )

        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}", extra={"request_id": request_id, "path": path, "method": method, "error": str(e), "traceback": traceback.format_exc()}, exc_info=True)
            return JSONResponse(
                status_code=500,
                content=error_response(
                    status_code=500, error_type="internal_server_error",
                    message="An unexpected internal server error occurred.",
                    request_id=request_id, code="INTERNAL_SERVER_ERROR"
                ),
                headers={"X-Request-ID": request_id}
            ) 