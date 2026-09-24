from typing import Dict, Any, List
import os
import psutil
import time
import platform
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Response
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import redis
import gc
import tracemalloc
import json
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, Counter, Gauge

from app.core import deps
from app.core.deps import get_db
from app.core.config import settings
from app.core.logging import logger, get_logger
from app.core.database import get_db_stats
from app.core.cache import cache_service
from app.utils.system import get_memory_usage, get_cpu_usage
from app.services.health_service import HealthService

# Create router
router = APIRouter(prefix="/health", tags=["health"])

# In-memory storage for memory snapshots
_memory_snapshots = []
_memory_snapshot_interval = 15  # minutes

# Prometheus metrics for rate limiting
RATE_LIMIT_EXCEEDED = Counter(
    'rate_limit_exceeded_total',
    'Total number of rate limit exceeded events',
    ['endpoint']
)

RATE_LIMIT_CURRENT = Gauge(
    'rate_limit_current',
    'Current number of requests within rate limit window',
    ['endpoint']
)

@router.get(
    "",
    response_model=Dict[str, Any],
    responses={
        200: {
            "description": "System health status",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "version": "1.0.0",
                        "database": "connected",
                        "redis": "connected",
                        "storage": "connected"
                    }
                }
            }
        },
        503: {
            "description": "System unhealthy",
            "content": {
                "application/json": {
                    "example": {
                        "status": "unhealthy",
                        "database": "error: connection failed",
                        "redis": "connected",
                        "storage": "connected"
                    }
                }
            }
        }
    }
)
async def health_check(health_service: HealthService = Depends(deps.get_async_health_service)) -> Dict[str, Any]:
    """
    Check system health status.
    
    Returns status of:
    * API service
    * Database connection
    * Redis connection
    * Storage service
    * Current version
    """
    return await health_service.check_health()

@router.get("/db", response_model=Dict[str, Any])
async def db_health_check(db: AsyncSession = Depends(deps.get_async_db)) -> Dict[str, Any]:
    """
    Database health check with detailed metrics.
    
    Returns:
        Database health information
    """
    start_time = time.time()
    
    try:
        # Check if we're using SQLite or PostgreSQL
        is_sqlite = "sqlite" in str(db.bind.url)
        
        if is_sqlite:
            # SQLite version and simple check
            await db.execute(text("SELECT 1"))
            return {
                "status": "healthy",
                "version": "SQLite (test environment)",
                "connection_count": 1,
                "largest_tables": [],
                "pool": get_db_stats(),
                "response_time_ms": round((time.time() - start_time) * 1000, 2)
            }
        
        # PostgreSQL checks
        # Get database version
        version_query = text("SELECT version()")
        version_result = await db.execute(version_query)
        version = version_result.scalar_one_or_none()
        
        # Get connection count
        connections_query = text(
            "SELECT count(*) FROM pg_stat_activity"
        )
        connection_count_result = await db.execute(connections_query)
        connection_count = connection_count_result.scalar_one_or_none()
        
        # Get active query count
        active_query = text(
            "SELECT count(*) FROM pg_stat_activity WHERE state = 'active'"
        )
        active_count_result = await db.execute(active_query)
        active_count = active_count_result.scalar_one_or_none()
        
        # Get table sizes
        table_sizes_query = text("""
            SELECT
                table_name,
                pg_size_pretty(pg_relation_size(quote_ident(table_name)))
            FROM
                information_schema.tables
            WHERE
                table_schema = 'public'
            ORDER BY
                pg_relation_size(quote_ident(table_name)) DESC
            LIMIT 5;
        """)
        table_sizes_result = await db.execute(table_sizes_query)
        table_sizes = table_sizes_result.fetchall()
        
        # Get idle connections
        idle_query = text(
            "SELECT count(*) FROM pg_stat_activity WHERE state = 'idle'"
        )
        idle_count_result = await db.execute(idle_query)
        idle_count = idle_count_result.scalar_one_or_none()
        
        # Get database size
        db_size_query = text(
            "SELECT pg_size_pretty(pg_database_size(current_database()))"
        )
        db_size_result = await db.execute(db_size_query)
        db_size = db_size_result.scalar_one_or_none()
        
        # Get connection pool stats
        db_stats = get_db_stats()
        
        return {
            "status": "healthy",
            "version": version,
            "connection_count": connection_count,
            "active_queries": active_count,
            "idle_connections": idle_count,
            "database_size": db_size,
            "pool": {
                "size": db_stats.get("pool_size", "N/A"),
                "in_use": db_stats.get("in_use", "N/A"),
                "available": db_stats.get("available", "N/A")
            },
            "largest_tables": [
                {"name": name, "size": size} for name, size in table_sizes
            ],
            "response_time_ms": round((time.time() - start_time) * 1000, 2)
        }
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "response_time_ms": round((time.time() - start_time) * 1000, 2)
        }

