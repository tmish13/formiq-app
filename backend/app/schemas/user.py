"""User schema module."""
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, validator, constr
from app.core.validators import validate_password
import re

from app.core.config import settings

class UserBase(BaseModel):
    """
    Base user schema with common fields.
    
    Attributes:
        email: User's email address
        is_active: Whether the user account is active
        full_name: User's full name (optional)
        username: User's username for login
    """
    email: Optional[EmailStr] = Field(None, description="User's email address")
    is_active: Optional[bool] = Field(True, description="Whether the user account is active")
    full_name: Optional[str] = Field(None, description="User's full name")
    username: Optional[constr(min_length=3, max_length=50)] = Field(
        None, 
        description="Username for login (3-50 characters)"
    )
    
    @validator("username")
    def validate_username(cls, v):
        """Validate username format."""
        if v is None:
            return v
        if not v.isalnum() and not any(c in v for c in "_-"):
            raise ValueError("Username must contain only alphanumeric characters, underscores, or hyphens")
        return v

class UserCreate(UserBase):
    """
    Schema for creating a new user.
    
    Requires email and password. Username is optional and defaults to using email.
    """
    email: EmailStr = Field(..., description="User's email address")
    username: Optional[constr(min_length=3, max_length=50)] = Field(
        None, 
        description="Username (3-50 characters). If not provided, email will be used"
    )
    password: constr(min_length=8) = Field(..., description="Password (min 8 characters)")
    full_name: Optional[str] = Field(None, description="User's full name")
    is_superuser: Optional[bool] = Field(False, description="Whether user is a superuser")

    @validator("username")
    def set_username_default(cls, v, values):
        """Set username to email if not provided."""
        if not v and "email" in values:
            # Use part before @ as username if email is available
            return values["email"].split("@")[0]
        return v

    @validator("password")
    def validate_password(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one number")
        if not any(c in "!@#$%^&*()-_=+[]{}|;:'\",.<>/?`~" for c in v):
            raise ValueError("Password must contain at least one special character")
        return v

class UserUpdate(UserBase):
    """
    Schema for updating an existing user.
    
    All fields are optional to allow partial updates.
    """
    password: Optional[constr(min_length=8)] = Field(None, description="New password")
    subscription_tier: Optional[str] = Field(None, description="User's subscription tier")
    is_superuser: Optional[bool] = Field(None, description="Whether user is a superuser")

    @validator("password")
    def validate_password_field(cls, v):
        """Validate password strength."""
        if v is None:
            return v
        
        try:
            validate_password(v)
        except Exception as e:
            raise ValueError(str(e))
        
        return v
    
    @validator("subscription_tier")
    def validate_subscription_tier(cls, v):
        """Validate subscription tier."""
        if v is None:
            return v
        allowed_tiers = ["FREE", "BASIC", "PRO", "PREMIUM"]
        if v not in allowed_tiers:
            raise ValueError(f"Subscription tier must be one of: {', '.join(allowed_tiers)}")
        return v

class UserInDBBase(UserBase):
    """
    Base schema for user data stored in the database.
    
    Includes database-specific fields like ID and timestamps.
    """
    id: Optional[UUID] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    is_superuser: Optional[bool] = False
    is_verified: Optional[bool] = False
    is_email_verified: Optional[bool] = False
    subscription_tier: str = Field("FREE", description="User's subscription tier")
    subscription_end_date: Optional[datetime] = None

    class Config:
        """Pydantic config."""
        from_attributes = True

class User(UserInDBBase):
    """
    Complete user schema for API responses.
    
    Excludes sensitive information like password.
    """
    form_checks_count: Optional[int] = Field(0, description="Number of form checks submitted")
    
    @validator("subscription_tier")
    def validate_subscription_tier(cls, v):
        """Validate subscription tier."""
        allowed_tiers = ["FREE", "BASIC", "PRO", "PREMIUM"]
        if v not in allowed_tiers:
            raise ValueError(f"Subscription tier must be one of: {', '.join(allowed_tiers)}")
        return v

class UserInDB(UserInDBBase):
    """
    Complete user schema for database operations.
    
    Includes sensitive information like hashed_password.
    """
    hashed_password: str = Field(..., description="Hashed password (not returned in API responses)")

class UserFilter(BaseModel):
    """
    Schema for filtering users in queries.
    
    All fields are optional to allow flexible filtering.
    """
    email: Optional[str] = Field(None, description="Filter by email")
    username: Optional[str] = Field(None, description="Filter by username")
    is_active: Optional[bool] = Field(None, description="Filter by active status")
    is_superuser: Optional[bool] = Field(None, description="Filter by superuser status")
    is_verified: Optional[bool] = Field(None, description="Filter by verification status")
    subscription_tier: Optional[str] = Field(None, description="Filter by subscription tier")
    
    @validator("subscription_tier")
    def validate_subscription_tier(cls, v):
        """Validate subscription tier."""
        if v is None:
            return v
        allowed_tiers = ["FREE", "BASIC", "PRO", "PREMIUM"]
        if v not in allowed_tiers:
            raise ValueError(f"Subscription tier must be one of: {', '.join(allowed_tiers)}")
        return v

class UserUpdatePassword(BaseModel):
    """User password update schema."""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(
        ...,
        description="New password",
        min_length=8,
        max_length=128
    )
    
    @validator("new_password")
    def validate_password(cls, v):
        """Validate password."""
        # Check for uppercase letters
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        
        # Check for lowercase letters
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        
        # Check for digits
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one number")
        
        # Check for special characters
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            raise ValueError("Password must contain at least one special character")
        
        return v

class UserPasswordReset(BaseModel):
    """User password reset schema."""
    token: str = Field(..., description="Password reset token")
    new_password: str = Field(
        ...,
        description="New password",
        min_length=8,
        max_length=128
    )
    
    @validator("new_password")
    def validate_password(cls, v):
        """Validate password."""
        # Check for uppercase letters
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        
        # Check for lowercase letters
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        
        # Check for digits
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one number")
        
        # Check for special characters
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            raise ValueError("Password must contain at least one special character")
        
        return v 