import time
from typing import Any
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from app.core.logger import logger

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Any
    ) -> Response:
        # Start timing the request
        start_time = time.time()
        
        # Log request details
        logger.info(
            "request_started",
            method=request.method,
            url=str(request.url),
            client_ip=request.client.host,
            user_agent=request.headers.get("user-agent")
        )
        
        try:
            response = await call_next(request)
            
            # Calculate request duration
            duration = time.time() - start_time
            
            # Log response details
            logger.info(
                "request_completed",
                method=request.method,
                url=str(request.url),
                status_code=response.status_code,
                duration=f"{duration:.3f}s"
            )
            
            return response
            
        except Exception as e:
            # Log error details
            logger.error(
                "request_failed",
                method=request.method,
                url=str(request.url),
                error=str(e),
                duration=f"{time.time() - start_time:.3f}s"
            )
            raise 