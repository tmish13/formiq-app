"""Service for analyzing exercise form."""
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum
from sqlalchemy.orm import Session
from app.models.form_check import FormCheck
from app.models.user import User
from app.core.exceptions import ValidationError
from app.core.logging import get_logger
from app.services.ai import AIService

logger = get_logger(__name__)

class FormCheckError(Exception):
    """Custom exception for form check service errors."""
    pass

class ExerciseType(str, Enum):
    """Supported exercise types for form checking."""
    SQUAT = "squat"
    DEADLIFT = "deadlift"
    BENCH_PRESS = "bench_press"

class FormCheckService:
    """Service for analyzing exercise form."""
    
    def __init__(self, db: Session):
        """Initialize form check service with database session."""
        self.db = db
        self.ai_service = AIService()

    def create_form_check(self, user_id: int, video_url: str, exercise_type: ExerciseType) -> FormCheck:
        """Create a new form check entry."""
        try:
            form_check = FormCheck(
                user_id=user_id,
                video_url=video_url,
                exercise_type=exercise_type,
                status="pending",
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            self.db.add(form_check)
            self.db.commit()
            self.db.refresh(form_check)
            logger.info(f"Created form check {form_check.id} for user {user_id}")
            return form_check
        except Exception as e:
            logger.error(f"Failed to create form check: {str(e)}")
            self.db.rollback()
            raise FormCheckError(f"Failed to create form check: {str(e)}")

    async def analyze_form(self, form_check_id: int) -> Dict[str, Any]:
        """Analyze exercise form using AI service."""
        try:
            form_check = self.db.query(FormCheck).filter(FormCheck.id == form_check_id).first()
            if not form_check:
                raise FormCheckError(f"Form check {form_check_id} not found")

            # Get analysis from AI service
            analysis_results = await self.ai_service.analyze_form(
                form_check.video_url,
                form_check.exercise_type
            )

            # Update form check with results
            form_check.status = "completed"
            form_check.score = analysis_results["score"]
            form_check.feedback = analysis_results["feedback"]
            form_check.keypoints = analysis_results["keypoints"]
            form_check.suggestions = analysis_results["suggestions"]
            form_check.updated_at = datetime.now()

            self.db.commit()
            self.db.refresh(form_check)
            logger.info(f"Completed form analysis for form check {form_check_id}")
            return analysis_results
        except Exception as e:
            logger.error(f"Failed to analyze form: {str(e)}")
            if "form_check" in locals():
                form_check.status = "failed"
                form_check.updated_at = datetime.now()
                self.db.commit()
            raise FormCheckError(f"Failed to analyze form: {str(e)}")

    def get_form_check(self, form_check_id: int) -> FormCheck:
        """Get form check by ID."""
        form_check = self.db.query(FormCheck).filter(FormCheck.id == form_check_id).first()
        if not form_check:
            raise FormCheckError(f"Form check {form_check_id} not found")
        return form_check

    def get_user_form_checks(self, user_id: int) -> List[FormCheck]:
        """Get all form checks for a user."""
        return self.db.query(FormCheck).filter(FormCheck.user_id == user_id).all()

    def delete_form_check(self, form_check_id: int) -> None:
        """Delete a form check entry."""
        try:
            form_check = self.get_form_check(form_check_id)
            self.db.delete(form_check)
            self.db.commit()
            logger.info(f"Deleted form check {form_check_id}")
        except Exception as e:
            logger.error(f"Failed to delete form check: {str(e)}")
            self.db.rollback()
            raise FormCheckError(f"Failed to delete form check: {str(e)}")

    def get_exercise_history(self, user_id: int, exercise_type: ExerciseType) -> List[Dict[str, Any]]:
        """Get exercise form history for a user."""
        form_checks = self.db.query(FormCheck).filter(
            FormCheck.user_id == user_id,
            FormCheck.exercise_type == exercise_type,
            FormCheck.status == "completed"
        ).order_by(FormCheck.created_at.desc()).all()

        return [{
            "id": fc.id,
            "date": fc.created_at,
            "score": fc.score,
            "feedback": fc.feedback,
            "suggestions": fc.suggestions
        } for fc in form_checks] 