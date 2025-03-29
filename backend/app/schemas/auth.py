"""Authentication schemas."""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, validator

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
    
    class Config:
        json_schema_extra={
            "example": {
                "email": "user@example.com",
                "password": "strongpassword123",
                "full_name": "John Doe"
            }
        }

class UserLogin(BaseModel):
    """User login schema."""
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., description="User's password")
    remember_me: bool = Field(default=False, description="Remember login session")
    
    class Config:
        json_schema_extra={
            "example": {
                "email": "user@example.com",
                "password": "userpassword",
                "remember_me": False
            }
        }

class TokenResponse(BaseModel):
    """Token response schema."""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_at: datetime = Field(..., description="Token expiration timestamp")
    
    class Config:
        json_schema_extra={
            "example": {
                "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
                "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
                "token_type": "bearer",
                "expires_at": "2024-02-20T12:00:00Z"
            }
        }

class PasswordResetRequest(BaseModel):
    """Password reset request schema."""
    email: EmailStr = Field(..., description="Email address for password reset")
    
    class Config:
        json_schema_extra={
            "example": {
                "email": "user@example.com"
            }
        }

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
    
    @validator("confirm_password")
    def passwords_match(cls, v, values, **kwargs):
        if "new_password" in values and v != values["new_password"]:
            raise ValueError("Passwords do not match")
        return v

    @validator("new_password")
    def validate_password_length(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if len(v) > 100:
            raise ValueError("Password must not exceed 100 characters")
        return v

    class Config:
        json_schema_extra={
            "example": {
                "token": "reset-token-123",
                "new_password": "newstrongpassword123",
                "confirm_password": "newstrongpassword123"
            }
        }

class TokenRefresh(BaseModel):
    """Token refresh schema."""
    refresh_token: str = Field(..., description="JWT refresh token")
    
    class Config:
        json_schema_extra={
            "example": {
                "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
            }
        }

class TokenVerify(BaseModel):
    """Token verification schema."""
    token: str = Field(..., description="JWT token to verify")
    
    class Config:
        json_schema_extra={
            "example": {
                "token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
            }
        } 