from typing import Dict, Any, Optional
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

# Authentication metrics
AUTH_FAILED_LOGINS = Counter(
    'auth_failed_login_attempts_total',
    'Total number of failed login attempts',
    ['user_email', 'ip_address']
)

AUTH_PASSWORD_RESETS = Counter(
    'auth_password_reset_requests_total',
    'Total number of password reset requests',
    ['user_email', 'status']
)

AUTH_EMAIL_VERIFICATIONS = Counter(
    'auth_email_verification_attempts_total',
    'Total number of email verification attempts',
    ['user_email', 'status']
)

# Session metrics
SESSION_DURATION = Histogram(
    'auth_session_duration_seconds',
    'Duration of user sessions',
    ['user_id'],
    buckets=(300, 900, 1800, 3600, 7200, 14400, 28800, 86400)  # 5m, 15m, 30m, 1h, 2h, 4h, 8h, 24h
)

ACTIVE_SESSIONS = Gauge(
    'auth_active_sessions',
    'Number of currently active sessions',
    ['user_id']
)

# Rate limiting metrics
RATE_LIMIT_HITS = Counter(
    'auth_rate_limit_hits_total',
    'Total number of rate limit hits',
    ['endpoint', 'ip_address']
)

# Video processing metrics
VIDEO_PROCESSING_DURATION = Histogram(
    'video_processing_duration_seconds',
    'Duration of video processing',
    ['exercise_type'],
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0]
)

VIDEO_FRAME_COUNT = Histogram(
    'video_frame_count',
    'Number of frames processed per video',
    ['exercise_type'],
    buckets=[10, 30, 60, 120, 300]
)

VIDEO_PROCESSING_ERRORS = Counter(
    'video_processing_errors_total',
    'Total number of video processing errors',
    ['error_type']
)

VIDEO_UPLOAD_SIZE = Histogram(
    'video_upload_size_bytes',
    'Size of uploaded videos in bytes',
    ['exercise_type'],
    buckets=(1e6, 5e6, 10e6, 50e6, 100e6)  # 1MB, 5MB, 10MB, 50MB, 100MB
)

# ML model metrics
MODEL_INFERENCE_ERRORS = Counter(
    'model_inference_errors_total',
    'Total number of ML model inference errors',
    ['model_type', 'error_type']
)

# Feedback system metrics
FEEDBACK_MESSAGES_SENT = Counter(
    'feedback_messages_sent_total',
    'Total number of feedback messages sent',
    ['exercise_type']
)

FEEDBACK_ITEMS_SENT = Counter(
    'feedback_items_sent_total',
    'Total number of feedback items sent',
    ['user_id']
)

ACTIVE_WEBSOCKET_CONNECTIONS = Gauge(
    'active_websocket_connections',
    'Number of active WebSocket connections',
    ['exercise_type']
)

WEBSOCKET_ERRORS = Counter(
    'websocket_errors_total',
    'Total number of WebSocket errors',
    ['error_type']
)

# Progress tracking metrics
PROGRESS_UPDATES = Counter(
    'progress_updates_total',
    'Total number of progress updates',
    ['user_id', 'exercise_type']
)

EXERCISE_FORM_SCORES = Histogram(
    'exercise_form_scores',
    'Distribution of exercise form scores',
    ['exercise_type'],
    buckets=[0.1, 0.3, 0.5, 0.7, 0.9]
)

EXERCISE_CONSISTENCY_SCORES = Histogram(
    'exercise_consistency_scores',
    'Distribution of exercise consistency scores',
    ['exercise_type'],
    buckets=(0.1, 0.3, 0.5, 0.7, 0.9)
)

EXERCISE_REPS = Counter(
    'exercise_reps_total',
    'Total number of exercise repetitions',
    ['user_id', 'exercise_type']
)

EXERCISE_REPS_COMPLETED = Counter(
    'exercise_reps_completed_total',
    'Total number of exercise repetitions completed',
    ['exercise_type', 'user_id']
)

