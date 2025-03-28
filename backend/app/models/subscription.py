from enum import Enum
from sqlalchemy import Column, String, DateTime, Enum as SQLEnum, Integer, Boolean
from app.models.base import BaseModel

class SubscriptionTier(str, Enum):
    """Subscription tiers available in the application."""
    FREE = "free"
    BASIC = "basic"
    PRO = "pro"
    ENTERPRISE = "enterprise"

class Subscription(BaseModel):
    """Subscription model for tracking user subscriptions."""
    __tablename__ = "subscriptions"

    user_id = Column(Integer, nullable=False)
    tier = Column(SQLEnum(SubscriptionTier), nullable=False)
    stripe_subscription_id = Column(String, unique=True)
    stripe_customer_id = Column(String, nullable=False)
    status = Column(String, nullable=False)  # active, canceled, past_due, etc.
    current_period_start = Column(DateTime)
    current_period_end = Column(DateTime)
    cancel_at_period_end = Column(Boolean, default=False)
    canceled_at = Column(DateTime)
    trial_start = Column(DateTime)
    trial_end = Column(DateTime) 