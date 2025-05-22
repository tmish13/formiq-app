"""Authentication schemas."""
from typing import Optional, Dict, List, Any
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict
from app.core.validators import validate_password

class UserCreate(BaseModel):
    """User creation schema."""
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(
        ...,
        description="User's password (min 8 chars)",
        min_length=8,
        max_length=100
    )
    full_name: str = Field(
        ...,
        description="User's full name",
        min_length=1,
        max_length=100
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "user@example.com",
                "password": "strongpassword123",
                "full_name": "John Doe"
            }
        }
    )

class UserLogin(BaseModel):
    """User login schema."""
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., description="User's password")
    remember_me: bool = Field(default=False, description="Remember login session")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "user@example.com",
                "password": "userpassword",
                "remember_me": False
            }
        }
    )

class TokenResponse(BaseModel):
    """Token response schema."""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_at: datetime = Field(..., description="Token expiration timestamp")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
                "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
                "token_type": "bearer",
                "expires_at": "2024-02-20T12:00:00Z"
            }
        }
    )

class PasswordResetRequest(BaseModel):
    """Password reset request schema."""
    email: EmailStr = Field(..., description="Email address for password reset")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "user@example.com"
            }
        }
    )

class PasswordReset(BaseModel):
    """Password reset schema."""
    token: str = Field(..., description="Password reset token")
    new_password: str = Field(
        ...,
        description="New password (min 8 chars)",
        min_length=8,
        max_length=100
    )
    confirm_password: str = Field(..., description="Confirm new password")
    
    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v, info: Any):
        """
        Validate that passwords match.
        
        Args:
            v: The confirm_password value
            info: Validation info containing other fields
            
        Returns:
            The validated confirm_password
        """
        if "new_password" in info.data and v != info.data["new_password"]:
            raise ValueError("Passwords do not match")
        return v

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v):
        """
        Validate password strength.
        
        Args:
            v: The password value
            
        Returns:
            The validated password
        """
        try:
            validate_password(v)
        except Exception as e:
            raise ValueError(str(e))
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "token": "reset-token-123",
                "new_password": "newstrongpassword123",
                "confirm_password": "newstrongpassword123"
            }
        }
    )

class TokenRefresh(BaseModel):
    """Token refresh schema."""
    refresh_token: str = Field(..., description="JWT refresh token")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
            }
        }
    )

class TokenVerify(BaseModel):
    """Token verification schema."""
    token: str = Field(..., description="JWT token to verify")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
            }
        }
    )

class EmailVerificationRequest(BaseModel):
    """Email verification request schema."""
    email: EmailStr = Field(..., description="Email address for verification link")
    model_config = ConfigDict(json_schema_extra={"example": {"email": "user@example.com"}})

class EmailVerificationConfirm(BaseModel):
    """Email verification confirmation schema."""
    token: str = Field(..., description="Email verification token")
    model_config = ConfigDict(json_schema_extra={"example": {"token": "your_verification_token_string"}}) 