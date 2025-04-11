"""Logging configuration for the application."""
import logging
import logging.handlers
import os
import sys
from typing import Dict, Any, Optional
import json
from pathlib import Path
from datetime import datetime
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
import structlog

from app.core.config import settings

import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.redis import RedisIntegration

# Constants
LOG_DIR = os.path.join(os.getcwd(), "logs")
LOG_FILE = os.path.join(LOG_DIR, "app.log")
ERROR_LOG_FILE = os.path.join(LOG_DIR, "error.log")


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as JSON."""
        # Base log data
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "environment": settings.ENVIRONMENT
        }
        
        # Add extra fields from record
        if hasattr(record, "extra"):
            log_data.update(record.extra)
            
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
            
        # Add stack info if present
        if record.stack_info:
            log_data["stack_info"] = self.formatStack(record.stack_info)
            
        return json.dumps(log_data)


def setup_logging(
    environment: str = settings.ENVIRONMENT,
    log_level: str = None,
    log_file: str = LOG_FILE,
    sentry_dsn: str = settings.SENTRY_DSN
) -> None:
    """
    Configure application logging.
    
    Args:
        environment: Application environment (development, production, etc.)
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (if file logging is desired)
        sentry_dsn: Sentry DSN for error reporting
    """
    # Create logs directory if it doesn't exist
    log_dir = os.path.dirname(log_file)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
    
    # Determine log level
    if log_level is None:
        log_level = "DEBUG" if settings.DEBUG else "INFO"
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Base configuration
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": JSONFormatter
            },
            "standard": {
                "format": "%(asctime)s [%(levelname)s] %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "standard" if environment == "development" else "json",
                "stream": sys.stdout
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "json",
                "filename": log_file,
                "maxBytes": settings.LOG_MAX_BYTES,
                "backupCount": settings.LOG_BACKUP_COUNT
            },
            "error_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "json",
                "filename": ERROR_LOG_FILE,
                "maxBytes": settings.LOG_MAX_BYTES,
                "backupCount": settings.LOG_BACKUP_COUNT,
                "level": logging.ERROR
            }
        },
        "loggers": {
            "": {  # Root logger
                "handlers": ["console", "file", "error_file"],
                "level": numeric_level,
                "propagate": True
            },
            "uvicorn": {
                "handlers": ["console"],
                "level": logging.WARNING if environment == "production" else numeric_level,
                "propagate": False
            },
            "sqlalchemy": {
                "handlers": ["console"],
                "level": logging.WARNING,
                "propagate": False
            }
        }
    }
    
    # Configure Sentry if DSN is provided
    if sentry_dsn and environment != "development":
        try:
            sentry_logging = LoggingIntegration(
                level=logging.WARNING,
                event_level=logging.ERROR
            )
            
            sentry_sdk.init(
                dsn=sentry_dsn,
                environment=environment,
                integrations=[
                    sentry_logging,
                    SqlalchemyIntegration(),
                    RedisIntegration()
                ],
                traces_sample_rate=1.0 if environment != "production" else 0.1,
                release=settings.VERSION
            )
        except ImportError:
            logging.warning("Sentry SDK not installed. Error reporting disabled.")
    
    # Apply configuration
    logging.config.dictConfig(config)
    
    # Log initial configuration
    logger = logging.getLogger(__name__)
    logger.info(
        "Logging configured",
        extra={
            "environment": environment,
            "log_level": log_level,
            "sentry_enabled": bool(sentry_dsn)
        }
    )


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name.
    
    Args:
        name: Logger name (usually __name__ of the module)
        
    Returns:
        logging.Logger: Configured logger instance
    """
    return logging.getLogger(name)

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
    if settings.SENTRY_DSN and settings.SENTRY_DSN != "https://sentry.io/your-project-id":
        try:
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
        except Exception as e:
            print(f"Failed to initialize Sentry: {e}")
    else:
        print("Sentry DSN not configured, skipping initialization")

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

# Add the configure_logging function
def configure_logging() -> None:
    """
    Configure application logging at startup.
    This function is called by the main FastAPI application.
    """
    # Re-initialize logging for runtime configuration
    setup_logging()
    
    # Apply custom configurations based on environment
    if settings.ENVIRONMENT == "production":
        # Set third-party loggers to higher levels in production
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
        logging.getLogger("uvicorn.error").setLevel(logging.ERROR)
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    else:
        # Development logging
        logging.getLogger("uvicorn.access").setLevel(logging.INFO)
        logging.getLogger("uvicorn.error").setLevel(logging.INFO)
        logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO if settings.DEBUG else logging.WARNING)
    
    # Log configuration information
    logger = get_logger("app.logging")
    logger.info(
        "Logging configured",
        environment=settings.ENVIRONMENT,
        log_level=get_log_level(),
        sentry_enabled=bool(settings.SENTRY_DSN),
    ) 