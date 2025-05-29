"""Form Check endpoints."""
import logging
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Query, Path, status
from datetime import datetime as dt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api import deps # Assuming this is still needed for DB session if not through service
# from app.core.security import get_current_active_user # Removed
from app.models.user import User
from app.models.enums import ExerciseType # Added
from app.models.enums import FormCheckStatus # ADDED for status_filter conversion
from app.services.form_check_service import get_async_form_check_service, FormCheckService
from app.schemas.form_check import (
    FormCheckCreate,
    FormCheckUpdate,
    FormCheckResponse,
    FormCheckListResponse,
    FormCheckDetailedResponse,
    FeedbackItemCreate,
    FeedbackItemUpdate,
    FeedbackItemResponse
)
from app.core.exceptions import NotFoundException, ServerErrorException, PermissionDeniedException
from app.services.video_service import VideoService
from app.models.form_check import FormCheck
from app.models.video import Video

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/form-checks", tags=["Form Checks"])

@router.post(
    "/submit",
    response_model=FormCheckResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        202: {
            "description": "Form check request accepted for processing.",
            "content": {
                "application/json": {
                    "example": {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "user_id": "123e4567-e89b-12d3-a456-426614174001",
                        "exercise_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
                        "video_url": "https://s3.amazonaws.com/bucket/video.mp4",
                        "status": "PENDING",
                        "notes": "Checking my squat form.",
                        "created_at": "2024-01-20T10:30:00Z",
                        "updated_at": "2024-01-20T10:30:00Z"
                    }
                }
            }
        },
        400: {"$ref": "#/components/responses/ValidationError"},
        401: {"$ref": "#/components/responses/UnauthorizedError"},
        413: {"description": "File too large", "content": {"application/json": {"example": {"detail": "File size exceeds 100MB limit"}}}},
        422: {"$ref": "#/components/responses/RequestValidationError"},
        429: {"$ref": "#/components/responses/RateLimitError"},
        500: {"$ref": "#/components/responses/ServerError"}
    }
)
async def submit_form_check_for_analysis(
    video_upload: UploadFile = File(..., description="Exercise video file (MP4/MOV, max 100MB)."),
    exercise_name: str = Query(..., description="Name of the exercise (e.g., 'Low Bar Squat'). Must match an existing ExerciseTemplate name."),
    notes: Optional[str] = Query(None, description="Additional notes about the exercise session."),
    # current_user: User = Depends(get_current_active_user), # Changed to deps.get_current_active_user
    current_user: User = Depends(deps.get_current_active_user),
    form_check_service: FormCheckService = Depends(deps.get_async_form_check_service)
):
    """
    Submit an exercise video for asynchronous form check analysis.
    """
    try:
        form_check_record = await form_check_service.submit_form_check(
            user_id=current_user.id,
            exercise_name=exercise_name,
            video_upload=video_upload,
            notes=notes
        )
        return form_check_record
    except HTTPException as he:
        raise he
    except ValueError as ve:
        logger.error(f"ValueError during form check submission: {str(ve)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except NotFoundException as nfe:
        logger.warning(f"NotFoundException during form check submission: {str(nfe)}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(nfe))
    except ServerErrorException as se:
        logger.error(f"ServerErrorException during form check submission: {str(se)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=se.detail)
    except Exception as e:
        logger.error(f"Unexpected error during form check submission: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred.")

@router.get(
    "/history",
    response_model=List[FormCheckDetailedResponse],
    responses={
        200: {"description": "Successfully retrieved form check history."},
        400: {"$ref": "#/components/responses/ValidationError"},
        401: {"$ref": "#/components/responses/UnauthorizedError"},
        429: {"$ref": "#/components/responses/RateLimitError"}
    }
)
async def get_form_check_history(
    exercise_id_filter: Optional[UUID] = Query(None, description="Filter by specific Exercise ID."),
    exercise_type_filter: Optional[ExerciseType] = Query(None, description="Filter by exercise type."),
    start_date_str: Optional[str] = Query(None, alias="start_date", description="Filter by start date (YYYY-MM-DD)."),
    end_date_str: Optional[str] = Query(None, alias="end_date", description="Filter by end date (YYYY-MM-DD)."),
    status_filter_str: Optional[str] = Query(None, alias="status", description="Filter by form check status (e.g., PENDING, COMPLETED, ERROR)."),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    # current_user: User = Depends(get_current_active_user), # Changed to deps.get_current_active_user
    current_user: User = Depends(deps.get_current_active_user),
    form_check_service: FormCheckService = Depends(deps.get_async_form_check_service)
):
    """
    Get form check history for the current user.
    """
    start_date: Optional[dt] = None
    end_date: Optional[dt] = None
    status_enum: Optional[FormCheckStatus] = None

    try:
        if start_date_str:
            start_date = dt.strptime(start_date_str, "%Y-%m-%d")
        if end_date_str:
            end_date = dt.strptime(end_date_str + "T23:59:59.999999", "%Y-%m-%dT%H:%M:%S.%f")
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid date format. Use YYYY-MM-DD.")

    if status_filter_str:
        try:
            status_enum = FormCheckStatus[status_filter_str.upper()]
        except KeyError:
            valid_statuses = [s.name for s in FormCheckStatus]
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid status filter: '{status_filter_str}'. Valid statuses are: {valid_statuses}"
            )

    try:
        form_checks = await form_check_service.list_user_form_checks_detailed(
            user_id=current_user.id, skip=offset, limit=limit,
            exercise_id=exercise_id_filter, exercise_type=exercise_type_filter,
            start_date=start_date, end_date=end_date, status_filter=status_enum
        )
        return form_checks
    except HTTPException as he:
        raise he
    except ValueError as ve:
        logger.error(f"ValueError in get_form_check_history: {str(ve)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        logger.error(f"Failed to get form check history: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error retrieving history.")

@router.get(
    "/{form_check_id}",
    response_model=FormCheckDetailedResponse,
    responses={
        200: {"description": "Successfully retrieved form check details."},
        401: {"$ref": "#/components/responses/UnauthorizedError"},
        404: {"$ref": "#/components/responses/NotFoundError"},
        429: {"$ref": "#/components/responses/RateLimitError"}
    }
)
async def get_form_check_details(
    form_check_id: UUID = Path(..., description="The ID of the form check to retrieve."),
    # current_user: User = Depends(get_current_active_user), # Changed to deps.get_current_active_user
    current_user: User = Depends(deps.get_current_active_user),
    form_check_service: FormCheckService = Depends(deps.get_async_form_check_service)
) -> FormCheckDetailedResponse:
    """
    Get detailed information for a specific form check.
    """
    try:
        form_check = await form_check_service.get_form_check_details(
            form_check_id=form_check_id, user_id=current_user.id
        )
        return form_check # Service handles NotFoundException
    except NotFoundException as nfe:
        logger.warning(f"NotFound for form_check_id {form_check_id}: {str(nfe)}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(nfe))
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Failed to get form check details for {form_check_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error retrieving details.")

@router.delete(
    "/{form_check_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Form check successfully deleted."},
        401: {"$ref": "#/components/responses/UnauthorizedError"},
        404: {"$ref": "#/components/responses/NotFoundError"},
        429: {"$ref": "#/components/responses/RateLimitError"}
    }
)
async def delete_form_check(
    form_check_id: UUID = Path(..., description="The ID of the form check to delete."),
    # current_user: User = Depends(get_current_active_user), # Changed to deps.get_current_active_user
    current_user: User = Depends(deps.get_current_active_user),
    form_check_service: FormCheckService = Depends(deps.get_async_form_check_service)
):
    """
    Delete a specific form check.
    """
    try:
        await form_check_service.delete_form_check_record(
            form_check_id=form_check_id, user_id=current_user.id
        )
        # No content to return on successful deletion
    except NotFoundException as nfe:
        logger.warning(f"NotFound during deletion of {form_check_id}: {str(nfe)}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(nfe))
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Failed to delete form check {form_check_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error deleting form check.")

@router.get("/{video_id}", response_model=FormCheckDetailedResponse)
async def get_form_check_by_video_id(
    video_id: UUID,
    # db: AsyncSession = Depends(get_db), # OLD - Incorrect for async, and missing deps prefix
    db: AsyncSession = Depends(deps.get_async_db), # NEW - Correct for async and uses deps prefix
    # current_user: User = Depends(get_current_active_user) # OLD - Missing deps prefix
    current_user: User = Depends(deps.get_current_active_user) # NEW - Corrected to use deps prefix
):
    """
    Retrieve a specific FormCheck and its feedback items by Video ID.

    Ensures that the requesting user owns the video associated with the FormCheck.
    """
    form_check_service = FormCheckService(db_session=db)
    video_service = VideoService(db_session=db) # Initialize VideoService

    # First, get the video to verify ownership and existence
    video = await video_service.get_video_by_id_async(video_id)
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")

    # Verify user ownership of the video
    if video.user_id != current_user.id:
        # Add admin/coach role check here in the future if needed
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this video's form check")

    # Now, fetch the form check associated with this video ID
    # We might have multiple form checks per video if re-analysis is allowed.
    # For now, let's assume we want the most recent one or any one if only one exists.
    # The FormCheckService might need a method like get_latest_form_check_by_video_id_async
    
    # Simplistic approach: get all form checks for the video and return the first one found (or latest by created_at)
    # A more robust service method would be better: form_check_service.get_form_check_by_video_id_with_details_async(video_id)
    
    # Assuming FormCheckService has a method to get FormCheck by video_id with eager loaded feedback_items
    # If not, we might need to query like this (less ideal in API layer):
    stmt = (
        select(FormCheck)
        .where(FormCheck.video_id == video_id)
        .options(selectinload(FormCheck.feedback_items), selectinload(FormCheck.exercise))
        .order_by(FormCheck.created_at.desc()) # Get the latest one if multiple exist
    )
    result = await db.execute(stmt)
    form_check = result.scalars().first()

    if not form_check:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Form check not found for this video")

    # The FormCheckDetailedResponse schema should handle the ORM to Pydantic conversion
    # Ensure the FormCheck ORM model has `feedback_items` and `exercise` relationships defined.
    return form_check 