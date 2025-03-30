from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Core imports
from app.core.config import settings
from app.core.logging import setup_logging, get_logger
from app.core.database import engine
from app.core.cache import cache_service

# API imports
from app.api.v1.api import api_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.docs import custom_openapi
from app.api.v1.endpoints.auth import SENSITIVE_ENDPOINTS

# Middleware imports
from app.middleware.error_handling import UnifiedErrorHandler
from app.middleware.rate_limiter import RateLimiter
from app.middleware.request_validator import RequestValidator

logger = get_logger(__name__)

def create_application() -> FastAPI:
    """Create and configure the FastAPI application."""
    # Initialize logging
    setup_logging()
    
    # Create FastAPI application
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description=settings.DESCRIPTION,
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        docs_url=f"{settings.API_V1_STR}/docs",
        redoc_url=f"{settings.API_V1_STR}/redoc",
    )
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add middlewares in correct order
    app.add_middleware(UnifiedErrorHandler)
    app.add_middleware(
        RateLimiter,
        redis_client=cache_service.redis_client,
        requests_per_minute=settings.RATE_LIMIT_REQUESTS_PER_MINUTE,
        burst_size=settings.RATE_LIMIT_BURST_SIZE,
        custom_rules=SENSITIVE_ENDPOINTS,  # Apply sensitive endpoint rate limits
        skip_paths=settings.RATE_LIMIT_SKIP_PATHS
    )
    app.add_middleware(
        RequestValidator,
        max_content_length=settings.MAX_CONTENT_LENGTH,
        allowed_content_types=settings.ALLOWED_CONTENT_TYPES
    )
    
    # Include API router
    app.include_router(api_router, prefix=settings.API_V1_STR)
    app.include_router(health_router, prefix=settings.API_V1_STR)
    
    # Set custom OpenAPI schema
    app.openapi = custom_openapi
    
    logger.info("Application initialized successfully")
    return app

app = create_application()

@app.on_event("startup")
async def startup_event():
    """Handle application startup."""
    logger.info("Application starting up...")
    try:
        # Test database connection
        await engine.connect()
        logger.info("Database connection successful")
        
        # Test Redis connection
        await cache_service.ping()
        logger.info("Redis connection successful")
        
    except Exception as e:
        logger.error("Startup error", error=str(e))
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Handle application shutdown."""
    logger.info("Application shutting down...")
    try:
        await engine.dispose()
        await cache_service.close()
        logger.info("Cleanup successful")
    except Exception as e:
        logger.error("Shutdown error", error=str(e))

@app.get("/")
async def root():
    """Root endpoint with basic API information."""
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "running",
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "api_prefix": settings.API_V1_STR
    }

@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok"} 