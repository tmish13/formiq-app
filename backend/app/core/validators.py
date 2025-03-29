import re
from typing import Any, Dict, List, Optional, Pattern, Union
from email_validator import validate_email as validate_email_format, EmailNotValidError
from app.core.exceptions import ValidationException

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
PASSWORD_REGEX: Pattern = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$"
)

def validate_password(password: str) -> None:
    """
    Validate password strength.
    Requirements:
    - At least 8 characters long
    - Contains at least one uppercase letter
    - Contains at least one lowercase letter
    - Contains at least one number
    - Contains at least one special character
    """
    if len(password) < 8:
        raise ValidationException(detail="Password must be at least 8 characters long")
    
    if not re.search(r"[A-Z]", password):
        raise ValidationException(detail="Password must contain at least one uppercase letter")
    
    if not re.search(r"[a-z]", password):
        raise ValidationException(detail="Password must contain at least one lowercase letter")
    
    if not re.search(r"\d", password):
        raise ValidationException(detail="Password must contain at least one number")
    
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        raise ValidationException(detail="Password must contain at least one special character")

# Username validation
USERNAME_MIN_LENGTH = 4
USERNAME_MAX_LENGTH = 20
USERNAME_REGEX: Pattern = re.compile(r"^[a-zA-Z0-9_]+$")

def validate_username(username: str) -> None:
    """
    Validate username format.
    Requirements:
    - Between 3 and 30 characters long
    - Contains only alphanumeric characters, underscores, and hyphens
    - Starts with a letter
    """
    if not 3 <= len(username) <= 30:
        raise ValidationException(detail="Username must be between 3 and 30 characters long")
    
    if not username[0].isalpha():
        raise ValidationException(detail="Username must start with a letter")
    
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9_-]*$", username):
        raise ValidationException(detail="Username can only contain letters, numbers, underscores, and hyphens")

# General validation functions
def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> bool:
    """
    Validate that all required fields are present.
    
    Args:
        data: Data to validate
        required_fields: List of required field names
        
    Returns:
        True if all required fields are present
        
    Raises:
        ValidationException: If any required field is missing
    """
    missing_fields = [field for field in required_fields if field not in data]
    
    if missing_fields:
        raise ValidationException(
            "Missing required fields",
            details={"missing_fields": missing_fields}
        )
    
    return True

def validate_field_length(
    value: str, 
    field_name: str, 
    min_length: Optional[int] = None, 
    max_length: Optional[int] = None
) -> bool:
    """
    Validate field length.
    
    Args:
        value: Field value to validate
        field_name: Name of the field
        min_length: Minimum length
        max_length: Maximum length
        
    Returns:
        True if field length is valid
        
    Raises:
        ValidationException: If field length is invalid
    """
    if min_length is not None and len(value) < min_length:
        raise ValidationException(
            f"{field_name} must be at least {min_length} characters long",
            details={"field": field_name, "min_length": min_length}
        )
    
    if max_length is not None and len(value) > max_length:
        raise ValidationException(
            f"{field_name} must be at most {max_length} characters long",
            details={"field": field_name, "max_length": max_length}
        )
    
    return True

def validate_numeric_range(
    value: Union[int, float], 
    field_name: str, 
    min_value: Optional[Union[int, float]] = None, 
    max_value: Optional[Union[int, float]] = None
) -> bool:
    """
    Validate numeric range.
    
    Args:
        value: Numeric value to validate
        field_name: Name of the field
        min_value: Minimum value
        max_value: Maximum value
        
    Returns:
        True if numeric range is valid
        
    Raises:
        ValidationException: If numeric range is invalid
    """
    if min_value is not None and value < min_value:
        raise ValidationException(
            f"{field_name} must be at least {min_value}",
            details={"field": field_name, "min_value": min_value}
        )
    
    if max_value is not None and value > max_value:
        raise ValidationException(
            f"{field_name} must be at most {max_value}",
            details={"field": field_name, "max_value": max_value}
        )
    
    return True 