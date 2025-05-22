"""Performance monitoring and telemetry service."""
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import time
import psutil
import redis # Import redis for type hint
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry
from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.schemas.monitoring import SystemEvent, SystemEventCreate, ServiceHealth, ServiceStatus, MonitoringDataResponse, SystemEventFilter
from app.core.redis import get_redis as get_redis_client

logger = get_logger(__name__)

# Create a specific registry for this application's metrics
# This helps avoid conflicts with other possible Prometheus clients or global state issues
app_specific_registry = CollectorRegistry()

# --- Metrics Initialization ---
_metrics_initialized = False
REQUEST_LATENCY = None
ERROR_COUNTER = None
ACTIVE_USERS = None
API_REQUESTS = None
CACHE_HITS = None
CACHE_MISSES = None

def initialize_app_metrics():
    """Initializes all Prometheus metrics for the application using a specific registry."""
    global _metrics_initialized
    global REQUEST_LATENCY, ERROR_COUNTER, ACTIVE_USERS, API_REQUESTS, CACHE_HITS, CACHE_MISSES

    if _metrics_initialized:
        return

    REQUEST_LATENCY = Histogram(
        'formiq_request_duration_seconds',  # Prefixed to ensure uniqueness
        'Request latency in seconds',
        ['method', 'endpoint'],
        registry=app_specific_registry
    )

    ERROR_COUNTER = Counter(
        'formiq_errors_total',  # Prefixed
        'Total number of errors',
        ['type', 'endpoint'],
        registry=app_specific_registry
    )

    ACTIVE_USERS = Gauge(
        'formiq_active_users',  # Prefixed
        'Number of currently active users',
        registry=app_specific_registry
    )

    API_REQUESTS = Counter(
        'formiq_api_requests_total',  # Prefixed
        'Total number of API requests',
        ['method', 'endpoint', 'status'],
        registry=app_specific_registry
    )

    CACHE_HITS = Counter(
        'formiq_cache_hits_total',  # Prefixed
        'Total number of cache hits',
        ['cache_type'],
        registry=app_specific_registry
    )

    CACHE_MISSES = Counter(
        'formiq_cache_misses_total',  # Prefixed
        'Total number of cache misses',
        ['cache_type'],
        registry=app_specific_registry
    )
    _metrics_initialized = True

initialize_app_metrics() # Initialize metrics when module is loaded

