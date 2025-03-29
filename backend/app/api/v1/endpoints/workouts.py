"""Workout endpoints."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.api.deps import (
    get_db,
    get_current_user,
    check_subscription_tier,
    validate_workout_access
)
from app.models.enums import SubscriptionTier
from app.schemas.workout import (
    WorkoutCreate,
    WorkoutUpdate,
    WorkoutResponse,
    ExerciseCreate,
    WorkoutPlanCreate,
    WorkoutPlanResponse,
    ExerciseProgressResponse
)
from app.services.workout_service import WorkoutService
from datetime import datetime

router = APIRouter()

@router.post("/", response_model=WorkoutResponse)
async def create_workout(
    *,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    workout: WorkoutCreate,
    exercises: List[ExerciseCreate]
) -> WorkoutResponse:
    """Create a new workout."""
    # Check subscription tier
    await check_subscription_tier(SubscriptionTier.BASIC, db, current_user)
    
    workout_service = WorkoutService()
    return await workout_service.create_workout(
        db,
        user_id=current_user.id,
        data=workout.dict(),
        exercises=exercises
    )

@router.get("/", response_model=List[WorkoutResponse])
async def get_workouts(
    *,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    page: int = Query(1, gt=0),
    per_page: int = Query(10, gt=0, le=100),
    search: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> List[WorkoutResponse]:
    """Get user's workouts."""
    workout_service = WorkoutService()
    return await workout_service.get_user_workouts(
        db,
        user_id=current_user.id,
        page=page,
        per_page=per_page,
        search=search,
        start_date=start_date,
        end_date=end_date
    )

@router.get("/{workout_id}", response_model=WorkoutResponse)
async def get_workout(
    *,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    workout_id: str
) -> WorkoutResponse:
    """Get a specific workout."""
    await validate_workout_access(workout_id, db, current_user)
    
    workout_service = WorkoutService()
    return await workout_service.get(db, id=workout_id)

@router.put("/{workout_id}", response_model=WorkoutResponse)
async def update_workout(
    *,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    workout_id: str,
    workout: WorkoutUpdate,
    exercises: Optional[List[ExerciseCreate]] = None
) -> WorkoutResponse:
    """Update a workout."""
    await validate_workout_access(workout_id, db, current_user)
    
    workout_service = WorkoutService()
    return await workout_service.update_workout(
        db,
        workout_id=workout_id,
        user_id=current_user.id,
        data=workout.dict(exclude_unset=True),
        exercises=exercises
    )

@router.delete("/{workout_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workout(
    *,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    workout_id: str
) -> None:
    """Delete a workout."""
    await validate_workout_access(workout_id, db, current_user)
    
    workout_service = WorkoutService()
    await workout_service.delete_workout(
        db,
        workout_id=workout_id,
        user_id=current_user.id
    )

@router.post("/{workout_id}/plan", response_model=WorkoutPlanResponse)
async def create_workout_plan(
    *,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    workout_id: str,
    plan: WorkoutPlanCreate
) -> WorkoutPlanResponse:
    """Create a workout plan."""
    # Check subscription tier
    await check_subscription_tier(SubscriptionTier.PRO, db, current_user)
    await validate_workout_access(workout_id, db, current_user)
    
    workout_service = WorkoutService()
    return await workout_service.create_workout_plan(
        db,
        user_id=current_user.id,
        workout_id=workout_id,
        data=plan
    )

@router.get("/plans/active", response_model=List[WorkoutPlanResponse])
async def get_active_plans(
    *,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
) -> List[WorkoutPlanResponse]:
    """Get user's active workout plans."""
    workout_service = WorkoutService()
    return await workout_service.get_active_plans(
        db,
        user_id=current_user.id
    )

@router.get("/plans/upcoming", response_model=List[WorkoutPlanResponse])
async def get_upcoming_workouts(
    *,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    days: int = Query(7, gt=0, le=30)
) -> List[WorkoutPlanResponse]:
    """Get upcoming scheduled workouts."""
    workout_service = WorkoutService()
    return await workout_service.get_upcoming_workouts(
        db,
        user_id=current_user.id,
        days=days
    )

@router.get("/progress/{exercise_name}", response_model=List[ExerciseProgressResponse])
async def track_exercise_progress(
    *,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    exercise_name: str,
    start_date: datetime,
    end_date: datetime
) -> List[ExerciseProgressResponse]:
    """Track progress for a specific exercise."""
    # Check subscription tier
    await check_subscription_tier(SubscriptionTier.PRO, db, current_user)
    
    workout_service = WorkoutService()
    return await workout_service.track_progress(
        db,
        user_id=current_user.id,
        exercise_name=exercise_name,
        start_date=start_date,
        end_date=end_date
    ) 