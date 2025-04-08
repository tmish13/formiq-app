"""Request logging middleware module."""
import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging request and response details.
    
    This middleware logs information about incoming requests and their corresponding
    responses, including timing information, status codes, and other relevant metadata.
    The level of detail can be configured based on the environment.
    """
    
    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        """Process and log the request/response cycle.
        
        Args:
            request: The incoming request
            call_next: The next middleware/route handler in the chain
            
        Returns:
            The response from the next handler
        """
        # Start timing
        start_time = time.time()
        
        # Extract request details before processing
        request_details = await self._get_request_details(request)
        
        # Process request
        response = await call_next(request)
        
        # Calculate timing
        process_time = (time.time() - start_time) * 1000
        
        # Log request/response details
        self._log_request_response(
            request_details=request_details,
            response=response,
            process_time=process_time,
        )
        
        return response
    
    async def _get_request_details(self, request: Request) -> dict:
        """Extract relevant details from the request.
        
        Args:
            request: The incoming request
            
        Returns:
            Dictionary containing request metadata
        """
        details = {
            "method": request.method,
            "path": request.url.path,
            "client_ip": request.client.host if request.client else "unknown",
            "user_agent": request.headers.get("user-agent", "unknown"),
        }
        
        # Add query params if present
        if request.query_params:
            details["query_params"] = dict(request.query_params)
            
        # In development, optionally log request body
        if settings.ENVIRONMENT == "development":
            try:
                body = await request.body()
                if body:
                    details["body"] = body.decode()
            except Exception:
                # Ignore body parsing errors
                pass
                
        return details
    
    def _log_request_response(
        self,
        *,
        request_details: dict,
        response: Response,
        process_time: float,
    ) -> None:
        """Log the request and response details.
        
        Args:
            request_details: Dictionary of request metadata
            response: The response object
            process_time: Time taken to process the request in milliseconds
        """
        log_data = {
            **request_details,
            "status_code": response.status_code,
            "process_time_ms": round(process_time, 2),
        }
        
        # Determine log level based on status code
        if response.status_code >= 500:
            logger.error("Request failed", extra=log_data)
        elif response.status_code >= 400:
            logger.warning("Request error", extra=log_data)
        else:
            logger.info("Request processed", extra=log_data)
            
        # In development, log response headers
        if settings.ENVIRONMENT == "development":
            log_data["response_headers"] = dict(response.headers)
            logger.debug("Response details", extra=log_data) 