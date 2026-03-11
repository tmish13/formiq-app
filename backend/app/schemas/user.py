"""User related schemas."""
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator, constr, UUID4, ConfigDict
from app.core.validators import validate_password
import re


class OnboardingComplete(BaseModel):
    """Payload accepted by POST /auth/complete-onboarding."""
    fitness_goal: Optional[str] = Field(None, max_length=100)
    preferred_exercises: Optional[List[str]] = None


class OnboardingCompleteResponse(BaseModel):
    """Response from POST /auth/complete-onboarding."""
    message: str
    user: "UserInDBBase"

    model_config = ConfigDict(from_attributes=True)

from app.core.config import settings

class UserBase(BaseModel):
    """Base user schema with common attributes."""
    email: EmailStr = Field(
        ...,
        description="User's email address",
        example="user@example.com"
    )
    full_name: Optional[str] = Field(
        None,
        description="User's full name",
        example="John Doe",
        max_length=100
    )
    is_active: bool = Field(
        True,
        description="Whether the user account is active"
    )
    username: Optional[constr(min_length=3, max_length=50)] = Field(
        None, 
        description="Username for login (3-50 characters)"
    )
    is_verified: bool = Field(False, description="Whether the user is verified")
    
    @field_validator("username")
    @classmethod
    def validate_username(cls, v):
        """Validate username format."""
        if v is None:
            return v
        if not v.isalnum() and not any(c in v for c in "_-"):
            raise ValueError("Username must contain only alphanumeric characters, underscores, or hyphens")
        return v

class UserCreate(UserBase):
    """Schema for creating a new user."""
    password: constr(min_length=8, max_length=100) = Field(
        ...,
        description="""
        User's password. Must be:
        * At least 8 characters long (max 100)
        * Contain at least one number
        * Contain at least one special character (!@#$%^&*()_-+=[]{}|;:'\",.<>/?`~)
        """,
        example="StrongPass123!"
    )
    username: Optional[constr(min_length=3, max_length=50)] = Field(
        None, 
        description="Username (3-50 characters). If not provided, email will be used"
    )
    full_name: Optional[str] = Field(None, description="User's full name")
    is_superuser: Optional[bool] = Field(False, description="Whether user is a superuser")
    confirm_password: str = Field(
        ...,
        description="Confirm the password",
        min_length=8,
        max_length=100
    )

    @model_validator(mode="after")
    def set_username_default(self):
        """Set username to email prefix if not provided."""
        if not self.username and self.email:
            self.username = self.email.split("@")[0]
        return self

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one number")
        if not any(c in "!@#$%^&*()-_=+[]{}|;:'\",.<>/?`~" for c in v):
            raise ValueError("Password must contain at least one special character")
        return v

    @field_validator('confirm_password')
    @classmethod
    def passwords_match(cls, v, info):
        """
        Validate that password and confirm_password match.
        
        Args:
            v: Confirm password value
            info: Validation info object containing processed values
            
        Returns:
            str: Confirmed password
        """
        if 'new_password' in info.data and v != info.data['new_password']:
            raise ValueError('Passwords do not match')
        return v

class UserUpdate(BaseModel):
    """Schema for updating user information. All fields optional for partial updates."""
    email: Optional[EmailStr] = Field(None, description="User's email address")
    full_name: Optional[str] = Field(None, description="User's full name", max_length=100)
    is_active: Optional[bool] = Field(None, description="Whether the user account is active")
    username: Optional[constr(min_length=3, max_length=50)] = Field(None, description="Username")
    is_verified: Optional[bool] = Field(None, description="Whether the user is verified")
    password: Optional[constr(min_length=8, max_length=100)] = Field(
        None,
        description="New password (must meet password requirements)",
        example="NewStrongPass123"
    )
    subscription_tier: Optional[str] = Field(None, description="User's subscription tier")
    is_superuser: Optional[bool] = Field(None, description="Whether user is a superuser")
    last_login: Optional[datetime] = Field(None, description="Timestamp of the last login")
    fitness_goal: Optional[str] = Field(None, description="Primary fitness goal", max_length=100)
    preferred_exercises: Optional[List[str]] = Field(None, description="Preferred exercise types")
    fitness_level: Optional[str] = Field(None, description="Fitness level (beginner/intermediate/advanced)")
    profile_image_url: Optional[str] = Field(None, description="URL to profile image")
    has_completed_onboarding: Optional[bool] = Field(None, description="Whether onboarding is complete")
    weight_kg: Optional[float] = Field(None, description="Body weight in kilograms")
    age: Optional[int] = Field(None, description="User age in years")
    height_cm: Optional[float] = Field(None, description="Height in centimetres")
    training_experience: Optional[str] = Field(None, description="Training experience level", max_length=50)

    @field_validator("password")
    @classmethod
    def validate_password_field(cls, v):
        """Validate password strength."""
        if v is None:
            return v
        
        try:
            validate_password(v)
        except Exception as e:
            raise ValueError(str(e))
        
        return v
    
    @field_validator("subscription_tier")
    @classmethod
    def validate_subscription_tier(cls, v):
        """Validate subscription tier."""
        if v is None:
            return v
        if hasattr(v, 'value'):
            v = v.value.upper()
        allowed_tiers = ["FREE", "BASIC", "PRO", "PREMIUM", "ENTERPRISE"]
        if str(v).upper() not in allowed_tiers:
            raise ValueError(f"Subscription tier must be one of: {', '.join(allowed_tiers)}")
        return str(v).lower()

