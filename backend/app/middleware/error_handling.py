"""Unified error handling middleware."""
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.exceptions import (
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    NotFoundException,
    ServiceError
)
from app.core.logging import get_logger

logger = get_logger(__name__)

class UnifiedErrorHandler(BaseHTTPMiddleware):
    """Middleware for unified error handling across the application."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            response = await call_next(request)
            return response

        except ValidationError as e:
            logger.warning(f"Validation error: {str(e)}")
            return Response(
                content={"detail": str(e)},
                status_code=400,
                media_type="application/json"
            )

        except AuthenticationError as e:
            logger.warning(f"Authentication error: {str(e)}")
            return Response(
                content={"detail": str(e)},
                status_code=401,
                media_type="application/json"
            )

        except AuthorizationError as e:
            logger.warning(f"Authorization error: {str(e)}")
            return Response(
                content={"detail": str(e)},
                status_code=403,
                media_type="application/json"
            )

        except NotFoundException as e:
            logger.warning(f"Not found error: {str(e)}")
            return Response(
                content={"detail": str(e)},
                status_code=404,
                media_type="application/json"
            )

        except ServiceError as e:
            logger.error(f"Service error: {str(e)}")
            return Response(
                content={"detail": str(e)},
                status_code=500,
                media_type="application/json"
            )

        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            return Response(
                content={"detail": "Internal server error"},
                status_code=500,
                media_type="application/json"
            ) 