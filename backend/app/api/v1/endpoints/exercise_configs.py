"""Exercise configuration endpoints for managing exercise settings and parameters."""

from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List, Optional
from uuid import UUID

from app.api import deps
from app.models.user import User
from app.services.exercise_config_service import ExerciseConfigService, get_async_exercise_config_service
from app.core.logging import get_logger
from app.core.exceptions import NotFoundException

# Initialize logger
logger = get_logger(__name__)

# Initialize router
router = APIRouter(prefix="/exercise-configs", tags=["exercise-configs"])


@router.get("/", response_model=List[Dict[str, Any]])
async def list_exercise_configs(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: User = Depends(deps.get_current_user),
    exercise_config_service: ExerciseConfigService = Depends(get_async_exercise_config_service),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    exercise_id: Optional[str] = Query(None, description="Filter by exercise ID")
) -> List[Dict[str, Any]]:
    """
    List all exercise configurations.
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        exercise_id: Optional filter by exercise ID
        
    Returns:
        List of exercise configurations
    """
    try:
        # Get all configs or filter by exercise
        if exercise_id:
            configs = await exercise_config_service.get_configs_by_exercise_async(
                exercise_id=UUID(exercise_id)
            )
        else:
            configs = await exercise_config_service.get_all_configs_async(
                skip=skip,
                limit=limit
            )
        
        # Convert to response format
        config_list = []
        for config in configs:
            config_dict = {
                "id": str(config.id),
                "exercise_id": str(config.exercise_id),
                "name": config.name or f"Config for {config.exercise_id}",
                "difficulty_level": getattr(config, 'difficulty_level', 'medium'),
                "target_reps": getattr(config, 'target_reps', 10),
                "target_sets": getattr(config, 'target_sets', 3),
                "form_criteria": config.form_criteria or {},
                "is_active": getattr(config, 'is_active', True),
                "created_at": config.created_at.isoformat() if hasattr(config, 'created_at') else None,
                "updated_at": config.updated_at.isoformat() if hasattr(config, 'updated_at') else None
            }
            config_list.append(config_dict)
        
        return config_list
        
    except Exception as e:
        logger.error(f"Error listing exercise configs: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing exercise configs: {str(e)}"
        )


@router.get("/{config_id}", response_model=Dict[str, Any])
async def get_exercise_config(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: User = Depends(deps.get_current_user),
    exercise_config_service: ExerciseConfigService = Depends(get_async_exercise_config_service),
    config_id: UUID = Path(...)
) -> Dict[str, Any]:
    """
    Get specific exercise configuration by ID.
    
    Args:
        config_id: Exercise configuration ID
        
    Returns:
        Exercise configuration details
    """
    try:
        config = await exercise_config_service.get_config_by_id_async(config_id)
        
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Exercise configuration not found"
            )
        
        return {
            "id": str(config.id),
            "exercise_id": str(config.exercise_id),
            "name": config.name or f"Config for {config.exercise_id}",
            "difficulty_level": getattr(config, 'difficulty_level', 'medium'),
            "target_reps": getattr(config, 'target_reps', 10),
            "target_sets": getattr(config, 'target_sets', 3),
            "form_criteria": config.form_criteria or {},
            "is_active": getattr(config, 'is_active', True),
            "created_at": config.created_at.isoformat() if hasattr(config, 'created_at') else None,
            "updated_at": config.updated_at.isoformat() if hasattr(config, 'updated_at') else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting exercise config: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting exercise config: {str(e)}"
        )


@router.get("/exercise/{exercise_id}", response_model=List[Dict[str, Any]])
async def get_configs_by_exercise(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: User = Depends(deps.get_current_user),
    exercise_config_service: ExerciseConfigService = Depends(get_async_exercise_config_service),
    exercise_id: UUID = Path(...)
) -> List[Dict[str, Any]]:
    """
    Get all configurations for a specific exercise.
    
    Args:
        exercise_id: Exercise ID
        
    Returns:
        List of configurations for the exercise
    """
    try:
        configs = await exercise_config_service.get_configs_by_exercise_async(exercise_id)
        
        config_list = []
        for config in configs:
            config_dict = {
                "id": str(config.id),
                "exercise_id": str(config.exercise_id),
                "name": config.name or f"Config for {config.exercise_id}",
                "difficulty_level": getattr(config, 'difficulty_level', 'medium'),
                "target_reps": getattr(config, 'target_reps', 10),
                "target_sets": getattr(config, 'target_sets', 3),
                "form_criteria": config.form_criteria or {},
                "is_active": getattr(config, 'is_active', True),
                "created_at": config.created_at.isoformat() if hasattr(config, 'created_at') else None,
                "updated_at": config.updated_at.isoformat() if hasattr(config, 'updated_at') else None
            }
            config_list.append(config_dict)
        
        return config_list
        
    except Exception as e:
        logger.error(f"Error getting configs by exercise: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting configs by exercise: {str(e)}"
        )