class UserInDBBase(UserBase):
    """Base schema for user in database."""
    id: UUID4 = Field(
        ...,
        description="Unique identifier for the user",
        example="123e4567-e89b-12d3-a456-426614174000"
    )
    created_at: datetime = Field(
        ...,
        description="When the user account was created",
        example="2024-01-20T10:30:00Z"
    )
    updated_at: Optional[datetime] = Field(
        None,
        description="When the user account was last updated",
        example="2024-01-20T10:35:00Z"
    )
    is_superuser: Optional[bool] = False
    is_verified: Optional[bool] = False
    is_email_verified: Optional[bool] = False
    subscription_tier: str = Field("FREE", description="User's subscription tier")
    subscription_end_date: Optional[datetime] = None
    
    # Onboarding fields
    has_completed_onboarding: Optional[bool] = Field(
        False,
        description="Whether the user has completed the onboarding process"
    )
    onboarding_completed_at: Optional[datetime] = Field(
        None,
        description="When the user completed onboarding",
        example="2024-01-20T10:45:00Z"
    )

    # Profile preference fields
    fitness_goal: Optional[str] = Field(None, description="Primary fitness goal")
    preferred_exercises: Optional[List[str]] = Field(None, description="Preferred exercise types")
    fitness_level: Optional[str] = Field(None, description="Fitness level")
    profile_image_url: Optional[str] = Field(None, description="URL to profile image")
    weight_kg: Optional[float] = Field(None, description="Body weight in kilograms")
    age: Optional[int] = Field(None, description="User age in years")
    height_cm: Optional[float] = Field(None, description="Height in centimetres")
    training_experience: Optional[str] = Field(None, description="Training experience level")

    model_config = ConfigDict(from_attributes=True)

class User(UserInDBBase):
    """
    Complete user schema for API responses.
    
    Excludes sensitive information like password.
    """
    form_checks_count: Optional[int] = Field(0, description="Number of form checks submitted")
    
    @field_validator("subscription_tier")
    @classmethod
    def validate_subscription_tier(cls, v):
        """Validate subscription tier."""
        if hasattr(v, 'value'):
            v = v.value.upper()
        allowed_tiers = ["FREE", "BASIC", "PRO", "PREMIUM", "ENTERPRISE"]
        if str(v).upper() not in allowed_tiers:
            raise ValueError(f"Subscription tier must be one of: {', '.join(allowed_tiers)}")
        return str(v).lower()

class UserInDB(UserInDBBase):
    """Schema for user in database with hashed password."""
    hashed_password: str = Field(
        ...,
        description="Hashed version of the user's password",
        example="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewYVx3"
    )
    failed_login_attempts: int = Field(0, description="Number of failed login attempts")
    locked_until: Optional[datetime] = Field(None, description="Lockout until")

class UserResponse(UserInDBBase):
    """Schema for user response (without password)."""
    subscription_status: Optional[str] = Field(
        None,
        description="User's subscription status",
        example="premium",
        pattern="^(free|basic|premium)$"
    )
    profile_image_url: Optional[str] = Field(
        None,
        description="URL to user's profile image",
        example="https://storage.formiq.com/profiles/user123.jpg"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "email": "user@example.com",
                "full_name": "John Doe",
                "is_active": True,
                "subscription_status": "premium",
                "profile_image_url": "https://storage.formiq.com/profiles/user123.jpg",
                "created_at": "2024-01-20T10:30:00Z",
                "updated_at": "2024-01-20T10:35:00Z"
            }
        }
    )

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
    
    @field_validator("subscription_tier")
    @classmethod
    def validate_subscription_tier(cls, v):
        """Validate subscription tier."""
        if v is None:
            return v
        if hasattr(v, 'value'):
            v = v.value.upper()
        allowed_tiers = ["FREE", "BASIC", "PRO", "PREMIUM", "ENTERPRISE"]
        if str(v).upper() not in allowed_tiers:
            raise ValueError(f"Subscription tier must be one of: {', '.join(allowed_tiers)}")
        return str(v).lower()

class UserUpdatePassword(BaseModel):
    """User password update schema."""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(
        ...,
        description="New password",
        min_length=8,
        max_length=100
    )

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v):
        """Validate password."""
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one number")

        special_chars = "!@#$%^&*()_-+=[]{}|;:'\",.<>/?`~"
        if not any(c in special_chars for c in v):
            raise ValueError("Password must contain at least one special character")

        return v

class UserPasswordReset(BaseModel):
    """User password reset schema."""
    token: str = Field(..., description="Password reset token")
    new_password: str = Field(
        ...,
        description="New password",
        min_length=8,
        max_length=100
    )
    confirm_password: str = Field(
        ...,
        description="Confirm the new password",
        min_length=8,
        max_length=100
    )

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v):
        """Validate password."""
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one number")

        special_chars = "!@#$%^&*()_-+=[]{}|;:'\",.<>/?`~"
        if not any(c in special_chars for c in v):
            raise ValueError("Password must contain at least one special character")

        return v

    @field_validator('confirm_password')
    @classmethod
    def passwords_match(cls, v, info):
        """
        Validate that password and confirm_password match.
        
        Args:
            v: Confirm password value
            info: Validation info object containing processed values
            
        Returns:
            str: Confirmed password
        """
        if 'new_password' in info.data and v != info.data['new_password']:
            raise ValueError('Passwords do not match')
        return v

class PasswordReset(BaseModel):
    """Schema for password reset."""
    token: str = Field(
        ...,
        description="Password reset token from email",
        example="eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
    )
    new_password: constr(min_length=8, max_length=100) = Field(
        ...,
        description="New password (must meet password requirements)",
        example="NewStrongPass123"
    )

class PasswordChange(BaseModel):
    """Schema for password change."""
    current_password: str = Field(
        ...,
        description="Current password for verification",
        example="OldStrongPass123"
    )
    new_password: constr(min_length=8, max_length=100) = Field(
        ...,
        description="New password (must meet password requirements)",
        example="NewStrongPass123"
    ) 