EXERCISE_DURATION = Histogram(
    'exercise_duration_seconds',
    'Duration of exercise sessions',
    ['exercise_type'],
    buckets=[30, 60, 120, 300, 600]
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

def track_model_inference(
    exercise_type: str,
    frame_count: int,
    has_errors: bool,
    model_type: str,
    duration: float,
    confidence: float,
    error_type: Optional[str] = None
) -> None:
    """Track ML model inference metrics."""
    # Track inference duration
    model_inference_duration.labels(
        model_type=model_type,
        operation=exercise_type
    ).observe(duration)
    
    # Track confidence scores
    model_confidence_scores.labels(
        model_type=model_type,
        keypoint_type=exercise_type
    ).observe(confidence)
    
    # Track errors if any
    if has_errors and error_type:
        MODEL_INFERENCE_ERRORS.labels(
            model_type=model_type,
            error_type=error_type
        ).inc()

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

def track_failed_login(email: str, ip_address: str) -> None:
    """Track failed login attempt."""
    AUTH_FAILED_LOGINS.labels(user_email=email, ip_address=ip_address).inc()

def track_password_reset(email: str, status: str) -> None:
    """Track password reset request."""
    AUTH_PASSWORD_RESETS.labels(user_email=email, status=status).inc()

def track_email_verification(email: str, status: str) -> None:
    """Track email verification attempt."""
    AUTH_EMAIL_VERIFICATIONS.labels(user_email=email, status=status).inc()

def track_session_start(user_id: int) -> None:
    """Track new session start."""
    ACTIVE_SESSIONS.labels(user_id=str(user_id)).inc()

def track_session_end(user_id: int, duration_seconds: float) -> None:
    """Track session end and duration."""
    ACTIVE_SESSIONS.labels(user_id=str(user_id)).dec()
    SESSION_DURATION.labels(user_id=str(user_id)).observe(duration_seconds)

def track_rate_limit_hit(endpoint: str, ip_address: str) -> None:
    """Track rate limit hit."""
    RATE_LIMIT_HITS.labels(endpoint=endpoint, ip_address=ip_address).inc()

def track_video_processing(
    exercise_type: str,
    duration: float,
    frame_count: int,
    error_type: Optional[str] = None
) -> None:
    """Track video processing metrics."""
    # Track processing duration
    VIDEO_PROCESSING_DURATION.labels(
        exercise_type=exercise_type
    ).observe(duration)
    
    # Track frame count
    VIDEO_FRAME_COUNT.labels(
        exercise_type=exercise_type
    ).observe(frame_count)
    
    # Track errors if any
    if error_type:
        VIDEO_PROCESSING_ERRORS.labels(
            error_type=error_type
        ).inc()

def track_video_upload(exercise_type: str, size_bytes: int) -> None:
    """Track video upload metrics."""
    VIDEO_UPLOAD_SIZE.labels(exercise_type=exercise_type).observe(size_bytes)

def track_feedback_sent(
    exercise_type: str,
    message_count: int = 1
) -> None:
    """Track feedback message metrics."""
    FEEDBACK_MESSAGES_SENT.labels(
        exercise_type=exercise_type
    ).inc(message_count)

def track_websocket_connection(
    exercise_type: str,
    is_connected: bool
) -> None:
    """Track WebSocket connection metrics."""
    if is_connected:
        ACTIVE_WEBSOCKET_CONNECTIONS.labels(
            exercise_type=exercise_type
        ).inc()
    else:
        ACTIVE_WEBSOCKET_CONNECTIONS.labels(
            exercise_type=exercise_type
        ).dec()

def track_websocket_error(error_type: str) -> None:
    """Track WebSocket error metrics."""
    WEBSOCKET_ERRORS.labels(
        error_type=error_type
    ).inc()

def track_progress_update(
    user_id: int,
    exercise_type: str,
    metrics_updated: int,
    form_score: Optional[float] = None,
    consistency_score: Optional[float] = None,
    reps: Optional[int] = None
) -> None:
    """Track progress update metrics."""
    PROGRESS_UPDATES.labels(
        user_id=str(user_id),
        exercise_type=exercise_type
    ).inc()
    
    if form_score is not None:
        EXERCISE_FORM_SCORES.labels(
            exercise_type=exercise_type
        ).observe(form_score)
    
    if consistency_score is not None:
        EXERCISE_CONSISTENCY_SCORES.labels(
            exercise_type=exercise_type
        ).observe(consistency_score)
    
    if reps is not None:
        EXERCISE_REPS.labels(
            user_id=str(user_id),
            exercise_type=exercise_type
        ).inc(reps)

def track_exercise_progress(
    exercise_type: str,
    user_id: str,
    reps: int,
    form_score: float,
    duration: float
) -> None:
    """Track exercise progress metrics."""
    # Track completed reps
    EXERCISE_REPS_COMPLETED.labels(
        exercise_type=exercise_type,
        user_id=user_id
    ).inc(reps)
    
    # Track form score
    EXERCISE_FORM_SCORES.labels(
        exercise_type=exercise_type
    ).observe(form_score)
    
    # Track exercise duration
    EXERCISE_DURATION.labels(
        exercise_type=exercise_type
    ).observe(duration)

def init_monitoring():
    """Initialize monitoring at application startup.
    
    This function initializes all monitoring systems,
    including Prometheus metrics, system metrics, and
    custom application metrics.
    """
    logger.info("Initializing monitoring system")
    
    try:
        # Initialize system metrics
        update_system_metrics()
        
        # Set initial values for database connections
        db_connections.labels(state="idle").set(0)
        db_connections.labels(state="active").set(0)
        db_connections.labels(state="total").set(0)
        
        # Set initial values for business metrics
        active_users.set(0)
        
        logger.info("Monitoring system initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize monitoring: {str(e)}")
        # Don't fail startup if monitoring initialization fails
        # This isn't critical for application operation 