class MonitoringService:
    """Service for monitoring application performance and collecting telemetry."""

    def __init__(self, app_settings: Settings, redis_client: Optional[redis.Redis] = None):
        """Initialize monitoring service."""
        self.settings = app_settings
        self.redis = redis_client
        self._start_time = time.time()
        self._request_times: Dict[str, float] = {}

    def track_request_start(self, request_id: str) -> None:
        """Track the start time of a request."""
        self._request_times[request_id] = time.time()

    def track_request_end(self, request_id: str, method: str, endpoint: str, status: int) -> None:
        """Track the end time of a request and record metrics."""
        if request_id in self._request_times:
            duration = time.time() - self._request_times[request_id]
            REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(duration)
            API_REQUESTS.labels(method=method, endpoint=endpoint, status=status).inc()
            del self._request_times[request_id]

    def track_error(self, error_type: str, endpoint: str) -> None:
        """Track an error occurrence."""
        ERROR_COUNTER.labels(type=error_type, endpoint=endpoint).inc()
        logger.error(f"Error occurred: {error_type} at {endpoint}")

    def track_cache_operation(self, cache_type: str, hit: bool) -> None:
        """Track cache hit/miss."""
        if hit:
            CACHE_HITS.labels(cache_type=cache_type).inc()
        else:
            CACHE_MISSES.labels(cache_type=cache_type).inc()

    def update_active_users(self, count: int) -> None:
        """Update the active users gauge."""
        ACTIVE_USERS.set(count)

    async def collect_performance_metrics(self) -> Dict[str, Any]:
        """Collect various performance metrics."""
        active_users_value = 0
        try:
            if hasattr(ACTIVE_USERS, '_value') and hasattr(ACTIVE_USERS._value, 'get'):
                 active_users_value = ACTIVE_USERS._value.get()
            elif hasattr(ACTIVE_USERS, '_value'):
                 active_users_value = ACTIVE_USERS._value
        except Exception as e:
            logger.warning(f"Could not retrieve ACTIVE_USERS value directly: {e}")

        return {
            "uptime": time.time() - self._start_time,
            "active_users": active_users_value,
            "error_rate": self._calculate_error_rate(),
            "average_response_time": self._calculate_average_response_time(),
            "cache_hit_rate": self._calculate_cache_hit_rate(),
            "memory_usage": self._get_memory_usage()
        }

    def _calculate_error_rate(self) -> float:
        """Calculate the current error rate."""
        total_requests = 0
        if hasattr(API_REQUESTS, '_metrics'):
            total_requests = sum(m._value for m in API_REQUESTS._metrics.values() if hasattr(m, '_value'))
        
        total_errors = 0
        if hasattr(ERROR_COUNTER, '_metrics'):
            total_errors = sum(m._value for m in ERROR_COUNTER._metrics.values() if hasattr(m, '_value'))
            
        return total_errors / total_requests if total_requests > 0 else 0.0

    def _calculate_average_response_time(self) -> float:
        """Calculate the average response time."""
        request_sum = 0.0
        request_count = 0.0
        if hasattr(REQUEST_LATENCY, '_sum') and hasattr(REQUEST_LATENCY._sum, 'get'):
            request_sum = REQUEST_LATENCY._sum.get()
        if hasattr(REQUEST_LATENCY, '_count') and hasattr(REQUEST_LATENCY._count, 'get'):
            request_count = REQUEST_LATENCY._count.get()
        return request_sum / request_count if request_count > 0 else 0.0

    def _calculate_cache_hit_rate(self) -> float:
        """Calculate the cache hit rate."""
        hits = 0
        if hasattr(CACHE_HITS, '_metrics'):
            hits = sum(m._value for m in CACHE_HITS._metrics.values() if hasattr(m, '_value'))
        misses = 0
        if hasattr(CACHE_MISSES, '_metrics'):
            misses = sum(m._value for m in CACHE_MISSES._metrics.values() if hasattr(m, '_value'))
        total = hits + misses
        return hits / total if total > 0 else 0.0

    def _get_memory_usage(self) -> Dict[str, float]:
        """Get current memory usage statistics."""
        process = psutil.Process()
        memory_info = process.memory_info()
        return {
            "rss": memory_info.rss / (1024 * 1024),  # RSS in MB
            "vms": memory_info.vms / (1024 * 1024),  # VMS in MB
        }

    async def get_performance_report(self, time_range: Optional[timedelta] = None) -> Dict[str, Any]:
        """Generate a comprehensive performance report."""
        if not time_range:
            time_range = timedelta(hours=24)

        metrics = await self.collect_performance_metrics()
        
        error_rate_val = metrics.get("error_rate", 0.0) 

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "time_range": str(time_range),
            "summary": {
                "status": "healthy" if error_rate_val < 0.01 else "degraded",
                "uptime": metrics.get("uptime"),
                "active_users": metrics.get("active_users")
            },
            "performance": {
                "error_rate": error_rate_val,
                "average_response_time": metrics.get("average_response_time"),
                "cache_hit_rate": metrics.get("cache_hit_rate"),
                "memory_usage": metrics.get("memory_usage")
            },
            "thresholds": {
                "error_rate_threshold": 0.01,
                "response_time_threshold": 0.5,
                "cache_hit_rate_threshold": 0.8
            },
            "alerts": self._generate_alerts(metrics)
        }

    def _generate_alerts(self, metrics: Dict[str, Any]) -> list:
        """Generate alerts based on metric thresholds."""
        alerts = []
        error_rate_val = metrics.get("error_rate", 0.0)
        avg_response_time_val = metrics.get("average_response_time", 0.0)
        cache_hit_rate_val = metrics.get("cache_hit_rate", 0.0)

        if error_rate_val > 0.01:
            alerts.append({
                "level": "error",
                "message": f"High error rate: {error_rate_val:.2%}"
            })
            
        if avg_response_time_val > 0.5:
            alerts.append({
                "level": "warning",
                "message": f"High average response time: {avg_response_time_val:.2f}s"
            })
            
        if cache_hit_rate_val < 0.8 and cache_hit_rate_val > 0:
            alerts.append({
                "level": "warning",
                "message": f"Low cache hit rate: {cache_hit_rate_val:.2%}"
            })
            
        return alerts

from fastapi import Depends
from app.core.config import get_settings
from redis import Redis as SyncRedis

async def get_async_monitoring_service(
    app_settings: Settings = Depends(get_settings),
    redis_client: Optional[SyncRedis] = Depends(get_redis_client)
) -> MonitoringService:
    """Dependency provider for MonitoringService."""
    return MonitoringService(app_settings=app_settings, redis_client=redis_client) 