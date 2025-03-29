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

# Load environment variables
if os.getenv("ENVIRONMENT") == "test":
    load_dotenv(".env.test")
else:
    load_dotenv()

# Generate a default Fernet key (32 url-safe base64-encoded bytes)
DEFAULT_ENCRYPTION_KEY = base64.urlsafe_b64encode(os.urandom(32)).decode()

class SecuritySettings(BaseSettings):
    """Security-related settings."""
    SECRET_KEY: SecretStr = SecretStr(os.getenv("SECRET_KEY", "your-secret-key-here"))
    ALGORITHM: str = DEFAULT_ALGORITHM
    ACCESS_TOKEN_EXPIRE_MINUTES: int = DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES
    ENCRYPTION_KEY: SecretStr = SecretStr(os.getenv("ENCRYPTION_KEY", DEFAULT_ENCRYPTION_KEY))
    JWT_SECRET: SecretStr = SecretStr(os.getenv("JWT_SECRET", "your-jwt-secret-here"))

class DatabaseSettings(BaseSettings):
    """Database-related settings."""
    POSTGRES_SERVER: str = os.getenv("POSTGRES_SERVER", "localhost")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: SecretStr = SecretStr(os.getenv("POSTGRES_PASSWORD", "postgres"))
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "formiq")
    SQLALCHEMY_DATABASE_URI: Optional[str] = None
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./test.db")
    DB_ECHO: bool = False
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 3600

    @validator("SQLALCHEMY_DATABASE_URI", pre=True)
    def assemble_db_connection(cls, v: str | None, values: Dict[str, Any]) -> Any:
        if isinstance(v, str):
            return v
        return f"postgresql://{values.get('POSTGRES_USER')}:{values.get('POSTGRES_PASSWORD').get_secret_value()}@{values.get('POSTGRES_SERVER')}/{values.get('POSTGRES_DB')}"

class RedisSettings(BaseSettings):
    """Redis-related settings."""
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    RATE_LIMIT_REQUESTS: int = DEFAULT_RATE_LIMIT_REQUESTS
    RATE_LIMIT_BURST: int = DEFAULT_RATE_LIMIT_BURST

class StorageSettings(BaseSettings):
    """Storage-related settings."""
    STORAGE_TYPE: str = os.getenv("STORAGE_TYPE", "local")
    STORAGE_PATH: str = os.getenv("STORAGE_PATH", "./storage")
    S3_BUCKET: str = os.getenv("S3_BUCKET", "formiq-storage")
    S3_ACCESS_KEY: SecretStr = SecretStr(os.getenv("S3_ACCESS_KEY", "your-s3-access-key"))
    S3_SECRET_KEY: SecretStr = SecretStr(os.getenv("S3_SECRET_KEY", "your-s3-secret-key"))
    S3_REGION: str = os.getenv("S3_REGION", "us-east-1")

class EmailSettings(BaseSettings):
    """Email-related settings."""
    EMAIL_SENDER: str = os.getenv("EMAIL_SENDER", "noreply@formiq.com")
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "your-smtp-user")
    SMTP_PASSWORD: SecretStr = SecretStr(os.getenv("SMTP_PASSWORD", "your-smtp-password"))
    SMTP_TLS: bool = True

class AISettings(BaseSettings):
    """AI-related settings."""
    MODEL_PATH: str = os.getenv("MODEL_PATH", "./models")
    MODEL_CONFIDENCE_THRESHOLD: float = 0.7
    MAX_VIDEO_DURATION: int = 300  # 5 minutes in seconds
    FRAME_EXTRACTION_RATE: int = 30  # Extract every 30th frame

class MonitoringSettings(BaseSettings):
    """Monitoring-related settings."""
    ENABLE_MONITORING: bool = True
    ENABLE_PROMETHEUS: bool = True
    ENABLE_ALERTS: bool = True
    ALERT_EMAIL_ENABLED: bool = True
    ALERT_SLACK_ENABLED: bool = False
    ALERT_SMS_ENABLED: bool = False
    ALERT_EMAIL_FROM: str = os.getenv("ALERT_EMAIL_FROM", "alerts@formiq.com")
    ALERT_EMAIL_TO: str = os.getenv("ALERT_EMAIL_TO", "admin@formiq.com")
    ALERT_THRESHOLDS: Dict[str, float] = {
        "error_rate": 0.05,
        "response_time": 2.0,
        "db_connections": 100,
        "redis_memory": 0.9,
        "cache_hit_ratio": 0.5,
        "cpu_usage": 80.0,
        "memory_usage": 85.0,
        "disk_usage": 90.0
    }

class Settings(
    BaseSettings,
    SecuritySettings,
    DatabaseSettings,
    RedisSettings,
    StorageSettings,
    EmailSettings,
    AISettings,
    MonitoringSettings
):
    """Main settings class combining all settings modules."""
    
    # Application
    PROJECT_NAME: str = PROJECT_NAME
    VERSION: str = VERSION
    DESCRIPTION: str = DESCRIPTION
    API_V1_STR: str = API_V1_STR
    ENVIRONMENT: str = DEFAULT_ENVIRONMENT
    DEBUG: bool = True
    
    # CORS
    CORS_ORIGINS: List[AnyHttpUrl] = []

    @validator("CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: str | List[str]) -> List[str] | str:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.SQLALCHEMY_DATABASE_URI:
            if self.ENVIRONMENT == "test":
                self.SQLALCHEMY_DATABASE_URI = "sqlite:///./test.db"
            else:
                self.SQLALCHEMY_DATABASE_URI = f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD.get_secret_value()}@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"

    model_config = SettingsConfigDict(case_sensitive=True, env_file=".env")

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings() 