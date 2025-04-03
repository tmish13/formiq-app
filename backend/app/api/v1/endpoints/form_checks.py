"""Form check endpoints."""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query, Request, Body
from sqlalchemy.orm import Session
from app.core.deps import (
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
from app.core.validators import validate_video_file, ValidationException
from app.core.config import settings
from app.services.storage import StorageService

router = APIRouter()

@router.post("/", response_model=FormCheckResponse, status_code=status.HTTP_201_CREATED)
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
        
        form_check_service = FormCheckService(db)
        return await form_check_service.submit_form_check(
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
        form_check_service = FormCheckService(db)
        return await form_check_service.get_user_form_checks(
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
        form_check_service = FormCheckService(db)
        return await form_check_service.get(id=form_check_id)
    except Exception as e:
        logger.error("Error getting form check", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Form check not found"
        )

@router.post("/{form_check_id}/feedback", response_model=FeedbackItemResponse, status_code=status.HTTP_201_CREATED)
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
    
    # Perform validation
    if feedback.timestamp < 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Timestamp cannot be negative"
        )
    
    if feedback.feedback_type not in [ft.value for ft in FeedbackType]:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid feedback type. Must be one of: {', '.join([ft.value for ft in FeedbackType])}"
        )
    
    if feedback.severity not in [fs.value for fs in FeedbackSeverity]:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid severity level. Must be one of: {', '.join([fs.value for fs in FeedbackSeverity])}"
        )
    
    try:
        form_check_service = FormCheckService(db)
        return await form_check_service.add_feedback(
            form_check_id=form_check_id,
            feedback_type=feedback.feedback_type,
            severity=feedback.severity,
            timestamp=feedback.timestamp,
            description=feedback.description,
            suggestions=feedback.suggestions,
            is_ai_generated=feedback.is_ai_generated
        )
    except ValidationException as e:
        logger.warning(f"Feedback validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        logger.error("Error adding feedback", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/{form_check_id}/feedback", response_model=List[FeedbackItemResponse])
async def get_feedback_items(
    *,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    form_check_id: str
) -> List[FeedbackItemResponse]:
    """Get all feedback items for a form check."""
    await validate_form_check_access(form_check_id, db, current_user)
    
    try:
        form_check_service = FormCheckService(db)
        return await form_check_service.get_feedback_items(form_check_id=form_check_id)
    except Exception as e:
        logger.error("Error getting feedback items", exc_info=e)
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
    
    # Validate inputs
    if not summary or len(summary) < 10:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Summary must be at least 10 characters"
        )
    
    if overall_score < 0 or overall_score > 10:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Overall score must be between 0 and 10"
        )
    
    try:
        form_check_service = FormCheckService(db)
        return await form_check_service.complete_analysis(
            form_check_id=form_check_id,
            summary=summary,
            overall_score=overall_score
        )
    except ValidationException as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
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
        form_check_service = FormCheckService(db)
        await form_check_service.delete_form_check(
            form_check_id=form_check_id,
            user_id=current_user.id
        )
    except Exception as e:
        logger.error("Error deleting form check", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/presigned-upload", response_model=Dict[str, Any])
async def get_presigned_upload_url(
    *,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    request: Request,
    filename: str = Body(...),
    content_type: str = Body(...),
    exercise_type: ExerciseType = Body(...)
) -> Dict[str, Any]:
    """Get a presigned URL for direct video upload to S3."""
    # Check subscription tier
    await check_subscription_tier(SubscriptionTier.BASIC, db, current_user)
    
    try:
        # Validate content type
        if content_type not in settings.ALLOWED_VIDEO_TYPES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid content type. Allowed types: {settings.ALLOWED_VIDEO_TYPES}"
            )
        
        # Create storage service
        storage = StorageService()
        
        # Generate folder path: users/{user_id}/form_checks/{exercise_type}
        folder = f"users/{current_user.id}/form_checks/{exercise_type}"
        
        # Get presigned URL
        presigned_data = await storage.generate_presigned_url(
            filename=filename,
            folder=folder,
            user_id=str(current_user.id),
            content_type=content_type
        )
        
        # Log the request
        logger.info(
            "Generated presigned upload URL",
            extra={
                "user_id": current_user.id,
                "filename": filename,
                "content_type": content_type,
                "exercise_type": exercise_type
            }
        )
        
        return presigned_data
    except Exception as e:
        logger.error(f"Error generating presigned URL: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/with-url", response_model=FormCheckResponse, status_code=status.HTTP_201_CREATED)
async def submit_form_check_with_url(
    *,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    data: Dict[str, Any] = Body(...)
) -> FormCheckResponse:
    """Submit a form check using an already uploaded video URL."""
    # Check subscription tier
    await check_subscription_tier(SubscriptionTier.BASIC, db, current_user)
    
    try:
        # Extract data
        video_url = data.get("video_url")
        exercise_type = data.get("exercise_type")
        notes = data.get("notes")
        
        # Validate inputs
        if not video_url:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Video URL is required"
            )
        
        if not exercise_type or exercise_type not in [et.value for et in ExerciseType]:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid exercise type. Must be one of: {', '.join([et.value for et in ExerciseType])}"
            )
        
        # Create form check service
        form_check_service = FormCheckService(db)
        
        # Create the form check
        return await form_check_service.create_with_url(
            user_id=current_user.id,
            video_url=video_url,
            exercise_type=exercise_type,
            notes=notes
        )
    except ValidationException as e:
        logger.warning(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error submitting form check with URL: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        ) 