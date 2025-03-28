import re
from typing import Any, Dict, List, Optional, Pattern, Union
from email_validator import validate_email, EmailNotValidError
from app.core.exceptions import ValidationException

# Email validation
EMAIL_REGEX: Pattern = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

def validate_email_format(email: str) -> bool:
    """
    Validate email format.
    
    Args:
        email: Email to validate
        
    Returns:
        True if email is valid
        
    Raises:
        ValidationException: If email is invalid
    """
    try:
        validate_email(email)
        return True
    except EmailNotValidError as e:
        raise ValidationException(
            f"Invalid email format: {str(e)}",
            details={"email": email}
        )

# Password validation
PASSWORD_MIN_LENGTH = 8
PASSWORD_REGEX: Pattern = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$"
)

def validate_password_strength(password: str) -> bool:
    """
    Validate password strength.
    
    Args:
        password: Password to validate
        
    Returns:
        True if password is strong enough
        
    Raises:
        ValidationException: If password is not strong enough
    """
    if len(password) < PASSWORD_MIN_LENGTH:
        raise ValidationException(
            f"Password must be at least {PASSWORD_MIN_LENGTH} characters long",
            details={"min_length": PASSWORD_MIN_LENGTH}
        )
    
    if not PASSWORD_REGEX.match(password):
        raise ValidationException(
            "Password must contain at least one uppercase letter, one lowercase letter, one number, and one special character",
            details={"regex": PASSWORD_REGEX.pattern}
        )
    
    return True

# Username validation
USERNAME_MIN_LENGTH = 4
USERNAME_MAX_LENGTH = 20
USERNAME_REGEX: Pattern = re.compile(r"^[a-zA-Z0-9_]+$")

def validate_username(username: str) -> bool:
    """
    Validate username.
    
    Args:
        username: Username to validate
        
    Returns:
        True if username is valid
        
    Raises:
        ValidationException: If username is invalid
    """
    if len(username) < USERNAME_MIN_LENGTH:
        raise ValidationException(
            f"Username must be at least {USERNAME_MIN_LENGTH} characters long",
            details={"min_length": USERNAME_MIN_LENGTH}
        )
    
    if len(username) > USERNAME_MAX_LENGTH:
        raise ValidationException(
            f"Username must be at most {USERNAME_MAX_LENGTH} characters long",
            details={"max_length": USERNAME_MAX_LENGTH}
        )
    
    if not USERNAME_REGEX.match(username):
        raise ValidationException(
            "Username can only contain letters, numbers, and underscores",
            details={"regex": USERNAME_REGEX.pattern}
        )
    
    return True

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