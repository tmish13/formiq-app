"""Feedback item endpoints."""
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.api import deps
from app.core.deps import get_db, get_current_user, validate_feedback_access
from app.services.form_check_service import FormCheckService
try:
    from app.services.rag_feedback_service import rag_feedback_service, FeedbackContext
except ImportError:
    rag_feedback_service = None
    FeedbackContext = None
from app.core.logging import logger
from app.schemas.form_check import FeedbackItemResponse, FeedbackItemUpdate
from app.core.validators import ValidationException
from app.models.user import User

router = APIRouter()


class RAGFeedbackRequest(BaseModel):
    exercise_name: str
    exercise_type: str
    posture_score: float
    stability_score: float
    depth_score: float
    identified_faults: List[str] = []
    user_level: str = "intermediate"
    additional_context: str = None


class RAGFeedbackResponse(BaseModel):
    feedback_text: str
    rag_enabled: bool
    exercise_name: str
    exercise_type: str


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


@router.post("/rag/generate", response_model=RAGFeedbackResponse)
async def generate_rag_feedback(
    *,
    request: RAGFeedbackRequest,
    current_user: User = Depends(deps.get_current_active_user)
) -> RAGFeedbackResponse:
    """Generate RAG-powered exercise feedback."""
    try:
        # Prepare feedback context
        feedback_context = FeedbackContext(
            exercise_name=request.exercise_name,
            exercise_type=request.exercise_type,
            form_scores={
                "posture_score": request.posture_score,
                "stability_score": request.stability_score,
                "depth_score": request.depth_score
            },
            identified_faults=request.identified_faults,
            user_level=request.user_level,
            additional_context=request.additional_context
        )
        
        # Generate feedback
        feedback_text = rag_feedback_service.generate_feedback(feedback_context)
        
        return RAGFeedbackResponse(
            feedback_text=feedback_text,
            rag_enabled=rag_feedback_service.is_available(),
            exercise_name=request.exercise_name,
            exercise_type=request.exercise_type
        )
        
    except Exception as e:
        logger.error(f"Error generating RAG feedback: {str(e)}", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while generating feedback"
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