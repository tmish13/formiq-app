"""
Application-wide constants.
"""
from enum import Enum, auto
from typing import Dict, List

# API constants
API_PREFIX = "/api/v1"
API_TITLE = "FormIQ API"
API_DESCRIPTION = "FormIQ API for exercise form analysis"

# Database constants
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# User constants
MIN_USERNAME_LENGTH = 4
MAX_USERNAME_LENGTH = 32
MIN_PASSWORD_LENGTH = 8
DEFAULT_USER_AVATAR = "default_avatar.png"

# Token constants
TOKEN_TYPE_ACCESS = "access"
TOKEN_TYPE_REFRESH = "refresh"
TOKEN_TYPE_RESET = "reset"
TOKEN_PREFIX = "Bearer"

# Cache constants
CACHE_PREFIX_USER = "user"
CACHE_PREFIX_EXERCISE = "exercise"
CACHE_PREFIX_WORKOUT = "workout"
CACHE_PREFIX_RATE_LIMIT = "rate_limit"
CACHE_DEFAULT_TTL = 3600  # 1 hour

# Rate limit constants
RATE_LIMIT_DEFAULT = 100
RATE_LIMIT_BURST = 200

# Exercise constants
EXERCISE_TYPES = ["strength", "cardio", "flexibility"]
EXERCISE_DIFFICULTY_LEVELS = ["beginner", "intermediate", "advanced"]
EXERCISE_BODY_PARTS = [
    "chest", "back", "arms", "shoulders", "legs", "core", "full_body"
]

# Workout constants
WORKOUT_TYPES = ["strength", "cardio", "hiit", "flexibility", "mixed"]
WORKOUT_STATUS = ["planned", "in_progress", "completed", "cancelled"]

# Permission constants
class Permissions(str, Enum):
    """Permission enum."""
    READ_USERS = "read:users"
    WRITE_USERS = "write:users"
    READ_EXERCISES = "read:exercises"
    WRITE_EXERCISES = "write:exercises"
    READ_WORKOUTS = "read:workouts"
    WRITE_WORKOUTS = "write:workouts"
    ADMIN = "admin"

# Role constants
class Roles(str, Enum):
    """Role enum."""
    ADMIN = "admin"
    USER = "user"
    TRAINER = "trainer"
    GUEST = "guest"

# Role permissions mapping
ROLE_PERMISSIONS: Dict[str, List[str]] = {
    Roles.ADMIN: [p.value for p in Permissions],
    Roles.USER: [
        Permissions.READ_EXERCISES.value,
        Permissions.READ_WORKOUTS.value,
        Permissions.WRITE_WORKOUTS.value,
    ],
    Roles.TRAINER: [
        Permissions.READ_EXERCISES.value,
        Permissions.WRITE_EXERCISES.value,
        Permissions.READ_WORKOUTS.value,
        Permissions.WRITE_WORKOUTS.value,
        Permissions.READ_USERS.value,
    ],
    Roles.GUEST: [
        Permissions.READ_EXERCISES.value,
    ],
}

# Error constants
class ErrorCodes(str, Enum):
    """Error code enum."""
    AUTHENTICATION_ERROR = "authentication_error"
    AUTHORIZATION_ERROR = "authorization_error"
    VALIDATION_ERROR = "validation_error"
    RESOURCE_NOT_FOUND = "resource_not_found"
    RESOURCE_ALREADY_EXISTS = "resource_already_exists"
    DATABASE_ERROR = "database_error"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    INTERNAL_SERVER_ERROR = "internal_server_error"

# HTTP Status codes with descriptions
HTTP_STATUS_CODES: Dict[int, str] = {
    200: "OK",
    201: "Created",
    204: "No Content",
    400: "Bad Request",
    401: "Unauthorized",
    403: "Forbidden",
    404: "Not Found",
    409: "Conflict",
    422: "Unprocessable Entity",
    429: "Too Many Requests",
    500: "Internal Server Error",
}

# Default configuration values
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_ENVIRONMENT = "development"

# Project metadata
PROJECT_NAME = "FormIQ"
VERSION = "1.0.0"
DESCRIPTION = "AI-powered exercise form analysis API"

# API configuration
API_V1_STR = "/api/v1"

# Logging configuration
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
LOG_FILE_MAX_BYTES = 10 * 1024 * 1024  # 10MB
LOG_FILE_BACKUP_COUNT = 5
LOG_DIR = "logs"
LOG_FILE = "app.log"
ERROR_LOG_FILE = "error.log"

# Security defaults
DEFAULT_ALGORITHM = "HS256"
DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Rate limiting defaults
DEFAULT_RATE_LIMIT_REQUESTS = 100
DEFAULT_RATE_LIMIT_BURST = 200

# CORS defaults
DEFAULT_CORS_ORIGINS = ["http://localhost:3000"]

# SMTP defaults
DEFAULT_SMTP_TLS = True
DEFAULT_SMTP_PORT = 587 