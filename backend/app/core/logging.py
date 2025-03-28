import json
import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
import structlog
from typing import Any, Dict, Optional
from app.core.config import settings
import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration

# Configure Sentry for error tracking
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

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    logger_factory=structlog.PrintLoggerFactory(),
)

# Create logger
logger = structlog.get_logger()

# Configure standard logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('app.log')
    ]
)

# Create standard logger
std_logger = logging.getLogger(__name__)

class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as JSON."""
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add extra fields if they exist
        if hasattr(record, "extra"):
            log_data.update(record.extra)
        
        # Add exception info if it exists
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)

def setup_logging():
    """Configure logging for the application."""
    # Create logs directory
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True
    )

    # Configure file handler
    file_handler = RotatingFileHandler(
        log_dir / "app.log",
        maxBytes=10485760,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.INFO)

    # Configure console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # Create logger for the application
    logger = structlog.get_logger("formiq")
    return logger

def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with proper configuration."""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, settings.LOG_LEVEL))
    
    # Prevent duplicate handlers
    if logger.handlers:
        return logger
    
    # Create formatters
    json_formatter = JSONFormatter()
    console_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    file_handler = RotatingFileHandler(
        log_dir / "app.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setFormatter(json_formatter)
    logger.addHandler(file_handler)
    
    # Error file handler
    error_file_handler = RotatingFileHandler(
        log_dir / "error.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8"
    )
    error_file_handler.setLevel(logging.ERROR)
    error_file_handler.setFormatter(json_formatter)
    logger.addHandler(error_file_handler)
    
    return logger

# Initialize logging
logger = setup_logging()

def log_error(
    message: str,
    error: Exception,
    extra: Dict[str, Any] = None,
    logger_name: str = "app"
) -> None:
    """Log an error with proper formatting."""
    log = get_logger(logger_name)
    error_data = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        **(extra or {})
    }
    log.error(message, extra=error_data)

def log_info(
    message: str,
    extra: Dict[str, Any] = None,
    logger_name: str = "app"
) -> None:
    """Log an info message with proper formatting."""
    log = get_logger(logger_name)
    log.info(message, extra=extra or {})

def log_warning(
    message: str,
    extra: Dict[str, Any] = None,
    logger_name: str = "app"
) -> None:
    """Log a warning message with proper formatting."""
    log = get_logger(logger_name)
    log.warning(message, extra=extra or {})

def log_debug(
    message: str,
    extra: Dict[str, Any] = None,
    logger_name: str = "app"
) -> None:
    """Log a debug message with proper formatting."""
    log = get_logger(logger_name)
    log.debug(message, extra=extra or {})

def get_logger():
    """Get the structured logger instance."""
    return logger

def get_std_logger():
    """Get the standard logger instance."""
    return std_logger 