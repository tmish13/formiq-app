"""Form check repository module."""
from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session

from app.models.form_check import FormCheck
from app.repositories.base import BaseRepository


class FormCheckRepository(BaseRepository[FormCheck]):
    """Form check repository."""

    def __init__(self, db: Session):
        """Initialize repository."""
        super().__init__(db, FormCheck)

    def get_by_user(self, user_id: UUID) -> List[FormCheck]:
        """Get form checks by user."""
        return self.db.query(FormCheck).filter(FormCheck.user_id == user_id).all()

    def get_by_exercise(self, exercise_id: UUID) -> List[FormCheck]:
        """Get form checks by exercise."""
        return self.db.query(FormCheck).filter(FormCheck.exercise_id == exercise_id).all()

    def get_multi(
        self, *, skip: int = 0, limit: int = 100
    ) -> List[FormCheck]:
        """Get multiple form checks."""
        return self.db.query(FormCheck).offset(skip).limit(limit).all()

    def create(self, *, obj_in: dict) -> FormCheck:
        """Create form check."""
        db_obj = FormCheck(**obj_in)
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def update(self, *, db_obj: FormCheck, obj_in: dict) -> FormCheck:
        """Update form check."""
        for field, value in obj_in.items():
            setattr(db_obj, field, value)
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def delete(self, *, id: UUID) -> Optional[FormCheck]:
        """Delete form check."""
        obj = self.db.query(FormCheck).get(id)
        if obj:
            self.db.delete(obj)
            self.db.commit()
        return obj 