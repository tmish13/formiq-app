"""Request validation middleware."""
from typing import Callable, List
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.exceptions import ValidationError
from app.core.logging import get_logger

logger = get_logger(__name__)

class RequestValidator(BaseHTTPMiddleware):
    """Middleware for validating incoming requests."""

    def __init__(
        self,
        app,
        max_content_length: int = 10 * 1024 * 1024,  # 10MB default
        allowed_content_types: List[str] = None
    ):
        super().__init__(app)
        self.max_content_length = max_content_length
        self.allowed_content_types = allowed_content_types or [
            "application/json",
            "multipart/form-data",
            "application/x-www-form-urlencoded"
        ]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            # Check content length
            content_length = request.headers.get("content-length")
            if content_length and int(content_length) > self.max_content_length:
                logger.warning(f"Request content length {content_length} exceeds maximum {self.max_content_length}")
                raise ValidationError("Request body too large")

            # Check content type for non-GET requests
            if request.method != "GET":
                content_type = request.headers.get("content-type", "").lower()
                if not any(allowed in content_type for allowed in self.allowed_content_types):
                    logger.warning(f"Invalid content type: {content_type}")
                    raise ValidationError("Invalid content type")

            response = await call_next(request)
            return response

        except ValidationError as e:
            logger.warning(f"Request validation error: {str(e)}")
            return Response(
                content={"detail": str(e)},
                status_code=400,
                media_type="application/json"
            )

        except Exception as e:
            logger.error(f"Unexpected error in request validation: {str(e)}")
            return Response(
                content={"detail": "Internal server error"},
                status_code=500,
                media_type="application/json"
            ) 