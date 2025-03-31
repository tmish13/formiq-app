"""Input validation module."""
import re
from typing import Any, Dict, List, Optional, Pattern, Union, Set
from email_validator import validate_email as validate_email_format, EmailNotValidError
from app.core.exceptions import ValidationException
from app.core.config import settings
import magic
import os
import tempfile
import cv2

# Email validation
EMAIL_REGEX: Pattern = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

def validate_email(email: str) -> str:
    """Validate email format."""
    try:
        valid = validate_email_format(email)
        return valid.email
    except EmailNotValidError as e:
        raise ValidationException(detail=str(e))

# Password validation
PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128
PASSWORD_REGEX: Pattern = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$"
)

def validate_password(password: str) -> None:
    """
    Validate password strength.
    Requirements:
    - Between 8 and 128 characters long
    - Contains at least one uppercase letter
    - Contains at least one lowercase letter
    - Contains at least one number
    - Contains at least one special character
    - No common passwords or patterns
    """
    if not PASSWORD_MIN_LENGTH <= len(password) <= PASSWORD_MAX_LENGTH:
        raise ValidationException(
            detail=f"Password must be between {PASSWORD_MIN_LENGTH} and {PASSWORD_MAX_LENGTH} characters long"
        )
    
    if not re.search(r"[A-Z]", password):
        raise ValidationException(detail="Password must contain at least one uppercase letter")
    
    if not re.search(r"[a-z]", password):
        raise ValidationException(detail="Password must contain at least one lowercase letter")
    
    if not re.search(r"\d", password):
        raise ValidationException(detail="Password must contain at least one number")
    
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        raise ValidationException(detail="Password must contain at least one special character")
    
    # Check for common patterns
    common_patterns = [
        r"12345",
        r"qwerty",
        r"password",
        r"admin",
        r"letmein",
        r"welcome",
    ]
    for pattern in common_patterns:
        if re.search(pattern, password.lower()):
            raise ValidationException(detail="Password contains a common pattern that is not allowed")

# Username validation
USERNAME_MIN_LENGTH = 4
USERNAME_MAX_LENGTH = 30
USERNAME_REGEX: Pattern = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]*$")

def validate_username(username: str) -> None:
    """
    Validate username format.
    Requirements:
    - Between 4 and 30 characters long
    - Starts with a letter
    - Contains only letters, numbers, underscores, and hyphens
    - Not a reserved word
    """
    if not USERNAME_MIN_LENGTH <= len(username) <= USERNAME_MAX_LENGTH:
        raise ValidationException(
            detail=f"Username must be between {USERNAME_MIN_LENGTH} and {USERNAME_MAX_LENGTH} characters long"
        )
    
    if not username[0].isalpha():
        raise ValidationException(detail="Username must start with a letter")
    
    if not USERNAME_REGEX.match(username):
        raise ValidationException(
            detail="Username can only contain letters, numbers, underscores, and hyphens"
        )
    
    # Check for reserved words
    reserved_words = {
        "admin", "root", "system", "user", "moderator", "support",
        "help", "info", "contact", "about", "privacy", "terms",
        "api", "test", "demo", "example", "null", "undefined"
    }
    if username.lower() in reserved_words:
        raise ValidationException(detail="This username is reserved and cannot be used")

# File validation
ALLOWED_VIDEO_TYPES = {
    "video/mp4": ".mp4",
    "video/quicktime": ".mov",
    "video/x-msvideo": ".avi",
    "video/x-ms-wmv": ".wmv"
}

ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif"
}

def validate_file_type(file_content: bytes, allowed_types: Dict[str, str]) -> str:
    """
    Validate file type using magic numbers.
    
    Args:
        file_content: File content in bytes
        allowed_types: Dictionary of allowed MIME types and their extensions
        
    Returns:
        File extension if valid
        
    Raises:
        ValidationException: If file type is not allowed
    """
    mime = magic.from_buffer(file_content, mime=True)
    if mime not in allowed_types:
        raise ValidationException(
            detail=f"File type {mime} not allowed. Allowed types: {', '.join(allowed_types.keys())}"
        )
    return allowed_types[mime]

def validate_file_size(size: int, max_size_mb: int) -> None:
    """
    Validate file size.
    
    Args:
        size: File size in bytes
        max_size_mb: Maximum allowed size in megabytes
        
    Raises:
        ValidationException: If file size exceeds maximum
    """
    max_size_bytes = max_size_mb * 1024 * 1024
    if size > max_size_bytes:
        raise ValidationException(
            detail=f"File size exceeds maximum allowed size of {max_size_mb}MB"
        )

