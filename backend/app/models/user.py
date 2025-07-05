"""User model module for managing user data and relationships."""
from typing import Optional, List, Dict, Any
from sqlalchemy import Column, Integer, String, Boolean, Enum, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, validates
from datetime import datetime
import enum
import re
from app.models.base import BaseModel
from app.models.enums import SubscriptionTier
from app.models.user_session import UserSession
from app.core.password import get_password_hash, verify_password
from app.core.exceptions import ValidationError
from app.core.validators import validate_password as validate_password_strength
import uuid
from uuid import uuid4

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
    - One-to-many with Workout
    - One-to-many with Video
    
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
        is_verified (bool): Whether the user is verified
        is_superuser (bool): Whether the user is a superuser
        verified_at (datetime): When the user was verified
        created_at (datetime): When the user account was created
        updated_at (datetime): When the user account was last updated
        last_login (datetime): When the user last logged in
        failed_login_attempts (int): Number of failed login attempts
        locked_until (datetime): When the user account will be unlocked
    """
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    is_active = Column(Boolean, default=True)
    
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
    is_verified = Column(Boolean, default=False, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    verified_at = Column(DateTime)
    
    # Onboarding fields
    has_completed_onboarding = Column(Boolean, default=False, nullable=False)
    onboarding_completed_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime)
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime)

    # Relationships
    form_checks = relationship("FormCheck", back_populates="user")
    subscriptions = relationship(
        "Subscription",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="select"
    )
    workouts = relationship(
        "Workout",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="select"
    )
    workout_plans = relationship(
        "WorkoutPlan",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="select"
    )
    settings = relationship("UserSettings", back_populates="user", uselist=False)
    sessions = relationship(UserSession, back_populates="user", cascade="all, delete-orphan")
    videos = relationship("Video", back_populates="user", cascade="all, delete-orphan")
    exercise_progress = relationship("ExerciseProgress", back_populates="user", cascade="all, delete-orphan", lazy="select")

    def __init__(self, **kwargs):
        """Initialize a new User instance.
        
        Args:
            **kwargs: Keyword arguments for user attributes
        """
        # Handle password hashing if provided
        if "password" in kwargs:
            kwargs["hashed_password"] = get_password_hash(kwargs.pop("password"))

        # Validate email and username before initialization
        if "email" in kwargs:
            kwargs["email"] = self._validate_email(kwargs["email"])
        if "username" in kwargs:
            kwargs["username"] = self._validate_username(kwargs["username"])

        # Initialize SQLAlchemy model
        super().__init__(**kwargs)

    def _validate_email(self, email: str) -> str:
        """
        Validate email format.
        
        Args:
            email: Email to validate
            
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

    def _validate_username(self, username: str) -> str:
        """
        Validate username format.
        
        Args:
            username: Username to validate
            
        Returns:
            str: Validated username
            
        Raises:
            ValidationError: If username is invalid
        """
        if not username:
            raise ValidationError("Username cannot be empty")
            
        if len(username) < 3:
            raise ValidationError("Username must be at least 3 characters long")
            
        if len(username) > 30:
            raise ValidationError("Username cannot exceed 30 characters")
            
        # Only allow alphanumeric characters, underscores, and hyphens
        if not re.match(r'^[a-zA-Z0-9_-]+$', username):
            raise ValidationError(
                "Username can only contain letters, numbers, underscores, and hyphens"
            )
            
        return username.lower()

    @validates('email')
    def validate_email(self, key: str, value: str) -> str:
        """SQLAlchemy validator for email field."""
        return self._validate_email(value)

    @validates('username')
    def validate_username(self, key: str, value: str) -> str:
        """SQLAlchemy validator for username field."""
        return self._validate_username(value)

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
        
        try:
            # Use the common password validator
            validate_password_strength(password)
            
            # Hash and store the password
            self.hashed_password = get_password_hash(password)
        except Exception as e:
            # Convert any exceptions to ValidationError
            raise ValidationError(str(e))

    def validate(self) -> None:
        """
        Validate all fields in the model.
        
        Raises:
            ValidationError: If any validation fails
        """
        super().validate()
        self.validate_email('email', self.email)
        self.validate_username('username', self.username)

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