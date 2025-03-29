from datetime import datetime
from enum import Enum
from typing import Optional
from sqlalchemy import Column, String, DateTime, Enum as SQLEnum, Integer, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, validates
from app.models.base import BaseModel
from app.core.exceptions import ValidationError

class SubscriptionTier(str, Enum):
    """Subscription tiers available in the application."""
    FREE = "free"
    BASIC = "basic"
    PRO = "pro"
    ENTERPRISE = "enterprise"

class Subscription(BaseModel):
    """
    Subscription model for tracking user subscriptions.
    
    This model handles:
    - Subscription tier management
    - Stripe integration
    - Trial periods
    - Subscription status
    
    Relationships:
    - Many-to-one with User
    
    Attributes:
        user_id (UUID): ID of the subscribed user
        tier (SubscriptionTier): Subscription tier level
        stripe_subscription_id (str): Stripe subscription identifier
        stripe_customer_id (str): Stripe customer identifier
        status (str): Current subscription status
        current_period_start (datetime): Start of current billing period
        current_period_end (datetime): End of current billing period
        cancel_at_period_end (bool): Whether to cancel at period end
        canceled_at (datetime): When subscription was canceled
        trial_start (datetime): Start of trial period
        trial_end (datetime): End of trial period
    """
    __tablename__ = "subscriptions"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    tier = Column(SQLEnum(SubscriptionTier), nullable=False)
    stripe_subscription_id = Column(String(255), unique=True)
    stripe_customer_id = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False)
    current_period_start = Column(DateTime(timezone=True))
    current_period_end = Column(DateTime(timezone=True))
    cancel_at_period_end = Column(Boolean, default=False, nullable=False)
    canceled_at = Column(DateTime(timezone=True))
    trial_start = Column(DateTime(timezone=True))
    trial_end = Column(DateTime(timezone=True))

    # Relationships
    user = relationship(
        "User",
        back_populates="subscriptions",
        lazy="select"
    )

    @validates('status')
    def validate_status(self, key: str, status: str) -> str:
        """
        Validate subscription status.
        
        Args:
            key (str): Field name
            status (str): Status to validate
            
        Returns:
            str: Validated status
            
        Raises:
            ValidationError: If status is invalid
        """
        valid_statuses = {
            'active',
            'past_due',
            'canceled',
            'incomplete',
            'incomplete_expired',
            'trialing',
            'unpaid'
        }
        
        if status not in valid_statuses:
            raise ValidationError(f"Invalid subscription status: {status}")
        
        return status

    @validates('stripe_subscription_id', 'stripe_customer_id')
    def validate_stripe_id(self, key: str, value: Optional[str]) -> Optional[str]:
        """
        Validate Stripe identifier format.
        
        Args:
            key (str): Field name
            value (Optional[str]): Stripe ID to validate
            
        Returns:
            Optional[str]: Validated Stripe ID
            
        Raises:
            ValidationError: If ID format is invalid
        """
        if not value:
            if key == 'stripe_customer_id':
                raise ValidationError("Stripe customer ID is required")
            return value

        if len(value) > 255:
            raise ValidationError(f"{key} is too long")

        prefix_map = {
            'stripe_subscription_id': 'sub_',
            'stripe_customer_id': 'cus_'
        }
        expected_prefix = prefix_map.get(key)
        
        if expected_prefix and not value.startswith(expected_prefix):
            raise ValidationError(f"Invalid {key} format")

        return value

    @validates('current_period_start', 'current_period_end', 'trial_start', 'trial_end')
    def validate_dates(self, key: str, value: Optional[datetime]) -> Optional[datetime]:
        """
        Validate subscription dates.
        
        Args:
            key (str): Field name
            value (Optional[datetime]): Date to validate
            
        Returns:
            Optional[datetime]: Validated date
            
        Raises:
            ValidationError: If date is invalid
        """
        if not value:
            return value

        now = datetime.utcnow()
        
        if key in ['current_period_start', 'trial_start'] and value > now:
            raise ValidationError(f"{key} cannot be in the future")
            
        if key == 'current_period_end':
            if self.current_period_start and value <= self.current_period_start:
                raise ValidationError("Period end must be after period start")
                
        if key == 'trial_end':
            if self.trial_start and value <= self.trial_start:
                raise ValidationError("Trial end must be after trial start")

        return value

    def validate(self) -> None:
        """
        Validate all fields in the model.
        
        Raises:
            ValidationError: If any validation fails
        """
        super().validate()
        self.validate_status('status', self.status)
        self.validate_stripe_id('stripe_customer_id', self.stripe_customer_id)
        if self.stripe_subscription_id:
            self.validate_stripe_id('stripe_subscription_id', self.stripe_subscription_id)
        
        # Validate dates if set
        if self.current_period_start:
            self.validate_dates('current_period_start', self.current_period_start)
        if self.current_period_end:
            self.validate_dates('current_period_end', self.current_period_end)
        if self.trial_start:
            self.validate_dates('trial_start', self.trial_start)
        if self.trial_end:
            self.validate_dates('trial_end', self.trial_end) 