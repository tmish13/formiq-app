"""Performance monitoring and telemetry service."""
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import time
from prometheus_client import Counter, Histogram, Gauge
from app.core.config import settings
from app.core.logging import get_logger
from app.core.cache import RedisClient

logger = get_logger(__name__)

# Prometheus metrics
REQUEST_LATENCY = Histogram(
    'request_duration_seconds',
    'Request latency in seconds',
    ['method', 'endpoint']
)

ERROR_COUNTER = Counter(
    'errors_total',
    'Total number of errors',
    ['type', 'endpoint']
)

ACTIVE_USERS = Gauge(
    'active_users',
    'Number of currently active users'
)

API_REQUESTS = Counter(
    'api_requests_total',
    'Total number of API requests',
    ['method', 'endpoint', 'status']
)

CACHE_HITS = Counter(
    'cache_hits_total',
    'Total number of cache hits',
    ['cache_type']
)

CACHE_MISSES = Counter(
    'cache_misses_total',
    'Total number of cache misses',
    ['cache_type']
)

class MonitoringService:
    """Service for monitoring application performance and collecting telemetry."""

    def __init__(self):
        """Initialize monitoring service."""
        self.redis = RedisClient()
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
        return {
            "uptime": time.time() - self._start_time,
            "active_users": ACTIVE_USERS._value.get(),
            "error_rate": self._calculate_error_rate(),
            "average_response_time": self._calculate_average_response_time(),
            "cache_hit_rate": self._calculate_cache_hit_rate(),
            "memory_usage": self._get_memory_usage()
        }

    def _calculate_error_rate(self) -> float:
        """Calculate the current error rate."""
        total_requests = sum(self._value.get() for metric in API_REQUESTS._metrics.values())
        total_errors = sum(self._value.get() for metric in ERROR_COUNTER._metrics.values())
        return total_errors / total_requests if total_requests > 0 else 0

    def _calculate_average_response_time(self) -> float:
        """Calculate the average response time."""
        return REQUEST_LATENCY._sum.get() / REQUEST_LATENCY._count.get() if REQUEST_LATENCY._count.get() > 0 else 0

    def _calculate_cache_hit_rate(self) -> float:
        """Calculate the cache hit rate."""
        hits = sum(self._value.get() for metric in CACHE_HITS._metrics.values())
        misses = sum(self._value.get() for metric in CACHE_MISSES._metrics.values())
        total = hits + misses
        return hits / total if total > 0 else 0

    def _get_memory_usage(self) -> Dict[str, float]:
        """Get current memory usage statistics."""
        import psutil
        process = psutil.Process()
        memory_info = process.memory_info()
        return {
            "rss": memory_info.rss / 1024 / 1024,  # RSS in MB
            "vms": memory_info.vms / 1024 / 1024,  # VMS in MB
        }

    async def get_performance_report(self, time_range: Optional[timedelta] = None) -> Dict[str, Any]:
        """Generate a comprehensive performance report."""
        if not time_range:
            time_range = timedelta(hours=24)

        metrics = await self.collect_performance_metrics()
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "time_range": str(time_range),
            "summary": {
                "status": "healthy" if metrics["error_rate"] < 0.01 else "degraded",
                "uptime": metrics["uptime"],
                "active_users": metrics["active_users"]
            },
            "performance": {
                "error_rate": metrics["error_rate"],
                "average_response_time": metrics["average_response_time"],
                "cache_hit_rate": metrics["cache_hit_rate"],
                "memory_usage": metrics["memory_usage"]
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
        
        if metrics["error_rate"] > 0.01:
            alerts.append({
                "level": "error",
                "message": f"High error rate: {metrics['error_rate']:.2%}"
            })
            
        if metrics["average_response_time"] > 0.5:
            alerts.append({
                "level": "warning",
                "message": f"High average response time: {metrics['average_response_time']:.2f}s"
            })
            
        if metrics["cache_hit_rate"] < 0.8:
            alerts.append({
                "level": "warning",
                "message": f"Low cache hit rate: {metrics['cache_hit_rate']:.2%}"
            })
            
        return alerts

monitoring_service = MonitoringService() 