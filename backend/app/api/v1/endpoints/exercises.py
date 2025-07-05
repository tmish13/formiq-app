"""Exercises router module."""
from typing import Any, List, Optional, Dict
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from uuid import UUID
from datetime import datetime

from app.core.deps import get_current_active_user, get_db, get_async_exercise_config_service
from app.repositories.exercise_repository import ExerciseRepository
from app.schemas.exercise import ExerciseResponse, ExerciseCreate, ExerciseUpdate
from app.core.cache import cache_service
from app.models.exercise import ExerciseTemplate
from app.services.exercise_service import ExerciseService, get_exercise_service
from app.services.exercise_config_service import ExerciseConfigService
from app.core.exceptions import NotFoundException

router = APIRouter()


@router.get("/", response_model=List[ExerciseResponse])
async def get_exercises(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    exercise_service: ExerciseService = Depends(get_exercise_service)
):
    """Get all exercises with caching."""
    cache_key = f"exercises:list:{skip}:{limit}"
    
    # Try to get from cache first
    cached_exercises = await cache_service.get(cache_key)
    if cached_exercises:
        return cached_exercises
    
    # If not in cache, get from database
    exercises = await exercise_service.get_all(skip=skip, limit=limit)
    
    # Cache the results
    await cache_service.set(cache_key, exercises, expires_in=3600)  # Cache for 1 hour
    
    return exercises


@router.post("/", response_model=ExerciseResponse)
async def create_exercise(
    exercise: ExerciseCreate,
    exercise_service: ExerciseService = Depends(get_exercise_service)
):
    """Create a new exercise and invalidate relevant caches."""
    new_exercise = await exercise_service.create(exercise)
    
    # Invalidate list cache
    await cache_service.delete("exercises:list:*")
    
    return new_exercise


@router.get("/{exercise_id}", response_model=ExerciseResponse)
async def get_exercise(
    exercise_id: str,
    exercise_service: ExerciseService = Depends(get_exercise_service)
):
    """Get a specific exercise by ID with caching."""
    cache_key = f"exercises:detail:{exercise_id}"
    
    # Try to get from cache first
    cached_exercise = await cache_service.get(cache_key)
    if cached_exercise:
        return cached_exercise
    
    # If not in cache, get from database
    exercise = await exercise_service.get_by_id(exercise_id)
    if not exercise:
        raise HTTPException(status_code=404, detail="Exercise not found")
    
    # Cache the result
    await cache_service.set(cache_key, exercise, expires_in=3600)  # Cache for 1 hour
    
    return exercise


@router.put("/{exercise_id}", response_model=ExerciseResponse)
async def update_exercise(
    exercise_id: str,
    exercise: ExerciseUpdate,
    exercise_service: ExerciseService = Depends(get_exercise_service)
):
    """Update an existing exercise and invalidate relevant caches."""
    updated_exercise = await exercise_service.update(exercise_id, exercise)
    if not updated_exercise:
        raise HTTPException(status_code=404, detail="Exercise not found")
    
    # Invalidate both list and detail caches
    await cache_service.delete("exercises:list:*")
    await cache_service.delete(f"exercises:detail:{exercise_id}")
    
    return updated_exercise