@router.get("/exercise/{exercise_id}/active", response_model=Dict[str, Any])
async def get_active_config_by_exercise(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: User = Depends(deps.get_current_user),
    exercise_config_service: ExerciseConfigService = Depends(get_async_exercise_config_service),
    exercise_id: UUID = Path(...)
) -> Dict[str, Any]:
    """
    Get the active configuration for a specific exercise.
    
    Args:
        exercise_id: Exercise ID
        
    Returns:
        Active configuration for the exercise
    """
    try:
        config = await exercise_config_service.get_active_config_for_exercise_async(exercise_id)
        
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active configuration found for this exercise"
            )
        
        return {
            "id": str(config.id),
            "exercise_id": str(config.exercise_id),
            "name": config.name or f"Config for {config.exercise_id}",
            "difficulty_level": getattr(config, 'difficulty_level', 'medium'),
            "target_reps": getattr(config, 'target_reps', 10),
            "target_sets": getattr(config, 'target_sets', 3),
            "form_criteria": config.form_criteria or {},
            "is_active": getattr(config, 'is_active', True),
            "created_at": config.created_at.isoformat() if hasattr(config, 'created_at') else None,
            "updated_at": config.updated_at.isoformat() if hasattr(config, 'updated_at') else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting active config: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting active config: {str(e)}"
        )


@router.post("/", response_model=Dict[str, Any])
async def create_exercise_config(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: User = Depends(deps.get_current_user),
    exercise_config_service: ExerciseConfigService = Depends(get_async_exercise_config_service),
    config_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Create a new exercise configuration.
    
    Args:
        config_data: Configuration data
        
    Returns:
        Created configuration
    """
    try:
        # Validate required fields
        if 'exercise_id' not in config_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="exercise_id is required"
            )
        
        # Create the configuration
        config = await exercise_config_service.create_config_async(
            exercise_id=UUID(config_data['exercise_id']),
            name=config_data.get('name'),
            difficulty_level=config_data.get('difficulty_level', 'medium'),
            target_reps=config_data.get('target_reps', 10),
            target_sets=config_data.get('target_sets', 3),
            form_criteria=config_data.get('form_criteria', {}),
            is_active=config_data.get('is_active', True)
        )
        
        return {
            "id": str(config.id),
            "exercise_id": str(config.exercise_id),
            "name": config.name or f"Config for {config.exercise_id}",
            "difficulty_level": getattr(config, 'difficulty_level', 'medium'),
            "target_reps": getattr(config, 'target_reps', 10),
            "target_sets": getattr(config, 'target_sets', 3),
            "form_criteria": config.form_criteria or {},
            "is_active": getattr(config, 'is_active', True),
            "created_at": config.created_at.isoformat() if hasattr(config, 'created_at') else None,
            "updated_at": config.updated_at.isoformat() if hasattr(config, 'updated_at') else None
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid data: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error creating exercise config: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating exercise config: {str(e)}"
        )


@router.put("/{config_id}", response_model=Dict[str, Any])
async def update_exercise_config(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: User = Depends(deps.get_current_user),
    exercise_config_service: ExerciseConfigService = Depends(get_async_exercise_config_service),
    config_id: UUID = Path(...),
    config_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Update an existing exercise configuration.
    
    Args:
        config_id: Configuration ID
        config_data: Updated configuration data
        
    Returns:
        Updated configuration
    """
    try:
        # Update the configuration
        config = await exercise_config_service.update_config_async(
            config_id=config_id,
            update_data=config_data
        )
        
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Exercise configuration not found"
            )
        
        return {
            "id": str(config.id),
            "exercise_id": str(config.exercise_id),
            "name": config.name or f"Config for {config.exercise_id}",
            "difficulty_level": getattr(config, 'difficulty_level', 'medium'),
            "target_reps": getattr(config, 'target_reps', 10),
            "target_sets": getattr(config, 'target_sets', 3),
            "form_criteria": config.form_criteria or {},
            "is_active": getattr(config, 'is_active', True),
            "created_at": config.created_at.isoformat() if hasattr(config, 'created_at') else None,
            "updated_at": config.updated_at.isoformat() if hasattr(config, 'updated_at') else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating exercise config: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating exercise config: {str(e)}"
        )


@router.delete("/{config_id}", response_model=Dict[str, str])
async def delete_exercise_config(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: User = Depends(deps.get_current_user),
    exercise_config_service: ExerciseConfigService = Depends(get_async_exercise_config_service),
    config_id: UUID = Path(...)
) -> Dict[str, str]:
    """
    Delete an exercise configuration.
    
    Args:
        config_id: Configuration ID to delete
        
    Returns:
        Deletion confirmation message
    """
    try:
        success = await exercise_config_service.delete_config_async(config_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Exercise configuration not found"
            )
        
        return {"message": "Exercise configuration deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting exercise config: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting exercise config: {str(e)}"
        )