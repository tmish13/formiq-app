"""Application lifespan management."""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.core.config import settings
from app.core.logging import get_logger
from app.core.cache import cache_service
from app.core.connection_pool import monitor as connection_monitor
from app.db.session import engine as async_engine
from app.core.database import init_db, close_db

logger = get_logger(__name__)

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
            else:
                logger.warning("Redis is not available - caching disabled")
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
        await close_db()
        logger.info("Database connections closed successfully")
        
        # Close Redis connections
        if cache_service.available:
            await cache_service.close()
            logger.info("Redis connections closed")
        
        logger.info("Cleanup successful")
    except Exception as e:
        logger.error(f"Shutdown error: {str(e)}") 