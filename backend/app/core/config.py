from typing import List, Union, Optional, Dict, Any
from pydantic import AnyHttpUrl, field_validator, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
import os
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
)
import base64
from datetime import datetime, timedelta
from pydantic import validator
import secrets

# Load environment variables
if os.getenv("ENVIRONMENT") == "test":
    load_dotenv(".env.test")
else:
    load_dotenv()

# Generate a default Fernet key (32 url-safe base64-encoded bytes)
DEFAULT_ENCRYPTION_KEY = base64.urlsafe_b64encode(os.urandom(32)).decode()

# Default values for file upload limits
DEFAULT_MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB
DEFAULT_MAX_VIDEO_DURATION = 300  # 5 minutes
DEFAULT_LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB

class Settings(BaseSettings):
    """Application settings."""

    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"
    SENTRY_DSN: Optional[str] = os.getenv("SENTRY_DSN")

    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ENCRYPTION_KEY: str = os.getenv("ENCRYPTION_KEY", DEFAULT_ENCRYPTION_KEY)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    ALGORITHM: str = "HS256"
    PROJECT_NAME: str = "FormIQ"
    VERSION: str = "1.0.0"

    # CORS
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []

    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: str | List[str]) -> List[str] | str:
        """Validate CORS origins."""
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # Database
    POSTGRES_SERVER: str = os.getenv("POSTGRES_SERVER", "localhost")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "formiq")
    SQLALCHEMY_DATABASE_URI: str = (
        "sqlite+aiosqlite:///./test.db"
        if os.getenv("ENVIRONMENT") == "test"
        else f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_SERVER}/{POSTGRES_DB}"
    )
    DB_ECHO: bool = os.getenv("DB_ECHO", "true").lower() == "true"
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "5"))
    DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "10"))
    DB_POOL_TIMEOUT: int = int(os.getenv("DB_POOL_TIMEOUT", "30"))
    DB_POOL_RECYCLE: int = int(os.getenv("DB_POOL_RECYCLE", "1800"))  # 30 minutes

    # Redis
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", 6379))
    REDIS_DB: int = int(os.getenv("REDIS_DB", 0))
    REDIS_PASSWORD: str = os.getenv("REDIS_PASSWORD", "")
    REDIS_URL: str = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

    # Storage
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "uploads/videos")
    UPLOAD_URL: str = os.getenv("UPLOAD_URL", "http://localhost:8000/uploads/videos")
    
    # AWS Settings
    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    AWS_BUCKET_NAME: str = os.getenv("AWS_BUCKET_NAME", "formiq-videos")
    AWS_S3_ENDPOINT: Optional[str] = os.getenv("AWS_S3_ENDPOINT")
    
    # Stripe Settings
    STRIPE_SECRET_KEY: str = os.getenv("STRIPE_SECRET_KEY", "")
    STRIPE_WEBHOOK_SECRET: str = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    STRIPE_PRICE_ID: str = os.getenv("STRIPE_PRICE_ID", "")
    
    # SMTP Settings
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_TLS: bool = os.getenv("SMTP_TLS", "true").lower() == "true"
    SMTP_FROM_EMAIL: str = os.getenv("SMTP_FROM_EMAIL", "noreply@formiq.app")
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
    RATE_LIMIT_BURST: int = int(os.getenv("RATE_LIMIT_BURST", "200"))
    RATE_LIMIT_WINDOW: int = int(os.getenv("RATE_LIMIT_WINDOW", "60"))
    
    # JWT Settings
    JWT_SECRET: str = os.getenv("JWT_SECRET", SECRET_KEY)
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", ALGORITHM)
    
    # File Upload Limits
    MAX_CONTENT_LENGTH: int = int(os.getenv("MAX_CONTENT_LENGTH", str(DEFAULT_MAX_CONTENT_LENGTH)))
    ALLOWED_VIDEO_TYPES: List[str] = ["video/mp4", "video/quicktime", "video/x-msvideo"]
    MAX_VIDEO_DURATION: int = int(os.getenv("MAX_VIDEO_DURATION", str(DEFAULT_MAX_VIDEO_DURATION)))
    
    # AI Model Settings
    AI_MODEL_PATH: str = os.getenv("AI_MODEL_PATH", "models")
    AI_CONFIDENCE_THRESHOLD: float = float(os.getenv("AI_CONFIDENCE_THRESHOLD", "0.7"))
    AI_MAX_BATCH_SIZE: int = int(os.getenv("AI_MAX_BATCH_SIZE", "32"))
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_FILE: str = os.getenv("LOG_FILE", "app.log")
    LOG_MAX_BYTES: int = int(os.getenv("LOG_MAX_BYTES", str(DEFAULT_LOG_MAX_BYTES)))
    LOG_BACKUP_COUNT: int = int(os.getenv("LOG_BACKUP_COUNT", "5"))

    class Config:
        """Pydantic config."""
        case_sensitive = True

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings() 