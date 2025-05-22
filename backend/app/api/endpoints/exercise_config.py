"""
API endpoints for exercise configurations.
"""
from typing import List, Dict, Any, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, Body, Path, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.repositories.exercise_config_repository import ExerciseConfigRepository
from app.schemas.exercise_config import (
    ExerciseConfigCreate,
    ExerciseConfigUpdate,
    ExerciseConfigInDB,
    ExerciseConfigWithExercise,
)

router = APIRouter()


@router.post("/", response_model=ExerciseConfigInDB, status_code=status.HTTP_201_CREATED)
def create_exercise_config(
    config_data: ExerciseConfigCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new exercise configuration.
    
    Args:
        config_data (ExerciseConfigCreate): Configuration data
        db (Session): Database session
        current_user (User): Current user
        
    Returns:
        ExerciseConfigInDB: Created configuration
    """
    # Check user permissions (admin-only operation)
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to create exercise configurations",
        )
    
    # Create the configuration
    return ExerciseConfigRepository.create(db, config_data)


@router.get("/{config_id}", response_model=ExerciseConfigWithExercise)
def get_exercise_config(
    config_id: UUID = Path(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get an exercise configuration by ID.
    
    Args:
        config_id (UUID): Configuration ID
        db (Session): Database session
        current_user (User): Current user
        
    Returns:
        ExerciseConfigWithExercise: Configuration with exercise details
    """
    config = ExerciseConfigRepository.get_with_exercise(db, config_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exercise configuration not found",
        )
    return config


@router.get("/", response_model=List[ExerciseConfigWithExercise])
def get_exercise_configs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    exercise_id: Optional[UUID] = Query(None),
    active_only: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get all exercise configurations, optionally filtered.
    
    Args:
        skip (int): Number of records to skip
        limit (int): Maximum number of records to return
        exercise_id (Optional[UUID]): Filter by exercise
        active_only (bool): Filter by active status
        db (Session): Database session
        current_user (User): Current user
        
    Returns:
        List[ExerciseConfigWithExercise]: List of configurations with exercise details
    """
    return ExerciseConfigRepository.get_all_with_exercise(
        db, skip=skip, limit=limit, exercise_id=exercise_id, active_only=active_only
    )


@router.get("/exercise/{exercise_id}/active", response_model=ExerciseConfigInDB)
def get_active_config_for_exercise(
    exercise_id: UUID = Path(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get the active configuration for an exercise.
    
    Args:
        exercise_id (UUID): Exercise ID
        db (Session): Database session
        current_user (User): Current user
        
    Returns:
        ExerciseConfigInDB: Active configuration
    """
    config = ExerciseConfigRepository.get_active_config_for_exercise(db, exercise_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active configuration found for this exercise",
        )
    return config


@router.put("/{config_id}", response_model=ExerciseConfigInDB)
def update_exercise_config(
    config_data: ExerciseConfigUpdate,
    config_id: UUID = Path(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update an exercise configuration.
    
    Args:
        config_data (ExerciseConfigUpdate): Update data
        config_id (UUID): Configuration ID
        db (Session): Database session
        current_user (User): Current user
        
    Returns:
        ExerciseConfigInDB: Updated configuration
    """
    # Check user permissions (admin-only operation)
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to update exercise configurations",
        )
    
    config = ExerciseConfigRepository.update(db, config_id, config_data)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exercise configuration not found",
        )
    return config


@router.post("/exercise/{exercise_id}/new_version", response_model=ExerciseConfigInDB)
def create_new_version(
    config_data: ExerciseConfigCreate,
    exercise_id: UUID = Path(...),
    deactivate_previous: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new version of an exercise configuration.
    
    Args:
        config_data (ExerciseConfigCreate): Configuration data
        exercise_id (UUID): Exercise ID
        deactivate_previous (bool): Whether to deactivate previous versions
        db (Session): Database session
        current_user (User): Current user
        
    Returns:
        ExerciseConfigInDB: Created configuration
    """
    # Check user permissions (admin-only operation)
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to create exercise configurations",
        )
    
    # Create new version of the configuration
    config_data.exercise_id = exercise_id  # Ensure the exercise ID matches the path parameter
    return ExerciseConfigRepository.create_new_version(
        db, exercise_id, config_data, deactivate_previous
    )


@router.delete("/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_exercise_config(
    config_id: UUID = Path(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete an exercise configuration.
    
    Args:
        config_id (UUID): Configuration ID
        db (Session): Database session
        current_user (User): Current user
    """
    # Check user permissions (admin-only operation)
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to delete exercise configurations",
        )
    
    success = ExerciseConfigRepository.delete(db, config_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exercise configuration not found",
        ) 