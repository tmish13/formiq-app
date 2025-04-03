"""Form check service module."""
from typing import Optional, List, Dict, Any
from uuid import UUID
import os
from fastapi import UploadFile
from sqlalchemy.orm import Session
from datetime import datetime
import uuid

from app.models.form_check import FormCheck, FeedbackItem
from app.models.enums import (
    FormCheckStatus,
    ExerciseType,
    FeedbackType,
    FeedbackSeverity
)
from app.repositories.form_check_repository import FormCheckRepository
from app.repositories.feedback_repository import FeedbackRepository
from app.core.storage import upload_video, delete_video
from app.core.validators import ValidationException
from app.schemas.form_check import (
    FormCheckCreate,
    FormCheckUpdate,
    FormCheckResponse,
    FeedbackItemCreate,
    FeedbackItemResponse
)
from app.services.storage import StorageService
from app.core.config import settings
from app.services.tasks import enqueue_form_check_analysis
from app.core.logging import logger


class FormCheckService:
    """Service class for form check operations."""

    def __init__(self, db: Session):
        """Initialize form check service.

        Args:
            db: Database session
        """
        self.db = db
        self.form_check_repository = FormCheckRepository(db)
        self.feedback_repository = FeedbackRepository(db)

    async def submit_form_check(
        self,
        user_id: UUID,
        video: UploadFile,
        exercise_type: ExerciseType,
        notes: Optional[str] = None
    ) -> FormCheckResponse:
        """Submit a new form check for analysis.

        Args:
            user_id: ID of the user submitting the form check
            video: Video file upload
            exercise_type: Type of exercise
            notes: Optional notes from the user

        Returns:
            Created form check data
        """
        # Upload video to storage
        video_url = await upload_video(video)
        
        # Create form check record
        form_check_data = {
            "video_url": video_url,
            "user_id": user_id,
            "exercise_type": exercise_type,
            "status": FormCheckStatus.PENDING,
            "notes": notes
        }
        
        # Create form check in database
        form_check = self.form_check_repository.create(form_check_data)
        
        # Queue form check for analysis (background task)
        # This would be implemented in a real application
        # self.queue_form_check_analysis(form_check.id)
        
        return form_check

    async def get_user_form_checks(
        self,
        user_id: UUID,
        status: Optional[FormCheckStatus] = None,
        exercise_type: Optional[ExerciseType] = None,
        page: int = 1,
        per_page: int = 10
    ) -> List[FormCheckResponse]:
        """Get form checks for a user with optional filtering.

        Args:
            user_id: ID of the user
            status: Optional filter by status
            exercise_type: Optional filter by exercise type
            page: Page number
            per_page: Items per page

        Returns:
            List of form checks
        """
        skip = (page - 1) * per_page
        limit = per_page
        
        # Apply filters
        filters = {"user_id": user_id}
        if status:
            filters["status"] = status
        if exercise_type:
            filters["exercise_type"] = exercise_type
            
        return self.form_check_repository.get_multi_filtered(
            filters=filters,
            skip=skip,
            limit=limit
        )

    async def get(self, id: UUID) -> FormCheckResponse:
        """Get a specific form check by ID.

        Args:
            id: Form check ID

        Returns:
            Form check data
            
        Raises:
            ValueError: If form check not found
        """
        form_check = self.form_check_repository.get(id=id)
        if not form_check:
            raise ValueError("Form check not found")
        return form_check

    async def get_feedback(self, feedback_id: int) -> FeedbackItemResponse:
        """Get a specific feedback item by ID.
        
        Args:
            feedback_id: ID of the feedback item
            
        Returns:
            Feedback item data
            
        Raises:
            ValueError: If feedback item not found
        """
        feedback_item = self.feedback_repository.get(id=feedback_id)
        if not feedback_item:
            raise ValueError("Feedback item not found")
        return feedback_item

    async def add_feedback(
        self,
        form_check_id: UUID,
        feedback_type: FeedbackType,
        severity: FeedbackSeverity,
        timestamp: float,
        description: str,
        suggestions: Optional[List[str]] = None,
        joint_angles: Optional[Dict[str, float]] = None,
        is_ai_generated: bool = False
    ) -> FeedbackItemResponse:
        """Add feedback to a form check.

        Args:
            form_check_id: ID of the form check
            feedback_type: Type of feedback
            severity: Severity level
            timestamp: Video timestamp in seconds
            description: Detailed feedback
            suggestions: Optional improvement suggestions
            joint_angles: Optional joint angle measurements
            is_ai_generated: Whether this feedback was generated by AI

        Returns:
            Created feedback item
            
        Raises:
            ValidationError: If validation fails
            ValueError: If form check not found
        """
        # Validate form check exists
        form_check = self.form_check_repository.get(id=form_check_id)
        if not form_check:
            raise ValueError("Form check not found")
        
        # Validate feedback data
        validate_feedback(
            feedback_type=feedback_type,
            severity=severity,
            timestamp=timestamp,
            description=description,
            suggestions=suggestions
        )
        
        # Create feedback item
        feedback_data = {
            "form_check_id": form_check_id,
            "type": feedback_type,
            "message": description,
            "timestamp": timestamp,
            "severity": severity,
            "suggestions": suggestions,
            "joint_angles": joint_angles,
            "is_ai_generated": is_ai_generated
        }
        
        feedback_item = self.feedback_repository.create(feedback_data)
        return feedback_item

    async def get_feedback_items(self, form_check_id: UUID) -> List[FeedbackItemResponse]:
        """Get all feedback items for a form check.

        Args:
            form_check_id: ID of the form check

        Returns:
            List of feedback items
            
        Raises:
            ValueError: If form check not found
        """
        # Validate form check exists
        form_check = self.form_check_repository.get(id=form_check_id)
        if not form_check:
            raise ValueError("Form check not found")
            
        return self.feedback_repository.get_by_form_check(form_check_id=form_check_id)

    async def update_feedback(
        self,
        feedback_id: int,
        update_data: Dict[str, Any]
    ) -> FeedbackItemResponse:
        """Update a feedback item.

        Args:
            feedback_id: ID of the feedback item
            update_data: Data to update

        Returns:
            Updated feedback item
            
        Raises:
            ValueError: If feedback item not found
        """
        # Get existing feedback item
        feedback_item = self.feedback_repository.get(id=feedback_id)
        if not feedback_item:
            raise ValueError("Feedback item not found")
            
        # Update feedback item
        updated_item = self.feedback_repository.update(
            db_obj=feedback_item,
            obj_in=update_data
        )
        return updated_item

    async def delete_feedback(self, feedback_id: int) -> None:
        """Delete a feedback item.

        Args:
            feedback_id: ID of the feedback item
            
        Raises:
            ValueError: If feedback item not found
        """
        # Get existing feedback item
        feedback_item = self.feedback_repository.get(id=feedback_id)
        if not feedback_item:
            raise ValueError("Feedback item not found")
            
        # Delete feedback item
        self.feedback_repository.delete(id=feedback_id)

    async def complete_analysis(
        self,
        form_check_id: UUID,
        summary: str,
        overall_score: float
    ) -> FormCheckResponse:
        """Complete form check analysis.

        Args:
            form_check_id: ID of the form check
            summary: Overall feedback summary
            overall_score: Score from 0-10

        Returns:
            Updated form check
            
        Raises:
            ValidationError: If validation fails
            ValueError: If form check not found
        """
        # Validate form check exists
        form_check = self.form_check_repository.get(id=form_check_id)
        if not form_check:
            raise ValueError("Form check not found")
        
        # Validate summary data
        validate_form_check_summary(summary=summary, overall_score=overall_score)
        
        # Update form check
        update_data = {
            "status": FormCheckStatus.COMPLETED,
            "overall_feedback": summary,
            "score": overall_score * 10  # Convert to 0-100 scale
        }
        
        updated_form_check = self.form_check_repository.update(
            db_obj=form_check,
            obj_in=update_data
        )
        return updated_form_check

    async def delete_form_check(self, form_check_id: UUID, user_id: UUID) -> None:
        """Delete a form check.

        Args:
            form_check_id: ID of the form check
            user_id: ID of the user
            
        Raises:
            ValueError: If form check not found or not owned by user
        """
        # Get form check
        form_check = self.form_check_repository.get(id=form_check_id)
        if not form_check:
            raise ValueError("Form check not found")
        
        # Verify ownership
        if form_check.user_id != user_id:
            raise ValueError("You do not have permission to delete this form check")
        
        # Delete video from storage
        if form_check.video_url:
            await delete_video(form_check.video_url)
            
        # Delete analysis video if exists
        if form_check.analysis_url:
            await delete_video(form_check.analysis_url)
        
        # Delete form check from database
        self.form_check_repository.delete(id=form_check_id)

    async def create_with_url(
        self,
        user_id: str,
        video_url: str,
        exercise_type: str,
        notes: Optional[str] = None
    ) -> FormCheck:
        """Create a form check with an already uploaded video URL."""
        try:
            # Get storage service to validate URL
            storage = StorageService()
            
            # Validate that the URL belongs to our S3 bucket
            try:
                file_info = await storage.get_file_info(video_url)
                logger.info(f"Valid video URL: {video_url}, size: {file_info.get('ContentLength', 0)}")
            except Exception as e:
                logger.error(f"Error validating video URL: {str(e)}")
                raise ValidationException(f"Invalid video URL: {str(e)}")
            
            # Generate a unique ID for the form check
            form_check_id = str(uuid.uuid4())
            
            # Create the form check model
            form_check = FormCheck(
                id=form_check_id,
                user_id=user_id,
                exercise_type=exercise_type,
                video_url=video_url,
                status=FormCheckStatus.pending,
                notes=notes,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            # Save to database
            self.db.add(form_check)
            await self.db.commit()
            await self.db.refresh(form_check)
            logger.info(f"Created form check with URL: {form_check_id}")
            
            # Start async analysis if enabled
            if settings.AUTO_ANALYZE_FORM_CHECKS:
                # Import here to avoid circular imports
                await enqueue_form_check_analysis(form_check_id)
                
                # Update status to analyzing
                form_check.status = FormCheckStatus.analyzing
                await self.db.commit()
                logger.info(f"Queued form check for analysis: {form_check_id}")
            
            return form_check
        except ValidationException as e:
            logger.warning(f"Validation error creating form check with URL: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error creating form check with URL: {str(e)}", exc_info=True)
            await self.db.rollback()
            raise Exception(f"Failed to create form check: {str(e)}")