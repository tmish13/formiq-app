"""Form check endpoints."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy.orm import Session
from app.api.deps import (
    get_db,
    get_current_user,
    check_subscription_tier,
    validate_form_check_access
)
from app.models.enums import (
    SubscriptionTier,
    FormCheckStatus,
    ExerciseType,
    FeedbackType,
    FeedbackSeverity
)
from app.schemas.form_check import (
    FormCheckCreate,
    FormCheckUpdate,
    FormCheckResponse,
    FeedbackItemCreate,
    FeedbackItemResponse
)
from app.services.form_check_service import FormCheckService
from app.core.logging import logger
from app.core.validators import validate_video_file
from app.core.config import settings

router = APIRouter()

@router.post("/", response_model=FormCheckResponse)
async def submit_form_check(
    *,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    video: UploadFile = File(...),
    exercise_type: ExerciseType,
    notes: Optional[str] = None
) -> FormCheckResponse:
    """Submit a new form check for analysis."""
    # Check subscription tier
    await check_subscription_tier(SubscriptionTier.BASIC, db, current_user)
    
    try:
        # Read video content
        content = await video.read()
        
        # Validate video file
        validate_video_file(
            content=content,
            filename=video.filename,
            max_size_mb=settings.MAX_VIDEO_SIZE_MB
        )
        
        form_check_service = FormCheckService()
        return await form_check_service.submit_form_check(
            db,
            user_id=current_user.id,
            video=video,
            exercise_type=exercise_type,
            notes=notes
        )
    except ValidationException as e:
        logger.warning(
            "Video validation failed",
            extra={
                "user_id": current_user.id,
                "filename": video.filename,
                "error": str(e)
            }
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "Error submitting form check",
            extra={
                "user_id": current_user.id,
                "filename": video.filename,
                "error": str(e)
            },
            exc_info=e
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/", response_model=List[FormCheckResponse])
async def get_form_checks(
    *,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    status: Optional[FormCheckStatus] = None,
    exercise_type: Optional[ExerciseType] = None,
    page: int = Query(1, gt=0),
    per_page: int = Query(10, gt=0, le=100)
) -> List[FormCheckResponse]:
    """Get user's form checks with optional filtering."""
    try:
        form_check_service = FormCheckService()
        return await form_check_service.get_user_form_checks(
            db,
            user_id=current_user.id,
            status=status,
            exercise_type=exercise_type,
            page=page,
            per_page=per_page
        )
    except Exception as e:
        logger.error("Error getting form checks", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/{form_check_id}", response_model=FormCheckResponse)
async def get_form_check(
    *,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    form_check_id: str
) -> FormCheckResponse:
    """Get a specific form check."""
    await validate_form_check_access(form_check_id, db, current_user)
    
    try:
        form_check_service = FormCheckService()
        return await form_check_service.get(db, id=form_check_id)
    except Exception as e:
        logger.error("Error getting form check", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Form check not found"
        )

@router.post("/{form_check_id}/feedback", response_model=FeedbackItemResponse)
async def add_feedback(
    *,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    form_check_id: str,
    feedback: FeedbackItemCreate
) -> FeedbackItemResponse:
    """Add feedback to a form check."""
    # Check subscription tier for AI feedback
    if feedback.is_ai_generated:
        await check_subscription_tier(SubscriptionTier.PRO, db, current_user)
    
    await validate_form_check_access(form_check_id, db, current_user)
    
    try:
        form_check_service = FormCheckService()
        return await form_check_service.add_feedback(
            db,
            form_check_id=form_check_id,
            feedback_type=feedback.feedback_type,
            severity=feedback.severity,
            timestamp=feedback.timestamp,
            description=feedback.description,
            suggestions=feedback.suggestions
        )
    except Exception as e:
        logger.error("Error adding feedback", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/{form_check_id}/complete", response_model=FormCheckResponse)
async def complete_analysis(
    *,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    form_check_id: str,
    summary: str,
    overall_score: float = Query(..., ge=0, le=10)
) -> FormCheckResponse:
    """Complete form check analysis."""
    await validate_form_check_access(form_check_id, db, current_user)
    
    try:
        form_check_service = FormCheckService()
        return await form_check_service.complete_analysis(
            db,
            form_check_id=form_check_id,
            summary=summary,
            overall_score=overall_score
        )
    except Exception as e:
        logger.error("Error completing analysis", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.delete("/{form_check_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_form_check(
    *,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    form_check_id: str
) -> None:
    """Delete a form check."""
    await validate_form_check_access(form_check_id, db, current_user)
    
    try:
        form_check_service = FormCheckService()
        await form_check_service.delete_form_check(
            db,
            form_check_id=form_check_id,
            user_id=current_user.id
        )
    except Exception as e:
        logger.error("Error deleting form check", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        ) 