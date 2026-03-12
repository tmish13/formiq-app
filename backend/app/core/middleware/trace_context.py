"""Trace context middleware for correlation ID injection."""

import logging
from typing import Callable
import uuid

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.tracing import get_trace_context, is_tracing_enabled

logger = logging.getLogger(__name__)


class TraceContextMiddleware(BaseHTTPMiddleware):
    """Middleware to inject trace context and correlation IDs into requests."""
    
    def __init__(self, app, generate_correlation_id: bool = True):
        """
        Initialize trace context middleware.
        
        Args:
            app: FastAPI application instance
            generate_correlation_id: Generate correlation ID if tracing is disabled
        """
        super().__init__(app)
        self.generate_correlation_id = generate_correlation_id
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and inject trace context."""
        
        # Extract or generate correlation information
        correlation_id = self._get_or_create_correlation_id(request)
        trace_context = {}
        
        # Get OpenTelemetry trace context if available
        if is_tracing_enabled():
            trace_context = get_trace_context()
            if not correlation_id and trace_context.get('correlation_id'):
                correlation_id = trace_context['correlation_id']
        
        # Store in request state for access by other middleware/endpoints
        request.state.correlation_id = correlation_id
        request.state.trace_context = trace_context
        
        # Add to request headers for downstream services
        if correlation_id:
            # Create a mutable copy of headers if needed
            if not hasattr(request, '_mutable_headers'):
                mutable_headers = dict(request.headers)
                mutable_headers['x-correlation-id'] = correlation_id
                request._mutable_headers = mutable_headers
        
        # Process request
        try:
            response = await call_next(request)
        except Exception as e:
            # Log error with trace context
            error_context = {
                'correlation_id': correlation_id,
                'path': request.url.path,
                'method': request.method
            }
            error_context.update(trace_context)
            logger.error(f"Request failed: {e}", extra=error_context)
            raise
        
        # Add correlation ID to response headers
        if correlation_id:
            response.headers['X-Correlation-ID'] = correlation_id
        
        # Add trace information to response headers if available
        if trace_context:
            if trace_context.get('trace_id'):
                response.headers['X-Trace-ID'] = trace_context['trace_id']
            if trace_context.get('span_id'):
                response.headers['X-Span-ID'] = trace_context['span_id']
        
        return response
    
    def _get_or_create_correlation_id(self, request: Request) -> str:
        """Extract or generate a correlation ID for the request."""
        
        # Check for existing correlation ID in headers
        correlation_id = (
            request.headers.get('x-correlation-id') or
            request.headers.get('X-Correlation-Id') or
            request.headers.get('correlation-id')
        )
        
        if correlation_id:
            logger.debug(f"Using existing correlation ID: {correlation_id}")
            return correlation_id
        
        # Generate new correlation ID if enabled
        if self.generate_correlation_id:
            correlation_id = str(uuid.uuid4())[:16]  # Short UUID
            logger.debug(f"Generated new correlation ID: {correlation_id}")
            return correlation_id
        
        return ""


def get_correlation_id(request: Request) -> str:
    """
    Get correlation ID from request state.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Correlation ID if available, empty string otherwise
    """
    return getattr(request.state, 'correlation_id', '')


def get_request_trace_context(request: Request) -> dict:
    """
    Get trace context from request state.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Dictionary containing trace context information
    """
    return getattr(request.state, 'trace_context', {})