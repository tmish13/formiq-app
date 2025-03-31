"""Main application module."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Core imports
from app.core.config import settings
from app.core.logging import setup_logging, get_logger
from app.core.database import async_engine
from app.core.cache import cache_service

# API imports
from app.api.v1.api import api_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.docs import custom_openapi

# Middleware imports
from app.middleware import ErrorHandlerMiddleware

logger = get_logger(__name__)

def create_application() -> FastAPI:
    """Create FastAPI application."""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        openapi_url=f"{settings.API_V1_STR}/openapi.json"
    )

    # Set all CORS enabled origins
    if settings.BACKEND_CORS_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Add custom middleware
    app.add_middleware(ErrorHandlerMiddleware)

    # Add API router
    app.include_router(api_router, prefix=settings.API_V1_STR)

    return app

app = create_application()

@app.on_event("startup")
async def startup_event():
    """Handle application startup."""
    logger.info("Application starting up...")
    try:
        # Use engine from app state if available (for testing), otherwise use default engine
        current_engine = getattr(app.state, "engine", async_engine)
        
        # Test database connection
        await current_engine.connect()
        logger.info("Database connection successful")
        
        # Test Redis connection
        if settings.ENVIRONMENT == "test":
            from tests.test_utils import MockRedis
            if not isinstance(cache_service.client, MockRedis):
                cache_service.client = MockRedis()
            logger.info("Using MockRedis for testing")
        else:
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
        await async_engine.dispose()
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