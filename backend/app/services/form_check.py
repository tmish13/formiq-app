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
from app.services.storage import StorageService
from app.core.config import settings

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
    
    def __init__(self, db: Session, storage_service: Optional[StorageService] = None):
        """Initialize form check service with database session and storage service."""
        self.db = db
        self.ai_service = AIService()
        self.storage_service = storage_service or StorageService()

    def create_form_check(self, user: User, video_url: str, exercise_type: ExerciseType) -> FormCheck:
        """Create a new form check entry."""
        try:
            form_check = FormCheck(
                user_id=user.id,
                video_url=video_url,
                exercise_type=exercise_type,
                status="pending",
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            self.db.add(form_check)
            self.db.commit()
            self.db.refresh(form_check)
            logger.info(f"Created form check {form_check.id} for user {user.id}")
            return form_check
        except Exception as e:
            logger.error(f"Failed to create form check: {str(e)}")
            self.db.rollback()
            raise FormCheckError(f"Failed to create form check: {str(e)}")

    async def analyze_form(self, form_check_id: int) -> Dict[str, Any]:
        """Analyze exercise form using AI service."""
        try:
            form_check = self.get_form_check(form_check_id)
            
            # Download video from storage
            video_data = await self.storage_service.download_file(form_check.video_url)
            
            # Get analysis from AI service
            analysis_results = await self.ai_service.analyze_form(
                video_data,
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
            # Delete video from storage
            self.storage_service.delete_file(form_check.video_url)
            # Delete from database
            self.db.delete(form_check)
            self.db.commit()
            logger.info(f"Deleted form check {form_check_id}")
        except Exception as e:
            logger.error(f"Failed to delete form check: {str(e)}")
            self.db.rollback()
            raise FormCheckError(f"Failed to delete form check: {str(e)}")

    def get_exercise_history(self, user_id: int, exercise_type: ExerciseType) -> List[Dict[str, Any]]:
        """Get exercise history for a user."""
        form_checks = self.db.query(FormCheck).filter(
            FormCheck.user_id == user_id,
            FormCheck.exercise_type == exercise_type,
            FormCheck.status == "completed"
        ).order_by(FormCheck.created_at.desc()).all()
        
        return [
            {
                "id": fc.id,
                "score": fc.score,
                "feedback": fc.feedback,
                "created_at": fc.created_at,
                "video_url": fc.video_url
            }
            for fc in form_checks
        ]

    def validate_video_format(self, video_url: str) -> bool:
        """Validate video format and size."""
        try:
            # Check file size
            file_size = self.storage_service.get_file_size(video_url)
            if file_size > settings.MAX_CONTENT_LENGTH:
                raise ValidationError(f"Video size exceeds maximum limit of {settings.MAX_CONTENT_LENGTH} bytes")
            
            # Check file type
            content_type = self.storage_service.get_file_metadata(video_url).get("content_type")
            if content_type not in settings.ALLOWED_VIDEO_TYPES:
                raise ValidationError(f"Invalid video format. Allowed formats: {settings.ALLOWED_VIDEO_TYPES}")
            
            return True
        except Exception as e:
            logger.error(f"Video validation failed: {str(e)}")
            raise FormCheckError(f"Video validation failed: {str(e)}")

    async def process_form_check_async(self, form_check_id: int) -> None:
        """Process form check asynchronously."""
        try:
            form_check = self.get_form_check(form_check_id)
            form_check.status = "processing"
            self.db.commit()
            
            # Analyze form
            await self.analyze_form(form_check_id)
            
            logger.info(f"Successfully processed form check {form_check_id}")
        except Exception as e:
            logger.error(f"Failed to process form check {form_check_id}: {str(e)}")
            if "form_check" in locals():
                form_check.status = "failed"
                form_check.error_message = str(e)
                self.db.commit()
            raise FormCheckError(f"Failed to process form check: {str(e)}")

    def get_form_check_statistics(self, user_id: int) -> Dict[str, Any]:
        """Get form check statistics for a user."""
        form_checks = self.get_user_form_checks(user_id)
        
        total_checks = len(form_checks)
        completed_checks = len([fc for fc in form_checks if fc.status == "completed"])
        failed_checks = len([fc for fc in form_checks if fc.status == "failed"])
        
        # Calculate average score
        completed_scores = [fc.score for fc in form_checks if fc.status == "completed" and fc.score is not None]
        avg_score = sum(completed_scores) / len(completed_scores) if completed_scores else 0
        
        return {
            "total_checks": total_checks,
            "completed_checks": completed_checks,
            "failed_checks": failed_checks,
            "average_score": avg_score,
            "completion_rate": (completed_checks / total_checks * 100) if total_checks > 0 else 0
        } 