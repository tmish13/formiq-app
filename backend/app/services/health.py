"""Health check service module."""
from typing import Dict, Any
from sqlalchemy.orm import Session
from fastapi import Depends

from app.core.deps import get_db
from app.core.cache import cache_service
from app.core.config import settings


class HealthService:
    """Service for health checks."""

    def __init__(self, db: Session):
        """Initialize the service."""
        self.db = db

    async def check_health(self) -> Dict[str, Any]:
        """Check system health.
        
        Returns:
            Dict containing health check results
        """
        # Check database connection
        db_status = "healthy"
        try:
            self.db.execute("SELECT 1")
        except Exception as e:
            db_status = f"unhealthy: {str(e)}"

        # Check Redis connection
        redis_status = "healthy"
        try:
            await cache_service.ping()
        except Exception as e:
            redis_status = f"unhealthy: {str(e)}"

        return {
            "status": "ok",
            "version": settings.VERSION,
            "environment": settings.ENVIRONMENT,
            "components": {
                "database": db_status,
                "redis": redis_status
            }
        }


def get_health_service(db: Session = Depends(get_db)) -> HealthService:
    """Get health service instance.
    
    Args:
        db: Database session
        
    Returns:
        Health service instance
    """
    return HealthService(db=db) 