"""Feedback item endpoints."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import deps
from app.core.deps import get_db, get_current_user, validate_feedback_access
from app.services.form_check_service import FormCheckService
from app.core.logging import logger
from app.schemas.form_check import FeedbackItemResponse, FeedbackItemUpdate
from app.core.validators import ValidationException
from app.models.user import User

router = APIRouter()


@router.get("/{feedback_id}", response_model=FeedbackItemResponse)
async def get_feedback(
    *,
    feedback_id: int,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: User = Depends(deps.get_current_active_user),
    form_check_service: FormCheckService = Depends(deps.get_form_check_service)
) -> FeedbackItemResponse:
    """Get a specific feedback item by ID."""
    await validate_feedback_access(feedback_id=feedback_id, db=db, current_user=current_user)
    
    try:
        feedback_item = await form_check_service.get_feedback(feedback_id)
        return feedback_item
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting feedback item: {str(e)}", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving the feedback item"
        )


@router.patch("/{feedback_id}", response_model=FeedbackItemResponse)
async def update_feedback(
    *,
    feedback_id: int,
    feedback_update: FeedbackItemUpdate,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: User = Depends(deps.get_current_active_user),
    form_check_service: FormCheckService = Depends(deps.get_form_check_service)
) -> FeedbackItemResponse:
    """Update an existing feedback item."""
    await validate_feedback_access(feedback_id=feedback_id, db=db, current_user=current_user)
    
    try:
        updated_feedback = await form_check_service.update_feedback(
            feedback_id=feedback_id,
            update_data=feedback_update.dict(exclude_unset=True)
        )
        return updated_feedback
    except ValidationException as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating feedback item: {str(e)}", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while updating the feedback item"
        )


@router.delete("/{feedback_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_feedback(
    *,
    feedback_id: int,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: User = Depends(deps.get_current_active_user),
    form_check_service: FormCheckService = Depends(deps.get_form_check_service)
) -> None:
    """Delete a feedback item."""
    await validate_feedback_access(feedback_id=feedback_id, db=db, current_user=current_user)
    
    try:
        await form_check_service.delete_feedback(feedback_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error deleting feedback item: {str(e)}", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while deleting the feedback item"
        ) 