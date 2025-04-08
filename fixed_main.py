"""Main application module."""
from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI, Depends
from starlette.middleware.cors import CORSMiddleware

# Core imports
from app.core.config import settings
from app.core.logging import setup_logging, get_logger
from app.core.cache import cache_service
from app.core.connection_pool import monitor as connection_monitor

# Database imports - import engine directly from session
from app.db.session import engine as async_engine

# API imports
from app.api.v1.api import api_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.docs import custom_openapi

# Middleware imports
from app.middleware import ErrorHandlerMiddleware, EnhancedRateLimiter

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup Logic
    logger.info(f"Application starting up in {settings.ENVIRONMENT} environment...")
    try:
        # Test database connection
        async with async_engine.connect() as conn:
            result = await conn.execute("SELECT 1")
            logger.info(f"Database connection successful: {result.scalar()}")
        
        # Initialize database tables if needed (dev/test environments)
        if settings.ENVIRONMENT in ["development", "test"]:
            try:
                # Import init_db function here to avoid circular imports
                from app.core.database import init_db
                await init_db()
                logger.info("Database tables initialized")
            except Exception as init_error:
                logger.error(f"Database initialization failed: {str(init_error)}")
                if settings.ENVIRONMENT == "test":
                    raise  # Re-raise in test environment
        
        # Start connection pool monitoring (only in production and staging)
        if settings.ENVIRONMENT in ["production", "staging"]:
            connection_monitor.start_monitoring()
            logger.info("Database connection pool monitoring started")
        
        # Initialize Redis connection
        try:
            await cache_service.connect()
            if cache_service.available:
                logger.info("Redis connection successful")
                
                # Setup performance cache
                # Preload common data, especially for form analysis endpoints
                if settings.ENVIRONMENT in ["production", "staging"]:
                    from app.core.preload import preload_caches
                    await preload_caches()
                    logger.info("Cache preloading complete")
                
                # Setup rate limiting middleware when Redis is available
                if app.middleware_stack is not None:  # Check if middleware stack is initialized
                    app.add_middleware(
                        EnhancedRateLimiter,
                        redis_client=cache_service.redis,
                        requests_per_minute=settings.RATE_LIMIT_REQUESTS,
                        burst_size=settings.RATE_LIMIT_BURST,
                        window_size=settings.RATE_LIMIT_WINDOW
                    )
                    logger.info("Rate limiting middleware initialized")
            else:
                logger.warning("Redis is not available - caching and rate limiting disabled")
        except Exception as redis_error:
            logger.error(f"Redis connection failed: {str(redis_error)}")
            if settings.ENVIRONMENT == "production":
                raise  # Re-raise in production
            
    except Exception as e:
        logger.error(f"Startup error: {str(e)}")
        if settings.ENVIRONMENT in ["production", "staging"]:
            raise  # Only raise in production/staging

    # Yield control to app
    yield
    
    # Shutdown Logic
    logger.info("Application shutting down...")
    try:
        # Stop connection pool monitoring
        if settings.ENVIRONMENT in ["production", "staging"]:
            connection_monitor.stop_monitoring()
            logger.info("Database connection pool monitoring stopped")
        
        # Close database connections
        from app.core.database import close_db
        await close_db()
        
        # Close Redis connections
        await cache_service.close()
        
        logger.info("Cleanup successful")
    except Exception as e:
        logger.error(f"Shutdown error: {str(e)}")

def create_application() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        description=settings.PROJECT_DESCRIPTION,
        version=settings.VERSION,
        openapi_url=f"{settings.API_V1_STR}/openapi.json" if settings.ENVIRONMENT != "production" else None,
        docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
        redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
        lifespan=lifespan,
    )

    # Configure CORS
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

@app.get("/")
async def root():
    """Root endpoint with basic API information."""
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "running",
        "docs_url": "/docs" if settings.ENVIRONMENT != "production" else None,
        "api_prefix": settings.API_V1_STR
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    from app.core.connection_pool import check_connection, get_connection_metrics
    
    # Check database connection asynchronously
    db_healthy = await check_connection(timeout=2.0)
    
    # Get database connection metrics
    db_metrics = get_connection_metrics() if db_healthy else {"status": "error"}
    
    # Check Redis connection with proper error handling
    redis_healthy = False
    redis_available = False
    try:
        if cache_service.redis is not None:
            redis_healthy = await cache_service.ping()
            redis_available = True
        else:
            logger.warning("Redis service is not initialized")
    except Exception as e:
        logger.error(f"Redis health check failed: {str(e)}")
    
    return {
        "status": "ok" if db_healthy else "error",
        "database": {
            "healthy": db_healthy,
            "metrics": db_metrics
        },
        "redis": {
            "healthy": redis_healthy,
            "available": redis_available
        },
        "environment": settings.ENVIRONMENT
    } 