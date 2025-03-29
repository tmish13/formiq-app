"""Workout service implementation with exercise and plan management."""
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from fastapi import Depends

from app.core.database import get_db
from app.core.exceptions import (
    ValidationError,
    NotFoundException,
    AuthorizationError
)
from app.models.workout import Workout, Exercise, WorkoutPlan
from app.schemas.workout import (
    WorkoutCreate,
    WorkoutUpdate,
    WorkoutFilter,
    WorkoutResponse,
    ExerciseCreate,
    WorkoutPlanCreate
)
from app.repositories.workout_repository import WorkoutRepository
from app.services.base import BaseService
from app.core.logging import logger

class WorkoutService(BaseService[Workout, WorkoutCreate, WorkoutUpdate, WorkoutFilter]):
    """
    Workout service with exercise and plan management.
    
    Features:
    - Workout creation and management
    - Exercise tracking
    - Workout plan scheduling
    - Progress tracking
    - Search and filtering
    """
    
    def __init__(self):
        super().__init__(
            repository=WorkoutRepository,
            model=Workout,
            create_schema=WorkoutCreate,
            update_schema=WorkoutUpdate,
            filter_schema=WorkoutFilter
        )

    async def create_workout(
        self,
        db: Session = Depends(get_db),
        *,
        user_id: UUID,
        data: Dict[str, Any],
        exercises: List[ExerciseCreate]
    ) -> Workout:
        """
        Create a new workout with exercises.
        
        Args:
            db: Database session
            user_id: User's ID
            data: Workout data
            exercises: List of exercises
        """
        try:
            # Add user ID to data
            data["user_id"] = user_id
            
            # Create workout with exercises
            return await self.repository.create_with_exercises(
                db,
                workout_data=data,
                exercises=exercises
            )
        except Exception as e:
            logger.error("Error in workout creation", exc_info=e)
            raise

    async def update_workout(
        self,
        db: Session = Depends(get_db),
        *,
        workout_id: UUID,
        user_id: UUID,
        data: Dict[str, Any],
        exercises: Optional[List[ExerciseCreate]] = None
    ) -> Workout:
        """
        Update a workout and its exercises.
        
        Args:
            db: Database session
            workout_id: Workout ID
            user_id: User's ID
            data: Updated workout data
            exercises: Updated list of exercises
        """
        try:
            # Check authorization
            workout = await self.get(db, id=workout_id)
            if workout.user_id != user_id:
                raise AuthorizationError("Not authorized to update this workout")
            
            # Update workout with exercises
            return await self.repository.update_with_exercises(
                db,
                workout_id=workout_id,
                workout_data=data,
                exercises=exercises
            )
        except Exception as e:
            logger.error("Error in workout update", exc_info=e)
            raise

    async def get_user_workouts(
        self,
        db: Session = Depends(get_db),
        *,
        user_id: UUID,
        page: int = 1,
        per_page: int = 10,
        search: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Workout]:
        """
        Get user's workouts with filtering and search.
        
        Args:
            db: Database session
            user_id: User's ID
            page: Page number
            per_page: Items per page
            search: Search term
            start_date: Filter by start date
            end_date: Filter by end date
        """
        try:
            filters = {"user_id": user_id}
            if start_date:
                filters["created_at__gte"] = start_date
            if end_date:
                filters["created_at__lte"] = end_date
            
            if search:
                return await self.repository.search_workouts(
                    db,
                    user_id=user_id,
                    search=search,
                    page=page,
                    per_page=per_page
                )
            
            return await self.get_multi(
                db,
                filters=filters,
                page=page,
                per_page=per_page,
                order_by=[("created_at", "desc")]
            )
        except Exception as e:
            logger.error("Error getting user workouts", exc_info=e)
            raise

    async def create_workout_plan(
        self,
        db: Session = Depends(get_db),
        *,
        user_id: UUID,
        workout_id: UUID,
        data: WorkoutPlanCreate
    ) -> WorkoutPlan:
        """
        Create a workout plan.
        
        Args:
            db: Database session
            user_id: User's ID
            workout_id: Workout ID
            data: Plan data
        """
        try:
            # Check workout ownership
            workout = await self.get(db, id=workout_id)
            if workout.user_id != user_id:
                raise AuthorizationError("Not authorized to use this workout")
            
            # Create plan
            return await self.repository.create_plan(
                db,
                data={
                    **data.dict(),
                    "user_id": user_id,
                    "workout_id": workout_id
                }
            )
        except Exception as e:
            logger.error("Error in plan creation", exc_info=e)
            raise

    async def get_active_plans(
        self,
        db: Session = Depends(get_db),
        *,
        user_id: UUID
    ) -> List[WorkoutPlan]:
        """
        Get user's active workout plans.
        
        Args:
            db: Database session
            user_id: User's ID
        """
        try:
            return await self.repository.get_active_plans(db, user_id=user_id)
        except Exception as e:
            logger.error("Error getting active plans", exc_info=e)
            raise

    async def get_upcoming_workouts(
        self,
        db: Session = Depends(get_db),
        *,
        user_id: UUID,
        days: int = 7
    ) -> List[Dict[str, Any]]:
        """
        Get upcoming scheduled workouts.
        
        Args:
            db: Database session
            user_id: User's ID
            days: Number of days to look ahead
        """
        try:
            end_date = datetime.utcnow() + timedelta(days=days)
            return await self.repository.get_upcoming_workouts(
                db,
                user_id=user_id,
                end_date=end_date
            )
        except Exception as e:
            logger.error("Error getting upcoming workouts", exc_info=e)
            raise

    async def delete_workout(
        self,
        db: Session = Depends(get_db),
        *,
        workout_id: UUID,
        user_id: UUID
    ) -> None:
        """
        Delete a workout and its exercises.
        
        Args:
            db: Database session
            workout_id: Workout ID
            user_id: User's ID
        """
        try:
            # Check authorization
            workout = await self.get(db, id=workout_id)
            if workout.user_id != user_id:
                raise AuthorizationError("Not authorized to delete this workout")
            
            # Delete workout and related data
            await self.delete(db, id=workout_id)
        except Exception as e:
            logger.error("Error deleting workout", exc_info=e)
            raise

    async def track_progress(
        self,
        db: Session = Depends(get_db),
        *,
        user_id: UUID,
        exercise_name: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """
        Track progress for a specific exercise.
        
        Args:
            db: Database session
            user_id: User's ID
            exercise_name: Exercise name
            start_date: Start date
            end_date: End date
        """
        try:
            return await self.repository.get_exercise_progress(
                db,
                user_id=user_id,
                exercise_name=exercise_name,
                start_date=start_date,
                end_date=end_date
            )
        except Exception as e:
            logger.error("Error tracking progress", exc_info=e)
            raise 