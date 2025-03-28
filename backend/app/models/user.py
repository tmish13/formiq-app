from sqlalchemy import Column, String, Boolean, Enum, DateTime, Integer
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin
from .enums import SubscriptionTier
from app.core.security import get_password_hash, verify_password

class User(Base, TimestampMixin):
    """User model for authentication and user management."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    first_name = Column(String)
    last_name = Column(String)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False)
    verification_token = Column(String, nullable=True)
    reset_password_token = Column(String, unique=True)
    stripe_customer_id = Column(String, nullable=True)
    stripe_subscription_id = Column(String, nullable=True)
    subscription_tier = Column(Enum(SubscriptionTier), default=SubscriptionTier.FREE, nullable=False)
    subscription_start_date = Column(DateTime)
    subscription_end_date = Column(DateTime, nullable=True)
    is_email_verified = Column(Boolean, default=False, nullable=False)
    last_login = Column(DateTime, nullable=True)
    failed_login_attempts = Column(Integer, default=0, nullable=False)

    # Relationships
    form_checks = relationship("FormCheck", back_populates="user", cascade="all, delete-orphan")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.email}>"

    def __init__(self, **kwargs):
        if "password" in kwargs:
            kwargs["hashed_password"] = get_password_hash(kwargs.pop("password"))
        super().__init__(**kwargs)

    def verify_password(self, password: str) -> bool:
        """Verify user password."""
        return verify_password(password, self.hashed_password)

    def update_password(self, password: str) -> None:
        """Update user password."""
        self.hashed_password = get_password_hash(password) 