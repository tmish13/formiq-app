"""User repository for database operations."""
from typing import List, Optional, Union
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from fastapi import Depends

from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.repositories.base_repository import BaseRepository
from app.core.database import get_db
from app.core.deps import get_async_db

class UserRepository(BaseRepository[User]):
    """Repository for user database operations."""
    
    def __init__(self, db: Union[Session, AsyncSession]):
        """Initialize repository with database session."""
        super().__init__(User, db)
    
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
        return self.db.query(User).filter(User.email == email).first()
    
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
        
        filters = {"email": email}
        result = await self.get_multi_async(skip=0, limit=1, **filters)
        return result[0] if result else None
            
    def get_by_id(self, user_id: str) -> Optional[User]:
        """
        Get user by ID synchronously.
        
        Args:
            user_id: User ID
            
        Returns:
            Optional[User]: User if found, None otherwise
        """
        return self.get(user_id)
    
    async def get_by_id_async(self, user_id: str) -> Optional[User]:
        """
        Get user by ID asynchronously.
        
        Args:
            user_id: User ID
            
        Returns:
            Optional[User]: User if found, None otherwise
        """
        return await self.get_async(user_id)
    
    def create_user(self, user_data: UserCreate) -> User:
        """
        Create a new user synchronously.
        
        Args:
            user_data: User data
            
        Returns:
            User: Created user
        """
        # Convert Pydantic model to dict
        user_dict = user_data.dict(exclude_unset=True)
        
        # Extract values that need special handling
        password = user_dict.pop("password", None)  # Password should be already hashed
        is_superuser = user_dict.pop("is_superuser", False)  # Extract is_superuser flag
        
        # Prepare user object data
        obj_in = {
            "email": user_data.email,
            "username": user_data.username or user_data.email.split('@')[0],
            "full_name": user_data.full_name,
            "hashed_password": password,  # Note: Should be hashed in the service layer
            "is_superuser": is_superuser  # Set superuser status
        }
        
        return self.create(obj_in=obj_in)
    
    async def create_user_async(self, user_data: UserCreate) -> User:
        """
        Create a new user asynchronously.
        
        Args:
            user_data: User data
            
        Returns:
            User: Created user
        """
        # Convert Pydantic model to dict
        user_dict = user_data.dict(exclude_unset=True)
        
        # Extract values that need special handling
        password = user_dict.pop("password", None)  # Password should be already hashed
        is_superuser = user_dict.pop("is_superuser", False)  # Extract is_superuser flag
        
        # Prepare user object data
        obj_in = {
            "email": user_data.email,
            "username": user_data.username or user_data.email.split('@')[0],
            "full_name": user_data.full_name,
            "hashed_password": password,  # Note: Should be hashed in the service layer
            "is_superuser": is_superuser  # Set superuser status
        }
        
        return await self.create_async(obj_in=obj_in)
    
    def update_user(self, user_id: str, user_data: UserUpdate) -> Optional[User]:
        """
        Update a user synchronously.
        
        Args:
            user_id: User ID
            user_data: User data to update
            
        Returns:
            Optional[User]: Updated user if found, None otherwise
        """
        db_obj = self.get(user_id)
        if not db_obj:
            return None
        
        obj_in = user_data.dict(exclude_unset=True)
        return self.update(db_obj=db_obj, obj_in=obj_in)
    
    async def update_user_async(self, user_id: str, user_data: UserUpdate) -> Optional[User]:
        """
        Update a user asynchronously.
        
        Args:
            user_id: User ID
            user_data: User data to update
            
        Returns:
            Optional[User]: Updated user if found, None otherwise
        """
        db_obj = await self.get_async(user_id)
        if not db_obj:
            return None
        
        obj_in = user_data.dict(exclude_unset=True)
        return await self.update_async(db_obj=db_obj, obj_in=obj_in)
    
    def get_all(self) -> List[User]:
        """
        Get all users synchronously.
        
        Returns:
            List[User]: List of all users
        """
        return self.get_multi(skip=0, limit=1000)
    
    async def get_all_async(self) -> List[User]:
        """
        Get all users asynchronously.
        
        Returns:
            List[User]: List of all users
        """
        return await self.get_multi_async(skip=0, limit=1000)
    
    def delete_user(self, user_id: str) -> bool:
        """
        Delete a user synchronously.
        
        Args:
            user_id: User ID
            
        Returns:
            bool: True if deleted, False otherwise
        """
        try:
            self.delete(id=user_id)
            return True
        except Exception:
            return False
    
    async def delete_user_async(self, user_id: str) -> bool:
        """
        Delete a user asynchronously.
        
        Args:
            user_id: User ID
            
        Returns:
            bool: True if deleted, False otherwise
        """
        try:
            await self.delete_async(id=user_id)
            return True
        except Exception:
            return False

def get_user_repository(db: Session = Depends(get_db)) -> UserRepository:
    """
    Get user repository instance for synchronous operations.
    
    Args:
        db: Database session
        
    Returns:
        User repository instance
    """
    return UserRepository(db=db)

def get_async_user_repository(db: AsyncSession = Depends(get_async_db)) -> UserRepository:
    """
    Get user repository instance for asynchronous operations.
    
    Args:
        db: Async database session
        
    Returns:
        User repository instance
    """
    return UserRepository(db=db) 