from typing import Any, Dict, Optional
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from app.core.exceptions import AppException
from app.core.logging import get_logger
from fastapi.exceptions import RequestValidationError, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from redis.exc import RedisError
from app.core.exceptions import (
    DatabaseError,
    AuthenticationError,
    ValidationError,
    NotFoundError,
    RateLimitError,
)

logger = get_logger(__name__)

class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.logger = get_logger("error_handler")

    async def dispatch(
        self, request: Request, call_next: Any
    ) -> Response:
        try:
            response = await call_next(request)
            return response
        except RequestValidationError as e:
            self.logger.error("validation_error", 
                            path=request.url.path,
                            method=request.method,
                            errors=e.errors())
            return Response(
                status_code=422,
                content={
                    "detail": e.errors(),
                    "message": "Validation error"
                }
            )
        except HTTPException as e:
            self.logger.error("http_error",
                        path=request.url.path,
                        method=request.method,
                        status_code=e.status_code,
                        detail=e.detail)
            return Response(
                status_code=e.status_code,
                content={"detail": e.detail}
            )
        except SQLAlchemyError as e:
            self.logger.error("database_error",
                        path=request.url.path,
                        method=request.method,
                        error=str(e))
            return Response(
                status_code=500,
                content={
                    "detail": "Database error occurred",
                    "message": "Internal server error"
                }
            )
        except RedisError as e:
            self.logger.error("redis_error",
                        path=request.url.path,
                        method=request.method,
                        error=str(e))
            return Response(
                status_code=500,
                content={
                    "detail": "Cache service error",
                    "message": "Internal server error"
                }
            )
        except Exception as e:
            self.logger.error("unhandled_error",
                        path=request.url.path,
                        method=request.method,
                        error=str(e),
                        exc_info=True)
            return Response(
                status_code=500,
                content={
                    "detail": "An unexpected error occurred",
                    "message": "Internal server error"
                }
            )

    def _handle_app_exception(self, exc: AppException) -> JSONResponse:
        """Handle application-specific exceptions."""
        error_response = {
            "error": {
                "code": exc.error_code,
                "message": exc.detail,
                "details": exc.extra
            }
        }
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response
        )

    def _handle_unexpected_exception(self, exc: Exception) -> JSONResponse:
        """Handle unexpected exceptions."""
        self.logger.exception(
            "unexpected_error",
            error=str(exc),
            error_type=type(exc).__name__
        )
        error_response = {
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred",
                "details": {}
            }
        }
        return JSONResponse(
            status_code=500,
            content=error_response
        )

async def error_handler_middleware(request: Request, call_next):
    """Global error handling middleware."""
    try:
        return await call_next(request)
    except AppException as e:
        logger.error(f"Application error: {str(e)}", extra={"path": request.url.path})
        return JSONResponse(
            status_code=e.status_code,
            content={
                "error": e.message,
                "code": e.code,
                "details": e.details
            }
        )
    except SQLAlchemyError as e:
        logger.error(f"Database error: {str(e)}", extra={"path": request.url.path})
        return JSONResponse(
            status_code=500,
            content={
                "error": "Database error occurred",
                "code": "DATABASE_ERROR",
                "details": str(e)
            }
        )
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", extra={"path": request.url.path})
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "code": "INTERNAL_ERROR",
                "details": str(e)
            }
        )

class ErrorHandlerMiddleware:
    """Middleware for handling application errors."""
    
    async def __call__(self, request: Request, call_next):
        """Process the request and handle any errors."""
        try:
            response = await call_next(request)
            return response
        except AppException as e:
            return await self.handle_app_exception(request, e)
        except SQLAlchemyError as e:
            return await self.handle_database_error(request, e)
        except Exception as e:
            return await self.handle_unexpected_error(request, e)

    async def handle_app_exception(self, request: Request, e: AppException):
        """Handle application-specific exceptions."""
        logger.error(
            f"Application error: {str(e)}",
            extra={
                "path": request.url.path,
                "method": request.method,
                "error_code": e.code
            }
        )
        return JSONResponse(
            status_code=e.status_code,
            content={
                "error": e.message,
                "code": e.code,
                "details": e.details
            }
        )

    async def handle_database_error(self, request: Request, e: SQLAlchemyError):
        """Handle database-related exceptions."""
        logger.error(
            f"Database error: {str(e)}",
            extra={
                "path": request.url.path,
                "method": request.method
            }
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": "Database error occurred",
                "code": "DATABASE_ERROR",
                "details": str(e)
            }
        )

    async def handle_unexpected_error(self, request: Request, e: Exception):
        """Handle unexpected exceptions."""
        logger.error(
            f"Unexpected error: {str(e)}",
            extra={
                "path": request.url.path,
                "method": request.method
            }
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "code": "INTERNAL_ERROR",
                "details": str(e)
            }
        ) 