"""
Connection pool management utilities.

This module provides utilities for monitoring and managing database connection pools.
"""
from typing import List, Dict, Any, Optional
import time
import threading
import asyncio
from app.core.logging import logger
from app.core.database import get_db_stats
from app.core.config import settings
from sqlalchemy.engine import Engine
from sqlalchemy.pool import Pool
from sqlalchemy import text

# Global variables for tracking connection pool health
_pool_stats = {
    "last_check_time": 0,
    "check_interval": 60,  # seconds
    "connection_warnings": 0,
    "slow_queries": 0,
    "max_active_connections": 0,
    "health_status": "healthy",
    "connection_timeouts": 0,
}

# Lock for thread-safe operations
_stats_lock = threading.Lock()

def update_pool_stats(stats: Dict[str, Any]) -> None:
    """
    Update pool statistics with new values.
    
    Args:
        stats: New statistics to update
    """
    with _stats_lock:
        for key, value in stats.items():
            if key in _pool_stats:
                _pool_stats[key] = value
        
        # Update health status based on current stats
        if _pool_stats.get("connection_timeouts", 0) > 5:
            _pool_stats["health_status"] = "critical"
        elif _pool_stats.get("connection_warnings", 0) > 10:
            _pool_stats["health_status"] = "warning"
        else:
            _pool_stats["health_status"] = "healthy"

def get_pool_health() -> Dict[str, Any]:
    """
    Get connection pool health information.
    
    Returns:
        Dict[str, Any]: Pool health statistics
    """
    with _stats_lock:
        current_time = time.time()
        # Check if stats need refreshing (at most once per check_interval)
        if current_time - _pool_stats["last_check_time"] > _pool_stats["check_interval"]:
            try:
                db_stats = get_db_stats()
                
                # Update pool stats with database stats
                _pool_stats["max_active_connections"] = max(
                    _pool_stats["max_active_connections"],
                    db_stats.get("active_connections", 0)
                )
                
                # Update last check time
                _pool_stats["last_check_time"] = current_time
                
                # Check if approaching connection limit
                pool_size = settings.DB_POOL_SIZE
                max_overflow = settings.DB_MAX_OVERFLOW
                active_connections = db_stats.get("active_connections", 0)
                
                if active_connections > (pool_size + max_overflow) * 0.8:
                    logger.warning(f"Connection pool usage high: {active_connections}/{pool_size + max_overflow}")
                    _pool_stats["connection_warnings"] += 1
            except Exception as e:
                logger.error(f"Error getting pool health: {str(e)}")
                
        return dict(_pool_stats)

def reset_pool_stats() -> None:
    """Reset pool statistics to default values."""
    with _stats_lock:
        _pool_stats.update({
            "last_check_time": 0,
            "connection_warnings": 0,
            "slow_queries": 0,
            "health_status": "healthy",
            "connection_timeouts": 0,
        })

