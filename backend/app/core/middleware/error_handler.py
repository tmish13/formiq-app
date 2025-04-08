"""Error handling middleware module."""
import traceback
from typing import Callable

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.exceptions import (
    AuthenticationException,
    PermissionDeniedException,
    ValidationException,
    ResourceNotFoundException,
    ConflictException,
    RateLimitExceededException,
)
from app.core.logging import get_logger

logger = get_logger(__name__)

class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Middleware for consistent error handling across the application.
    
    This middleware catches all exceptions and converts them to appropriate HTTP responses.
    It also ensures proper logging of errors and provides different levels of detail
    based on the environment (development vs production).
    """
    
    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> JSONResponse:
        """Process the request and handle any errors that occur.
        
        Args:
            request: The incoming request
            call_next: The next middleware/route handler in the chain
            
        Returns:
            A JSON response with appropriate error details
        """
        try:
            return await call_next(request)
            
        except AuthenticationException as e:
            return self._create_error_response(
                status_code=status.HTTP_401_UNAUTHORIZED,
                error_type="authentication_error",
                detail=str(e),
                request=request,
            )
            
        except PermissionDeniedException as e:
            return self._create_error_response(
                status_code=status.HTTP_403_FORBIDDEN,
                error_type="permission_denied",
                detail=str(e),
                request=request,
            )
            
        except ValidationException as e:
            return self._create_error_response(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                error_type="validation_error",
                detail=str(e),
                request=request,
                extra_data={"fields": e.fields} if hasattr(e, "fields") else None,
            )
            
        except ResourceNotFoundException as e:
            return self._create_error_response(
                status_code=status.HTTP_404_NOT_FOUND,
                error_type="not_found",
                detail=str(e),
                request=request,
            )
            
        except ConflictException as e:
            return self._create_error_response(
                status_code=status.HTTP_409_CONFLICT,
                error_type="conflict",
                detail=str(e),
                request=request,
            )
            
        except RateLimitExceededException as e:
            return self._create_error_response(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                error_type="rate_limit_exceeded",
                detail=str(e),
                request=request,
                extra_data={"retry_after": e.retry_after} if hasattr(e, "retry_after") else None,
            )
            
        except Exception as e:
            # Log unexpected errors with full details
            logger.error(
                "Unhandled error occurred",
                extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "traceback": traceback.format_exc(),
                    "path": request.url.path,
                    "method": request.method,
                    "client_ip": request.client.host if request.client else "unknown",
                }
            )
            
            return self._create_error_response(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                error_type="internal_server_error",
                detail="An unexpected error occurred" if settings.ENVIRONMENT == "production" else str(e),
                request=request,
                include_traceback=settings.ENVIRONMENT != "production",
            )
    
    def _create_error_response(
        self,
        *,
        status_code: int,
        error_type: str,
        detail: str,
        request: Request,
        extra_data: dict = None,
        include_traceback: bool = False,
    ) -> JSONResponse:
        """Create a consistent error response.
        
        Args:
            status_code: HTTP status code
            error_type: String identifier for the type of error
            detail: Human-readable error message
            request: The request that caused the error
            extra_data: Optional additional error data
            include_traceback: Whether to include the traceback in the response
            
        Returns:
            A JSON response with error details
        """
        response_data = {
            "error": {
                "type": error_type,
                "detail": detail,
                "status_code": status_code,
                "path": request.url.path,
            }
        }
        
        if extra_data:
            response_data["error"].update(extra_data)
            
        if include_traceback:
            response_data["error"]["traceback"] = traceback.format_exc()
            
        return JSONResponse(
            status_code=status_code,
            content=response_data,
        ) 