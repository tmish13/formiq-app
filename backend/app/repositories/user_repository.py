"""User repository for database operations."""
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete
from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate

class UserRepository:
    """Repository for user database operations."""
    
    def __init__(self, db: Session):
        """Initialize repository with database session."""
        self.db = db
        self._is_async = isinstance(db, AsyncSession)
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        if self._is_async:
            # Use SQLAlchemy 2.0 style for async
            result = await self.db.execute(
                select(User).where(User.email == email)
            )
            return result.scalars().first()
        else:
            # Legacy style for sync
            return self.db.query(User).filter(User.email == email).first()
            
    async def get_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        if self._is_async:
            result = await self.db.execute(
                select(User).where(User.id == user_id)
            )
            return result.scalars().first()
        else:
            return self.db.query(User).filter(User.id == user_id).first()
    
    async def create(self, user_data: UserCreate) -> User:
        """Create a new user."""
        user = User(
            email=user_data.email,
            username=user_data.username or user_data.email.split('@')[0],
            full_name=user_data.full_name,
            hashed_password=user_data.password  # Note: Should be hashed in a real app
        )
        
        self.db.add(user)
        
        if self._is_async:
            await self.db.commit()
            await self.db.refresh(user)
        else:
            self.db.commit()
            self.db.refresh(user)
            
        return user
    
    async def update(self, user_id: str, user_data: UserUpdate) -> Optional[User]:
        """Update a user."""
        # Get user first
        if self._is_async:
            result = await self.db.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalars().first()
        else:
            user = self.db.query(User).filter(User.id == user_id).first()
        
        if not user:
            return None
        
        # Update user attributes
        for key, value in user_data.dict(exclude_unset=True).items():
            setattr(user, key, value)
        
        # Commit changes
        if self._is_async:
            await self.db.commit()
            await self.db.refresh(user)
        else:
            self.db.commit()
            self.db.refresh(user)
            
        return user
    
    async def get_all(self) -> List[User]:
        """Get all users."""
        if self._is_async:
            result = await self.db.execute(select(User))
            return result.scalars().all()
        else:
            return self.db.query(User).all()
    
    async def delete(self, user_id: str) -> bool:
        """Delete a user."""
        if self._is_async:
            result = await self.db.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalars().first()
        else:
            user = self.db.query(User).filter(User.id == user_id).first()
            
        if not user:
            return False
        
        self.db.delete(user)
        
        if self._is_async:
            await self.db.commit()
        else:
            self.db.commit()
            
        return True 