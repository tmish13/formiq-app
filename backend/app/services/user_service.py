"""User service module."""
from typing import Optional, List, Dict, Any, Union
from uuid import UUID
from datetime import datetime, timedelta
import logging
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt
from fastapi import Depends, HTTPException, status

from app.core.config import settings
from app.core.token import (
    create_access_token,
    create_refresh_token,
    create_email_verification_token,
    verify_email_token
)
from app.core.exceptions import (
    AuthenticationException,
    ValidationException,
    NotFoundException,
    EmailError,
    ValidationError
)
from app.repositories.user_repository import UserRepository, get_user_repository, get_async_user_repository
from app.schemas.user import (
    UserCreate,
    UserUpdate,
    User,
    UserFilter,
    UserInDB
)
from app.schemas.token import Token
from app.services.email_service import EmailService
from app.core.database import get_db
from app.core.deps import get_async_db
from app.core.password import get_password_hash, verify_password
from app.models.user import User as DBUser
from app.models.subscription import Subscription as DBSubscription

# Setup logger
logger = logging.getLogger(__name__)

class UserService:
    """User service."""
    
    def __init__(self, repository: UserRepository):
        """Initialize service with repository."""
        self.repository = repository
        self._is_async = isinstance(repository.db, AsyncSession)

    def get_by_id(self, user_id: str) -> Optional[User]:
        """
        Get user by ID synchronously.
        
        Args:
            user_id: User ID
            
        Returns:
            Optional[User]: User if found, None otherwise
            
        Raises:
            NotFoundException: If user not found
        """
        if self._is_async:
            raise ValueError("Use get_by_id_async for async sessions")
            
        user = self.repository.get_by_id(user_id)
        if not user:
            raise NotFoundException("User not found")
        return User.from_orm(user)
        
    async def get_by_id_async(self, user_id: str) -> Optional[User]:
        """
        Get user by ID asynchronously.
        
        Args:
            user_id: User ID
            
        Returns:
            Optional[User]: User if found, None otherwise
            
        Raises:
            NotFoundException: If user not found
        """
        if not self._is_async:
            raise ValueError("Use get_by_id for sync sessions")
            
        user = await self.repository.get_by_id_async(user_id)
        if not user:
            raise NotFoundException("User not found")
        return User.from_orm(user)

    def get_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email synchronously.
        
        Args:
            email: User email
            
        Returns:
            Optional[User]: User if found, None otherwise
        """
        if self._is_async:
            raise ValueError("Use get_by_email_async for async sessions")
            
        user = self.repository.get_by_email(email)
        if user:
            return User.from_orm(user)
        return None

    async def get_by_email_async(self, email: str) -> Optional[User]:
        """
        Get user by email asynchronously.
        
        Args:
            email: User email
            
        Returns:
            Optional[User]: User if found, None otherwise
        """
        if not self._is_async:
            raise ValueError("Use get_by_email for sync sessions")
            
        user = await self.repository.get_by_email_async(email)
        if user:
            return User.from_orm(user)
        return None

    def get_all(self) -> List[User]:
        """
        Get all users synchronously.
        
        Returns:
            List[User]: List of all users
        """
        if self._is_async:
            raise ValueError("Use get_all_async for async sessions")
            
        users = self.repository.get_all()
        return [User.from_orm(user) for user in users]

    async def get_all_async(self) -> List[User]:
        """
        Get all users asynchronously.
        
        Returns:
            List[User]: List of all users
        """
        if not self._is_async:
            raise ValueError("Use get_all for sync sessions")
            
        users = await self.repository.get_all_async()
        return [User.from_orm(user) for user in users]

    def get_multi(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[UserFilter] = None
    ) -> List[User]:
        """
        Get multiple users synchronously.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            filters: Filter criteria
            
        Returns:
            List[User]: List of found users
        """
        if self._is_async:
            raise ValueError("Use get_multi_async for async sessions")
            
        filter_params = {}
        if filters:
            filter_dict = filters.dict(exclude_unset=True)
            filter_params.update(filter_dict)
            
        users = self.repository.get_multi(skip=skip, limit=limit, **filter_params)
        return [User.from_orm(user) for user in users]

    async def get_multi_async(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[UserFilter] = None
    ) -> List[User]:
        """
        Get multiple users asynchronously.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            filters: Filter criteria
            
        Returns:
            List[User]: List of found users
        """
        if not self._is_async:
            raise ValueError("Use get_multi for sync sessions")
            
        filter_params = {}
        if filters:
            filter_dict = filters.dict(exclude_unset=True)
            filter_params.update(filter_dict)
            
        users = await self.repository.get_multi_async(skip=skip, limit=limit, **filter_params)
        return [User.from_orm(user) for user in users]

    def create(self, user_data: UserCreate, is_superuser: bool = False) -> User:
        """
        Create a new user synchronously.
        
        Args:
            user_data: User create schema
            is_superuser: Whether the user should be a superuser (default: False)
            
        Returns:
            Created user
        """
        if self._is_async:
            raise ValueError("Use create_async for async sessions")
            
        # Hash the password
        hashed_password = get_password_hash(user_data.password)
        
        # Create a modified user object with hashed password
        user_data_dict = user_data.dict()
        user_data_dict["password"] = hashed_password
        user_data_dict["is_superuser"] = is_superuser
        
        # Create new user with modified data
        user = self.repository.create_user(UserCreate(**user_data_dict))
        return User.from_orm(user)

    def create_user(self, email: str, username: str, password: str, subscription_tier: str = "FREE") -> User:
        """
        Create a new user synchronously with individual parameters.
        
        Args:
            email: User email address
            username: User username
            password: User password (plain text)
            subscription_tier: Subscription tier (default: FREE)
            
        Returns:
            Created user
        """
        if self._is_async:
            raise ValueError("Use create_user_async for async sessions")
            
        # Convert individual parameters to UserCreate model
        user_data = UserCreate(
            email=email,
            username=username,
            password=password
        )
        
        # Add additional fields not in UserCreate
        user_dict = user_data.dict()
        user_dict["is_superuser"] = False
        user_dict["subscription_tier"] = subscription_tier
        
        # Create user using repository
        user = self.repository.create_user(user_dict)
        return User.from_orm(user)

    async def create_async(self, user_data: UserCreate, is_superuser: bool = False) -> User:
        """
        Create a new user asynchronously.
        
        Args:
            user_data: User create schema
            is_superuser: Whether the user should be a superuser (default: False)
            
        Returns:
            Created user
        """
        if not self._is_async:
            raise ValueError("Use create for sync sessions")
            
        # Hash the password
        hashed_password = get_password_hash(user_data.password)
        
        # Create a modified user object with hashed password
        user_data_dict = user_data.dict()
        user_data_dict["password"] = hashed_password
        user_data_dict["is_superuser"] = is_superuser
        
        # Create new user with modified data
        user = await self.repository.create_user_async(UserCreate(**user_data_dict))
        return User.from_orm(user)

    async def create_user_async(self, email: str, username: str, password: str, subscription_tier: str = "FREE") -> User:
        """
        Create a new user asynchronously with individual parameters.
        
        Args:
            email: User email address
            username: User username
            password: User password (plain text)
            subscription_tier: Subscription tier (default: FREE)
            
        Returns:
            Created user
        """
        if not self._is_async:
            raise ValueError("Use create_user for sync sessions")
            
        # Convert individual parameters to UserCreate model
        user_data = UserCreate(
            email=email,
            username=username,
            password=password
        )
        
        # Add additional fields not in UserCreate
        user_dict = user_data.dict()
        user_dict["is_superuser"] = False
        user_dict["subscription_tier"] = subscription_tier
        
        # Create user using repository
        user = await self.repository.create_user_async(user_dict)
        return User.from_orm(user)

    def update(self, user_id: str, user_data: Dict[str, Any]) -> Optional[User]:
        """
        Update a user synchronously.
        
        Args:
            user_id: User ID
            user_data: User data to update
            
        Returns:
            Optional[User]: Updated user
        """
        if self._is_async:
            raise ValueError("Use update_async for async sessions")
            
        # Handle password hashing if password is provided
        if "password" in user_data:
            user_data["password"] = get_password_hash(user_data["password"])
            
        # Update user with processed data
        update_data = UserUpdate(**user_data)
        user = self.repository.update_user(user_id, update_data)
        if user:
            return User.from_orm(user)
        return None

    async def update_async(self, user_id: str, user_data: Dict[str, Any]) -> Optional[User]:
        """
        Update a user asynchronously.
        
        Args:
            user_id: User ID
            user_data: User data to update
            
        Returns:
            Optional[User]: Updated user
        """
        if not self._is_async:
            raise ValueError("Use update for sync sessions")
            
        # Handle password hashing if password is provided
        if "password" in user_data:
            user_data["password"] = get_password_hash(user_data["password"])
            
        # Update user with processed data
        update_data = UserUpdate(**user_data)
        user = await self.repository.update_user_async(user_id, update_data)
        if user:
            return User.from_orm(user)
        return None

    def delete(self, user_id: str) -> bool:
        """
        Delete a user synchronously.
        
        Args:
            user_id: User ID
            
        Returns:
            bool: True if deleted, False otherwise
        """
        if self._is_async:
            raise ValueError("Use delete_async for async sessions")
            
        return self.repository.delete_user(user_id)

    async def delete_async(self, user_id: str) -> bool:
        """
        Delete a user asynchronously.
        
        Args:
            user_id: User ID
            
        Returns:
            bool: True if deleted, False otherwise
        """
        if not self._is_async:
            raise ValueError("Use delete for sync sessions")
            
        return await self.repository.delete_user_async(user_id)

    async def authenticate(
        self,
        email: str,
        password: str,
        device_info: Optional[Dict[str, Any]] = None
    ) -> Optional[User]:
        """
        Authenticate a user.
        
        Args:
            email: User's email
            password: User's password
            device_info: Optional device information for session tracking
            
        Returns:
            Optional[User]: Authenticated user or None
            
        Raises:
            AuthenticationException: If authentication fails
        """
        try:
            # Get user by email
            if self._is_async:
                user = await self.get_by_email_async(email)
            else:
                user = self.get_by_email(email)
                
            if not user:
                # Use constant time comparison to prevent timing attacks
                verify_password("dummy", "dummy")
                return None
            
            # Check if account is locked
            if user.locked_until and user.locked_until > datetime.utcnow():
                raise AuthenticationException(
                    "Account is locked. Try again later.",
                    retry_after=int((user.locked_until - datetime.utcnow()).total_seconds())
                )
            
            # Verify password
            if not verify_password(password, user.hashed_password):
                # Increment failed attempts
                failed_attempts = user.failed_login_attempts + 1
                lock_data = {}
                
                # Lock account after 5 failed attempts
                if failed_attempts >= 5:
                    lock_duration = timedelta(minutes=15)  # 15 minutes lockout
                    lock_data["locked_until"] = datetime.utcnow() + lock_duration
                
                # Update user
                if self._is_async:
                    await self.update_async(
                        user.id,
                        {
                            "failed_login_attempts": failed_attempts,
                            **lock_data
                        }
                    )
                else:
                    self.update(
                        user.id,
                        {
                            "failed_login_attempts": failed_attempts,
                            **lock_data
                        }
                    )
                
                return None
            
            # Authentication successful - update user
            update_data = {
                "last_login": datetime.utcnow(),
                "failed_login_attempts": 0,
                "locked_until": None
            }
            
            if self._is_async:
                await self.update_async(user.id, update_data)
            else:
                self.update(user.id, update_data)
            
            return user
            
        except Exception as e:
            logger.error(f"Authentication failed: {str(e)}")
            raise AuthenticationException("Authentication failed")

    def is_active(self, user: User) -> bool:
        """
        Check if user is active.
        
        Args:
            user: User to check
            
        Returns:
            True if user is active, False otherwise
        """
        return user.is_active

    def create_access_token(self, *, user_id: UUID, expires_delta: Optional[timedelta] = None) -> Token:
        """
        Create access token for user.
        
        Args:
            user_id: User ID
            expires_delta: Token expiration time
            
        Returns:
            Token: Access and refresh tokens
        """
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode = {"exp": expire, "sub": str(user_id)}
        access_token = create_access_token(data=to_encode)
        refresh_token = create_refresh_token(data=to_encode)
        
        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer"
        )

    def refresh_token(self, *, refresh_token: str) -> Token:
        """
        Refresh access token using refresh token.
        
        Args:
            refresh_token: Refresh token
            
        Returns:
            Token: New access and refresh tokens
            
        Raises:
            AuthenticationException: If token is invalid
        """
        try:
            payload = jwt.decode(
                refresh_token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM]
            )
            user_id = UUID(payload["sub"])
            return self.create_access_token(user_id=user_id)
        except (jwt.JWTError, ValueError):
            raise AuthenticationException("Invalid refresh token")

    async def send_verification_email(self, user: User) -> None:
        """
        Send email verification link to user.
        
        Args:
            user: User to send verification email to
            
        Raises:
            EmailError: If email sending fails
        """
        # Generate verification token
        token = create_email_verification_token(user.email)
        
        # Create verification URL
        verify_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"
        
        # Send email
        try:
            email_service = EmailService()
            await email_service.send_email(
                to_email=user.email,
                subject="Verify your FormIQ account",
                body=f"""
                <html>
                    <body>
                        <h2>Welcome to FormIQ!</h2>
                        <p>Please verify your email by clicking the link below:</p>
                        <p><a href="{verify_url}">Verify Email</a></p>
                        <p>If you didn't create this account, you can safely ignore this email.</p>
                        <p>Thank you,<br>The FormIQ Team</p>
                    </body>
                </html>
                """
            )
        except Exception as e:
            logger.error(f"Failed to send verification email: {str(e)}")
            raise EmailError("Failed to send verification email")

    async def verify_email(self, token: str) -> None:
        """
        Verify a user's email address using a verification token.
        
        Args:
            token: Email verification token
            
        Raises:
            ValidationException: If the token is invalid or expired, or if the user is not found
        """
        try:
            # Verify token and get email
            email = verify_email_token(token)
            
            # Get user by email
            if self._is_async:
                user = await self.get_by_email_async(email)
            else:
                user = self.get_by_email(email)
                
            if not user:
                raise ValidationException("User not found")
            
            # Update user's email verification status
            update_data = {"is_email_verified": True}
            
            if self._is_async:
                await self.update_async(user.id, update_data)
            else:
                self.update(user.id, update_data)
                
        except Exception as e:
            logger.error(f"Email verification failed: {str(e)}")
            raise ValidationException("Invalid or expired verification token")
            
    def update_subscription(self, 
                           user_id: int, 
                           tier: str, 
                           start_date: datetime = None, 
                           end_date: datetime = None,
                           is_active: bool = True,
                           provider: str = "internal",
                           provider_subscription_id: str = None) -> User:
        """
        Update a user's subscription with specific parameters.
        
        Args:
            user_id: ID of the user to update
            tier: Subscription tier level
            start_date: When the subscription starts
            end_date: When the subscription ends
            is_active: Whether the subscription is active
            provider: The subscription provider (e.g., "stripe", "internal")
            provider_subscription_id: ID from the provider's system
            
        Returns:
            Updated user
        """
        if self._is_async:
            raise ValueError("Use update_subscription_async for async sessions")
            
        try:
            # Create a transaction
            with self.repository.db.begin():
                # Get the user by ID
                user = self.repository.get_by_id(user_id)
                if not user:
                    raise ValueError(f"User with ID {user_id} not found")
                    
                # Update the user's subscription tier
                user.subscription_tier = tier
                
                # Create a new subscription record
                subscription = DBSubscription(
                    user_id=user_id,
                    tier=tier,
                    start_date=start_date or datetime.now(),
                    end_date=end_date,
                    is_active=is_active,
                    provider=provider,
                    provider_subscription_id=provider_subscription_id
                )
                self.repository.db.add(subscription)
                
                # Refresh the user
                self.repository.db.refresh(user)
                
                return User.from_orm(user)
        except Exception as e:
            # Transaction will be rolled back automatically
            raise ValueError(f"Failed to update subscription: {str(e)}")
            
    async def update_subscription_async(self, 
                                      user_id: int, 
                                      tier: str, 
                                      start_date: datetime = None, 
                                      end_date: datetime = None,
                                      is_active: bool = True,
                                      provider: str = "internal",
                                      provider_subscription_id: str = None) -> User:
        """
        Update a user's subscription asynchronously with specific parameters.
        
        Args:
            user_id: ID of the user to update
            tier: Subscription tier level
            start_date: When the subscription starts
            end_date: When the subscription ends
            is_active: Whether the subscription is active
            provider: The subscription provider (e.g., "stripe", "internal")
            provider_subscription_id: ID from the provider's system
            
        Returns:
            Updated user
        """
        if not self._is_async:
            raise ValueError("Use update_subscription for sync sessions")
            
        try:
            async with self.repository.db.begin():
                # Get the user by ID
                user = await self.repository.get_by_id_async(user_id)
                if not user:
                    raise ValueError(f"User with ID {user_id} not found")
                    
                # Update the user's subscription tier
                user.subscription_tier = tier
                
                # Create a new subscription record
                subscription = DBSubscription(
                    user_id=user_id,
                    tier=tier,
                    start_date=start_date or datetime.now(),
                    end_date=end_date,
                    is_active=is_active,
                    provider=provider,
                    provider_subscription_id=provider_subscription_id
                )
                self.repository.db.add(subscription)
                
                # Refresh the user
                await self.repository.db.refresh(user)
                
                return User.from_orm(user)
        except Exception as e:
            # Transaction will be rolled back automatically
            raise ValueError(f"Failed to update subscription: {str(e)}")


def get_user_service(
    repository: UserRepository = Depends(get_user_repository),
) -> UserService:
    """
    Get user service instance for synchronous operations.
    
    Args:
        repository: User repository
        
    Returns:
        User service instance
    """
    return UserService(repository=repository)

def get_async_user_service(
    repository: UserRepository = Depends(get_async_user_repository),
) -> UserService:
    """
    Get user service instance for asynchronous operations.
    
    Args:
        repository: User repository
        
    Returns:
        User service instance
    """
    return UserService(repository=repository)