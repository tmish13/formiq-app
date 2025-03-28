from datetime import datetime
from typing import Optional
from pydantic import EmailStr
from app.schemas.base import BaseSchema
from app.models.subscription import SubscriptionTier

class UserBase(BaseSchema):
    """Base user schema with common fields."""
    email: EmailStr
    first_name: str
    last_name: str
    is_active: bool
    is_verified: bool
    subscription_tier: SubscriptionTier
    subscription_end_date: Optional[datetime] = None

class UserCreate(UserBase):
    """Schema for creating a new user."""
    password: str

class UserUpdate(BaseSchema):
    """Schema for updating user information."""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    password: Optional[str] = None

class UserResponse(UserBase):
    """Schema for user response."""
    pass 