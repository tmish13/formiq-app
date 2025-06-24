"""
Application configuration module.

This module defines all application settings loaded from environment variables.
Settings are defined as Pydantic models with validation to ensure correct types and formats.
"""
from typing import List, Union, Optional, Dict, Any, ClassVar
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AnyHttpUrl, field_validator, SecretStr, PostgresDsn, RedisDsn, HttpUrl, validator, Field
from functools import lru_cache
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from app.core.constants import (
    PROJECT_NAME,
    VERSION,
    DESCRIPTION,
    API_V1_STR,
    DEFAULT_ENVIRONMENT,
    DEFAULT_CORS_ORIGINS,
    DEFAULT_ALGORITHM,
    DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES,
    DEFAULT_SMTP_TLS,
    DEFAULT_SMTP_PORT,
    DEFAULT_LOG_LEVEL,
    DEFAULT_RATE_LIMIT_REQUESTS,
    DEFAULT_RATE_LIMIT_BURST,
    Environment
)
import base64
from datetime import datetime, timedelta
import secrets
import logging
import json
from cryptography.fernet import Fernet

BASE_DIR = Path(__file__).resolve().parent.parent.parent # Should be backend/
logger = logging.getLogger(__name__)

# Load environment variables
def load_environment():
    """
    Load the appropriate environment file based on the ENVIRONMENT variable.
    """
    env = os.getenv("ENVIRONMENT", "development").lower()
    
    # Determine file path based on environment
    root_dir = Path(__file__).parent.parent.parent
    
    # Order of environment file loading (from most to least specific)
    env_files = [
        root_dir / f".env.{env}.local",  # Most specific: .env.{env}.local
        root_dir / f".env.{env}",        # Environment-specific: .env.{env}
        root_dir / ".env.local",         # Local override: .env.local
        root_dir / ".env"                # Default: .env
    ]
    
    # Load the first file that exists
    for env_file in env_files:
        if env_file.exists():
            print(f"Loading environment from {env_file}")
            load_dotenv(env_file)
            return
    
    # If no file exists, try to load .env which is the default
    load_dotenv()

# Load environment variables before initializing settings
load_environment()

# Generate a default Fernet key (32 url-safe base64-encoded bytes)
def generate_fernet_key() -> str:
    """Generate a valid Fernet key."""
    try:
        key = Fernet.generate_key()
        return key.decode()
    except Exception as e:
        raise ValueError(f"Failed to generate Fernet key: {str(e)}")

DEFAULT_ENCRYPTION_KEY = generate_fernet_key()

# Default values for file upload limits
DEFAULT_MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB
DEFAULT_MAX_VIDEO_DURATION = 300  # 5 minutes
DEFAULT_LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB

def safe_int(value, default=0):
    """
    Safely convert a value to an integer, handling None and empty strings.
    
    Args:
        value: The value to convert
        default: Default value if conversion fails
        
    Returns:
        int: Converted integer or default value
    """
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default

