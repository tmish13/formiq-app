"""Service for managing users and authentication."""
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.subscription import Subscription
from app.core.exceptions import NotFoundError, ValidationError, AuthenticationError
from app.core.security import get_password_hash, verify_password, create_access_token
from app.core.logging import get_logger
from app.core.database import get_db

logger = get_logger(__name__)

class UserService:
    """Service for managing users and authentication."""
    
    def __init__(self, db: Session):
        """Initialize user service with database session."""
        self.db = db

    def create_user(self, user_data: Dict[str, Any]) -> User:
        """Create a new user."""
        try:
            # Check if user already exists
            existing_user = self.db.query(User).filter(
                User.email == user_data["email"]
            ).first()
            if existing_user:
                raise ValidationError("User with this email already exists")

            # Create new user
            user = User(
                email=user_data["email"],
                username=user_data["username"],
                hashed_password=get_password_hash(user_data["password"]),
                is_active=True,
                is_superuser=False,
                subscription_tier="FREE",
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
            logger.info(f"Created user {user.id}")
            return user
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Failed to create user: {str(e)}")
            self.db.rollback()
            raise ValidationError(f"Failed to create user: {str(e)}")

    def authenticate_user(self, email: str, password: str) -> Dict[str, Any]:
        """Authenticate user and return access token."""
        try:
            user = self.db.query(User).filter(User.email == email).first()
            if not user:
                raise AuthenticationError("Invalid email or password")

            if not verify_password(password, user.hashed_password):
                raise AuthenticationError("Invalid email or password")

            if not user.is_active:
                raise AuthenticationError("User account is inactive")

            access_token = create_access_token(data={"sub": user.email})
            logger.info(f"User {user.id} authenticated successfully")
            return {
                "access_token": access_token,
                "token_type": "bearer",
                "user": user
            }
        except AuthenticationError:
            raise
        except Exception as e:
            logger.error(f"Authentication failed: {str(e)}")
            raise AuthenticationError("Authentication failed")

    def get_user_by_id(self, user_id: int) -> User:
        """Get user by ID."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise NotFoundError(f"User {user_id} not found")
        return user

    def get_user_by_email(self, email: str) -> User:
        """Get user by email."""
        user = self.db.query(User).filter(User.email == email).first()
        if not user:
            raise NotFoundError(f"User with email {email} not found")
        return user

    def update_user(self, user_id: int, update_data: Dict[str, Any]) -> User:
        """Update user information."""
        try:
            user = self.get_user_by_id(user_id)
            
            # Update fields
            for field, value in update_data.items():
                if field == "password":
                    user.hashed_password = get_password_hash(value)
                elif hasattr(user, field):
                    setattr(user, field, value)
            
            user.updated_at = datetime.now()
            self.db.commit()
            self.db.refresh(user)
            logger.info(f"Updated user {user_id}")
            return user
        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to update user: {str(e)}")
            self.db.rollback()
            raise ValidationError(f"Failed to update user: {str(e)}")

    def update_subscription(self, user_id: int, subscription_data: Dict[str, Any]) -> User:
        """Update user subscription."""
        try:
            user = self.get_user_by_id(user_id)
            
            # Update subscription
            user.subscription_tier = subscription_data["tier"]
            user.updated_at = datetime.now()
            
            # Create subscription record
            subscription = Subscription(
                user_id=user_id,
                tier=subscription_data["tier"],
                start_date=datetime.now(),
                end_date=datetime.now() + timedelta(days=subscription_data["duration_days"]),
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            self.db.add(subscription)
            
            self.db.commit()
            self.db.refresh(user)
            logger.info(f"Updated subscription for user {user_id}")
            return user
        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to update subscription: {str(e)}")
            self.db.rollback()
            raise ValidationError(f"Failed to update subscription: {str(e)}")

    def deactivate_user(self, user_id: int) -> User:
        """Deactivate a user account."""
        try:
            user = self.get_user_by_id(user_id)
            user.is_active = False
            user.updated_at = datetime.now()
            self.db.commit()
            self.db.refresh(user)
            logger.info(f"Deactivated user {user_id}")
            return user
        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to deactivate user: {str(e)}")
            self.db.rollback()
            raise ValidationError(f"Failed to deactivate user: {str(e)}") 