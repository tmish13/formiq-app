from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.form_check import FormCheck
from app.repositories.form_check_repository import FormCheckRepository
from app.core.logging import get_logger

logger = get_logger(__name__)

class FormCheckService:
    """Service for form check operations."""
    
    def __init__(self):
        self.repository = FormCheckRepository()

    def create_form_check(self, db: Session, *, form_check_data: dict) -> FormCheck:
        """Create a new form check."""
        return self.repository.create(db, obj_in=form_check_data)

    def get_user_form_checks(
        self, 
        db: Session, 
        *, 
        user_id: int, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[FormCheck]:
        """Get form checks for a specific user."""
        return self.repository.get_by_user(
            db, 
            user_id=user_id, 
            skip=skip, 
            limit=limit
        )

    def get_exercise_form_checks(
        self, 
        db: Session, 
        *, 
        user_id: int, 
        exercise_type: str
    ) -> List[FormCheck]:
        """Get form checks for a specific exercise type."""
        return self.repository.get_by_exercise_type(
            db, 
            user_id=user_id, 
            exercise_type=exercise_type
        )

    def get_latest_form_checks(
        self, 
        db: Session, 
        *, 
        user_id: int, 
        limit: int = 10
    ) -> List[FormCheck]:
        """Get latest form checks for a user."""
        return self.repository.get_latest_by_user(
            db, 
            user_id=user_id, 
            limit=limit
        )

    def update_form_check(
        self, 
        db: Session, 
        *, 
        form_check: FormCheck, 
        form_check_data: dict
    ) -> FormCheck:
        """Update form check information."""
        return self.repository.update(
            db, 
            db_obj=form_check, 
            obj_in=form_check_data
        )

    def delete_form_check(self, db: Session, *, form_check: FormCheck) -> FormCheck:
        """Delete a form check."""
        return self.repository.remove(db, id=form_check.id) 