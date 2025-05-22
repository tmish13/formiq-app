"""Main middleware setup for the application."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
# Assuming BaseHTTPMiddleware is not directly used by setup_middleware but by the individual middlewares.

from app.core.config import settings
from app.core.logging import get_logger # Use get_logger consistently
from app.core.cache import cache_service

# Imports from within the app.core.middleware package
from .error_handler import ErrorHandlerMiddleware
from .rate_limiter import EnhancedRateLimiter
from .validate_request import EnhancedValidateRequestMiddleware

logger = get_logger(__name__)

def setup_middleware(app: FastAPI) -> None:
    """Configure all middleware for the application.
    
    Args:
        app: The FastAPI application instance
    """
    # 1. CORS Middleware (must be first)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    logger.info(f"CORS middleware configured for origins: {settings.CORS_ORIGINS}")

    # 2. Compression Middleware
    app.add_middleware(
        GZipMiddleware,
        minimum_size=1000,  # Only compress responses larger than 1KB
    )
    logger.info("Compression middleware configured")

    # 3. Request Validation Middleware
    # Ensure EnhancedValidateRequestMiddleware is initialized if it takes 'app'
    app.add_middleware(EnhancedValidateRequestMiddleware) # If it takes app: EnhancedValidateRequestMiddleware(app)
    logger.info("Request validation middleware configured")

    # 4. Rate Limiting Middleware (if Redis is available)
    if cache_service and hasattr(cache_service, 'redis') and cache_service.is_available():
        try:
            custom_rules = {
                "/api/v1/auth/login": settings.RATE_LIMIT_RULES.get("auth_login", {"limit": 5, "burst": 10, "window": 60}),
                "/api/v1/auth/register": settings.RATE_LIMIT_RULES.get("auth_register", {"limit": 3, "burst": 5, "window": 60}),
                # Add other custom rules from settings or define them here
            }
            
            exclude_paths = settings.RATE_LIMIT_EXCLUDE_PATHS or [
                "/health", "/metrics", "/docs", "/redoc", "/openapi.json", "/api/v1/auth/verify",
            ]
            
            app.add_middleware(
                EnhancedRateLimiter,
                redis_client=cache_service.redis_client, # Pass the actual redis client instance
                requests_per_minute=settings.RATE_LIMIT_REQUESTS, # Default for paths not in endpoint_limits
                burst_size=settings.RATE_LIMIT_BURST, # Default burst
                window_size=settings.RATE_LIMIT_WINDOW, # Default window
                exclude_paths=exclude_paths,
                endpoint_limits=custom_rules # Pass the custom rules dict
            )
            logger.info("Rate limiting middleware (EnhancedRateLimiter from core) configured with Redis backend")
        except Exception as e:
            logger.error(f"Failed to configure EnhancedRateLimiter: {str(e)}", exc_info=True)
            logger.warning("API will operate without rate limiting due to EnhancedRateLimiter setup error!")
    else:
        logger.warning("Redis unavailable or cache_service not properly initialized - rate limiting disabled!")

    # 5. Error Handler Middleware (must be last before application code)
    app.add_middleware(ErrorHandlerMiddleware) # This is app.core.middleware.error_handler.ErrorHandlerMiddleware
    logger.info("Error handler middleware configured") 