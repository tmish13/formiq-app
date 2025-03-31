"""Exercises router module."""
from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_active_user, get_db
from app.repositories.exercise_repository import ExerciseRepository
from app.schemas.exercise import Exercise, ExerciseCreate, ExerciseUpdate

router = APIRouter()


@router.get("/", response_model=List[Exercise])
def read_exercises(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: Any = Depends(get_current_active_user),
) -> Any:
    """Get exercises."""
    exercise_repository = ExerciseRepository(db)
    exercises = exercise_repository.get_multi(skip=skip, limit=limit)
    return exercises


@router.post("/", response_model=Exercise)
def create_exercise(
    *,
    db: Session = Depends(get_db),
    exercise_in: ExerciseCreate,
    current_user: Any = Depends(get_current_active_user),
) -> Any:
    """Create exercise."""
    exercise_repository = ExerciseRepository(db)
    exercise = exercise_repository.get_by_name(name=exercise_in.name)
    if exercise:
        raise HTTPException(
            status_code=400,
            detail="The exercise with this name already exists in the system.",
        )
    exercise = exercise_repository.create(obj_in=exercise_in.dict())
    return exercise


@router.get("/{exercise_id}", response_model=Exercise)
def read_exercise(
    *,
    db: Session = Depends(get_db),
    exercise_id: int,
    current_user: Any = Depends(get_current_active_user),
) -> Any:
    """Get exercise by ID."""
    exercise_repository = ExerciseRepository(db)
    exercise = exercise_repository.get(id=exercise_id)
    if not exercise:
        raise HTTPException(
            status_code=404,
            detail="The exercise with this id does not exist in the system",
        )
    return exercise


@router.put("/{exercise_id}", response_model=Exercise)
def update_exercise(
    *,
    db: Session = Depends(get_db),
    exercise_id: int,
    exercise_in: ExerciseUpdate,
    current_user: Any = Depends(get_current_active_user),
) -> Any:
    """Update exercise."""
    exercise_repository = ExerciseRepository(db)
    exercise = exercise_repository.get(id=exercise_id)
    if not exercise:
        raise HTTPException(
            status_code=404,
            detail="The exercise with this id does not exist in the system",
        )
    exercise = exercise_repository.update(db_obj=exercise, obj_in=exercise_in.dict(exclude_unset=True))
    return exercise


@router.delete("/{exercise_id}", response_model=Exercise)
def delete_exercise(
    *,
    db: Session = Depends(get_db),
    exercise_id: int,
    current_user: Any = Depends(get_current_active_user),
) -> Any:
    """Delete exercise."""
    exercise_repository = ExerciseRepository(db)
    exercise = exercise_repository.get(id=exercise_id)
    if not exercise:
        raise HTTPException(
            status_code=404,
            detail="The exercise with this id does not exist in the system",
        )
    exercise = exercise_repository.delete(id=exercise_id)
    return exercise 