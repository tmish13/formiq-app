"""Workout endpoints."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import (
    get_async_db,
    get_current_active_user,
    get_async_progress_service
)
from app.core.deps import check_subscription_tier
from app.models.user import User
from app.models.workout import Workout
from app.models.enums import SubscriptionTier
from app.schemas.workout import (
    WorkoutCreate,
    WorkoutUpdate,
    WorkoutRead,
    WorkoutWithExercises,
    ExerciseCreate,
    WorkoutPlanCreate,
    WorkoutPlanUpdate,
    WorkoutPlanRead,
    WorkoutPlanWithExercises,
    ExerciseProgressResponse,
    WorkoutShare,
    WorkoutShareResponse,
)
from app.schemas.exercise import (
    ExerciseProgressCreate,
    ExerciseSetCreate,
    ExerciseSetUpdate,
    ExerciseSetResponse,
)
from app.services.workout_service import WorkoutService, get_async_workout_service
from app.services.progress_service import ProgressService
from datetime import date, timedelta

# Inline utility function for generating next workout date
def generate_next_workout_date(frequency_days: int, last_workout_date: date) -> date:
    """Generate the next workout date based on frequency."""
    return last_workout_date + timedelta(days=frequency_days)

# Dependency factory for subscription tier checking
def require_subscription_tier(required_tiers: List[str]):
    """Create a dependency that checks if user has one of the required subscription tiers."""
    async def _check_tier(current_user: User = Depends(get_current_active_user)) -> None:
        user_tier = current_user.subscription_tier.value if current_user.subscription_tier else SubscriptionTier.FREE.value
        if user_tier not in required_tiers and user_tier.upper() not in required_tiers:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This feature requires one of these subscription tiers: {', '.join(required_tiers)}"
            )
    return _check_tier

router = APIRouter()

# Local dependency function
async def validate_workout_access(
    workout_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db)
) -> Workout:
    """Validate that the current user has access to the specified workout."""
    from sqlalchemy import select
    
    stmt = select(Workout).where(
        Workout.id == workout_id,
        Workout.user_id == current_user.id
    )
    result = await db.execute(stmt)
    workout = result.scalars().first()
    
    if not workout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout not found or access denied"
        )
    return workout

@router.post("/", response_model=WorkoutRead, status_code=status.HTTP_201_CREATED)
async def create_workout(
    *,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    workout_in: WorkoutCreate,
    workout_service: WorkoutService = Depends(get_async_workout_service),
    _: None = Depends(require_subscription_tier(["STANDARD", "PREMIUM"]))
) -> WorkoutRead:
    """Create a new workout."""
    workout = await workout_service.create_workout_async(
        user_id=current_user.id,
        data=workout_in
    )
    return workout

@router.get("/", response_model=List[WorkoutRead])
async def get_workouts(
    *,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    skip: int = 0,
    limit: int = 100,
    workout_service: WorkoutService = Depends(get_async_workout_service)
) -> List[WorkoutRead]:
    """Get user's workouts."""
    workouts = await workout_service.get_user_workouts_async(
        user_id=current_user.id,
        skip=skip,
        limit=limit
    )
    return workouts

@router.get("/upcoming", response_model=List[WorkoutRead])
async def get_upcoming_workouts(
    *,\
    db: AsyncSession = Depends(get_async_db), 
    current_user: User = Depends(get_current_active_user),\
    workout_service: WorkoutService = Depends(get_async_workout_service),\
) -> List[WorkoutRead]: 
    """Get upcoming scheduled workouts for the next 7 days."""
    today = date.today()
    end_date = today + timedelta(days=7)
    upcoming_workouts = await workout_service.get_upcoming_planned_workouts_async(
        user_id=current_user.id, start_date=today, end_date=end_date
    )
    return upcoming_workouts

@router.get("/{workout_id}", response_model=WorkoutWithExercises)
async def get_workout(
    *,
    workout_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    workout_service: WorkoutService = Depends(get_async_workout_service)
) -> WorkoutWithExercises:
    """Get a specific workout."""
    workout = await workout_service.get_workout_details_async(
        workout_id=workout_id, user_id=current_user.id
    )
    if not workout:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workout not found")
    return workout

@router.put("/{workout_id}", response_model=WorkoutRead)
async def update_workout(
    *,
    workout_id: int,
    workout_in: WorkoutUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    workout_service: WorkoutService = Depends(get_async_workout_service)
) -> WorkoutRead:
    """Update a workout."""
    updated_workout = await workout_service.update_workout_async(
        workout_id=workout_id,
        user_id=current_user.id,
        data=workout_in
    )
    return updated_workout

@router.delete("/{workout_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workout(
    *,
    workout_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    workout_service: WorkoutService = Depends(get_async_workout_service)
) -> None:
    """Delete a workout."""
    await workout_service.delete_workout_async(
        workout_id=workout_id,
        user_id=current_user.id
    )

