"""User service module."""
from typing import Optional, List, Dict, Any, Union
from uuid import UUID
from datetime import datetime, timedelta
import logging
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from jose import jwt
from fastapi import Depends, HTTPException, status

from app.core.config import settings, Settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    create_email_verification_token,
    verify_email_verification_token_and_get_email
)
from app.core.exceptions import (
    AuthenticationException,
    ValidationException,
    NotFoundException,
    EmailError,
    ValidationError,
    ServiceError
)
from app.schemas.user import (
    UserCreate,
    UserUpdate,
    User,
    UserFilter,
    UserInDB
)
from app.schemas.token import Token
from app.core.password import get_password_hash, verify_password
from app.models.user import User as DBUser
from app.models.subscription import Subscription as DBSubscription
from app.services.base_service import BaseService

# Setup logger
logger = logging.getLogger(__name__)

class UserService(BaseService[DBUser, UserCreate, UserUpdate]):
    """User service for managing users, now inheriting from BaseService."""
    
    def __init__(self, db: Union[AsyncSession, Session], app_settings: Settings):
        super().__init__(db=db, model=DBUser, settings=app_settings)

    async def get_by_email_async(self, email: str) -> Optional[DBUser]:
        """Get user by email asynchronously."""
        try:
            stmt = select(self.model).filter(self.model.email == email.lower())
            result = await self.db.execute(stmt)
            return result.scalars().first()
        except Exception as e:
            logger.error(f"Error fetching user by email {email}: {e}", exc_info=True)
            raise ServiceError(f"Failed to get user by email: {str(e)}")

    async def create_user_async(self, user_in: UserCreate, is_superuser: bool = False) -> DBUser:
        """Create a new user asynchronously, handling password hashing."""
        hashed_password = get_password_hash(user_in.password)
        user_data_dict = user_in.model_dump(exclude_unset=True)
        user_data_dict["hashed_password"] = hashed_password
        user_data_dict["password"] = None
        user_data_dict["is_superuser"] = is_superuser
        
        db_user = await super().create_async(obj_in=user_data_dict)
        return db_user

    async def update_user_async(self, user_id: UUID, user_in: UserUpdate) -> Optional[DBUser]:
        """Update an existing user asynchronously."""
        db_obj = await super().get_async(id=user_id)
        if not db_obj:
                return None
            
        update_data = user_in.model_dump(exclude_unset=True)
        if "password" in update_data and update_data["password"]:
            hashed_password = get_password_hash(update_data["password"])
            update_data["hashed_password"] = hashed_password
            del update_data["password"]
        else:
            update_data.pop("password", None)
            update_data.pop("hashed_password", None)

        return await super().update_async(db_obj=db_obj, obj_in=update_data)

    async def update_user_subscription_async(self, 
                                      user_id: UUID,
                                      tier: str, 
                                      start_date: Optional[datetime] = None, 
                                      end_date: Optional[datetime] = None,
                                      is_active: bool = True,
                                      provider: str = "internal",
                                      provider_subscription_id: Optional[str] = None) -> DBUser:
        """Update a user's subscription asynchronously with specific parameters."""
        user = await super().get_async(id=user_id)
        if not user:
            raise NotFoundException(f"User with ID {user_id} not found")
        
        user.subscription_tier = tier
        user.subscription_is_active = is_active
        self.db.add(user)

        await self.db.commit()
        await self.db.refresh(user)
        logger.info(f"Subscription updated for user {user_id} to tier {tier}")
        return user

def get_user_service(
) -> UserService:
    """
    Get user service instance for synchronous operations.
    
    Args:
        db: SQLAlchemy database session
        app_settings: Application settings
        
    Returns:
        User service instance
    """
    from app.core.deps import get_db, get_settings
    from fastapi import Depends
    
    # Re-declare with Depends pointing to the now-imported functions
    actual_db: Session = Depends(get_db)
    actual_app_settings: Settings = Depends(get_settings)
    
    return UserService(db=actual_db, app_settings=actual_app_settings)

async def get_async_user_service(
) -> UserService:
    """
    Get user service instance for asynchronous operations.
    
    Args:
        db: SQLAlchemy asynchronous database session
        app_settings: Application settings
        
    Returns:
        User service instance
    """
    from app.core.deps import get_async_db, get_settings
    from fastapi import Depends

    # Re-declare with Depends pointing to the now-imported functions
    actual_db: AsyncSession = Depends(get_async_db)
    actual_app_settings: Settings = Depends(get_settings)

    return UserService(db=actual_db, app_settings=actual_app_settings)