class ConnectionPoolMonitor:
    """
    Connection pool monitoring class.
    
    This class provides utilities for monitoring and managing database connection pools.
    It can be used to log pool statistics periodically and detect connection issues.
    """
    
    def __init__(self, engine: Optional[Engine] = None, interval: int = 300):
        """
        Initialize connection pool monitor.
        
        Args:
            engine: SQLAlchemy engine to monitor
            interval: Monitoring interval in seconds
        """
        self.engine = engine
        self.interval = interval
        self.stop_event = threading.Event()
        self.monitoring_thread = None
        self.pool_size_warning_threshold = 0.8  # 80% of max pool size
        self.pool_size_critical_threshold = 0.95  # 95% of max pool size
    
    def start_monitoring(self) -> None:
        """
        Start monitoring connection pool in a background thread.
        
        This method starts a background thread that periodically checks the pool
        health and logs warnings if issues are detected.
        """
        if self.monitoring_thread is not None and self.monitoring_thread.is_alive():
            logger.warning("Pool monitoring thread already running")
            return
            
        self.stop_event.clear()
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            daemon=True
        )
        self.monitoring_thread.start()
        logger.info(f"Started connection pool monitoring with interval of {self.interval}s")
    
    def stop_monitoring(self) -> None:
        """Stop monitoring connection pool."""
        if self.monitoring_thread is None or not self.monitoring_thread.is_alive():
            return
            
        self.stop_event.set()
        self.monitoring_thread.join(timeout=2.0)
        logger.info("Stopped connection pool monitoring")
    
    def _monitoring_loop(self) -> None:
        """
        Main monitoring loop.
        
        This method runs in a background thread and periodically checks pool health.
        """
        while not self.stop_event.is_set():
            try:
                self._check_pool_health()
            except Exception as e:
                logger.error(f"Error in pool monitoring: {str(e)}")
                
            # Sleep for the monitoring interval, but check stop event regularly
            for _ in range(self.interval):
                if self.stop_event.is_set():
                    break
                time.sleep(1)
    
    def _check_pool_health(self) -> None:
        """
        Check pool health and log warnings if issues are detected.
        
        This method checks connection pool statistics and logs warnings if
        the pool is approaching capacity or showing other signs of issues.
        """
        try:
            db_stats = get_db_stats()
            pool_health = get_pool_health()
            
            pool_size = settings.DB_POOL_SIZE
            max_overflow = settings.DB_MAX_OVERFLOW
            max_connections = pool_size + max_overflow
            active = db_stats.get("active_connections", 0)
            
            # Check pool usage
            usage_ratio = active / max_connections if max_connections > 0 else 0
            
            if usage_ratio > self.pool_size_critical_threshold:
                logger.error(
                    f"CRITICAL: Connection pool near capacity: {active}/{max_connections} "
                    f"({usage_ratio:.2%})"
                )
            elif usage_ratio > self.pool_size_warning_threshold:
                logger.warning(
                    f"WARNING: Connection pool usage high: {active}/{max_connections} "
                    f"({usage_ratio:.2%})"
                )
            
            # Check for connection errors
            errors = db_stats.get("connection_errors", 0)
            if errors > 0:
                last_error = db_stats.get("last_error_message", "Unknown error")
                last_time = db_stats.get("last_error_time", "Unknown time")
                logger.warning(
                    f"Connection pool has {errors} errors. "
                    f"Last error at {last_time}: {last_error}"
                )
                
            # Log pool stats every 5 intervals
            current_time = time.time()
            if int(current_time) % (self.interval * 5) < self.interval:
                logger.info(
                    f"Pool stats: active={active}, max_concurrent={db_stats.get('max_concurrent', 0)}, "
                    f"total={db_stats.get('total_connections', 0)}, "
                    f"health={pool_health.get('health_status', 'unknown')}"
                )
                
        except Exception as e:
            logger.error(f"Error checking pool health: {str(e)}")

async def check_connection(timeout: float = 5.0) -> bool:
    """
    Check if database connection is working.
    
    Args:
        timeout: Timeout in seconds
        
    Returns:
        bool: True if connection is working, False otherwise
    """
    try:
        # Import here to avoid circular imports
        from app.core.database import async_engine, async_session
        from sqlalchemy import text
        
        # Define connection check function
        async def connection_check():
            try:
                async with async_session() as session:
                    result = await session.execute(text("SELECT 1 as check_value"))
                    row = result.first()
                    if row is None:
                        return False
                    return row[0] == 1
            except Exception as e:
                logger.error(f"Connection check failed: {str(e)}")
                return False
        
        # Run with timeout
        return await asyncio.wait_for(connection_check(), timeout)
    except asyncio.TimeoutError:
        logger.error(f"Database connection check timed out after {timeout}s")
        with _stats_lock:
            _pool_stats["connection_timeouts"] += 1
        return False
    except Exception as e:
        logger.error(f"Error checking database connection: {str(e)}")
        return False

def get_connection_metrics() -> Dict[str, Any]:
    """
    Get connection metrics for monitoring.
    
    Returns:
        Dict[str, Any]: Connection metrics
    """
    db_stats = get_db_stats()
    pool_health = get_pool_health()
    
    return {
        "pool_size": settings.DB_POOL_SIZE,
        "max_overflow": settings.DB_MAX_OVERFLOW,
        "active_connections": db_stats.get("active_connections", 0),
        "max_concurrent": db_stats.get("max_concurrent", 0),
        "total_connections": db_stats.get("total_connections", 0),
        "connection_errors": db_stats.get("connection_errors", 0),
        "connection_warnings": pool_health.get("connection_warnings", 0),
        "health_status": pool_health.get("health_status", "unknown"),
        "slow_queries": pool_health.get("slow_queries", 0),
        "connection_timeouts": pool_health.get("connection_timeouts", 0),
    }

# Initialize global monitor instance that can be used by the application
monitor = ConnectionPoolMonitor(interval=300)  # 5 minute interval 