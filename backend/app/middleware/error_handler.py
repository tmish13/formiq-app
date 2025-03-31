from typing import Any, Callable
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp, Message, Receive, Scope, Send
from app.core.exceptions import (
    AuthenticationException,
    ValidationException,
    NotFoundException,
    RateLimitException
)
from fastapi.exceptions import RequestValidationError, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from redis import RedisError
from app.core.logging import logger
import traceback
from datetime import datetime

class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Error handler middleware."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Any]
    ) -> Response:
        """Handle errors in request processing."""
        try:
            response = await call_next(request)
            return response
        except AuthenticationException as e:
            return JSONResponse(
                status_code=401,
                content={"detail": str(e)}
            )
        except ValidationException as e:
            return JSONResponse(
                status_code=400,
                content={"detail": str(e)}
            )
        except NotFoundException as e:
            return JSONResponse(
                status_code=404,
                content={"detail": str(e)}
            )
        except RateLimitException as e:
            return JSONResponse(
                status_code=429,
                content={"detail": str(e)}
            )
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error"}
            )