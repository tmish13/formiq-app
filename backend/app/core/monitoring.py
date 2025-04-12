from typing import Dict, Any
from prometheus_client import Counter, Histogram, Gauge, Summary
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import REGISTRY, PROCESS_COLLECTOR, PLATFORM_COLLECTOR
from prometheus_client.exposition import generate_latest
from fastapi import FastAPI, Response
from app.core.logging import get_logger
from app.core.config import settings
import psutil
import time
from datetime import datetime

logger = get_logger(__name__)

# Remove default collectors
REGISTRY.unregister(PROCESS_COLLECTOR)
REGISTRY.unregister(PLATFORM_COLLECTOR)

# HTTP metrics
http_requests_total = Counter(
    "http_requests_total",
    "Total number of HTTP requests",
    ["method", "endpoint", "status"]
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0]
)

# Database metrics
db_query_duration_seconds = Histogram(
    "db_query_duration_seconds",
    "Database query duration in seconds",
    ["operation", "table"],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0]
)

db_connections = Gauge(
    "db_connections",
    "Number of active database connections",
    ["state"]
)

# Cache metrics
cache_hits = Counter(
    "cache_hits_total",
    "Total number of cache hits",
    ["namespace"]
)

cache_misses = Counter(
    "cache_misses_total",
    "Total number of cache misses",
    ["namespace"]
)

cache_size = Gauge(
    "cache_size_bytes",
    "Current size of the cache in bytes",
    ["namespace"]
)

# System metrics
cpu_usage = Gauge(
    "cpu_usage_percent",
    "Current CPU usage percentage"
)

memory_usage = Gauge(
    "memory_usage_bytes",
    "Current memory usage in bytes"
)

disk_usage = Gauge(
    "disk_usage_bytes",
    "Current disk usage in bytes"
)

# Business metrics
active_users = Gauge(
    "active_users",
    "Number of currently active users"
)

form_checks_total = Counter(
    "form_checks_total",
    "Total number of form checks submitted",
    ["status"]
)

workouts_completed = Counter(
    "workouts_completed_total",
    "Total number of completed workouts",
    ["type"]
)

# AI Model metrics
model_inference_duration = Histogram(
    "model_inference_duration_seconds",
    "AI model inference duration in seconds",
    ["model_type", "operation"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0]
)

model_confidence_scores = Histogram(
    "model_confidence_scores",
    "Distribution of model confidence scores",
    ["model_type", "keypoint_type"],
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)

model_errors = Counter(
    "model_errors_total",
    "Total number of AI model errors",
    ["model_type", "error_type"]
)

model_fallbacks = Counter(
    "model_fallbacks_total",
    "Number of times fallback model was used",
    ["primary_model", "fallback_model"]
)

# Enhanced error tracking
error_details = Counter(
    "error_details_total",
    "Detailed error tracking",
    ["service", "endpoint", "error_type", "error_code"]
)

def setup_monitoring(app: FastAPI) -> None:
    """Configure monitoring for the application."""
    try:
        # Initialize Prometheus instrumentator
        Instrumentator().instrument(app).expose(app)
        
        # Add custom metrics endpoint
        @app.get("/metrics")
        async def metrics():
            # Update system metrics
            update_system_metrics()
            
            # Generate metrics response
            return Response(generate_latest(), media_type="text/plain")
        
        logger.info("Monitoring configured successfully")
        
    except Exception as e:
        logger.error(f"Failed to configure monitoring: {str(e)}")
        raise

def update_system_metrics() -> None:
    """Update system-related metrics."""
    try:
        # CPU usage
        cpu_usage.set(psutil.cpu_percent())
        
        # Memory usage
        memory = psutil.virtual_memory()
        memory_usage.set(memory.used)
        
        # Disk usage
        disk = psutil.disk_usage("/")
        disk_usage.set(disk.used)
        
    except Exception as e:
        logger.error(f"Failed to update system metrics: {str(e)}")

def track_request(method: str, endpoint: str, duration: float, status: int) -> None:
    """Track HTTP request metrics."""
    try:
        http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status=status
        ).inc()
        
        http_request_duration_seconds.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)
        
    except Exception as e:
        logger.error(f"Failed to track request metrics: {str(e)}")

def track_db_operation(operation: str, table: str, duration: float) -> None:
    """Track database operation metrics."""
    try:
        db_query_duration_seconds.labels(
            operation=operation,
            table=table
        ).observe(duration)
        
    except Exception as e:
        logger.error(f"Failed to track DB operation metrics: {str(e)}")

def track_cache_operation(namespace: str, hit: bool) -> None:
    """Track cache operation metrics."""
    try:
        if hit:
            cache_hits.labels(namespace=namespace).inc()
        else:
            cache_misses.labels(namespace=namespace).inc()
            
    except Exception as e:
        logger.error(f"Failed to track cache operation metrics: {str(e)}")

def update_business_metrics(metrics: Dict[str, Any]) -> None:
    """Update business-related metrics."""
    try:
        if "active_users" in metrics:
            active_users.set(metrics["active_users"])
            
        if "form_checks" in metrics:
            for status, count in metrics["form_checks"].items():
                form_checks_total.labels(status=status).inc(count)
                
        if "workouts" in metrics:
            for type_, count in metrics["workouts"].items():
                workouts_completed.labels(type=type_).inc(count)
                
    except Exception as e:
        logger.error(f"Failed to update business metrics: {str(e)}")

def track_model_inference(model_type: str, operation: str, duration: float) -> None:
    """Track AI model inference duration."""
    try:
        model_inference_duration.labels(
            model_type=model_type,
            operation=operation
        ).observe(duration)
    except Exception as e:
        logger.error(f"Failed to track model inference: {str(e)}")

def track_model_confidence(model_type: str, keypoint_type: str, score: float) -> None:
    """Track model confidence scores."""
    try:
        model_confidence_scores.labels(
            model_type=model_type,
            keypoint_type=keypoint_type
        ).observe(score)
    except Exception as e:
        logger.error(f"Failed to track model confidence: {str(e)}")

def track_model_error(model_type: str, error_type: str) -> None:
    """Track AI model errors."""
    try:
        model_errors.labels(
            model_type=model_type,
            error_type=error_type
        ).inc()
    except Exception as e:
        logger.error(f"Failed to track model error: {str(e)}")

def track_model_fallback(primary_model: str, fallback_model: str) -> None:
    """Track when fallback model is used."""
    try:
        model_fallbacks.labels(
            primary_model=primary_model,
            fallback_model=fallback_model
        ).inc()
    except Exception as e:
        logger.error(f"Failed to track model fallback: {str(e)}")

def track_detailed_error(
    service: str,
    endpoint: str,
    error_type: str,
    error_code: str
) -> None:
    """Track detailed error information."""
    try:
        error_details.labels(
            service=service,
            endpoint=endpoint,
            error_type=error_type,
            error_code=error_code
        ).inc()
        
        # Log error details
        logger.error(
            "Application error",
            extra={
                "service": service,
                "endpoint": endpoint,
                "error_type": error_type,
                "error_code": error_code,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    except Exception as e:
        logger.error(f"Failed to track error details: {str(e)}") 