@router.delete("/{exercise_id}")
async def delete_exercise(
    exercise_id: str,
    exercise_service: ExerciseService = Depends(get_exercise_service)
):
    """Delete an exercise and invalidate relevant caches."""
    deleted = await exercise_service.delete(exercise_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Exercise not found")
    
    # Invalidate both list and detail caches
    await cache_service.delete("exercises:list:*")
    await cache_service.delete(f"exercises:detail:{exercise_id}")
    
    return {"message": "Exercise deleted successfully"}


@router.get("/search/", response_model=List[ExerciseResponse])
async def search_exercises(
    query: str = Query(..., min_length=1, description="Search query string"),
    muscle_group: Optional[str] = Query(None, description="Filter by muscle group"),
    difficulty: Optional[str] = Query(None, description="Filter by difficulty level"),
    equipment: Optional[str] = Query(None, description="Filter by required equipment"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    exercise_service: ExerciseService = Depends(get_exercise_service)
):
    """
    Search exercises with optional filters.
    
    The search looks through exercise names and descriptions.
    Results can be filtered by muscle group, difficulty level, and required equipment.
    Results are paginated and cached for performance.
    """
    cache_key = f"exercises:search:{query}:{muscle_group}:{difficulty}:{equipment}:{skip}:{limit}"
    
    # Try to get from cache first
    cached_results = await cache_service.get(cache_key)
    if cached_results:
        return cached_results
    
    # If not in cache, search in database
    results = await exercise_service.search(
        query=query,
        muscle_group=muscle_group,
        difficulty=difficulty,
        equipment=equipment,
        skip=skip,
        limit=limit
    )
    
    # Cache the results
    await cache_service.set(cache_key, results, expires_in=1800)  # Cache for 30 minutes
    
    return results


@router.get(
    "/{exercise_template_id}/reference-overlay", 
    response_model=Optional[Dict[str, Any]],
    summary="Get Reference Visual Overlay Data",
    description="Retrieves the reference pose data (keypoints, ideal angles for key phases) for the active configuration of a given exercise template. Auto-generates reference pose if it doesn't exist for supported exercises."
)
async def get_reference_overlay_data(
    exercise_template_id: UUID,
    body_proportions: Optional[str] = Query(None, description="JSON string of body proportions for scaling"),
    generate_if_missing: bool = Query(True, description="Auto-generate reference pose if missing"),
    exercise_config_service: ExerciseConfigService = Depends(get_async_exercise_config_service)
):
    """
    Get reference visual overlay data for an exercise template.
    
    - Fetches the active ExerciseConfig for the given exercise_template_id.
    - Retrieves the reference_pose_data from that configuration.
    - Auto-generates reference pose if missing and exercise is supported.
    """
    try:
        # Parse body proportions if provided
        body_props = None
        if body_proportions:
            try:
                import json
                body_props = json.loads(body_proportions)
            except json.JSONDecodeError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid body_proportions JSON format"
                )
        
        # Use the new method that auto-generates if missing
        if generate_if_missing:
            reference_data = await exercise_config_service.get_reference_pose_by_exercise_id(
                exercise_id=exercise_template_id,
                body_proportions=body_props
            )
        else:
            # Original behavior - just get existing data
            active_config = await exercise_config_service.get_active_config_for_exercise_async(
                exercise_id=exercise_template_id
            )
            if not active_config:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Active exercise configuration not found for exercise template ID: {exercise_template_id}"
                )
            
            reference_data = await exercise_config_service.get_reference_pose_data_async(
                exercise_config_id=active_config.id
            )
        
        if not reference_data:
            # Return null if no reference data available
            return None 
            
        return reference_data
        
    except NotFoundException as e: # Catch specific NotFound from services if they raise it
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        # Log the exception for debugging
        # logger.error(f"Error fetching reference overlay data for {exercise_template_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while fetching reference overlay data."
        )


@router.post(
    "/generate-reference-poses",
    response_model=Dict[str, bool],
    summary="Bulk Generate Reference Poses",
    description="Generate reference poses for multiple exercises in bulk. Useful for admin/setup operations."
)
async def bulk_generate_reference_poses(
    exercise_types: Optional[List[str]] = Query(None, description="List of exercise types to generate for"),
    exercise_config_service: ExerciseConfigService = Depends(get_async_exercise_config_service)
):
    """
    Generate reference poses for multiple exercises in bulk.
    
    Args:
        exercise_types: Optional list of exercise types. If not provided, generates for all supported types.
        
    Returns:
        Dictionary mapping exercise type to success status
    """
    try:
        results = await exercise_config_service.bulk_generate_reference_poses(
            exercise_types=exercise_types
        )
        
        return results
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during bulk reference pose generation: {str(e)}"
        )


