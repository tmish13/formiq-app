from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from app.core.logger import logger
from typing import Any
import json

class RequestValidationMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Any
    ) -> Any:
        # Skip validation for certain paths
        if request.url.path in ["/api/v1/health", "/api/v1/metrics"]:
            return await call_next(request)
            
        # Validate content type
        content_type = request.headers.get("content-type", "")
        if request.method in ["POST", "PUT", "PATCH"] and not content_type.startswith("application/json"):
            logger.warning(
                "invalid_content_type",
                method=request.method,
                content_type=content_type,
                path=request.url.path
            )
            raise HTTPException(
                status_code=415,
                detail="Unsupported media type. Use application/json"
            )
            
        # Validate request size
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > 10 * 1024 * 1024:  # 10MB limit
            logger.warning(
                "request_too_large",
                content_length=content_length,
                path=request.url.path
            )
            raise HTTPException(
                status_code=413,
                detail="Request too large. Maximum size is 10MB"
            )
            
        # Validate JSON body if present
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                if body:
                    json.loads(body)
            except json.JSONDecodeError:
                logger.warning(
                    "invalid_json",
                    method=request.method,
                    path=request.url.path
                )
                raise HTTPException(
                    status_code=400,
                    detail="Invalid JSON in request body"
                )
                
        return await call_next(request)

# Create middleware instance
validate_request_middleware = RequestValidationMiddleware 