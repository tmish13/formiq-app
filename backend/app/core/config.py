"""
Application configuration module.

This module defines all application settings loaded from environment variables.
Settings are defined as Pydantic models with validation to ensure correct types and formats.
"""
from typing import List, Union, Optional, Dict, Any, ClassVar
from pydantic import AnyHttpUrl, field_validator, SecretStr, PostgresDsn, RedisDsn, HttpUrl, validator, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
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
DEFAULT_ENCRYPTION_KEY = base64.urlsafe_b64encode(os.urandom(32)).decode()

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
    
    @validator("SENTRY_DSN")
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
        default_factory=lambda: os.getenv("SECRET_KEY", secrets.token_urlsafe(32)),
        description="Secret key for JWT and other cryptographic operations"
    )
    ENCRYPTION_KEY: str = Field(
        default=os.getenv("ENCRYPTION_KEY", DEFAULT_ENCRYPTION_KEY),
        description="Encryption key for sensitive data"
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

    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        """Validate and process CORS origins from string to list."""
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # Database
    POSTGRES_SERVER: str = Field(
        default=os.getenv("POSTGRES_SERVER", "localhost"),
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
    SQLALCHEMY_DATABASE_URI: Optional[str] = Field(
        default=None,
        description="SQLAlchemy database URI"
    )
    
    @validator("SQLALCHEMY_DATABASE_URI", pre=True)
    def assemble_db_connection(cls, v: Optional[str], values: Dict[str, Any]) -> str:
        """
        Assemble database connection URI from components or use the provided one.
        """
        if v:
            return v
            
        # Use SQLite for test and development environments for simplicity
        if values.get("ENVIRONMENT") in ["test", "development"]:
            db_name = "test.db" if values.get("ENVIRONMENT") == "test" else "dev.db"
            return f"sqlite:///./{db_name}"
        
        # Use direct string formatting to ensure correct URI structure
        user = values.get("POSTGRES_USER")
        password = values.get("POSTGRES_PASSWORD")
        server = values.get("POSTGRES_SERVER")
        db = values.get("POSTGRES_DB")
        
        # Construct connection string manually to avoid path formatting issues
        return f"postgresql://{user}:{password}@{server}/{db}"
    
    DB_ECHO: bool = Field(
        default=os.getenv("DB_ECHO", "false").lower() == "true",
        description="Enable SQLAlchemy query logging"
    )
    DB_POOL_SIZE: int = Field(
        default=safe_int(os.getenv("DB_POOL_SIZE"), 20),
        description="Database connection pool size"
    )
    DB_MAX_OVERFLOW: int = Field(
        default=safe_int(os.getenv("DB_MAX_OVERFLOW"), 30),
        description="Maximum overflow connections in the pool"
    )
    DB_POOL_TIMEOUT: int = Field(
        default=safe_int(os.getenv("DB_POOL_TIMEOUT"), 60),
        description="Connection pool timeout in seconds"
    )
    DB_POOL_RECYCLE: int = Field(
        default=safe_int(os.getenv("DB_POOL_RECYCLE"), 1800),  # 30 minutes
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
    
    @validator("REDIS_URL", pre=True)
    def assemble_redis_connection(cls, v: Optional[str], values: Dict[str, Any]) -> str:
        """
        Assemble Redis connection URL from components or use the provided one.
        """
        if v:
            return v
            
        password = values.get("REDIS_PASSWORD")
        auth = f":{password}@" if password else ""
        
        return f"redis://{auth}{values.get('REDIS_HOST')}:{values.get('REDIS_PORT')}/{values.get('REDIS_DB')}"

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
    
    # SMTP Settings
    SMTP_HOST: str = Field(
        default=os.getenv("SMTP_HOST", "smtp.gmail.com"),
        description="SMTP server hostname"
    )
    SMTP_PORT: int = Field(
        default=safe_int(os.getenv("SMTP_PORT"), 587),
        description="SMTP server port"
    )
    SMTP_USER: str = Field(
        default=os.getenv("SMTP_USER", ""),
        description="SMTP username"
    )
    SMTP_PASSWORD: str = Field(
        default=os.getenv("SMTP_PASSWORD", ""),
        description="SMTP password"
    )
    SMTP_TLS: bool = Field(
        default=os.getenv("SMTP_TLS", "true").lower() == "true",
        description="Enable SMTP TLS"
    )
    SMTP_FROM_EMAIL: str = Field(
        default=os.getenv("SMTP_FROM_EMAIL", "noreply@formiq.app"),
        description="From email address"
    )
    SMTP_USERNAME: str = Field(
        default_factory=lambda: os.getenv("SMTP_USERNAME", os.getenv("SMTP_USER", "")),
        description="Alias for SMTP_USER"
    )
    
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
        default=os.getenv("JWT_SECRET", ""),
        description="Secret key for JWT tokens"
    )

    @validator("JWT_SECRET")
    def validate_jwt_secret(cls, v, values):
        """Validate JWT secret key."""
        if not v:
            # If JWT_SECRET is not set, use SECRET_KEY
            return values.get("SECRET_KEY", "")
        return v
        
    JWT_ALGORITHM: str = Field(
        default=os.getenv("JWT_ALGORITHM", "HS256"),
        description="Algorithm for JWT token signing"
    )
    
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
    AI_CONFIDENCE_THRESHOLD: float = Field(
        default=float(os.getenv("AI_CONFIDENCE_THRESHOLD") or "0.7"),
        description="Confidence threshold for AI predictions"
    )
    AI_MAX_BATCH_SIZE: int = Field(
        default=safe_int(os.getenv("AI_MAX_BATCH_SIZE"), 32),
        description="Maximum batch size for AI inference"
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

    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
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
        if not self.SMTP_HOST or not self.SMTP_USER:
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