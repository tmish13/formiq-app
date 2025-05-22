"""Health check service module."""
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from fastapi import Depends

from app.core.config import settings, Settings
from app.core.cache import CacheService

import logging
logger = logging.getLogger(__name__)

class HealthService:
    """Service for health checks."""

    def __init__(self, db: AsyncSession, app_settings: Settings, cache_client: Optional[CacheService]):
        """Initialize the service."""
        self.db = db
        self.settings = app_settings
        self.cache_client = cache_client

    async def check_health(self) -> Dict[str, Any]:
        """Check system health.
        
        Returns:
            Dict containing health check results
        """
        db_status = "healthy"
        try:
            await self.db.execute(text("SELECT 1"))
        except Exception as e:
            logger.error(f"Database health check failed: {str(e)}")
            db_status = f"unhealthy: {str(e)}"

        redis_status = "healthy"
        if self.cache_client:
            try:
                await self.cache_client.ping()
            except Exception as e:
                logger.error(f"Redis health check failed: {str(e)}")
                redis_status = f"unhealthy: {str(e)}"
        else:
            redis_status = "not_configured_or_unavailable"

        return {
            "status": "ok",
            "version": self.settings.VERSION,
            "environment": self.settings.ENVIRONMENT,
            "components": {
                "database": db_status,
                "redis": redis_status
            }
        }

async def get_async_health_service(
) -> HealthService:
    """Get health service instance asynchronously."""
    # Add imports locally to avoid circular dependency
    from app.core.deps import get_async_db, get_settings, get_cache_service
    
    db: AsyncSession = Depends(get_async_db)
    app_settings: Settings = Depends(get_settings)
    cache_client: Optional[CacheService] = Depends(get_cache_service) # Make sure CacheService is Optional if get_cache_service can return None or not exist

    return HealthService(db=db, app_settings=app_settings, cache_client=cache_client) 