class Settings(BaseSettings):
    """
    Application settings class with validation.
    
    This class defines all application settings with appropriate types,
    default values, and validation rules. All settings are loaded from
    environment variables.
    """
    # Environment settings
    ENVIRONMENT: Environment = Field(
        default=os.getenv("ENVIRONMENT", "development"), 
        description="Application environment (development, test, production)"
    )
    DEBUG: bool = Field(
        default=os.getenv("DEBUG", "true").lower() == "true",
        description="Enable or disable debug mode"
    )
    SENTRY_DSN: Optional[str] = Field(
        default=None,
        description="Sentry DSN URL for error reporting"
    )
    SENTRY_ENVIRONMENT: str = Field(
        default=os.getenv("SENTRY_ENVIRONMENT", os.getenv("ENVIRONMENT", "development")),
        description="Sentry environment name"
    )
    SENTRY_TRACES_SAMPLE_RATE: float = Field(
        default=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
        description="Sentry traces sample rate"
    )
    SENTRY_ENABLED_IN_DEVELOPMENT: bool = Field(
        default=os.getenv("SENTRY_ENABLED_IN_DEVELOPMENT", "false").lower() == "true",
        description="Enable Sentry error reporting in the development environment"
    )
    
    @field_validator("SENTRY_DSN")
    @classmethod
    def validate_sentry_dsn(cls, v):
        """
        Validate Sentry DSN if provided.
        
        Args:
            v: Sentry DSN value
            
        Returns:
            str: Valid Sentry DSN or None
        """
        if v is None or v == "":
            return None
        
        # Simple URL validation
        if not v.startswith(("http://", "https://")):
            raise ValueError("Sentry DSN must be a valid URL")
        
        return v

    # API settings
    API_V1_STR: str = Field(
        default="/api/v1",
        description="API version 1 prefix"
    )
    SECRET_KEY: str = Field(
        default=os.getenv("SECRET_KEY", secrets.token_urlsafe(32)),
        min_length=32,
        description="Primary secret key for non-JWT cryptographic operations (e.g., CSRF, message signing). Must be strong."
    )
    ENCRYPTION_KEY: str = Field(
        default=os.getenv("ENCRYPTION_KEY", DEFAULT_ENCRYPTION_KEY),
        description="Encryption key for sensitive data using Fernet (e.g., PII). Must be a valid Fernet key."
    )
    REQUIRE_ENCRYPTION_KEY_IN_PROD: bool = Field(
        default=os.getenv("REQUIRE_ENCRYPTION_KEY_IN_PROD", "false").lower() == "true",
        description="If true, application will fail to start in production if ENCRYPTION_KEY is invalid or not set."
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=60 * 24,  # 24 hours
        description="Access token expiration time in minutes"
    )
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        default=30,  # 30 days
        description="Refresh token expiration time in days"
    )
    ALGORITHM: str = Field(
        default="HS256",
        description="Algorithm used for JWT token signing"
    )
    PROJECT_NAME: str = Field(
        default="FormIQ",
        description="Name of the project"
    )
    PROJECT_DESCRIPTION: str = Field(
        default="AI-powered form checking for fitness",
        description="Description of the project"
    )
    VERSION: str = Field(
        default="1.0.0",
        description="API version"
    )

    # Admin settings
    ADMIN_REGISTRATION_CODE: str = Field(
        default=os.getenv("ADMIN_REGISTRATION_CODE", secrets.token_urlsafe(16)),
        description="Secret code required for admin account registration"
    )

    # CORS
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = Field(
        default=[],
        description="List of allowed CORS origins"
    )

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        """Validate and process CORS origins from string to list."""
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # Database
    POSTGRES_SERVER: str = Field(
        default=os.getenv("POSTGRES_SERVER", "db"),
        description="PostgreSQL server hostname"
    )
    POSTGRES_USER: str = Field(
        default=os.getenv("POSTGRES_USER", "postgres"),
        description="PostgreSQL username"
    )
    POSTGRES_PASSWORD: str = Field(
        default=os.getenv("POSTGRES_PASSWORD", ""),
        description="PostgreSQL password"
    )
    POSTGRES_DB: str = Field(
        default=os.getenv("POSTGRES_DB", "formiq"),
        description="PostgreSQL database name"
    )
    TEST_DATABASE_URL: Optional[str] = Field(
        default=None, 
        description="Database URI for test environment (loaded from .env.test)"
    )
    SQLALCHEMY_DATABASE_URI: Optional[str] = Field(
        default=None,
        description="SQLAlchemy database URI (for synchronous operations if any)"
    )
    ASYNC_DATABASE_URL: Optional[str] = Field(
        default=None,
        description="Asynchronous database URI (e.g., postgresql+asyncpg or sqlite+aiosqlite for test)"
    )
    
    @field_validator("SQLALCHEMY_DATABASE_URI", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: Optional[str], info) -> str:
        """
        Assemble database connection URI from components or use the provided one.
        Prioritizes TEST_DATABASE_URL (synchronous version) for test environment.
        """
        current_env = info.data.get("ENVIRONMENT") or os.getenv("ENVIRONMENT", "development")
        test_db_url_from_env = info.data.get("TEST_DATABASE_URL") # Loaded from .env.test

        if current_env == "test":
            if test_db_url_from_env:
                # Use the synchronous part for alembic if TEST_DATABASE_URL is sqlite+aiosqlite
                sync_url = test_db_url_from_env.replace("+aiosqlite", "")
                print(f"CONFIG/TEST: Using synchronous test DB URL: {sync_url}")
                return sync_url
            # Fallback if not in .env.test 
            print("CONFIG/TEST: Using fallback synchronous test DB URL: sqlite:///./test.db")
            return "sqlite:///./test.db" 
        
        if v: # If SQLALCHEMY_DATABASE_URI is explicitly set in env for non-test, use it
             print(f"CONFIG/NON-TEST: Using explicit SQLALCHEMY_DATABASE_URI: {v}")
             return v
        
        # For non-test environments, assemble PostgreSQL URL
        user = info.data.get("POSTGRES_USER") or os.getenv("POSTGRES_USER", "postgres")
        password = info.data.get("POSTGRES_PASSWORD") or os.getenv("POSTGRES_PASSWORD", "")
        server = info.data.get("POSTGRES_SERVER") or os.getenv("POSTGRES_SERVER", "db")
        db_name = info.data.get("POSTGRES_DB") or os.getenv("POSTGRES_DB", "formiq")
        pg_url = f"postgresql://{user}:{password}@{server}/{db_name}"
        print(f"CONFIG/NON-TEST: Assembled PostgreSQL URL: {pg_url}")
        return pg_url
    
    @field_validator("ASYNC_DATABASE_URL", mode="before")
    @classmethod
    def assemble_async_db_connection(cls, v: Optional[str], info) -> Optional[str]:
        """
        Assemble async database connection URI.
        Prioritizes TEST_DATABASE_URL for test environment.
        """
        current_env = info.data.get("ENVIRONMENT") or os.getenv("ENVIRONMENT", "development")
        test_db_url_from_env = info.data.get("TEST_DATABASE_URL") # Loaded from .env.test

        if current_env == "test":
            if test_db_url_from_env:
                print(f"CONFIG/TEST: Using async test DB URL from TEST_DATABASE_URL: {test_db_url_from_env}")
                return test_db_url_from_env # Should be sqlite+aiosqlite:///./test.db
            # Fallback if not in .env.test
            print("CONFIG/TEST: Using fallback async test DB URL: sqlite+aiosqlite:///./test.db")
            return "sqlite+aiosqlite:///./test.db" 

        if v: # If ASYNC_DATABASE_URL is explicitly set in env for non-test, use it
            print(f"CONFIG/NON-TEST: Using explicit ASYNC_DATABASE_URL: {v}")
            return v
        
        # For non-test environments, assemble async PostgreSQL URL
        user = info.data.get("POSTGRES_USER") or os.getenv("POSTGRES_USER", "postgres")
        password = info.data.get("POSTGRES_PASSWORD") or os.getenv("POSTGRES_PASSWORD", "")
        server = info.data.get("POSTGRES_SERVER") or os.getenv("POSTGRES_SERVER", "db")
        db_name = info.data.get("POSTGRES_DB") or os.getenv("POSTGRES_DB", "formiq")
        async_pg_url = f"postgresql+asyncpg://{user}:{password}@{server}:5432/{db_name}"
        print(f"CONFIG/NON-TEST: Assembled async PostgreSQL URL: {async_pg_url}")
        return async_pg_url
    
    DB_ECHO: bool = Field(
        default=os.getenv("DB_ECHO", "false").lower() == "true",
        description="Enable SQLAlchemy query logging"
    )
    DB_POOL_SIZE: Optional[int] = Field(
        default=safe_int(os.getenv("DB_POOL_SIZE"), 20) if not os.getenv("SQLALCHEMY_DATABASE_URI", "").startswith("sqlite") else None,
        description="Database connection pool size"
    )
    DB_MAX_OVERFLOW: Optional[int] = Field(
        default=safe_int(os.getenv("DB_MAX_OVERFLOW"), 30) if not os.getenv("SQLALCHEMY_DATABASE_URI", "").startswith("sqlite") else None,
        description="Maximum overflow connections in the pool"
    )
    DB_POOL_TIMEOUT: Optional[int] = Field(
        default=safe_int(os.getenv("DB_POOL_TIMEOUT"), 60) if not os.getenv("SQLALCHEMY_DATABASE_URI", "").startswith("sqlite") else None,
        description="Connection pool timeout in seconds"
    )
    DB_POOL_RECYCLE: Optional[int] = Field(
        default=safe_int(os.getenv("DB_POOL_RECYCLE"), 1800) if not os.getenv("SQLALCHEMY_DATABASE_URI", "").startswith("sqlite") else None,  # 30 minutes
        description="Connection recycle time in seconds"
    )
    SSL_REQUIRED: bool = Field(
        default=os.getenv("SSL_REQUIRED", "false").lower() == "true",
        description="Whether SSL is required for database connections"
    )

    # Redis
    REDIS_HOST: str = Field(
        default=os.getenv("REDIS_HOST", "localhost"),
        description="Redis server hostname"
    )
    REDIS_PORT: int = Field(
        default=safe_int(os.getenv("REDIS_PORT"), 6379),
        description="Redis server port"
    )
    REDIS_DB: int = Field(
        default=safe_int(os.getenv("REDIS_DB"), 0),
        description="Redis database number"
    )
    REDIS_PASSWORD: str = Field(
        default=os.getenv("REDIS_PASSWORD", ""),
        description="Redis password"
    )
    REDIS_URL: Optional[str] = Field(
        default=None,
        description="Redis connection URL"
    )
    
    @field_validator("REDIS_URL", mode="before")
    @classmethod
    def assemble_redis_connection(cls, v: Optional[str], info) -> str:
        """
        Assemble Redis connection URL from components or use the provided one.
        """
        if v:
            return v
            
        password = info.data.get("REDIS_PASSWORD", "")
        host = info.data.get("REDIS_HOST", "")
        port = info.data.get("REDIS_PORT", "")
        db = info.data.get("REDIS_DB", "")
        
        auth = f":{password}@" if password else ""
        
        return f"redis://{auth}{host}:{port}/{db}"

    # Celery Configuration
    CELERY_BROKER_URL: str = Field(
        default=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
        description="URL for the Celery message broker."
    )
    CELERY_RESULT_BACKEND: Optional[str] = Field(
        default=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1"),
        description="URL for the Celery result backend (optional)."
    )
    CELERY_SHARED_DATA_PATH: str = Field(
        default=os.getenv("CELERY_SHARED_DATA_PATH", "/tmp/formiq_celery_shared"),
        description="Shared filesystem path for Celery tasks to exchange large data."
    )
    CELERY_TASK_ALWAYS_EAGER: bool = Field(
        default=os.getenv("CELERY_TASK_ALWAYS_EAGER", "false").lower() == "true",
        description="If true, Celery tasks execute locally, useful for testing."
    )
    CELERY_MAX_RETRIES: int = Field(
        default=safe_int(os.getenv("CELERY_MAX_RETRIES"), 3),
        description="Maximum number of retries for a Celery task."
    )
    CELERY_RETRY_COUNTDOWN: int = Field(
        default=safe_int(os.getenv("CELERY_RETRY_COUNTDOWN"), 60), # Default to 60 seconds
        description="Default countdown in seconds before retrying a Celery task."
    )
    TIMEZONE: str = Field(
        default=os.getenv("TIMEZONE", "UTC"),
        description="Application timezone."
    )

    # Storage
    UPLOAD_DIR: str = Field(
        default=os.getenv("UPLOAD_DIR", "uploads/videos"),
        description="Directory for uploaded files"
    )
    UPLOAD_URL: str = Field(
        default=os.getenv("UPLOAD_URL", "http://localhost:8000/uploads/videos"),
        description="Base URL for accessing uploaded files"
    )
    USE_S3_STORAGE: bool = Field(
        default=os.getenv("USE_S3_STORAGE", "false").lower() == "true",
        description="Whether to use S3 for storage in production"
    )
    S3_PUBLIC_ACCESS: bool = Field(
        default=os.getenv("S3_PUBLIC_ACCESS", "false").lower() == "true",
        description="Whether S3 files should be publicly accessible by default"
    )
    
    # AWS Settings
    AWS_ACCESS_KEY_ID: str = Field(
        default=os.getenv("AWS_ACCESS_KEY_ID", ""),
        description="AWS access key ID"
    )
    AWS_SECRET_ACCESS_KEY: str = Field(
        default=os.getenv("AWS_SECRET_ACCESS_KEY", ""),
        description="AWS secret access key"
    )
    AWS_REGION: str = Field(
        default=os.getenv("AWS_REGION", "us-east-1"),
        description="AWS region for services"
    )
    AWS_BUCKET_NAME: str = Field(
        default=os.getenv("AWS_BUCKET_NAME", "formiq-videos"),
        description="AWS S3 bucket name for video storage"
    )
    AWS_S3_ENDPOINT: Optional[str] = Field(
        default=os.getenv("AWS_S3_ENDPOINT"),
        description="Custom S3 endpoint URL (for non-AWS S3 services)"
    )
    S3_BUCKET: str = Field(
        default_factory=lambda: os.getenv("S3_BUCKET", os.getenv("AWS_BUCKET_NAME", "formiq-videos")),
        description="Alias for AWS_BUCKET_NAME"
    )
    
    # Stripe Settings
    STRIPE_SECRET_KEY: str = Field(
        default=os.getenv("STRIPE_SECRET_KEY", ""),
        description="Stripe API secret key"
    )
    STRIPE_WEBHOOK_SECRET: str = Field(
        default=os.getenv("STRIPE_WEBHOOK_SECRET", ""),
        description="Stripe webhook signing secret"
    )
    STRIPE_PRICE_ID: str = Field(
        default=os.getenv("STRIPE_PRICE_ID", ""),
        description="Default Stripe price ID"
    )
    STRIPE_BASIC_PRICE_ID: str = Field(
        default=os.getenv("STRIPE_BASIC_PRICE_ID", "price_basic"),
        description="Stripe price ID for basic plan"
    )
    STRIPE_PRO_PRICE_ID: str = Field(
        default=os.getenv("STRIPE_PRO_PRICE_ID", "price_pro"),
        description="Stripe price ID for pro plan"
    )
    STRIPE_PREMIUM_PRICE_ID: str = Field(
        default=os.getenv("STRIPE_PREMIUM_PRICE_ID", "price_premium"),
        description="Stripe price ID for premium plan"
    )
    
    # SMTP Settings / Email Configuration for fastapi-mail
    MAIL_SERVER: str = Field(
        default=os.getenv("MAIL_SERVER", os.getenv("SMTP_HOST", "smtp.gmail.com")),
        description="SMTP server hostname for fastapi-mail"
    )
    MAIL_PORT: int = Field(
        default=safe_int(os.getenv("MAIL_PORT", os.getenv("SMTP_PORT")), 587),
        description="SMTP server port for fastapi-mail"
    )
    MAIL_USERNAME: str = Field(
        default=os.getenv("MAIL_USERNAME", os.getenv("SMTP_USER", "")),
        description="SMTP username for fastapi-mail"
    )
    MAIL_PASSWORD: SecretStr = Field(
        default=SecretStr(os.getenv("MAIL_PASSWORD", os.getenv("SMTP_PASSWORD", ""))),
        description="SMTP password for fastapi-mail"
    )
    MAIL_FROM_EMAIL: str = Field( # Used as MAIL_FROM by ConnectionConfig
        default=os.getenv("MAIL_FROM_EMAIL", os.getenv("SMTP_FROM_EMAIL", "noreply@formiq.app")),
        description="Sender email address for fastapi-mail"
    )
    MAIL_FROM_NAME: Optional[str] = Field(
        default=os.getenv("MAIL_FROM_NAME", os.getenv("SMTP_FROM_NAME")),
        description="Sender name for fastapi-mail (optional)"
    )
    MAIL_STARTTLS: bool = Field(
        default=(os.getenv("MAIL_STARTTLS", os.getenv("SMTP_TLS", "true")).lower() == "true"),
        description="Enable STARTTLS for fastapi-mail"
    )
    MAIL_SSL_TLS: bool = Field(
        default=(os.getenv("MAIL_SSL_TLS", "false").lower() == "true"),
        description="Enable SSL/TLS for fastapi-mail"
    )
    MAIL_USE_CREDENTIALS: bool = Field(
        default=(os.getenv("MAIL_USE_CREDENTIALS", "true").lower() == "true"),
        description="Use credentials for fastapi-mail"
    )
    MAIL_VALIDATE_CERTS: bool = Field(
        default=(os.getenv("MAIL_VALIDATE_CERTS", "true").lower() == "true"),
        description="Validate certificates for fastapi-mail"
    )
    EMAIL_TEMPLATES_DIR: Path = Field(
        default="app/templates/email", # Default to relative, validator will absolutize
        description="Directory for email templates"
    )
    
    @field_validator("EMAIL_TEMPLATES_DIR", mode="before")
    @classmethod
    def absolutize_template_dir(cls, v: Union[str, Path]) -> Path:
        # logger.debug(f"Current environment for EMAIL_TEMPLATES_DIR validation: {info.data.get('ENVIRONMENT')}") # Commented out/removed

        # if str(info.data.get("ENVIRONMENT")).lower() == "test": 
        #     test_templates_dir = Path(__file__).resolve().parent.parent 
        #     logger.debug(f"TEST ENV: Overriding EMAIL_TEMPLATES_DIR to: {test_templates_dir} which is backend/app/")
        #     logger.debug(f"Check from config.py for {test_templates_dir}: Exists: {test_templates_dir.exists()}, Is Dir: {test_templates_dir.is_dir()}")
        #     return test_templates_dir

        # Original logic restored
        path = Path(v)
        if not path.is_absolute():
            # BASE_DIR is defined at the module level
            logger.debug(f"EMAIL_TEMPLATES_DIR: Resolving relative path '{v}' against BASE_DIR '{BASE_DIR}'")
            abs_path = (BASE_DIR / path).resolve()
            logger.debug(f"EMAIL_TEMPLATES_DIR: Resolved to absolute path '{abs_path}'")
            return abs_path
        resolved_path = path.resolve()
        logger.debug(f"EMAIL_TEMPLATES_DIR: Using absolute path '{resolved_path}'")
        return resolved_path

    # Old SMTP_USERNAME alias is no longer needed as MAIL_USERNAME covers it.
    # SMTP_USERNAME: str = Field(
    #     default_factory=lambda: os.getenv("SMTP_USERNAME", os.getenv("SMTP_USER", "")),
    #     description="Alias for SMTP_USER"
    # )
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = Field(
        default=safe_int(os.getenv("RATE_LIMIT_REQUESTS"), 60),
        description="Default rate limit requests per window"
    )
    RATE_LIMIT_BURST: int = Field(
        default=safe_int(os.getenv("RATE_LIMIT_BURST"), 120),
        description="Default rate limit burst size"
    )
    RATE_LIMIT_WINDOW: int = Field(
        default=safe_int(os.getenv("RATE_LIMIT_WINDOW"), 60),
        description="Default rate limit window in seconds"
    )
    RATE_LIMIT_PER_MINUTE: int = Field(
        default=safe_int(os.getenv("RATE_LIMIT_PER_MINUTE"), 60),
        description="Rate limit requests per minute (potentially redundant, review usage)"
    )
    RATE_LIMIT_RULES: Dict[str, Dict[str, int]] = Field(
        default_factory=lambda: json.loads(os.getenv("RATE_LIMIT_RULES", "{}")),
        description="Specific rate limits for endpoints, e.g., {\"/api/v1/auth/login\": {\"limit\": 5, \"window\": 60}}"
    )
    RATE_LIMIT_EXCLUDE_PATHS: List[str] = Field(
        default_factory=lambda: json.loads(os.getenv("RATE_LIMIT_EXCLUDE_PATHS", '["/health", "/metrics", "/docs", "/redoc", "/openapi.json"]')),
        description="Paths to exclude from API rate limiting"
    )
    EMAIL_VERIFICATION_RATE_LIMIT: int = Field(
        default=safe_int(os.getenv("EMAIL_VERIFICATION_RATE_LIMIT"), 3),
        description="Rate limit for email verification requests per window (e.g., per hour)"
    )
    EMAIL_VERIFICATION_WINDOW: int = Field(
        default=safe_int(os.getenv("EMAIL_VERIFICATION_WINDOW"), 3600),  # 1 hour in seconds
        description="Window in seconds for email verification rate limit"
    )
    EMAIL_PASSWORD_RESET_RATE_LIMIT: int = Field(
        default=safe_int(os.getenv("EMAIL_PASSWORD_RESET_RATE_LIMIT"), 3),
        description="Rate limit for password reset requests per window"
    )
    EMAIL_PASSWORD_RESET_WINDOW: int = Field(
        default=safe_int(os.getenv("EMAIL_PASSWORD_RESET_WINDOW"), 3600),
        description="Window in seconds for password reset rate limit (default 1 hour)"
    )
    EMAIL_NOTIFICATION_RATE_LIMIT: int = Field(
        default=safe_int(os.getenv("EMAIL_NOTIFICATION_RATE_LIMIT"), 5),
        description="Rate limit for general email notifications per window"
    )
    EMAIL_NOTIFICATION_WINDOW: int = Field(
        default=safe_int(os.getenv("EMAIL_NOTIFICATION_WINDOW"), 3600),  # 1 hour in seconds
        description="Window in seconds for email notification rate limit"
    )
    RATE_LIMIT_ENABLED: bool = Field(
        default=os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true",
        description="Whether rate limiting is enabled"
    )
    RATE_LIMIT_STORAGE: str = Field(
        default=os.getenv("RATE_LIMIT_STORAGE", "memory"),
        description="Storage backend for rate limit data (memory or redis)"
    )
    
    # JWT Settings
    JWT_SECRET: str = Field(
        default=os.getenv("JWT_SECRET", secrets.token_urlsafe(32)),
        min_length=32,
        description="Secret key dedicated to JWT signing and verification. Must be strong."
    )

    @field_validator("JWT_SECRET")
    @classmethod
    def validate_jwt_secret(cls, v):
        """Validate JWT secret key."""
        if len(v) < 32:
            raise ValueError("JWT_SECRET must be at least 32 characters long")
        return v
        
    JWT_ALGORITHM: str = Field(
        default=DEFAULT_ALGORITHM,
        description="Algorithm used for JWT token signing (e.g., HS256)"
    )
    
    # Note: We use standard JWT token authentication with tokens stored in localStorage
    # This is suitable for both web and mobile applications without the need for HttpOnly cookies
    # and CSRF protection, which are less compatible with mobile apps.

    # File Upload Limits
    MAX_CONTENT_LENGTH: int = Field(
        default=safe_int(os.getenv("MAX_CONTENT_LENGTH"), DEFAULT_MAX_CONTENT_LENGTH),
        description="Maximum content length for uploads in bytes"
    )
    ALLOWED_VIDEO_TYPES: List[str] = Field(
        default=["video/mp4", "video/quicktime", "video/x-msvideo"],
        description="List of allowed video MIME types"
    )
    MAX_VIDEO_DURATION: int = Field(
        default=safe_int(os.getenv("MAX_VIDEO_DURATION"), DEFAULT_MAX_VIDEO_DURATION),
        description="Maximum video duration in seconds"
    )
    
    # AI Model Settings
    AI_MODEL_PATH: str = Field(
        default=os.getenv("AI_MODEL_PATH", "models"),
        description="Path to AI model files"
    )
    AI_MODEL_COMPLEXITY: int = Field(
        default=safe_int(os.getenv("AI_MODEL_COMPLEXITY"), 1),
        description="MediaPipe Pose model complexity (0, 1, or 2)."
    )
    AI_MIN_DETECTION_CONFIDENCE: float = Field(
        default=float(os.getenv("AI_MIN_DETECTION_CONFIDENCE", "0.5")),
        description="MediaPipe Pose minimum detection confidence."
    )
    AI_MIN_TRACKING_CONFIDENCE: float = Field(
        default=float(os.getenv("AI_MIN_TRACKING_CONFIDENCE", "0.5")),
        description="MediaPipe Pose minimum tracking confidence."
    )
    AI_CONFIDENCE_THRESHOLD: float = Field(
        default=float(os.getenv("AI_CONFIDENCE_THRESHOLD") or "0.7"),
        description="Confidence threshold for AI predictions"
    )
    AI_MAX_BATCH_SIZE: int = Field(
        default=safe_int(os.getenv("AI_MAX_BATCH_SIZE"), 32),
        description="Maximum batch size for AI inference"
    )
    AI_SMOOTHING_WINDOW_SIZE: int = Field(
        default=safe_int(os.getenv("AI_SMOOTHING_WINDOW_SIZE"), 5),
        description="Window size for moving average smoothing of pose landmarks (must be odd)."
    )
    AI_MAX_INTERPOLATION_GAP: int = Field(
        default=safe_int(os.getenv("AI_MAX_INTERPOLATION_GAP"), 3),
        description="Maximum number of consecutive frames to interpolate missing pose landmarks across."
    )
    AI_TARGET_FRAME_WIDTH: int = Field(
        default=safe_int(os.getenv("AI_TARGET_FRAME_WIDTH"), 256),
        description="Target width for frames processed by AI pipeline (e.g., for normalization)."
    )
    AI_TARGET_FRAME_HEIGHT: int = Field(
        default=safe_int(os.getenv("AI_TARGET_FRAME_HEIGHT"), 256),
        description="Target height for frames processed by AI pipeline (e.g., for normalization)."
    )
    EXERCISE_CLASSIFICATION_THRESHOLD: float = Field(
        default=float(os.getenv("EXERCISE_CLASSIFICATION_THRESHOLD", "0.75")),
        description="Minimum confidence score for an automatically classified exercise to be considered valid."
    )
    USE_ML_MODELS: bool = Field(
        default=os.getenv("USE_ML_MODELS", "true").lower() == "true",
        description="Enable ML models for form analysis (squat XGBoost model). Falls back to rule-based analysis when disabled."
    )
    
    # Logging
    LOG_LEVEL: str = Field(
        default=os.getenv("LOG_LEVEL", "INFO"),
        description="Logging level"
    )
    LOG_FORMAT: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log message format"
    )
    LOG_FILE: str = Field(
        default=os.getenv("LOG_FILE", "app.log"),
        description="Path to log file"
    )
    LOG_MAX_BYTES: int = Field(
        default=safe_int(os.getenv("LOG_MAX_BYTES"), DEFAULT_LOG_MAX_BYTES),
        description="Maximum log file size before rotation"
    )
    LOG_BACKUP_COUNT: int = Field(
        default=safe_int(os.getenv("LOG_BACKUP_COUNT"), 5),
        description="Number of backup log files to keep"
    )

    # Application
    PROJECT_NAME: str = "FormIQ API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # Security
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60  # 1 hour
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30  # 30 days
    SESSION_EXPIRE_DAYS: int = 7  # 7 days
    PASSWORD_RESET_TOKEN_EXPIRE_HOURS: int = 24  # 24 hours
    EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS: int = 24  # 24 hours
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 60  # Default requests per window
    RATE_LIMIT_WINDOW: int = 60  # Default window in seconds
    RATE_LIMIT_BURST: int = 100  # Default burst limit
    
    # Session Management
    MAX_FAILED_LOGIN_ATTEMPTS: int = 5  # Max failed attempts before lockout
    ACCOUNT_LOCKOUT_MINUTES: int = 15  # Lockout duration after max failed attempts
    MAX_SESSIONS_PER_USER: int = 5  # Maximum concurrent sessions per user
    SESSION_REFRESH_GRACE_PERIOD: int = 300  # 5 minutes grace period for refresh
    
    # Frontend
    FRONTEND_URL: str = "http://localhost:3000"
    
    # Email (This block will be removed)
    # SMTP_TLS: bool = True
    # SMTP_PORT: Optional[int] = None
    # SMTP_HOST: Optional[str] = None
    # SMTP_USER: Optional[str] = None
    # SMTP_PASSWORD: Optional[str] = None
    # EMAILS_FROM_EMAIL: Optional[str] = None
    # EMAILS_FROM_NAME: Optional[str] = None
    # EMAIL_TEMPLATES_DIR: str = "app/email-templates"
    
    # Database
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "formiq"
    SQLALCHEMY_DATABASE_URI: Optional[str] = None
    
    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DB: int = 0
    
    # Storage
    STORAGE_TYPE: str = "local"  # "local" or "s3"
    UPLOAD_DIR: str = "uploads"
    S3_BUCKET_NAME: Optional[str] = None
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: Optional[str] = None
    
    # Admin
    ADMIN_EMAIL: str = "admin@formiq.com"
    ADMIN_PASSWORD: str = "admin"
    ADMIN_REGISTRATION_CODE: str = "admin123"  # For initial admin setup

    # Video processing settings
    VIDEO_FRAME_RATE: int = int(os.getenv("VIDEO_FRAME_RATE", "30"))
    MAX_VIDEO_FRAMES: int = int(os.getenv("MAX_VIDEO_FRAMES", "300"))
    MAX_VIDEO_SIZE_MB: int = int(os.getenv("MAX_VIDEO_SIZE_MB", "100"))
    MAX_VIDEO_DURATION: int = int(os.getenv("MAX_VIDEO_DURATION", "60"))
    FFMPEG_TIMEOUT: int = safe_int(os.getenv("FFMPEG_TIMEOUT"), 60)  # Timeout for FFmpeg commands in seconds
    SUPPORTED_VIDEO_FORMATS: List[str] = ["mp4", "mov", "webm"]
    
    # Form analysis settings
    MIN_CONFIDENCE_THRESHOLD: float = float(os.getenv("MIN_CONFIDENCE_THRESHOLD", "0.7"))
    POSE_DETECTION_MODEL: str = os.getenv("POSE_DETECTION_MODEL", "movenet")  # movenet, mediapipe
    TRAINING_API_KEY: Optional[str] = Field( # Added for training data submission
        default=os.getenv("TRAINING_API_KEY"),
        description="API key for submitting training data externally (e.g., Zapier)"
    )
    EXERCISE_CONFIGS: Dict[str, Any] = {
        "squat": {
            "key_points": ["hip", "knee", "ankle"],
            "target_angles": {"knee": 90, "hip": 90},
            "angle_tolerances": {"knee": 15, "hip": 15},
            "depth_threshold": 0.7
        },
        "pushup": {
            "key_points": ["shoulder", "elbow", "wrist"],
            "target_angles": {"elbow": 90},
            "angle_tolerances": {"elbow": 15},
            "body_alignment_threshold": 0.1
        },
        "plank": {
            "key_points": ["shoulder", "hip", "ankle"],
            "target_angles": {"shoulder": 180, "hip": 180},
            "angle_tolerances": {"shoulder": 15, "hip": 15},
            "sag_threshold": 0.1
        }
    }
    
    # WebSocket settings
    WS_PING_INTERVAL: int = int(os.getenv("WS_PING_INTERVAL", "30"))  # seconds
    WS_PING_TIMEOUT: int = int(os.getenv("WS_PING_TIMEOUT", "10"))  # seconds
    WS_MAX_CONNECTIONS: int = int(os.getenv("WS_MAX_CONNECTIONS", "1000"))
    WS_MAX_KEEPALIVE: int = int(os.getenv("WS_MAX_KEEPALIVE", "300"))  # seconds
    
    # CORS settings
    CORS_ORIGINS: List[str] = json.loads(
        os.getenv("CORS_ORIGINS", '["http://localhost:3000"]')
    )
    
    # Rate limiting settings
    RATE_LIMIT_DEFAULT_LIMIT: int = 100
    RATE_LIMIT_DEFAULT_WINDOW: int = 60
    
    # Cache settings
    CACHE_TTL: int = 3600  # 1 hour
    CACHE_PREFIX: str = "formiq:"
    
    # Monitoring settings
    ENABLE_METRICS: bool = True
    METRICS_PREFIX: str = "formiq_"
    
    BCRYPT_ROUNDS: int = Field(
        default=safe_int(os.getenv("BCRYPT_ROUNDS"), 12),
        description="Number of rounds for bcrypt password hashing"
    )
    
    LOGIN_ATTEMPT_LOCKOUT_TIME: int = Field(
        default=300,  # 5 minutes in seconds
        description="Lockout duration in seconds after too many failed login attempts"
    )
    LOGIN_MAX_ATTEMPTS: int = Field(
        default=5,
        description="Maximum allowed failed login attempts before lockout"
    )
    LOGIN_ATTEMPT_KEY_TTL_SECONDS: int = Field(
        default=600,  # 10 minutes in seconds
        description="TTL for login attempt tracking keys in Redis"
    )
    
    @field_validator("ENCRYPTION_KEY")
    @classmethod
    def validate_encryption_key(cls, v: str) -> str:
        """
        Validate that the encryption key is a valid Fernet key.
        If not provided or invalid, a new one is generated (and will be used by the settings instance).
        """
        try:
            if not v: # if v is None or empty string
                logger.warning("ENCRYPTION_KEY not provided or empty, generating a new one for this session.")
                return generate_fernet_key()
            
            key_bytes = base64.urlsafe_b64decode(v.encode() if isinstance(v, str) else v) # Ensure it's bytes
            if len(key_bytes) != 32: # Fernet keys must be 32 url-safe base64-encoded bytes
                raise ValueError("Fernet key must be 32 url-safe base64-encoded bytes.")
            Fernet(v.encode() if isinstance(v, str) else v) # Check if it can initialize Fernet
            return v
        except Exception as e:
            logger.warning(f"Provided ENCRYPTION_KEY is invalid ('{str(e)}'), generating a new one for this session.")
            return generate_fernet_key()

    model_config = SettingsConfigDict(
        env_file=".env",          # Default .env file
        env_file_encoding="utf-8",
        extra="ignore",           # Ignore extra fields from environment
        case_sensitive=False,     # Environment variable names are case-insensitive
        env_nested_delimiter='__' # For nested model settings from env vars
    )
    
    def validate_settings(self) -> List[Dict[str, Any]]:
        """
        Validate all settings and return a list of warnings/errors.
        
        Returns:
            List[Dict[str, Any]]: List of warnings or errors with severity level
        """
        issues = []
        
        # Check if database URI is set for non-test environment
        if self.ENVIRONMENT != Environment.TEST and not self.SQLALCHEMY_DATABASE_URI:
            issues.append({
                "severity": "critical",
                "message": "DATABASE_URI is not set",
                "context": "Database connection will fail"
            })
        
        # Check if JWT secret is secure enough in production
        if self.ENVIRONMENT == Environment.PRODUCTION and len(self.JWT_SECRET) < 32:
            issues.append({
                "severity": "high",
                "message": "JWT_SECRET is too short for production",
                "context": "Minimum 32 characters recommended for security"
            })
        
        # Check if Stripe settings are set in production
        if self.ENVIRONMENT == Environment.PRODUCTION and not self.STRIPE_SECRET_KEY:
            issues.append({
                "severity": "high",
                "message": "STRIPE_SECRET_KEY is not set in production",
                "context": "Payment processing will fail"
            })
        
        # Check if AWS credentials are set for production
        if self.ENVIRONMENT == Environment.PRODUCTION and not self.AWS_ACCESS_KEY_ID:
            issues.append({
                "severity": "high",
                "message": "AWS_ACCESS_KEY_ID is not set in production",
                "context": "File storage operations will fail"
            })
        
        # Check if SMTP settings are valid
        if not self.MAIL_SERVER or not self.MAIL_USERNAME:
            issues.append({
                "severity": "medium",
                "message": "SMTP settings are incomplete",
                "context": "Email notifications will not work"
            })
        
        return issues

@lru_cache()
def get_settings() -> Settings:
    """
    Get application settings.
    
    This function is cached to avoid repeated parsing of environment variables.
    Clear the cache using `get_settings.cache_clear()` when environment variables change.
    
    Returns:
        Settings: Application settings instance
    """
    settings = Settings()
    
    # Validate settings
    issues = settings.validate_settings()
    
    # Log warnings for issues if not in test environment
    if issues and settings.ENVIRONMENT != Environment.TEST:
        for issue in issues:
            if issue["severity"] == "critical":
                logging.critical(f"Configuration critical issue: {issue['message']} - {issue['context']}")
            elif issue["severity"] == "high":
                logging.error(f"Configuration error: {issue['message']} - {issue['context']}")
            elif issue["severity"] == "medium":
                logging.warning(f"Configuration warning: {issue['message']} - {issue['context']}")
            else:
                logging.info(f"Configuration notice: {issue['message']} - {issue['context']}")
    
    return settings

# Global settings instance
settings = get_settings() 