"""Form analysis endpoints."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Query, Path
from sqlalchemy.orm import Session

from app.api import deps
from app.core.security import get_current_active_user
from app.schemas.form_analysis import (
    FormAnalysisRequest,
    FormAnalysisResult,
    FormAnalysisHistoryRequest
)
from app.models.user import User
from app.services.form_analysis import FormAnalysisService
from app.core.cache import cache_service
from app.core.rate_limit import rate_limit

router = APIRouter(prefix="/form-analysis", tags=["form-analysis"])

@router.post(
    "/analyze",
    response_model=FormAnalysisResult,
    status_code=201,
    responses={
        201: {
            "description": "Successfully analyzed exercise form",
            "content": {
                "application/json": {
                    "example": {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "user_id": "123e4567-e89b-12d3-a456-426614174001",
                        "exercise_type": "squat",
                        "score": 85.5,
                        "feedback": [
                            {"type": "success", "message": "Good depth achieved"},
                            {"type": "warning", "message": "Slight knee valgus detected"}
                        ],
                        "created_at": "2024-01-20T10:30:00Z"
                    }
                }
            }
        },
        400: {"$ref": "#/components/responses/ValidationError"},
        401: {"$ref": "#/components/responses/UnauthorizedError"},
        413: {
            "description": "File too large",
            "content": {
                "application/json": {
                    "example": {"detail": "File size exceeds 100MB limit"}
                }
            }
        },
        429: {"$ref": "#/components/responses/RateLimitError"}
    }
)
@rate_limit(limit=10, window=120, burst=20)  # 10 requests per 2 minutes, burst of 20
async def analyze_form(
    video: UploadFile = File(..., description="Exercise video file (MP4/MOV, max 100MB)"),
    exercise_type: str = Query(..., description="Type of exercise being analyzed"),
    notes: str = Query(None, description="Additional notes about the exercise"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(deps.get_db)
):
    """
    Analyze exercise form from uploaded video.
    
    Args:
        video: Video file to analyze
        exercise_type: Type of exercise being analyzed
        notes: Optional notes about the exercise
        current_user: Currently authenticated user
        db: Database session
        
    Returns:
        FormAnalysisResult: Analysis results including feedback and metrics
    """
    try:
        # Create form analysis request
        request = FormAnalysisRequest(
            video_file=video.filename,
            exercise_type=exercise_type,
            user_id=current_user.id,
            notes=notes
        )
        
        # Initialize service and analyze form
        service = FormAnalysisService(db)
        result = await service.analyze_form(request)
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Form analysis failed: {str(e)}"
        )

@router.get(
    "/history",
    response_model=List[FormAnalysisResult],
    responses={
        200: {
            "description": "Successfully retrieved analysis history",
            "content": {
                "application/json": {
                    "example": [{
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "user_id": "123e4567-e89b-12d3-a456-426614174001",
                        "exercise_type": "squat",
                        "score": 85.5,
                        "feedback": [
                            {"type": "success", "message": "Good depth achieved"}
                        ],
                        "created_at": "2024-01-20T10:30:00Z"
                    }]
                }
            }
        },
        401: {"$ref": "#/components/responses/UnauthorizedError"},
        429: {"$ref": "#/components/responses/RateLimitError"}
    }
)
@rate_limit(limit=60, window=60)  # 60 requests per minute
async def get_analysis_history(
    exercise_type: str = Query(None, description="Filter by exercise type"),
    start_date: str = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(None, description="End date (YYYY-MM-DD)"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(deps.get_db)
):
    """
    Get form analysis history for the current user.
    
    Args:
        exercise_type: Optional filter by exercise type
        start_date: Optional start date filter
        end_date: Optional end date filter
        limit: Maximum number of results to return
        offset: Number of results to skip
        current_user: Currently authenticated user
        db: Database session
        
    Returns:
        List[FormAnalysisResult]: List of form analysis results
    """
    try:
        # Create history request
        request = FormAnalysisHistoryRequest(
            user_id=current_user.id,
            exercise_type=exercise_type,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset
        )
        
        # Get history from service
        service = FormAnalysisService(db)
        history = await service.get_user_history(request)
        
        return history
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get analysis history: {str(e)}"
        )

@router.get(
    "/{analysis_id}",
    response_model=FormAnalysisResult,
    responses={
        200: {
            "description": "Successfully retrieved form analysis",
            "content": {
                "application/json": {
                    "example": {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "user_id": "123e4567-e89b-12d3-a456-426614174001",
                        "exercise_type": "squat",
                        "score": 85.5,
                        "feedback": [
                            {"type": "success", "message": "Good depth achieved"},
                            {"type": "warning", "message": "Slight knee valgus detected"}
                        ],
                        "created_at": "2024-01-20T10:30:00Z"
                    }
                }
            }
        },
        401: {"$ref": "#/components/responses/UnauthorizedError"},
        404: {"$ref": "#/components/responses/NotFoundError"},
        429: {"$ref": "#/components/responses/RateLimitError"}
    }
)
@rate_limit(limit=60, window=60)  # 60 requests per minute
async def get_analysis(
    analysis_id: str = Path(..., description="The ID of the form analysis to retrieve"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(deps.get_db)
) -> FormAnalysisResult:
    """
    Retrieve a specific form analysis result.
    
    Returns detailed analysis results including:
    * Overall form score
    * Feedback points
    * Joint angles
    * Identified issues
    
    Rate limit: 60 requests per minute
    """
    analysis_service = FormAnalysisService(db)
    result = await analysis_service.get_analysis(analysis_id, current_user)
    if not result:
        raise HTTPException(status_code=404, detail=f"Analysis with ID {analysis_id} not found")
    return result

@router.delete(
    "/{analysis_id}",
    status_code=204,
    responses={
        204: {"description": "Analysis successfully deleted"},
        401: {"$ref": "#/components/responses/UnauthorizedError"},
        404: {"$ref": "#/components/responses/NotFoundError"},
        429: {"$ref": "#/components/responses/RateLimitError"}
    }
)
@rate_limit(limit=30, window=60)  # 30 requests per minute
async def delete_analysis(
    analysis_id: str = Path(..., description="The ID of the form analysis to delete"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(deps.get_db)
) -> None:
    """
    Delete a specific form analysis.
    
    Permanently removes:
    * Analysis results
    * Associated feedback
    * Video files
    * Generated data
    
    This action cannot be undone.
    Rate limit: 30 requests per minute
    """
    analysis_service = FormAnalysisService(db)
    result = await analysis_service.delete_analysis(analysis_id, current_user)
    if not result:
        raise HTTPException(status_code=404, detail=f"Analysis with ID {analysis_id} not found")

@router.get(
    "/analysis",
    response_model=List[FormAnalysisResult],
    responses={
        200: {
            "description": "Successfully retrieved form analyses",
            "content": {
                "application/json": {
                    "example": [{
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "user_id": "123e4567-e89b-12d3-a456-426614174001",
                        "exercise_type": "squat",
                        "score": 85.5,
                        "feedback": [
                            {"type": "success", "message": "Good depth achieved"}
                        ],
                        "created_at": "2024-01-20T10:30:00Z"
                    }]
                }
            }
        },
        401: {"$ref": "#/components/responses/UnauthorizedError"}
    }
)
async def list_analyses(
    exercise_type: Optional[str] = Query(None, description="Filter by exercise type"),
    skip: int = Query(0, description="Number of records to skip for pagination"),
    limit: int = Query(10, description="Maximum number of records to return"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(deps.get_db)
) -> List[FormAnalysisResult]:
    """
    List form analysis results for the current user.
    
    Supports:
    * Filtering by exercise type
    * Pagination
    * Sorting by date (newest first)
    
    Returns a list of analysis results with scores and feedback.
    """
    analysis_service = FormAnalysisService(db)
    return await analysis_service.list_analyses(current_user, exercise_type, skip, limit)

@router.get("/history", response_model=List[FormAnalysisResult])
async def get_analysis_history(
    skip: int = 0,
    limit: int = 100,
    form_analysis_service: FormAnalysisService = Depends()
):
    """Get form analysis history with caching."""
    cache_key = f"form_analysis:history:{skip}:{limit}"
    
    # Try to get from cache first
    cached_history = await cache_service.get(cache_key)
    if cached_history:
        return cached_history
    
    # If not in cache, get from database
    history = await form_analysis_service.get_history(skip=skip, limit=limit)
    
    # Cache the results
    await cache_service.set(cache_key, history, expires_in=1800)  # Cache for 30 minutes
    
    return history

@router.delete("/{analysis_id}")
async def delete_analysis(
    analysis_id: str,
    form_analysis_service: FormAnalysisService = Depends()
):
    """Delete a form analysis and invalidate relevant caches."""
    deleted = await form_analysis_service.delete_analysis(analysis_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    # Invalidate both list and detail caches
    await cache_service.delete("form_analysis:history:*")
    await cache_service.delete(f"form_analysis:result:{analysis_id}")
    
    return {"message": "Analysis deleted successfully"} 