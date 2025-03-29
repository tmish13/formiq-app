from typing import Optional
from datetime import datetime
from app.schemas.base import BaseSchema

class SubscriptionBase(BaseSchema):
    """Base subscription schema with common fields."""
    tier: str
    status: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    stripe_customer_id: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

class SubscriptionCreate(SubscriptionBase):
    """Schema for creating a new subscription."""
    user_id: int

class SubscriptionUpdate(SubscriptionBase):
    """Schema for updating a subscription."""
    tier: Optional[str] = None
    status: Optional[str] = None

class SubscriptionResponse(SubscriptionBase):
    """Schema for subscription response."""
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None 