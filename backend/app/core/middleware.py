"""Application middleware configuration."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.logging import get_logger
from app.core.cache import cache_service
from app.middleware.error_handler import ErrorHandlerMiddleware
from app.middleware.rate_limiter import EnhancedRateLimiter
from app.middleware.validate_request import EnhancedValidateRequestMiddleware

logger = get_logger(__name__)

def setup_middleware(app: FastAPI) -> None:
    """Configure all middleware for the application.
    
    Args:
        app: The FastAPI application instance
    """
    # 1. CORS Middleware (must be first)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    logger.info("CORS middleware configured")

    # 2. Compression Middleware
    app.add_middleware(
        GZipMiddleware,
        minimum_size=1000,  # Only compress responses larger than 1KB
    )
    logger.info("Compression middleware configured")

    # 3. Request Validation Middleware
    app.add_middleware(EnhancedValidateRequestMiddleware)
    logger.info("Request validation middleware configured")

    # 4. Rate Limiting Middleware (if Redis is available)
    if cache_service.available:
        try:
            # Configure rate limits for different endpoint types
            custom_rules = {
                # Auth endpoints - strict limits
                "/api/v1/auth/login": {"limit": 5, "burst": 10, "window": 60},
                "/api/v1/auth/register": {"limit": 3, "burst": 5, "window": 60},
                "/api/v1/auth/refresh": {"limit": 10, "burst": 20, "window": 60},
                
                # Form check analysis - resource intensive
                "/api/v1/form-checks/analyze": {"limit": 10, "burst": 20, "window": 120},
                "/api/v1/form-checks/upload": {"limit": 20, "burst": 40, "window": 60},
                
                # Standard API endpoints - more lenient
                "/api/v1/exercises": {"limit": 100, "burst": 200, "window": 60},
                "/api/v1/workouts": {"limit": 60, "burst": 120, "window": 60},
                "/api/v1/users/profile": {"limit": 40, "burst": 80, "window": 60},
            }
            
            # Paths to exclude from rate limiting
            exclude_paths = [
                "/health",
                "/metrics",
                "/docs",
                "/redoc",
                "/openapi.json",
                "/api/v1/auth/verify",  # Allow email verification without limits
            ]
            
            app.add_middleware(
                EnhancedRateLimiter,
                redis_client=cache_service.redis,
                requests_per_minute=settings.RATE_LIMIT_REQUESTS,
                burst_size=settings.RATE_LIMIT_BURST,
                window_size=settings.RATE_LIMIT_WINDOW,
                custom_rules=custom_rules,
                exclude_paths=exclude_paths
            )
            logger.info("Rate limiting middleware configured with Redis backend")
        except Exception as e:
            logger.error(f"Failed to configure rate limiting middleware: {str(e)}")
            logger.warning("API will operate without rate limiting!")
    else:
        logger.warning("Redis unavailable - rate limiting disabled!")

    # 5. Error Handler Middleware (must be last before application code)
    app.add_middleware(ErrorHandlerMiddleware)
    logger.info("Error handler middleware configured") 