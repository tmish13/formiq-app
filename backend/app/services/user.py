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
        self._is_async = False

    def set_async_mode(self, is_async: bool = True) -> None:
        """Set the service to operate in async or sync mode."""
        self._is_async = is_async
        
    def is_async(self) -> bool:
        """Return whether the service is operating in async mode."""
        return self._is_async

    def create_user(self, 
                   email: str, 
                   username: str, 
                   password: str, 
                   subscription_tier: str = "FREE") -> User:
        """
        Create a new user.
        
        Args:
            email: User's email address
            username: User's username
            password: User's password (plain text)
            subscription_tier: Subscription tier (default: FREE)
            
        Returns:
            User: Created user object
            
        Raises:
            ValidationError: If validation fails
        """
        # Check if session is asynchronous
        if self._is_async:
            raise ValueError("Use create_user_async for async sessions")
            
        try:
            # Check if user already exists
            existing_user = self.db.query(User).filter(
                User.email == email
            ).first()
            if existing_user:
                raise ValidationError("User with this email already exists")

            # Create new user
            user = User(
                email=email,
                username=username,
                hashed_password=get_password_hash(password),
                is_active=True,
                is_superuser=False,
                subscription_tier=subscription_tier,
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

    async def create_user_async(self, 
                              email: str, 
                              username: str, 
                              password: str, 
                              subscription_tier: str = "FREE") -> User:
        """
        Create a new user asynchronously.
        
        Args:
            email: User's email address
            username: User's username
            password: User's password (plain text)
            subscription_tier: Subscription tier (default: FREE)
            
        Returns:
            User: Created user object
            
        Raises:
            ValidationError: If validation fails
        """
        # Check if session is synchronous
        if not self._is_async:
            raise ValueError("Use create_user for sync sessions")
            
        try:
            # Check if user already exists
            stmt = User.__table__.select().where(User.email == email)
            result = await self.db.execute(stmt)
            existing_user = result.scalar_one_or_none()
            
            if existing_user:
                raise ValidationError("User with this email already exists")

            # Create new user
            user = User(
                email=email,
                username=username,
                hashed_password=get_password_hash(password),
                is_active=True,
                is_superuser=False,
                subscription_tier=subscription_tier,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            self.db.add(user)
            await self.db.commit()
            await self.db.refresh(user)
            logger.info(f"Created user {user.id}")
            return user
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Failed to create user: {str(e)}")
            await self.db.rollback()
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

    def update_subscription(self, 
                            user_id: int, 
                            tier: str,
                            start_date: datetime = None,
                            end_date: datetime = None,
                            status: str = "active",
                            stripe_subscription_id: str = None,
                            stripe_customer_id: str = None) -> User:
        """
        Update user subscription.
        
        Args:
            user_id: User ID
            tier: Subscription tier
            start_date: Start date of subscription
            end_date: End date of subscription
            status: Subscription status
            stripe_subscription_id: Stripe subscription ID
            stripe_customer_id: Stripe customer ID
            
        Returns:
            User: Updated user object
            
        Raises:
            NotFoundError: If user not found
            ValidationError: If validation fails
        """
        try:
            user = self.get_user_by_id(user_id)
            
            # Default dates if not provided
            if start_date is None:
                start_date = datetime.now()
            if end_date is None:
                end_date = start_date + timedelta(days=30)  # Default to 30 days
            
            # Validate dates
            if end_date <= start_date:
                raise ValidationError("End date must be after start date")
            
            # Update subscription tier
            user.subscription_tier = tier
            user.updated_at = datetime.now()
            
            # Create subscription record
            subscription = Subscription(
                user_id=user_id,
                tier=tier,
                start_date=start_date,
                end_date=end_date,
                status=status,
                stripe_subscription_id=stripe_subscription_id,
                stripe_customer_id=stripe_customer_id,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            self.db.add(subscription)
            
            # Commit changes
            self.db.commit()
            
            # Refresh the user to get the updated data
            self.db.refresh(user)
            logger.info(f"Updated subscription for user {user_id}")
            return user
        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to update subscription: {str(e)}")
            self.db.rollback()
            raise ValidationError(f"Failed to update subscription: {str(e)}")

    async def update_subscription_async(self, 
                                 user_id: int, 
                                 tier: str,
                                 start_date: datetime = None,
                                 end_date: datetime = None,
                                 status: str = "active",
                                 stripe_subscription_id: str = None,
                                 stripe_customer_id: str = None) -> User:
        """
        Update user subscription asynchronously.
        
        Args:
            user_id: User ID
            tier: Subscription tier
            start_date: Start date of subscription
            end_date: End date of subscription
            status: Subscription status
            stripe_subscription_id: Stripe subscription ID
            stripe_customer_id: Stripe customer ID
            
        Returns:
            User: Updated user object
            
        Raises:
            NotFoundError: If user not found
            ValidationError: If validation fails
        """
        try:
            # Get user
            user = await self.repository.get_by_id_async(user_id)
            if not user:
                raise NotFoundError(f"User {user_id} not found")
            
            # Default dates if not provided
            if start_date is None:
                start_date = datetime.now()
            if end_date is None:
                end_date = start_date + timedelta(days=30)  # Default to 30 days
            
            # Validate dates
            if end_date <= start_date:
                raise ValidationError("End date must be after start date")
            
            # Update subscription tier
            user.subscription_tier = tier
            user.updated_at = datetime.now()
            
            # Create subscription record
            subscription = Subscription(
                user_id=user_id,
                tier=tier,
                start_date=start_date,
                end_date=end_date,
                status=status,
                stripe_subscription_id=stripe_subscription_id,
                stripe_customer_id=stripe_customer_id,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            self.db.add(subscription)
            await self.db.commit()
            await self.db.refresh(user)
            logger.info(f"Updated subscription for user {user_id}")
            return user
        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to update subscription: {str(e)}")
            await self.db.rollback()
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