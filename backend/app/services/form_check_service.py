"""Form check service module."""
from typing import Optional, List
from sqlalchemy.orm import Session

from app.models.form_check import FormCheck
from app.repositories.form_check_repository import FormCheckRepository
from app.schemas.form_check import FormCheckCreate, FormCheckUpdate


class FormCheckService:
    """Form check service class."""

    def __init__(self, db: Session):
        """Initialize form check service.

        Args:
            db: Database session
        """
        self.repository = FormCheckRepository(db)

    def get_by_id(self, form_check_id: int) -> Optional[FormCheck]:
        """Get form check by id.

        Args:
            form_check_id: Form check id

        Returns:
            Form check if found, None otherwise
        """
        return self.repository.get_by_id(form_check_id)

    def get_all(self) -> List[FormCheck]:
        """Get all form checks.

        Returns:
            List of form checks
        """
        return self.repository.get_all()

    def get_by_user_id(self, user_id: int) -> List[FormCheck]:
        """Get form checks by user id.

        Args:
            user_id: User id

        Returns:
            List of form checks
        """
        return self.repository.get_by_user_id(user_id)

    def get_by_exercise_id(self, exercise_id: int) -> List[FormCheck]:
        """Get form checks by exercise id.

        Args:
            exercise_id: Exercise id

        Returns:
            List of form checks
        """
        return self.repository.get_by_exercise_id(exercise_id)

    def create(self, form_check_in: FormCheckCreate) -> FormCheck:
        """Create new form check.

        Args:
            form_check_in: Form check create schema

        Returns:
            Created form check
        """
        form_check = FormCheck(
            video_url=form_check_in.video_url,
            exercise_id=form_check_in.exercise_id,
            user_id=form_check_in.user_id,
            feedback=form_check_in.feedback,
            score=form_check_in.score,
            keypoints=form_check_in.keypoints,
            status=form_check_in.status,
        )
        return self.repository.create(form_check)

    def update(self, form_check: FormCheck, form_check_in: FormCheckUpdate) -> FormCheck:
        """Update form check.

        Args:
            form_check: Form check to update
            form_check_in: Form check update schema

        Returns:
            Updated form check
        """
        update_data = form_check_in.dict(exclude_unset=True)
        return self.repository.update(form_check, update_data)

    def delete(self, form_check: FormCheck) -> FormCheck:
        """Delete form check.

        Args:
            form_check: Form check to delete

        Returns:
            Deleted form check
        """
        return self.repository.delete(form_check)