@router.post(
    "/{exercise_template_id}/pose-comparison",
    response_model=Dict[str, Any],
    summary="Compare User Pose with Reference",
    description="Compare a user's pose with the reference pose for real-time feedback and visual overlay data."
)
async def compare_pose_with_reference(
    exercise_template_id: UUID,
    user_pose: Dict[str, Any],
    phase: Optional[str] = Query("setup", description="Movement phase to compare against (setup, mid_descent, bottom, mid_ascent)"),
    exercise_config_service: ExerciseConfigService = Depends(get_async_exercise_config_service)
):
    """
    Compare a user's pose with the reference pose for the specified exercise and phase.
    
    Args:
        exercise_template_id: ID of the exercise template
        user_pose: User's pose data (keypoints with confidence scores)
        phase: Movement phase to compare against
        
    Returns:
        Dictionary containing similarity scores, visual overlay data, and feedback
    """
    try:
        from app.services.pose_comparison_service import PoseAlignmentService
        from app.core.config import get_settings
        
        # Get reference pose data
        reference_data = await exercise_config_service.get_reference_pose_by_exercise_id(
            exercise_id=exercise_template_id
        )
        
        if not reference_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Reference pose data not found for exercise {exercise_template_id}"
            )
        
        # Check if requested phase exists
        if 'key_poses' not in reference_data or phase not in reference_data['key_poses']:
            available_phases = list(reference_data.get('key_poses', {}).keys())
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Phase '{phase}' not available. Available phases: {available_phases}"
            )
        
        reference_pose = reference_data['key_poses'][phase]
        
        # Initialize pose comparison service
        settings = get_settings()
        alignment_service = PoseAlignmentService(settings)
        
        # Calculate pose similarity
        similarity_result = alignment_service.calculate_pose_similarity(
            user_pose=user_pose,
            reference_pose=reference_pose,
            normalize_positions=True
        )
        
        # Generate visual overlay data
        overlay_data = alignment_service.generate_overlay_alignment_data(
            user_pose=user_pose,
            reference_pose=reference_pose,
            highlight_deviations=True
        )
        
        return {
            "exercise_id": str(exercise_template_id),
            "phase": phase,
            "similarity_result": similarity_result,
            "overlay_data": overlay_data,
            "reference_pose": reference_pose,
            "timestamp": str(datetime.utcnow())
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during pose comparison: {str(e)}"
        )


@router.get("/categories", response_model=List[Dict[str, Any]])
async def get_exercise_categories(
    exercise_service: ExerciseService = Depends(get_exercise_service)
):
    """
    Get all exercise categories with counts.
    
    Returns:
        List of exercise categories with exercise counts
    """
    try:
        categories = await exercise_service.get_categories()
        return categories
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching exercise categories: {str(e)}"
        )


@router.get("/muscle-groups", response_model=List[Dict[str, Any]])
async def get_muscle_groups(
    exercise_service: ExerciseService = Depends(get_exercise_service)
):
    """
    Get all muscle groups with exercise counts.
    
    Returns:
        List of muscle groups with exercise counts
    """
    try:
        muscle_groups = await exercise_service.get_muscle_groups()
        return muscle_groups
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching muscle groups: {str(e)}"
        )


@router.get("/difficulty-levels", response_model=List[Dict[str, Any]])
async def get_difficulty_levels(
    exercise_service: ExerciseService = Depends(get_exercise_service)
):
    """
    Get all difficulty levels with exercise counts.
    
    Returns:
        List of difficulty levels with exercise counts
    """
    try:
        difficulty_levels = await exercise_service.get_difficulty_levels()
        return difficulty_levels
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching difficulty levels: {str(e)}"
        )


@router.get("/{exercise_id}/reference-pose", response_model=Dict[str, Any])
async def get_reference_pose(
    exercise_id: str,
    exercise_service: ExerciseService = Depends(get_exercise_service)
):
    """
    Get reference pose data for an exercise.
    
    Args:
        exercise_id: Exercise ID
        
    Returns:
        Reference pose data including keypoints and angles
    """
    try:
        reference_pose = await exercise_service.get_reference_pose(exercise_id)
        if not reference_pose:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reference pose not found for this exercise"
            )
        
        return reference_pose
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching reference pose: {str(e)}"
        ) 