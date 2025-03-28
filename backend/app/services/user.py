from typing import Optional
from sqlalchemy.orm import Session
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.core.utils.email import generate_verification_token, send_verification_email, send_password_reset_email
from app.core.logging import get_logger

logger = get_logger(__name__)

class UserService:
    """Service for user operations."""
    
    def __init__(self):
        self.repository = UserRepository()

    def create_user(self, db: Session, *, user_data: dict) -> User:
        """Create a new user."""
        user = self.repository.create(db, obj_in=user_data)
        
        # Generate verification token and send email
        token = generate_verification_token()
        user.verification_token = token
        db.commit()
        
        if not send_verification_email(user.email, token):
            logger.error(f"Failed to send verification email to {user.email}")
        
        return user

    def verify_email(self, db: Session, *, token: str) -> Optional[User]:
        """Verify user email with token."""
        user = self.repository.get_by_verification_token(db, token=token)
        if not user:
            return None
        
        user.is_verified = True
        user.verification_token = None
        db.commit()
        return user

    def initiate_password_reset(self, db: Session, *, email: str) -> bool:
        """Initiate password reset process."""
        user = self.repository.get_by_email(db, email=email)
        if not user:
            return False
        
        token = generate_verification_token()
        user.reset_password_token = token
        db.commit()
        
        return send_password_reset_email(email, token)

    def reset_password(self, db: Session, *, token: str, new_password: str) -> Optional[User]:
        """Reset user password with token."""
        user = self.repository.get_by_reset_token(db, token=token)
        if not user:
            return None
        
        user.update_password(new_password)
        user.reset_password_token = None
        db.commit()
        return user

    def update_user(self, db: Session, *, user: User, user_data: dict) -> User:
        """Update user information."""
        if "password" in user_data:
            user.update_password(user_data.pop("password"))
        
        return self.repository.update(db, db_obj=user, obj_in=user_data)

    def get_user_by_email(self, db: Session, *, email: str) -> Optional[User]:
        """Get user by email."""
        return self.repository.get_by_email(db, email=email)

    def get_user_by_stripe_customer(self, db: Session, *, customer_id: str) -> Optional[User]:
        """Get user by Stripe customer ID."""
        return self.repository.get_by_stripe_customer(db, customer_id=customer_id)

    def get_user_by_stripe_subscription(self, db: Session, *, subscription_id: str) -> Optional[User]:
        """Get user by Stripe subscription ID."""
        return self.repository.get_by_stripe_subscription(db, subscription_id=subscription_id) 