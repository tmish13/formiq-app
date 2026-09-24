"""Logging configuration for the application."""
import logging
import logging.handlers
import os
import sys
from typing import Dict, Any, Optional
import json
from pathlib import Path
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
import structlog
from logging.config import dictConfig

from app.core.config import settings

import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.redis import RedisIntegration

# Constants
LOG_DIR = os.path.join(os.getcwd(), "logs")
LOG_FILE = os.path.join(LOG_DIR, "app.log")
ERROR_LOG_FILE = os.path.join(LOG_DIR, "error.log")

from app.core.redaction import redact_event

# Custom processor to add trace context to logs
def add_trace_context(logger, method_name, event_dict):
    """Add OpenTelemetry trace context to log records."""
    try:
        from app.core.tracing import get_trace_context
        trace_context = get_trace_context()
        event_dict.update(trace_context)
    except Exception:
        # Gracefully handle cases where tracing is not available
        pass
    return event_dict

# Structlog configuration for JSON output
structlog.configure(
    processors=[
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info, # Sets exc_info correctly for format_exc_info
        structlog.processors.format_exc_info, # Formats the exception
        structlog.processors.TimeStamper(fmt="iso", key="timestamp"), # Adds timestamp
        add_trace_context,  # Add OpenTelemetry trace context
        # Add environment to the log output if needed by all logs
        structlog.processors.dict_tracebacks, # For better tracebacks in JSON
        redact_event,  # G-16: credentials and e-mail local parts never reach the renderer
        structlog.processors.JSONRenderer()  # Renders the final dict to JSON string
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

def setup_logging(
    environment: str = settings.ENVIRONMENT,
    log_level: str = None,
    log_file: str = LOG_FILE,
    sentry_dsn: str = settings.SENTRY_DSN
) -> None:
    """
    Configure application logging. structlog will format to JSON.
    Standard library handlers will just pass through the pre-formatted message.
    """
    log_dir_path = Path(log_file).parent # Path import needed
    log_dir_path.mkdir(parents=True, exist_ok=True)
    error_log_dir_path = Path(ERROR_LOG_FILE).parent
    error_log_dir_path.mkdir(parents=True, exist_ok=True)

    if log_level is None:
        log_level_to_use = "DEBUG" if settings.DEBUG else "INFO"
    else:
        log_level_to_use = log_level.upper()
    numeric_level = getattr(logging, log_level_to_use, logging.INFO)

    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "passthrough": { # For messages already formatted by structlog
                "format": "%(message)s"
            },
            "standard_dev": { # For development console, if non-JSON is preferred for readability
                 "format": "%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
                 "datefmt": "%Y-%m-%d %H:%M:%S"
            }
        },
        "filters": {
            # G-16: every handler scrubs stdlib records too (structlog records are scrubbed upstream)
            "redact": {"()": "app.core.redaction.RedactingFilter"}
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "filters": ["redact"],
                "formatter": "standard_dev" if environment == "development" else "passthrough",
                "stream": sys.stdout,
                "level": numeric_level
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "filters": ["redact"],
                "formatter": "passthrough", # structlog provides JSON
                "filename": log_file,
                "maxBytes": settings.LOG_MAX_BYTES,
                "backupCount": settings.LOG_BACKUP_COUNT,
                "level": numeric_level
            },
            "error_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "filters": ["redact"],
                "formatter": "passthrough", # structlog provides JSON
                "filename": ERROR_LOG_FILE,
                "maxBytes": settings.LOG_MAX_BYTES,
                "backupCount": settings.LOG_BACKUP_COUNT,
                "level": logging.ERROR
            }
        },
        "loggers": {
            "": { 
                "handlers": ["console", "file", "error_file"],
                "level": numeric_level,
                "propagate": False # Set to False if this is the final handling point for root
            },
            "uvicorn.access": {
                "handlers": ["console"],
                "level": logging.WARNING,
                "propagate": False
            },
            "uvicorn.error": {
                "handlers": ["console", "error_file"],
                "level": numeric_level,
                "propagate": False
            },
            "sqlalchemy": {
                "handlers": ["console"],
                "level": logging.WARNING,
                "propagate": False
            },
            "app": { # Specific logger for app, if needed for separate handling
                "handlers": ["console", "file", "error_file"],
                "level": numeric_level,
                "propagate": False
            }
        }
    }
    
    if sentry_dsn and (environment != "development" or settings.SENTRY_ENABLED_IN_DEVELOPMENT):
      # Sentry setup (remains largely the same)
        try:
            sentry_logging_integration = LoggingIntegration(
                level=logging.INFO, 
                event_level=logging.ERROR 
            )
            sentry_sdk.init(
                dsn=sentry_dsn,
                environment=environment,
                integrations=[
                    sentry_logging_integration, 
                    SqlalchemyIntegration(),
                    RedisIntegration()
                ],
                traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE, 
                release=settings.VERSION,
                send_default_pii=True 
            )
            logging.info("Sentry initialized for error reporting.") # This will be structlog formatted
        except ImportError:
            logging.warning("Sentry SDK not installed or import error. Sentry error reporting disabled.")
        except Exception as e:
            logging.error(f"Failed to initialize Sentry: {e}", exc_info=True)

    dictConfig(config)
    
    # Initial log message using structlog logger
    init_logger = get_logger("app.core.logging.setup") # get_logger now returns structlog logger
    init_logger.info(
        "Application logging configured with structlog to JSON.",
        environment=environment,
        log_level_configured=log_level_to_use,
        sentry_enabled=bool(sentry_dsn and (environment != "development" or settings.SENTRY_ENABLED_IN_DEVELOPMENT)),
        log_file_path=log_file,
        error_log_file_path=ERROR_LOG_FILE
    )

def get_logger(name: str) -> structlog.BoundLogger:
    """Get a structured logger instance with the specified name."""
    return structlog.get_logger(name)

def log_error(
    message: str,
    error: Optional[Exception] = None, 
    logger_name: str = "app",
    **kwargs: Any 
) -> None:
    """Log an error with exception details using structlog."""
    log = get_logger(logger_name)
    if error:
        log.error(message, exc_info=error, **kwargs)
    else:
        log.error(message, **kwargs)

def log_info(
    message: str,
    logger_name: str = "app",
    **kwargs: Any 
) -> None:
    """Log an info message with proper formatting using structlog."""
    log = get_logger(logger_name)
    log.info(message, **kwargs)

def log_warning(
    message: str,
    logger_name: str = "app",
    **kwargs: Any 
) -> None:
    """Log a warning message with proper formatting using structlog."""
    log = get_logger(logger_name)
    log.warning(message, **kwargs)

def log_debug(
    message: str,
    logger_name: str = "app",
    **kwargs: Any
) -> None:
    """Log a debug message with proper formatting using structlog."""
    log = get_logger(logger_name)
    log.debug(message, **kwargs)

logger = get_logger("app")
init_logging = setup_logging 