@router.post("/plans/", response_model=WorkoutPlanRead, status_code=status.HTTP_201_CREATED)
async def create_workout_plan(
    *,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    plan_in: WorkoutPlanCreate,
    workout_service: WorkoutService = Depends(get_async_workout_service),
    _: None = Depends(require_subscription_tier(["PREMIUM"]))
) -> WorkoutPlanRead:
    """Create a workout plan."""
    plan = await workout_service.create_workout_plan_async(
        user_id=current_user.id,
        data=plan_in
    )
    return plan

@router.get("/plans/", response_model=List[WorkoutPlanRead])
async def list_workout_plans(
    *,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    workout_service: WorkoutService = Depends(get_async_workout_service),
    skip: int = 0,
    limit: int = 100
) -> List[WorkoutPlanRead]:
    """Get user's workout plans."""
    plans = await workout_service.get_user_workout_plans_async(
        user_id=current_user.id,
        skip=skip,
        limit=limit
    )
    return plans

@router.get("/plans/{plan_id}", response_model=WorkoutPlanWithExercises)
async def get_workout_plan(
    *,
    plan_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    workout_service: WorkoutService = Depends(get_async_workout_service)
) -> WorkoutPlanWithExercises:
    """Get a specific workout plan."""
    plan = await workout_service.get_workout_plan_with_workouts_async(
        plan_id=plan_id, user_id=current_user.id
    )
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workout plan not found or access denied")
    return plan

@router.put("/plans/{plan_id}", response_model=WorkoutPlanRead)
async def update_workout_plan(
    *,
    plan_id: int,
    plan_in: WorkoutPlanUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    workout_service: WorkoutService = Depends(get_async_workout_service)
) -> WorkoutPlanRead:
    """Update a workout plan."""
    updated_plan = await workout_service.update_workout_plan_async(
        plan_id=plan_id,
        data=plan_in,
        user_id=current_user.id
    )
    if not updated_plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workout plan not found or access denied for update")
    return updated_plan

@router.delete("/plans/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workout_plan(
    *,
    plan_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    workout_service: WorkoutService = Depends(get_async_workout_service)
) -> None:
    """Delete a workout plan."""
    success = await workout_service.delete_workout_plan_async(
        plan_id=plan_id, user_id=current_user.id
    )
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workout plan not found or not authorized to delete")

@router.get("/progress/{exercise_name}", response_model=List[ExerciseProgressResponse])
async def track_exercise_progress(
    *,
    exercise_name: str,
    start_date: Optional[date] = Query(None, description="Start date for progress query (Note: server-side filtering by date range not fully implemented via time_range)"),
    end_date: Optional[date] = Query(None, description="End date for progress query (Note: server-side filtering by date range not fully implemented via time_range)"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    progress_service: ProgressService = Depends(get_async_progress_service),
    _: None = Depends(require_subscription_tier(["STANDARD", "PREMIUM"]))
) -> List[ExerciseProgressResponse]:
    """Track progress for a specific exercise.
    Note: The service currently accepts a 'time_range' (e.g., last 30 days) rather than specific start/end dates.
    This endpoint currently fetches all progress for the exercise type and does not apply server-side date filtering based on start_date/end_date.
    """
    time_range_to_pass: Optional[timedelta] = None

    progress_data = await progress_service.get_progress_async(
        user_id=current_user.id,
        exercise_type=exercise_name,
        time_range=time_range_to_pass
    )
    
    if not progress_data and progress_data != []:
        return []
        
    return progress_data

@router.post(
    "/progress/",
    response_model=ExerciseProgressResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_subscription_tier(["STANDARD", "PREMIUM"]))],
)
async def log_exercise_progress(
    *,
    progress_in: ExerciseProgressCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    progress_service: ProgressService = Depends(get_async_progress_service),
) -> ExerciseProgressResponse:
    """Log new exercise progress. Requires STANDARD or PREMIUM subscription."""
    if not hasattr(progress_in, 'exercise_name') or not hasattr(progress_in, 'metrics'):
        raise HTTPException(status_code=400, detail="Payload must include exercise_name and metrics.")

    created_progress = await progress_service.update_progress_async(
        user_id=current_user.id,
        exercise_type=progress_in.exercise_name,
        metrics=progress_in.metrics,
    )
    return created_progress

