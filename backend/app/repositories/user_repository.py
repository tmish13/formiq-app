"""User repository module."""
from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """User repository."""

    def __init__(self, db: Session):
        """Initialize repository."""
        super().__init__(db, User)

    def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        return self.db.query(User).filter(User.email == email).first()

    def get_multi(
        self, *, skip: int = 0, limit: int = 100
    ) -> List[User]:
        """Get multiple users."""
        return self.db.query(User).offset(skip).limit(limit).all()

    def create(self, *, obj_in: dict) -> User:
        """Create user."""
        db_obj = User(**obj_in)
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def update(self, *, db_obj: User, obj_in: dict) -> User:
        """Update user."""
        for field, value in obj_in.items():
            setattr(db_obj, field, value)
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def delete(self, *, id: UUID) -> Optional[User]:
        """Delete user."""
        obj = self.db.query(User).get(id)
        if obj:
            self.db.delete(obj)
            self.db.commit()
        return obj 