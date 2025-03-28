from typing import Dict, Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.cache import cache_service
from app.core.config import settings
from app.core.logging import logger

router = APIRouter(tags=["health"])

@router.get("/health", response_model=Dict[str, Any])
async def health_check(
    detailed: bool = Query(False, description="Include detailed health information"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Health check endpoint that verifies all critical services.
    
    Args:
        detailed: Whether to include detailed health information
        db: Database session
        
    Returns:
        Health status information
    """
    if detailed:
        return await _detailed_health_check(db)
    else:
        return await _basic_health_check(db)

async def _basic_health_check(db: Session) -> Dict[str, Any]:
    """Basic health check with essential service status."""
    health_status = {
        "status": "healthy",
        "version": settings.VERSION,
        "services": {
            "database": "healthy",
            "redis": "healthy",
            "api": "healthy"
        }
    }
    
    try:
        # Check database connection
        db.execute("SELECT 1")
    except Exception as e:
        logger.error("database_health_check_failed", error=str(e))
        health_status["services"]["database"] = "unhealthy"
        health_status["status"] = "unhealthy"
    
    try:
        # Check Redis connection
        cache_service.redis_client.ping()
    except Exception as e:
        logger.error("redis_health_check_failed", error=str(e))
        health_status["services"]["redis"] = "unhealthy"
        health_status["status"] = "unhealthy"
    
    # Log health check result
    logger.info(
        "health_check_completed",
        status=health_status["status"],
        services=health_status["services"]
    )
    
    return health_status

async def _detailed_health_check(db: Session) -> Dict[str, Any]:
    """Detailed health check with additional metrics."""
    health_status = {
        "status": "healthy",
        "version": settings.VERSION,
        "services": {
            "database": {
                "status": "healthy",
                "latency_ms": None,
                "connections": None
            },
            "redis": {
                "status": "healthy",
                "latency_ms": None,
                "used_memory": None
            },
            "api": {
                "status": "healthy",
                "uptime": None
            }
        }
    }
    
    try:
        # Check database with metrics
        import time
        start = time.time()
        db.execute("SELECT 1")
        db_latency = (time.time() - start) * 1000
        
        # Get connection pool info
        pool_info = db.get_bind().pool.status()
        
        health_status["services"]["database"].update({
            "latency_ms": round(db_latency, 2),
            "connections": {
                "active": pool_info.checkedin + pool_info.checkedout,
                "available": pool_info.checkedin,
                "total": pool_info.size
            }
        })
    except Exception as e:
        logger.error("database_detailed_health_check_failed", error=str(e))
        health_status["services"]["database"]["status"] = "unhealthy"
        health_status["status"] = "unhealthy"
    
    try:
        # Check Redis with metrics
        start = time.time()
        cache_service.redis_client.ping()
        redis_latency = (time.time() - start) * 1000
        
        # Get Redis info
        redis_info = cache_service.redis_client.info()
        
        health_status["services"]["redis"].update({
            "latency_ms": round(redis_latency, 2),
            "used_memory": redis_info["used_memory_human"],
            "connected_clients": redis_info["connected_clients"],
            "uptime_days": round(redis_info["uptime_in_days"], 2)
        })
    except Exception as e:
        logger.error("redis_detailed_health_check_failed", error=str(e))
        health_status["services"]["redis"]["status"] = "unhealthy"
        health_status["status"] = "unhealthy"
    
    # Add API metrics
    import psutil
    process = psutil.Process()
    
    health_status["services"]["api"].update({
        "memory_usage": f"{process.memory_info().rss / 1024 / 1024:.2f}MB",
        "cpu_percent": f"{process.cpu_percent()}%",
        "threads": len(process.threads()),
        "open_files": len(process.open_files())
    })
    
    # Log detailed health check result
    logger.info(
        "detailed_health_check_completed",
        status=health_status["status"]
    )
    
    return health_status 