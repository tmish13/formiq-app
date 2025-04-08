"""Middleware configuration module."""
import logging
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.cache import cache_service
from app.core.logging import get_logger
from app.core.middleware.error_handler import ErrorHandlerMiddleware
from app.core.middleware.request_logging import RequestLoggingMiddleware
from app.core.middleware.rate_limiter import EnhancedRateLimiter
from app.core.middleware.timing import TimingMiddleware

logger = get_logger(__name__)

def setup_middleware(app: FastAPI) -> None:
    """Configure all middleware for the application.
    
    The order of middleware is important:
    1. CORS (outermost)
    2. Request Logging
    3. Timing
    4. Rate Limiting (if Redis available)
    5. Error Handler (innermost)
    
    Args:
        app: The FastAPI application instance
    """
    # 1. CORS Middleware (must be first)
    if settings.BACKEND_CORS_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        logger.info("CORS middleware configured")

    # 2. Request Logging Middleware
    if settings.ENVIRONMENT != "test":  # Don't log requests in test environment
        app.add_middleware(
            RequestLoggingMiddleware,
            exclude_paths=["/health", "/metrics"],  # Don't log health checks
            log_request_body=settings.DEBUG,  # Only log request bodies in debug mode
        )
        logger.info("Request logging middleware configured")

    # 3. Timing Middleware (adds X-Response-Time header)
    app.add_middleware(TimingMiddleware)
    logger.info("Timing middleware configured")

    # 4. Rate Limiting Middleware (if Redis is available)
    if cache_service.available and settings.ENVIRONMENT not in ["test", "development"]:
        try:
            app.add_middleware(
                EnhancedRateLimiter,
                redis_client=cache_service.redis,
                requests_per_minute=settings.RATE_LIMIT_REQUESTS,
                burst_size=settings.RATE_LIMIT_BURST,
                window_size=settings.RATE_LIMIT_WINDOW,
                exclude_paths=["/health", "/metrics"],  # Don't rate limit monitoring endpoints
            )
            logger.info("Rate limiting middleware configured")
        except Exception as e:
            logger.error(f"Failed to configure rate limiting middleware: {str(e)}")

    # 5. Error Handler Middleware (must be last before application code)
    app.add_middleware(ErrorHandlerMiddleware)
    logger.info("Error handler middleware configured") 