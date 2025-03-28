from typing import Optional
from sqlalchemy.orm import Session
from app.models.user import User
from app.repositories.base import BaseRepository

class UserRepository(BaseRepository[User]):
    """Repository for user operations."""
    
    def __init__(self):
        super().__init__(User)

    def get_by_email(self, db: Session, *, email: str) -> Optional[User]:
        """Get user by email."""
        return db.query(User).filter(User.email == email).first()

    def get_by_verification_token(self, db: Session, *, token: str) -> Optional[User]:
        """Get user by verification token."""
        return db.query(User).filter(User.verification_token == token).first()

    def get_by_reset_token(self, db: Session, *, token: str) -> Optional[User]:
        """Get user by password reset token."""
        return db.query(User).filter(User.reset_password_token == token).first()

    def get_by_stripe_customer(self, db: Session, *, customer_id: str) -> Optional[User]:
        """Get user by Stripe customer ID."""
        return db.query(User).filter(User.stripe_customer_id == customer_id).first()

    def get_by_stripe_subscription(self, db: Session, *, subscription_id: str) -> Optional[User]:
        """Get user by Stripe subscription ID."""
        return db.query(User).filter(User.stripe_subscription_id == subscription_id).first() 