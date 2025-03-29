"""Error handling middleware and utilities."""
from typing import Any, Dict, Optional, Type
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from app.core.exceptions import AppException
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
from redis import RedisError
from app.core.logging import logger
from prometheus_client import Counter

# Prometheus metrics
ERROR_COUNTER = Counter(
    'app_errors_total',
    'Total number of application errors',
    ['error_type', 'endpoint', 'method']
)

class UnifiedErrorHandler(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.error_handlers: Dict[Type[Exception], Any] = {
            AppException: self._handle_app_exception,
            SQLAlchemyError: self._handle_database_error,
            RedisError: self._handle_redis_error,
            RequestValidationError: self._handle_validation_error,
            HTTPException: self._handle_http_exception,
        }

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        try:
            return await call_next(request)
        except Exception as e:
            handler = self.error_handlers.get(type(e), self._handle_unexpected_error)
            return await handler(request, e)

    async def _handle_app_exception(self, request: Request, e: AppException) -> JSONResponse:
        """Handle application-specific exceptions."""
        ERROR_COUNTER.labels(
            error_type='app_exception',
            endpoint=request.url.path,
            method=request.method
        ).inc()
        
        logger.error(
            "application_error",
            extra={
                "path": request.url.path,
                "method": request.method,
                "error_code": e.code,
                "details": e.details
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

    async def _handle_database_error(self, request: Request, e: SQLAlchemyError) -> JSONResponse:
        """Handle database-related exceptions."""
        ERROR_COUNTER.labels(
            error_type='database_error',
            endpoint=request.url.path,
            method=request.method
        ).inc()
        
        logger.error(
            "database_error",
            extra={
                "path": request.url.path,
                "method": request.method,
                "error": str(e)
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

    async def _handle_redis_error(self, request: Request, e: RedisError) -> JSONResponse:
        """Handle Redis-related exceptions."""
        ERROR_COUNTER.labels(
            error_type='redis_error',
            endpoint=request.url.path,
            method=request.method
        ).inc()
        
        logger.error(
            "redis_error",
            extra={
                "path": request.url.path,
                "method": request.method,
                "error": str(e)
            }
        )
        
        return JSONResponse(
            status_code=503,
            content={
                "error": "Service temporarily unavailable",
                "code": "REDIS_ERROR",
                "details": str(e)
            }
        )

    async def _handle_validation_error(self, request: Request, e: RequestValidationError) -> JSONResponse:
        """Handle request validation errors."""
        ERROR_COUNTER.labels(
            error_type='validation_error',
            endpoint=request.url.path,
            method=request.method
        ).inc()
        
        logger.error(
            "validation_error",
            extra={
                "path": request.url.path,
                "method": request.method,
                "errors": e.errors()
            }
        )
        
        return JSONResponse(
            status_code=422,
            content={
                "error": "Validation error",
                "code": "VALIDATION_ERROR",
                "details": e.errors()
            }
        )

    async def _handle_http_exception(self, request: Request, e: HTTPException) -> JSONResponse:
        """Handle HTTP exceptions."""
        ERROR_COUNTER.labels(
            error_type='http_error',
            endpoint=request.url.path,
            method=request.method
        ).inc()
        
        logger.error(
            "http_error",
            extra={
                "path": request.url.path,
                "method": request.method,
                "status_code": e.status_code,
                "detail": e.detail
            }
        )
        
        return JSONResponse(
            status_code=e.status_code,
            content={
                "error": str(e.detail),
                "code": f"HTTP_{e.status_code}",
                "details": e.detail
            }
        )

    async def _handle_unexpected_error(self, request: Request, e: Exception) -> JSONResponse:
        """Handle unexpected exceptions."""
        ERROR_COUNTER.labels(
            error_type='unexpected_error',
            endpoint=request.url.path,
            method=request.method
        ).inc()
        
        logger.error(
            "unexpected_error",
            extra={
                "path": request.url.path,
                "method": request.method,
                "error": str(e),
                "error_type": type(e).__name__
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