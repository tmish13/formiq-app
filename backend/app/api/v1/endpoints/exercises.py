"""Exercises router module."""
from typing import Any, List, Optional, Dict
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from uuid import UUID

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
    description="Retrieves the reference pose data (keypoints, ideal angles for key phases) for the active configuration of a given exercise template. Used for displaying 'green reference' visual overlays."
)
async def get_reference_overlay_data(
    exercise_template_id: UUID,
    exercise_config_service: ExerciseConfigService = Depends(get_async_exercise_config_service)
):
    """
    Get reference visual overlay data for an exercise template.
    
    - Fetches the active ExerciseConfig for the given exercise_template_id.
    - Retrieves the reference_pose_data from that configuration.
    """
    try:
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
            # It's okay if reference_data is None/empty, means it's not defined for this config
            # Frontend should handle this gracefully (e.g., not show the overlay)
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