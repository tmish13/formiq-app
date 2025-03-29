"""Logging configuration module."""
import json
import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
import structlog
from typing import Any, Dict, Optional
import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration
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
        }
        
        if hasattr(record, "extra"):
            log_data.update(record.extra)
            
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_data)

def init_sentry() -> None:
    """Initialize Sentry for error tracking."""
    if settings.SENTRY_DSN:
        sentry_logging = LoggingIntegration(
            level=logging.INFO,
            event_level=logging.ERROR
        )
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            integrations=[sentry_logging],
            traces_sample_rate=1.0,
            environment=settings.ENVIRONMENT
        )

def setup_logging() -> None:
    """Configure logging with both file and console handlers."""
    # Create logs directory if it doesn't exist
    log_dir = Path(LOG_DIR)
    log_dir.mkdir(exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(settings.LOG_LEVEL)
    
    # Clear existing handlers
    root_logger.handlers = []
    
    # File handler with rotation
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=LOG_FILE_MAX_BYTES,
        backupCount=LOG_FILE_BACKUP_COUNT,
        encoding="utf-8"
    )
    file_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(file_handler)
    
    # Error file handler
    error_handler = RotatingFileHandler(
        ERROR_LOG_FILE,
        maxBytes=LOG_FILE_MAX_BYTES,
        backupCount=LOG_FILE_BACKUP_COUNT,
        encoding="utf-8"
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(error_handler)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(console_handler)
    
    # Set logging level for specific modules
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

# Initialize logging
setup_logging()

# Initialize Sentry
init_sentry()

# Create logger instance
logger = logging.getLogger("app")

def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the specified name."""
    return logging.getLogger(name)

def log_error(
    message: str,
    error: Exception,
    extra: Optional[Dict[str, Any]] = None,
    logger_name: str = "app"
) -> None:
    """Log an error with proper formatting."""
    log = get_logger(logger_name)
    error_data = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        **(extra or {})
    }
    log.error(message, **error_data)

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