@router.get("/logs", response_model=Dict[str, Any])
async def logs_status() -> Dict[str, Any]:
    """
    Check log files status.
    
    This endpoint provides information about log files and any error counts.
    
    Returns:
        Log file status information
    """
    try:
        logs_dir = os.path.join(os.getcwd(), "logs")
        if os.path.exists(logs_dir):
            log_files = []
            main_log_path = os.path.join(logs_dir, "app.log")
            error_log_path = os.path.join(logs_dir, "error.log")
            
            main_log_exists = os.path.exists(main_log_path)
            error_log_exists = os.path.exists(error_log_path)
            error_count = 0
            
            # List all log files
            for filename in os.listdir(logs_dir):
                if filename.endswith(".log"):
                    file_path = os.path.join(logs_dir, filename)
                    file_size = os.path.getsize(file_path)
                    file_modified = datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
                    
                    log_files.append({
                        "name": filename,
                        "path": file_path,
                        "size_mb": round(file_size / (1024 * 1024), 2),
                        "last_modified": file_modified
                    })
            
            # Count errors in error log
            if error_log_exists:
                try:
                    with open(error_log_path, 'r') as f:
                        # Count lines with ERROR or CRITICAL
                        for line in f:
                            if '"level": "ERROR"' in line or '"level": "CRITICAL"' in line:
                                error_count += 1
                except Exception as e:
                    logger.warning(f"Could not parse error log: {str(e)}")
            
            return {
                "status": "ok",
                "logs_directory": logs_dir,
                "main_log_exists": main_log_exists,
                "error_log_exists": error_log_exists,
                "error_count": error_count,
                "log_files": sorted(log_files, key=lambda x: x["size_mb"], reverse=True)
            }
        else:
            # Create logs directory if it doesn't exist
            try:
                os.makedirs(logs_dir, exist_ok=True)
                return {
                    "status": "ok",
                    "logs_directory": logs_dir,
                    "message": "Logs directory created",
                    "log_files": []
                }
            except Exception as e:
                return {
                    "status": "warning",
                    "error": f"Could not create logs directory: {str(e)}"
                }
    except Exception as e:
        logger.error(f"Logs status check failed: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }

@router.get("/metrics")
async def prometheus_metrics() -> Response:
    """Prometheus text exposition of this process's registry.

    Today that is the default process/platform collectors plus any counters the app registers; the
    HTTP instrumentator is not installed (plan D8: no Prometheus stack), so this is a liveness-grade
    signal, not a dashboard. The previous handler built ``HealthService()`` without its three
    arguments and called a method that did not exist, so it returned 500 on every call.
    ``/health/rate-limits`` did the same and reported on a middleware that has never been
    installed; it is gone.
    """
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@router.get("/ready", response_model=Dict[str, Any])
async def readiness_check(db: AsyncSession = Depends(deps.get_async_db)) -> Dict[str, Any]:
    """
    Readiness probe for Kubernetes-style deployments.
    
    This endpoint checks if the application is ready to receive traffic.
    
    Returns:
        Readiness status
    """
    try:
        # Check database
        await db.execute(text("SELECT 1"))
        
        # Check cache if available
        cache_ok = True
        if cache_service.available:
            try:
                cache_ok = await cache_service.ping()
            except Exception:
                cache_ok = False
        
        # Check disk space for uploads
        upload_dir = settings.UPLOAD_DIR
        disk_ok = True
        disk_percent = 0
        
        try:
            if os.path.exists(upload_dir):
                disk = psutil.disk_usage(os.path.abspath(upload_dir))
                disk_percent = disk.percent
                disk_ok = disk.percent < 90  # Less than 90% used
        except Exception:
            disk_ok = False
        
        # Overall status - must have database working
        ready = disk_ok and cache_ok
        
        # Non-critical checks
        warnings = []
        if not cache_ok and settings.ENVIRONMENT == "production":
            warnings.append("Cache service not available")
        
        if not disk_ok:
            warnings.append(f"Disk usage high: {disk_percent}%")
        
        return {
            "status": "ready" if ready else "not_ready",
            "checks": {
                "database": disk_ok,
                "cache": cache_ok,
                "disk": disk_ok
            },
            "warnings": warnings if warnings else None,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Readiness check failed: {str(e)}")
        return {
            "status": "not_ready",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@router.get("/live", response_model=Dict[str, Any])
async def liveness_check() -> Dict[str, Any]:
    """
    Liveness probe for Kubernetes-style deployments.
    
    This endpoint checks if the application is alive and not deadlocked.
    
    Returns:
        Liveness status
    """
    try:
        # Process information
        process = psutil.Process(os.getpid())
        
        # Collect metrics that could indicate a problem
        memory_percent = process.memory_percent()
        cpu_percent = process.cpu_percent(interval=0.1)
        thread_count = process.num_threads()
        
        # Consider the app alive if not using excessive resources
        alive = memory_percent < 95 and thread_count < 1000
        
        return {
            "status": "alive" if alive else "unhealthy",
            "process": {
                "memory_percent": memory_percent,
                "cpu_percent": cpu_percent,
                "thread_count": thread_count
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Liveness check failed: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@router.post("/debug/gc", response_model=Dict[str, Any])
async def trigger_garbage_collection() -> Dict[str, Any]:
    """
    Trigger manual garbage collection.
    
    This is a maintenance endpoint for debugging memory issues.
    
    Returns:
        GC status information
    """
    if settings.ENVIRONMENT == "production":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is disabled in production"
        )
    
    try:
        # Get memory before GC
        process = psutil.Process(os.getpid())
        memory_before = process.memory_info().rss
        
        # Trigger garbage collection
        collected = gc.collect()
        
        # Get memory after GC
        memory_after = process.memory_info().rss
        memory_diff = memory_before - memory_after
        
        return {
            "status": "ok",
            "collected_objects": collected,
            "memory_before_mb": memory_before / (1024 * 1024),
            "memory_after_mb": memory_after / (1024 * 1024),
            "memory_freed_mb": memory_diff / (1024 * 1024) if memory_diff > 0 else 0,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"GC triggering failed: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }

@router.post("/debug/memory-snapshot", response_model=Dict[str, Any])
async def take_memory_snapshot(background_tasks: BackgroundTasks) -> Dict[str, Any]:
    """
    Take a memory snapshot for leak detection.
    
    This endpoint is for debugging memory issues.
    
    Returns:
        Memory snapshot information
    """
    if settings.ENVIRONMENT == "production":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is disabled in production"
        )
    
    try:
        # Track memory in background to avoid blocking the response
        background_tasks.add_task(record_memory_snapshot)
        
        return {
            "status": "ok",
            "message": "Memory snapshot initiated in the background",
            "snapshots_count": len(_memory_snapshots),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Memory snapshot failed: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }

@router.get("/storage", response_model=Dict[str, Any])
async def storage_health_check() -> Dict[str, Any]:
    """
    Storage provider health check with connection test.
    
    Tests the configured storage provider by attempting a 
    real connection and basic operations.
    
    Returns:
        Storage health information
    """
    from app.core.storage import storage_provider
    
    start_time = time.time()
    
    result = {
        "status": "healthy",
        "provider_type": storage_provider.__class__.__name__,
        "timestamp": datetime.now().isoformat(),
        "checks": {},
    }
    
    # Check if using S3
    is_s3 = result["provider_type"] == "S3StorageProvider"
    
    if is_s3:
        try:
            # Use the new S3 health check method for comprehensive testing
            s3_health = await storage_provider.health_check()
            
            # Map S3 health results to our response format
            result["status"] = "healthy" if s3_health["healthy"] else "degraded"
            
            if not s3_health["healthy"] and s3_health.get("error"):
                result["error"] = s3_health["error"]
            
            # Map individual checks
            result["checks"] = {
                "bucket_exists": {
                    "status": "success" if s3_health["bucket_exists"] else "failed"
                },
                "list_operation": {
                    "status": "success" if s3_health["can_list_objects"] else "failed"
                },
                "write_operation": {
                    "status": "success" if s3_health["can_write"] else "failed"
                },
                "read_operation": {
                    "status": "success" if s3_health["can_read"] else "failed"
                },
                "delete_operation": {
                    "status": "success" if s3_health["can_delete"] else "failed"
                }
            }
            
            # Add configuration info
            result["config"] = {
                "bucket": getattr(storage_provider, "bucket_name", "unknown"),
                "region": getattr(storage_provider, "region", "unknown"),
                "endpoint": getattr(storage_provider, "endpoint_url", None),
                "public_access": getattr(settings, "S3_PUBLIC_ACCESS", False)
            }
            
        except Exception as e:
            logger.error(f"S3 storage health check failed: {str(e)}")
            result["status"] = "degraded"
            result["error"] = str(e)
            result["checks"]["api_call"] = {
                "status": "failed",
                "error": str(e)
            }
    else:
        # Local storage checks
        try:
            # Check if upload directory exists and is writable
            upload_dir = getattr(storage_provider, "base_dir", "uploads")
            
            if os.path.exists(upload_dir):
                # Try to create a test file
                test_path = os.path.join(upload_dir, ".health_check")
                try:
                    with open(test_path, "w") as f:
                        f.write("test")
                    os.remove(test_path)
                    
                    result["checks"]["write_test"] = {
                        "status": "success"
                    }
                except Exception as write_err:
                    result["status"] = "degraded"
                    result["checks"]["write_test"] = {
                        "status": "failed",
                        "error": str(write_err)
                    }
                
                # Get directory stats
                dir_stats = os.statvfs(upload_dir)
                free_space_gb = (dir_stats.f_bavail * dir_stats.f_frsize) / (1024 * 1024 * 1024)
                
                result["checks"]["space_available"] = {
                    "status": "success" if free_space_gb > 1 else "warning",
                    "free_gb": round(free_space_gb, 2)
                }
                
                if free_space_gb < 1:
                    result["status"] = "degraded"
                    result["warnings"] = ["Low storage space available"]
                
            else:
                result["status"] = "degraded"
                result["checks"]["directory_exists"] = {
                    "status": "failed",
                    "error": f"Upload directory {upload_dir} does not exist"
                }
            
            # Add configuration info
            result["config"] = {
                "base_dir": getattr(storage_provider, "base_dir", "unknown"),
                "base_url": getattr(storage_provider, "base_url", "unknown")
            }
            
        except Exception as e:
            logger.error(f"Local storage health check failed: {str(e)}")
            result["status"] = "degraded"
            result["error"] = str(e)
    
    # Response time
    result["response_time_ms"] = round((time.time() - start_time) * 1000, 2)
    
    return result

@router.get("/auth-config", tags=["health"])
async def auth_config():
    """
    Returns the current auth mode configuration.

    Use this to instantly diagnose the BETA_ALLOW_UNVERIFIED + SMTP deadlock
    before inviting beta testers:
      - beta_allow_unverified: true  → Mode A (local beta, no email required)
      - smtp_configured: true        → Mode B (real email verification)
      - deadlock: true               → BROKEN: verification enforced but no SMTP
    """
    return {
        "beta_allow_unverified": settings.BETA_ALLOW_UNVERIFIED,
        "smtp_configured": settings.emails_enabled,
        "deadlock": not settings.BETA_ALLOW_UNVERIFIED and not settings.emails_enabled,
    }


# Helper functions
def get_uptime() -> str:
    """Get application uptime."""
    import os
    
    # Get process start time
    process = psutil.Process(os.getpid())
    start_time = datetime.fromtimestamp(process.create_time())
    uptime = datetime.now() - start_time
    
    # Format uptime nicely
    days = uptime.days
    hours, remainder = divmod(uptime.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    if days > 0:
        return f"{days}d {hours}h {minutes}m"
    elif hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"

def record_memory_snapshot():
    """Take a snapshot of memory usage and store it."""
    global _memory_snapshots
    
    # Start tracemalloc if not already started
    if not tracemalloc.is_tracing():
        tracemalloc.start()
    
    # Take snapshot
    snapshot = tracemalloc.take_snapshot()
    
    # Get process info
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    
    # Store snapshot with metadata
    _memory_snapshots.append({
        "timestamp": datetime.now().isoformat(),
        "rss_mb": memory_info.rss / (1024 * 1024),
        "vms_mb": memory_info.vms / (1024 * 1024),
        "snapshot": snapshot,
    })
    
    # Keep only the last 5 snapshots to avoid memory issues
    if len(_memory_snapshots) > 5:
        _memory_snapshots.pop(0)
    
    logger.info(f"Recorded memory snapshot, size: {memory_info.rss / (1024 * 1024):.2f} MB")

def check_memory_growth() -> float:
    """Check for memory growth between snapshots."""
    if len(_memory_snapshots) < 2:
        record_memory_snapshot()
        return 0.0
    
    # Get first and last snapshots
    first = _memory_snapshots[0]
    last = _memory_snapshots[-1]
    
    # Calculate growth percentage
    growth_mb = last["rss_mb"] - first["rss_mb"]
    growth_percent = (growth_mb / first["rss_mb"]) * 100 if first["rss_mb"] > 0 else 0
    
    # Only consider positive growth
    return max(0, growth_percent) 