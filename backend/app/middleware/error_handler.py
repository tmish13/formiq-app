from typing import Any, Dict
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp, Message, Receive, Scope, Send
from app.core.exceptions import AppException
from fastapi.exceptions import RequestValidationError, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from redis import RedisError
from app.core.logging import logger
import traceback
from datetime import datetime

class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Middleware for handling application errors."""
    
    async def dispatch(self, request: Request, call_next: Any) -> JSONResponse:
        """Process the request and handle any errors."""
        try:
            response = await call_next(request)
            return response
        except RequestValidationError as e:
            return await self.handle_validation_error(request, e)
        except HTTPException as e:
            return await self.handle_http_error(request, e)
        except SQLAlchemyError as e:
            return await self.handle_database_error(request, e)
        except RedisError as e:
            return await self.handle_redis_error(request, e)
        except AppException as e:
            return await self.handle_app_exception(request, e)
        except Exception as e:
            return await self.handle_unexpected_error(request, e)

    async def handle_validation_error(self, request: Request, e: RequestValidationError) -> JSONResponse:
        """Handle validation errors."""
        logger.error("validation_error", 
                    extra={
                        "path": request.url.path,
                        "method": request.method,
                        "errors": e.errors()
                    })
        return JSONResponse(
            status_code=422,
            content={
                "detail": e.errors(),
                "message": "Validation error"
            }
        )

    async def handle_http_error(self, request: Request, e: HTTPException) -> JSONResponse:
        """Handle HTTP exceptions."""
        logger.warning("http_exception",
                      extra={
                          "path": request.url.path,
                          "method": request.method,
                          "status_code": e.status_code,
                          "detail": e.detail
                      })
        return JSONResponse(
            status_code=e.status_code,
            content={"detail": e.detail}
        )

    async def handle_database_error(self, request: Request, e: SQLAlchemyError) -> JSONResponse:
        """Handle database-related exceptions."""
        logger.error("database_error",
                    extra={
                        "path": request.url.path,
                        "method": request.method,
                        "error": str(e)
                    })
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Database error occurred",
                "message": "Internal server error"
            }
        )

    async def handle_redis_error(self, request: Request, e: RedisError) -> JSONResponse:
        """Handle Redis-related exceptions."""
        logger.error("redis_error",
                    extra={
                        "path": request.url.path,
                        "method": request.method,
                        "error": str(e)
                    })
        return JSONResponse(
            status_code=503,
            content={"detail": "Service temporarily unavailable"}
        )

    async def handle_app_exception(self, request: Request, e: AppException) -> JSONResponse:
        """Handle application-specific exceptions."""
        logger.error("application_error",
                    extra={
                        "path": request.url.path,
                        "method": request.method,
                        "error_code": e.code,
                        "message": e.message
                    })
        return JSONResponse(
            status_code=e.status_code,
            content={
                "error": e.message,
                "code": e.code,
                "details": e.details
            }
        )

    async def handle_unexpected_error(self, request: Request, e: Exception) -> JSONResponse:
        """Handle unexpected exceptions."""
        logger.error("unexpected_error",
                    extra={
                        "path": request.url.path,
                        "method": request.method,
                        "error_type": type(e).__name__,
                        "error_details": str(e),
                        "traceback": traceback.format_exc(),
                        "timestamp": datetime.utcnow().isoformat()
                    })
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error",
                "error_type": type(e).__name__
            }
        ) 