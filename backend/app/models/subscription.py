from datetime import datetime
from enum import Enum
from typing import Optional
from sqlalchemy import Column, String, DateTime, Enum as SQLEnum, Integer, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, validates
from app.models.base import BaseModel, SQLiteUUID
from app.core.exceptions import ValidationError
from app.models.enums import SubscriptionTier

class Subscription(BaseModel):
    """
    Subscription model for tracking user subscriptions.
    
    This model handles:
    - Subscription details
    - Payment information
    - Subscription history
    
    Relationships:
    - Many-to-one with User
    
    Attributes:
        user_id (UUID): ID of the user this subscription belongs to
        tier (SubscriptionTier): Subscription tier level
        start_date (datetime): When subscription started
        end_date (datetime): When subscription ends/ended
        stripe_subscription_id (str): Stripe subscription identifier
        stripe_customer_id (str): Stripe customer identifier
        status (str): Current status of subscription
        cancel_at_period_end (bool): Whether subscription will cancel at period end
    """
    __tablename__ = "subscriptions"

    id = Column(SQLiteUUID(), primary_key=True, index=True)
    user_id = Column(SQLiteUUID(), ForeignKey("users.id"), nullable=False)
    tier = Column(SQLEnum(SubscriptionTier), nullable=False)
    start_date = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    end_date = Column(DateTime(timezone=True), nullable=True)
    stripe_subscription_id = Column(String(255), unique=True, nullable=True)
    stripe_customer_id = Column(String(255), nullable=True)
    status = Column(String(50), nullable=False, default="active")
    cancel_at_period_end = Column(String(50), nullable=False, default=False)

    # Relationships
    user = relationship("User", back_populates="subscriptions")

    def __repr__(self) -> str:
        """String representation of the subscription."""
        return f"<Subscription {self.id} - {self.tier} - {self.status}>"

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

    @validates('start_date', 'end_date')
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
        
        if key == 'start_date' and value > now:
            raise ValidationError(f"{key} cannot be in the future")
            
        if key == 'end_date':
            if self.start_date and value <= self.start_date:
                raise ValidationError("End date must be after start date")

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
        if self.start_date:
            self.validate_dates('start_date', self.start_date)
        if self.end_date:
            self.validate_dates('end_date', self.end_date) 