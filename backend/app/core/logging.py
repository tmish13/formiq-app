"""Logging configuration module."""
import json
import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
import structlog
from typing import Any, Dict, Optional
import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from app.core.config import settings
from app.core.constants import (
    LOG_FORMAT,
    LOG_DATE_FORMAT,
    LOG_FILE_MAX_BYTES,
    LOG_FILE_BACKUP_COUNT,
    LOG_DIR,
    LOG_FILE,
    ERROR_LOG_FILE,
)
import os
from datetime import datetime
import traceback

class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as JSON."""
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "environment": settings.ENVIRONMENT,
            "service": settings.PROJECT_NAME,
            "version": settings.VERSION,
        }
        
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
            
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
            
        if hasattr(record, "extra"):
            log_data.update(record.extra)
            
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_data)

def get_log_level() -> str:
    """Get the appropriate log level based on environment."""
    if settings.ENVIRONMENT == "production":
        return "INFO"
    elif settings.ENVIRONMENT == "staging":
        return "INFO"
    elif settings.ENVIRONMENT == "test":
        return "DEBUG" if settings.DEBUG else "INFO"
    else:  # development
        return "DEBUG" if settings.DEBUG else "INFO"

def init_sentry() -> None:
    """Initialize Sentry for error tracking."""
    if settings.SENTRY_DSN:
        sentry_logging = LoggingIntegration(
            level=logging.INFO,
            event_level=logging.ERROR
        )
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            integrations=[
                sentry_logging,
                SqlalchemyIntegration(),
                RedisIntegration(),
            ],
            traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
            environment=settings.SENTRY_ENVIRONMENT,
            release=settings.VERSION
        )

def setup_logging() -> None:
    """Configure logging with both file and console handlers."""
    # Create logs directory if it doesn't exist
    log_dir = Path(LOG_DIR)
    log_dir.mkdir(exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(get_log_level())
    
    # Clear existing handlers
    root_logger.handlers = []
    
    # Main log file handler with daily rotation
    file_handler = TimedRotatingFileHandler(
        LOG_FILE,
        when="midnight",
        interval=1,
        backupCount=30,  # Keep 30 days of logs
        encoding="utf-8"
    )
    file_handler.setFormatter(JSONFormatter())
    file_handler.setLevel(get_log_level())
    
    # Error log file handler with size-based rotation
    error_handler = RotatingFileHandler(
        ERROR_LOG_FILE,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8"
    )
    error_handler.setFormatter(JSONFormatter())
    error_handler.setLevel(logging.ERROR)
    
    # Console handler with color formatting in development
    console_handler = logging.StreamHandler(sys.stdout)
    if settings.ENVIRONMENT == "development":
        console_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
        )
    else:
        console_handler.setFormatter(JSONFormatter())
    console_handler.setLevel(get_log_level())
    
    # Add handlers
    root_logger.addHandler(file_handler)
    root_logger.addHandler(error_handler)
    root_logger.addHandler(console_handler)
    
    # Set log levels for third-party libraries
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("redis").setLevel(logging.WARNING)
    
    # Initialize Sentry if configured
    if settings.ENVIRONMENT != "test":
        init_sentry()

# Initialize logging
setup_logging()

# Create logger instance
logger = structlog.get_logger("app")

def get_logger(name: str) -> structlog.BoundLogger:
    """Get a structured logger instance with the specified name."""
    return structlog.get_logger(name)

def log_error(
    message: str,
    error: Exception,
    extra: Optional[Dict[str, Any]] = None,
    logger_name: str = "app"
) -> None:
    """Log an error with exception details."""
    log_data = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        "traceback": traceback.format_exc()
    }
    if extra:
        log_data.update(extra)
    logger.error(message, extra=log_data)

def log_info(
    message: str,
    extra: Optional[Dict[str, Any]] = None,
    logger_name: str = "app"
) -> None:
    """Log an info message with proper formatting."""
    log = get_logger(logger_name)
    log.info(message, **(extra or {}))

def log_warning(
    message: str,
    extra: Optional[Dict[str, Any]] = None,
    logger_name: str = "app"
) -> None:
    """Log a warning message with proper formatting."""
    log = get_logger(logger_name)
    log.warning(message, **(extra or {}))

def log_debug(
    message: str,
    extra: Optional[Dict[str, Any]] = None,
    logger_name: str = "app"
) -> None:
    """Log a debug message with proper formatting."""
    log = get_logger(logger_name)
    log.debug(message, **(extra or {})) 