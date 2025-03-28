from typing import Dict, Any
from prometheus_client import Counter, Histogram, Gauge
from prometheus_fastapi_instrumentator import Instrumentator
from fastapi import FastAPI
from app.core.logging import get_logger
from app.core.config import settings

logger = get_logger(__name__)

# Define metrics
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint']
)

DB_QUERY_LATENCY = Histogram(
    'db_query_duration_seconds',
    'Database query latency',
    ['operation']
)

CACHE_HITS = Counter(
    'cache_hits_total',
    'Total cache hits',
    ['cache_type']
)

CACHE_MISSES = Counter(
    'cache_misses_total',
    'Total cache misses',
    ['cache_type']
)

ACTIVE_CONNECTIONS = Gauge(
    'db_active_connections',
    'Number of active database connections'
)

REDIS_MEMORY_USAGE = Gauge(
    'redis_memory_usage_bytes',
    'Redis memory usage in bytes'
)

ERROR_COUNT = Counter(
    "http_errors_total",
    "Total number of HTTP errors",
    ["method", "endpoint", "error_type"]
)

DB_QUERY_DURATION = Histogram(
    "db_query_duration_seconds",
    "Database query duration in seconds",
    ["operation", "table"],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0]
)

DB_CONNECTION_POOL = Gauge(
    "db_connection_pool_size",
    "Database connection pool size",
    ["state"]
)

REDIS_CONNECTION_POOL = Gauge(
    "redis_connection_pool_size",
    "Redis connection pool size",
    ["state"]
)

def init_monitoring(app: FastAPI) -> None:
    """Initialize monitoring for the FastAPI application."""
    try:
        # Initialize FastAPI instrumentator
        instrumentator = Instrumentator(
            should_group_status_codes=True,
            should_ignore_untemplated=True,
            should_respect_env_var=True,
            should_instrument_requests_inprogress=True,
            excluded_handlers=["/metrics"],
        )
        
        # Add custom metrics
        instrumentator.add(
            REQUEST_COUNT,
            REQUEST_LATENCY,
            ERROR_COUNT,
        )
        
        # Instrument the application
        instrumentator.instrument(app).expose(app)
        
        logger.info("monitoring_setup_complete")
    except Exception as e:
        logger.error("monitoring_setup_failed", error=str(e))
        raise

def track_request(method: str, endpoint: str, status: int, duration: float):
    """Track HTTP request metrics."""
    REQUEST_COUNT.labels(
        method=method,
        endpoint=endpoint,
        status=status
    ).inc()
    
    REQUEST_LATENCY.labels(
        method=method,
        endpoint=endpoint
    ).observe(duration)

def track_db_query(operation: str, duration: float):
    """Track database query metrics."""
    DB_QUERY_LATENCY.labels(operation=operation).observe(duration)

def track_cache_hit(cache_type: str):
    """Track cache hit metrics."""
    CACHE_HITS.labels(cache_type=cache_type).inc()

def track_cache_miss(cache_type: str):
    """Track cache miss metrics."""
    CACHE_MISSES.labels(cache_type=cache_type).inc()

def update_active_connections(count: int):
    """Update active database connections count."""
    ACTIVE_CONNECTIONS.set(count)

def update_redis_memory_usage(bytes_used: int):
    """Update Redis memory usage."""
    REDIS_MEMORY_USAGE.set(bytes_used)

def record_error_metrics(
    method: str,
    endpoint: str,
    error_type: str
) -> None:
    """Record error metrics."""
    ERROR_COUNT.labels(
        method=method,
        endpoint=endpoint,
        error_type=error_type
    ).inc()

def update_connection_pool_metrics(
    db_pool_size: int,
    db_pool_used: int,
    redis_pool_size: int,
    redis_pool_used: int
) -> None:
    """Update connection pool metrics."""
    DB_CONNECTION_POOL.labels(state="total").set(db_pool_size)
    DB_CONNECTION_POOL.labels(state="used").set(db_pool_used)
    REDIS_CONNECTION_POOL.labels(state="total").set(redis_pool_size)
    REDIS_CONNECTION_POOL.labels(state="used").set(redis_pool_used) 