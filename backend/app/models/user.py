"""User model module for managing user data and relationships."""
from typing import Optional, List, Dict, Any
from sqlalchemy import Column, Integer, String, Boolean, Enum, DateTime, ForeignKey
from sqlalchemy.orm import relationship, validates
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import enum
import re
from app.models.base import BaseModel
from app.models.enums import SubscriptionTier
from app.core.security import get_password_hash, verify_password
from app.core.exceptions import ValidationError

class User(BaseModel):
    """
    User model for storing user account information.
    
    This model handles:
    - User authentication
    - Profile information
    - Subscription status
    - Email verification
    - Password management
    
    Relationships:
    - One-to-many with FormCheck
    - One-to-many with Subscription
    
    Attributes:
        email (str): User's email address (unique)
        username (str): User's username (unique)
        hashed_password (str): Securely hashed password
        is_active (bool): Whether the account is active
        subscription_tier (SubscriptionTier): Current subscription level
        subscription_end_date (datetime): When current subscription expires
        stripe_customer_id (str): Stripe customer identifier
        stripe_subscription_id (str): Stripe subscription identifier
        is_email_verified (bool): Whether email is verified
        verification_token (str): Token for email verification
    """
    __tablename__ = "users"

    # Profile fields
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Subscription fields
    subscription_tier = Column(
        Enum(SubscriptionTier),
        default=SubscriptionTier.FREE,
        nullable=False
    )
    subscription_end_date = Column(DateTime(timezone=True), nullable=True)
    stripe_customer_id = Column(String(255), unique=True, nullable=True)
    stripe_subscription_id = Column(String(255), unique=True, nullable=True)
    
    # Verification fields
    is_email_verified = Column(Boolean, default=False, nullable=False)
    verification_token = Column(String(255), nullable=True)

    # Relationships
    form_checks = relationship(
        "FormCheck",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="select"
    )
    subscriptions = relationship(
        "Subscription",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="select"
    )

    @validates('email')
    def validate_email(self, key: str, email: str) -> str:
        """
        Validate email format.
        
        Args:
            key (str): Field name
            email (str): Email to validate
            
        Returns:
            str: Validated email
            
        Raises:
            ValidationError: If email format is invalid
        """
        if not email:
            raise ValidationError("Email is required")
        
        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        if not email_pattern.match(email):
            raise ValidationError("Invalid email format")
        
        return email.lower()

    @validates('username')
    def validate_username(self, key: str, username: str) -> str:
        """
        Validate username format.
        
        Args:
            key (str): Field name
            username (str): Username to validate
            
        Returns:
            str: Validated username
            
        Raises:
            ValidationError: If username format is invalid
        """
        if not username:
            raise ValidationError("Username is required")
        
        if not 3 <= len(username) <= 50:
            raise ValidationError("Username must be between 3 and 50 characters")
        
        username_pattern = re.compile(r'^[a-zA-Z0-9_-]+$')
        if not username_pattern.match(username):
            raise ValidationError("Username can only contain letters, numbers, underscores, and hyphens")
        
        return username.lower()

    def verify_password(self, password: str) -> bool:
        """
        Verify if provided password matches stored hash.
        
        Args:
            password (str): Password to verify
            
        Returns:
            bool: True if password matches, False otherwise
        """
        return verify_password(password, self.hashed_password)

    def update_password(self, password: str) -> None:
        """
        Update user's password with new hash.
        
        Args:
            password (str): New password to set
            
        Raises:
            ValidationError: If password format is invalid
        """
        if not password:
            raise ValidationError("Password is required")
        
        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters")
        
        if not any(c.isupper() for c in password):
            raise ValidationError("Password must contain at least one uppercase letter")
        
        if not any(c.islower() for c in password):
            raise ValidationError("Password must contain at least one lowercase letter")
        
        if not any(c.isdigit() for c in password):
            raise ValidationError("Password must contain at least one number")
        
        self.hashed_password = get_password_hash(password)

    def validate(self) -> None:
        """
        Validate all fields in the model.
        
        Raises:
            ValidationError: If any validation fails
        """
        super().validate()
        self.validate_email(None, self.email)
        self.validate_username(None, self.username)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'User':
        """
        Create user instance from dictionary with password hashing.
        
        Args:
            data (Dict[str, Any]): Dictionary containing user data
            
        Returns:
            User: New user instance
            
        Raises:
            ValidationError: If data validation fails
        """
        if "password" in data:
            data["hashed_password"] = get_password_hash(data.pop("password"))
        return super().from_dict(data)

    def __repr__(self) -> str:
        return f"<User {self.id} - {self.email}>"

    def __init__(self, **kwargs):
        if "password" in kwargs:
            kwargs["hashed_password"] = get_password_hash(kwargs.pop("password"))
        super().__init__(**kwargs) 