def validate_video_file(content: bytes, filename: str, max_size_mb: int = 100) -> None:
    """
    Validate video file format and size.
    
    Args:
        content: Video file content
        filename: Original filename
        max_size_mb: Maximum allowed size in MB
    """
    # Check file size
    size_mb = len(content) / (1024 * 1024)
    if size_mb > max_size_mb:
        raise ValidationException(
            detail=f"Video file size ({size_mb:.1f}MB) exceeds maximum allowed size ({max_size_mb}MB)"
        )
    
    # Check file extension
    allowed_extensions = {".mp4", ".mov", ".avi", ".webm"}
    file_ext = os.path.splitext(filename)[1].lower()
    if file_ext not in allowed_extensions:
        raise ValidationException(
            detail=f"Invalid file extension. Allowed extensions: {', '.join(allowed_extensions)}"
        )
    
    # Check file type using python-magic
    mime = magic.Magic(mime=True)
    file_type = mime.from_buffer(content)
    allowed_types = {
        "video/mp4": "MP4",
        "video/quicktime": "MOV",
        "video/x-msvideo": "AVI",
        "video/webm": "WEBM"
    }
    
    if file_type not in allowed_types:
        raise ValidationException(
            detail=f"Invalid file type. Allowed types: {', '.join(allowed_types.values())}"
        )
    
    # Check video duration using OpenCV
    with tempfile.NamedTemporaryFile(suffix=file_ext, delete=False) as temp_file:
        temp_file.write(content)
        temp_file.flush()
        
        cap = cv2.VideoCapture(temp_file.name)
        if not cap.isOpened():
            raise ValidationException(detail="Invalid video file")
            
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = frame_count / fps if fps > 0 else 0
        
        if duration > settings.MAX_VIDEO_DURATION:
            raise ValidationException(
                detail=f"Video duration ({duration:.1f}s) exceeds maximum allowed duration ({settings.MAX_VIDEO_DURATION}s)"
            )
        
        cap.release()
        os.unlink(temp_file.name)

# General validation functions
def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> None:
    """
    Validate that all required fields are present and not empty.
    
    Args:
        data: Data to validate
        required_fields: List of required field names
        
    Raises:
        ValidationException: If any required field is missing or empty
    """
    missing_fields = []
    empty_fields = []
    
    for field in required_fields:
        if field not in data:
            missing_fields.append(field)
        elif not data[field] and not isinstance(data[field], (bool, int, float)):
            empty_fields.append(field)
    
    if missing_fields:
        raise ValidationException(
            detail="Missing required fields",
            details={"missing_fields": missing_fields}
        )
    
    if empty_fields:
        raise ValidationException(
            detail="Required fields cannot be empty",
            details={"empty_fields": empty_fields}
        )

def validate_field_length(
    value: str, 
    field_name: str, 
    min_length: Optional[int] = None, 
    max_length: Optional[int] = None
) -> None:
    """
    Validate field length.
    
    Args:
        value: Field value to validate
        field_name: Name of the field
        min_length: Minimum length
        max_length: Maximum length
        
    Raises:
        ValidationException: If field length is invalid
    """
    if min_length is not None and len(value) < min_length:
        raise ValidationException(
            detail=f"{field_name} must be at least {min_length} characters long",
            details={"field": field_name, "min_length": min_length}
        )
    
    if max_length is not None and len(value) > max_length:
        raise ValidationException(
            detail=f"{field_name} must be at most {max_length} characters long",
            details={"field": field_name, "max_length": max_length}
        )

def validate_numeric_range(
    value: Union[int, float], 
    field_name: str, 
    min_value: Optional[Union[int, float]] = None, 
    max_value: Optional[Union[int, float]] = None
) -> None:
    """
    Validate numeric range.
    
    Args:
        value: Numeric value to validate
        field_name: Name of the field
        min_value: Minimum value
        max_value: Maximum value
        
    Raises:
        ValidationException: If numeric range is invalid
    """
    if min_value is not None and value < min_value:
        raise ValidationException(
            detail=f"{field_name} must be at least {min_value}",
            details={"field": field_name, "min_value": min_value}
        )
    
    if max_value is not None and value > max_value:
        raise ValidationException(
            detail=f"{field_name} must be at most {max_value}",
            details={"field": field_name, "max_value": max_value}
        )

def validate_rate_limit(requests: int, burst: int) -> None:
    """
    Validate rate limit parameters.
    
    Args:
        requests: Number of requests allowed per time window
        burst: Maximum burst size
    """
    if requests < 1:
        raise ValidationException(detail="Rate limit requests must be greater than 0")
    
    if burst < requests:
        raise ValidationException(detail="Burst size must be greater than or equal to requests")
    
    if requests > settings.RATE_LIMIT_REQUESTS:
        raise ValidationException(
            detail=f"Rate limit requests ({requests}) exceeds maximum allowed ({settings.RATE_LIMIT_REQUESTS})"
        )
    
    if burst > settings.RATE_LIMIT_BURST:
        raise ValidationException(
            detail=f"Burst size ({burst}) exceeds maximum allowed ({settings.RATE_LIMIT_BURST})"
        )

def validate_workout_data(data: Dict[str, Any]) -> None:
    """
    Validate workout data.
    
    Args:
        data: Workout data dictionary
    """
    required_fields = ["name", "type", "duration", "difficulty"]
    validate_required_fields(data, required_fields)
    
    # Validate name
    validate_field_length(data["name"], "name", min_length=3, max_length=100)
    
    # Validate type
    valid_types = {"strength", "cardio", "flexibility", "balance"}
    if data["type"] not in valid_types:
        raise ValidationException(
            detail=f"Invalid workout type. Must be one of: {', '.join(valid_types)}"
        )
    
    # Validate duration
    validate_numeric_range(data["duration"], "duration", min_value=1, max_value=180)
    
    # Validate difficulty
    valid_difficulties = {"beginner", "intermediate", "advanced"}
    if data["difficulty"] not in valid_difficulties:
        raise ValidationException(
            detail=f"Invalid difficulty level. Must be one of: {', '.join(valid_difficulties)}"
        ) 