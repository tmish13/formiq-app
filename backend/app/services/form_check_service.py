"""Form check service implementation with analysis and feedback management."""
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import Depends, UploadFile
from app.core.exceptions import (
    ValidationError,
    NotFoundException,
    SubscriptionError,
    ProcessingError
)
from app.core.database import get_db
from app.core.logging import get_logger
from app.core.storage.video import upload_video, delete_video
from app.core.analysis.form import analyze_form
from app.models.form_check import FormCheck, FeedbackItem
from app.models.enums import FormCheckStatus, ExerciseType, FeedbackType, FeedbackSeverity
from app.schemas.form_check import (
    FormCheckCreate,
    FormCheckUpdate,
    FormCheckFilter,
    FormCheckResponse,
    FeedbackItemCreate
)
from app.repositories.form_check_repository import FormCheckRepository
from app.services.base import BaseService
from app.services.subscription_service import SubscriptionService

# Initialize logger
logger = get_logger(__name__)

class FormCheckService(BaseService[FormCheck, FormCheckCreate, FormCheckUpdate, FormCheckFilter]):
    """
    Form check service with analysis and feedback management.
    
    Features:
    - Video upload and processing
    - Form analysis using AI
    - Feedback generation and management
    - Subscription tier validation
    - Status tracking and updates
    """
    
    def __init__(self):
        super().__init__(
            repository=FormCheckRepository,
            model=FormCheck,
            create_schema=FormCheckCreate,
            update_schema=FormCheckUpdate,
            filter_schema=FormCheckFilter
        )
        self.subscription_service = SubscriptionService()

    async def submit_form_check(
        self,
        db: Session = Depends(get_db),
        *,
        user_id: UUID,
        video: UploadFile,
        exercise_type: ExerciseType,
        notes: Optional[str] = None
    ) -> FormCheck:
        """
        Submit a new form check for analysis.
        
        Args:
            db: Database session
            user_id: User's ID
            video: Video file
            exercise_type: Type of exercise
            notes: Additional notes
        """
        try:
            # Validate subscription
            subscription = await self.subscription_service.get_active_subscription(
                db, user_id=user_id
            )
            if not subscription:
                raise SubscriptionError("Active subscription required")
            
            # Check monthly limit
            count = await self.repository.count_monthly_submissions(db, user_id=user_id)
            if count >= subscription.tier.monthly_form_checks:
                raise SubscriptionError("Monthly form check limit reached")
            
            # Upload video
            video_url = await upload_video(video, user_id)
            
            # Create form check
            form_check = await self.create(
                db,
                data={
                    "user_id": user_id,
                    "video_url": video_url,
                    "exercise_type": exercise_type,
                    "notes": notes,
                    "status": FormCheckStatus.PENDING
                }
            )
            
            # Start analysis
            await self._start_analysis(db, form_check)
            
            return form_check
        except Exception as e:
            logger.error("Error in form check submission", exc_info=e)
            raise

    async def get_user_form_checks(
        self,
        db: Session = Depends(get_db),
        *,
        user_id: UUID,
        status: Optional[FormCheckStatus] = None,
        exercise_type: Optional[ExerciseType] = None,
        page: int = 1,
        per_page: int = 10
    ) -> List[FormCheck]:
        """
        Get user's form checks with optional filtering.
        
        Args:
            db: Database session
            user_id: User's ID
            status: Filter by status
            exercise_type: Filter by exercise type
            page: Page number
            per_page: Items per page
        """
        try:
            filters = {"user_id": user_id}
            if status:
                filters["status"] = status
            if exercise_type:
                filters["exercise_type"] = exercise_type
            
            return await self.get_multi(
                db,
                filters=filters,
                page=page,
                per_page=per_page,
                order_by=[("created_at", "desc")]
            )
        except Exception as e:
            logger.error("Error getting user form checks", exc_info=e)
            raise

    async def add_feedback(
        self,
        db: Session = Depends(get_db),
        *,
        form_check_id: UUID,
        feedback_type: FeedbackType,
        severity: FeedbackSeverity,
        timestamp: float,
        description: str,
        suggestions: Optional[str] = None
    ) -> FeedbackItem:
        """
        Add feedback to a form check.
        
        Args:
            db: Database session
            form_check_id: Form check ID
            feedback_type: Type of feedback
            severity: Feedback severity
            timestamp: Video timestamp
            description: Feedback description
            suggestions: Improvement suggestions
        """
        try:
            form_check = await self.get(db, id=form_check_id)
            if form_check.status == FormCheckStatus.COMPLETED:
                raise ValidationError("Cannot add feedback to completed form check")
            
            feedback = await self.repository.add_feedback(
                db,
                data=FeedbackItemCreate(
                    form_check_id=form_check_id,
                    feedback_type=feedback_type,
                    severity=severity,
                    timestamp=timestamp,
                    description=description,
                    suggestions=suggestions
                )
            )
            
            # Update form check status if needed
            if form_check.status == FormCheckStatus.PENDING:
                await self.update(
                    db,
                    id=form_check_id,
                    data={"status": FormCheckStatus.IN_PROGRESS}
                )
            
            return feedback
        except Exception as e:
            logger.error("Error adding feedback", exc_info=e)
            raise

    async def complete_analysis(
        self,
        db: Session = Depends(get_db),
        *,
        form_check_id: UUID,
        summary: str,
        overall_score: float
    ) -> FormCheck:
        """
        Complete form check analysis.
        
        Args:
            db: Database session
            form_check_id: Form check ID
            summary: Analysis summary
            overall_score: Overall form score
        """
        try:
            form_check = await self.get(db, id=form_check_id)
            if form_check.status == FormCheckStatus.COMPLETED:
                raise ValidationError("Form check already completed")
            
            return await self.update(
                db,
                id=form_check_id,
                data={
                    "status": FormCheckStatus.COMPLETED,
                    "summary": summary,
                    "overall_score": overall_score,
                    "completed_at": datetime.utcnow()
                }
            )
        except Exception as e:
            logger.error("Error completing analysis", exc_info=e)
            raise

    async def delete_form_check(
        self,
        db: Session = Depends(get_db),
        *,
        form_check_id: UUID,
        user_id: UUID
    ) -> None:
        """
        Delete a form check and its associated data.
        
        Args:
            db: Database session
            form_check_id: Form check ID
            user_id: User's ID for authorization
        """
        try:
            form_check = await self.get(db, id=form_check_id)
            if form_check.user_id != user_id:
                raise ValidationError("Not authorized to delete this form check")
            
            # Delete video
            if form_check.video_url:
                await delete_video(form_check.video_url)
            
            # Delete form check and feedback
            await self.delete(db, id=form_check_id)
        except Exception as e:
            logger.error("Error deleting form check", exc_info=e)
            raise

    async def _start_analysis(self, db: Session, form_check: FormCheck) -> None:
        """Start form check analysis process."""
        try:
            # Start async analysis task
            await analyze_form(
                form_check_id=form_check.id,
                video_url=form_check.video_url,
                exercise_type=form_check.exercise_type
            )
        except Exception as e:
            logger.error("Error starting analysis", exc_info=e)
            # Update form check status to error
            await self.update(
                db,
                id=form_check.id,
                data={
                    "status": FormCheckStatus.ERROR,
                    "error_message": str(e)
                }
            )
            raise ProcessingError("Failed to start analysis") 