@router.get(
    "/plans/{plan_id}/next-workout-date",
    response_model=date,
)
async def get_next_workout_date_for_plan(
    plan_id: int,
    last_workout_date: Optional[date] = Query(None, description="Date of the last completed workout for this plan. If None, assumes plan just started."),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    workout_service: WorkoutService = Depends(get_async_workout_service),
) -> date:
    """Calculates the next workout date for a given plan."""
    plan = await workout_service.get_workout_plan_async(plan_id=plan_id, user_id=current_user.id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workout plan not found or access denied.")

    if not plan.frequency_days or plan.frequency_days <= 0:
        raise HTTPException(status_code=status.HTTP_400, detail="Workout plan has invalid frequency.")

    base_date = last_workout_date if last_workout_date else plan.start_date if hasattr(plan, 'start_date') and plan.start_date else date.today()

    next_date = generate_next_workout_date(
        frequency_days=plan.frequency_days, 
        last_workout_date=base_date
    )
    return next_date

# --- Exercise Set Endpoints ---

@router.post(
    "/{workout_id}/exercises/{exercise_id}/sets",
    response_model=ExerciseSetResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add an exercise set to a workout's exercise",
    description="Adds a new set to a specific exercise within a workout. Ensures user has access to the workout.",
    # Note: Workout access validation is handled inside the service method
)
async def add_exercise_set_to_workout_exercise(
    *,
    workout_id: int, # Used by validate_workout_access
    exercise_id: int, # Specific exercise within the workout
    set_data: ExerciseSetCreate,
    db: AsyncSession = Depends(get_async_db), # Ensure db session is available
    current_user: User = Depends(get_current_active_user), # For logging or if service needs user context beyond ownership
    workout_service: WorkoutService = Depends(get_async_workout_service),
) -> ExerciseSetResponse:
    """Add an exercise set to a specific exercise within a workout.
    The `validate_workout_access` dependency ensures the user owns the workout.
    The service method `add_exercise_set_async` should handle associating the set
    with the correct exercise_id that is part of the workout_id.
    """
    # The service method will need to confirm that exercise_id is valid for the given workout_id.
    exercise_set = await workout_service.add_exercise_set_async(
        workout_id=workout_id, 
        exercise_id=exercise_id, 
        user_id=current_user.id, # For service-side validation of exercise within user's workout
        set_data=set_data
    )
    # If service raises error for invalid exercise_id for workout, it will be caught by FastAPI.
    # If it returns None for a non-error case (e.g. exercise not found in workout), handle here.
    if not exercise_set:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Failed to add exercise set. Exercise may not be part of the specified workout."
        )
    return exercise_set


@router.put(
    "/exercises/sets/{set_id}",
    response_model=ExerciseSetResponse,
    summary="Update an exercise set",
    description="Updates details of an existing exercise set. User must own the workout the set belongs to.",
)
async def update_exercise_set(
    *,
    set_id: int,
    set_data: ExerciseSetUpdate,
    db: AsyncSession = Depends(get_async_db), # Ensure db session is available
    current_user: User = Depends(get_current_active_user), # For ownership check via service
    workout_service: WorkoutService = Depends(get_async_workout_service),
) -> ExerciseSetResponse:
    """Update an existing exercise set.
    The service method `update_exercise_set_async` must verify that the set_id
    belongs to the current_user before performing the update.
    """
    updated_set = await workout_service.update_exercise_set_async(
        set_id=set_id, 
        set_data=set_data, 
        user_id=current_user.id # Service uses this to verify ownership
    )
    if not updated_set:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Exercise set not found or user not authorized to update."
        )
    return updated_set


@router.delete(
    "/exercises/sets/{set_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an exercise set",
    description="Deletes an existing exercise set. User must own the workout the set belongs to.",
)
async def delete_exercise_set(
    *,
    set_id: int,
    db: AsyncSession = Depends(get_async_db), # Ensure db session is available
    current_user: User = Depends(get_current_active_user), # For ownership check via service
    workout_service: WorkoutService = Depends(get_async_workout_service),
) -> None:
    """Delete an existing exercise set.
    The service method `delete_exercise_set_async` must verify that the set_id
    belongs to the current_user before performing the deletion.
    """
    success = await workout_service.delete_exercise_set_async(
        set_id=set_id, 
        user_id=current_user.id # Service uses this to verify ownership
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Exercise set not found or user not authorized to delete."
        )
    # No content returned for 204
    return None

@router.post(
    "/{workout_id}/share",
    response_model=WorkoutShareResponse,
    summary="Share a workout",
    description="Shares a workout with another user via email.",
    # Note: Workout access validation is handled inside the service method
)
async def share_workout(
    *,
    workout_id: int,
    share_data: WorkoutShare,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    workout_service: WorkoutService = Depends(get_async_workout_service),
) -> WorkoutShareResponse:
    """
    Share a workout with another user.
    """
    share_response = await workout_service.share_workout_async(
        workout_id=workout_id,
        share_with_email=share_data.share_with_email,
        sharer_user_id=current_user.id,
    )
    if not share_response: 
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workout not found or sharing failed")
    return share_response