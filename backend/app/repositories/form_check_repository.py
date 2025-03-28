from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.form_check import FormCheck
from app.repositories.base import BaseRepository

class FormCheckRepository(BaseRepository[FormCheck]):
    """Repository for form check operations."""
    
    def __init__(self):
        super().__init__(FormCheck)

    def get_by_user(
        self, db: Session, *, user_id: int, skip: int = 0, limit: int = 100
    ) -> List[FormCheck]:
        """Get form checks for a specific user."""
        return (
            db.query(FormCheck)
            .filter(FormCheck.user_id == user_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_exercise_type(
        self, db: Session, *, user_id: int, exercise_type: str
    ) -> List[FormCheck]:
        """Get form checks for a specific exercise type."""
        return (
            db.query(FormCheck)
            .filter(
                FormCheck.user_id == user_id,
                FormCheck.exercise_type == exercise_type
            )
            .all()
        )

    def get_latest_by_user(
        self, db: Session, *, user_id: int, limit: int = 5
    ) -> List[FormCheck]:
        """Get latest form checks for a user."""
        return (
            db.query(FormCheck)
            .filter(FormCheck.user_id == user_id)
            .order_by(FormCheck.created_at.desc())
            .limit(limit)
            .all()
        ) 