"""Workout service implementation with exercise and plan management."""
from typing import Optional, List, Dict, Any, Union
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, and_, or_
from fastapi import Depends

from app.core.database import get_db
from app.core.exceptions import (
    ValidationError,
    NotFoundException,
    AuthorizationError
)
from app.core.config import Settings
from app.models.workout import Workout, Exercise, WorkoutPlan
from app.schemas.workout import (
    WorkoutCreate,
    WorkoutUpdate,
    Workout,
    ExerciseCreate,
    WorkoutPlanCreate,
    WorkoutPlan
)
from app.services.base_service import BaseService
from app.core.logging import logger

class WorkoutService(BaseService[Workout, WorkoutCreate, WorkoutUpdate]):
    """
    Workout service with exercise and plan management.
    
    Features:
    - Workout creation and management
    - Exercise tracking
    - Workout plan scheduling
    - Progress tracking
    - Search and filtering
    """
    
    def __init__(self, db: Union[AsyncSession, Session], app_settings: Settings):
        super().__init__(db=db, settings=app_settings, model=Workout)

    async def create_workout_async(
        self,
        user_id: UUID,
        workout_data_in: WorkoutCreate,
        exercises_in: List[ExerciseCreate]
    ) -> Workout:
        """Create a new workout with exercises asynchronously in a single transaction."""
        try:
            workout_dict = workout_data_in.model_dump()
            workout_dict["user_id"] = user_id
            
            # Manual creation for single transaction for Workout + Exercises
            workout_obj = Workout(**workout_dict) # Create SQLAlchemy model instance
            self.db.add(workout_obj)
            # Must flush here to get workout_obj.id for exercises if workout_obj.id is DB-generated (e.g. autoincrement int)
            # If Workout.id is a client-generated UUID, flush might be deferrable until before commit.
            # Assuming Workout.id is set (e.g. default=uuid4 in model), we might not need pre-flush for ID.
            # However, to be safe for FK constraints, flushing before adding dependent objects is good.
            await self.db.flush() 
            
            created_exercises_objs = []
            for ex_in in exercises_in:
                ex_dict = ex_in.model_dump()
                ex_dict["workout_id"] = workout_obj.id # Use the ID from the flushed workout_obj
                exercise_obj = Exercise(**ex_dict)
                self.db.add(exercise_obj)
                created_exercises_objs.append(exercise_obj)
            
            await self.db.commit() # Single commit for workout and all exercises
            
            # Refresh parent and children to get all DB state (like loaded relationships)
            await self.db.refresh(workout_obj)
            for ex_obj in created_exercises_objs:
                await self.db.refresh(ex_obj) # Refresh each exercise

            # After commit and refresh, relationships should be populated if configured in models.
            # To be absolutely sure WorkoutResponse has exercises, explicitly load them if necessary,
            # though refresh with proper relationship setup should handle it.
            # For safety, an explicit load before returning the response schema:
            stmt_workout = select(Workout).options(selectinload(Workout.exercises)).where(Workout.id == workout_obj.id)
            refreshed_workout_with_exercises = (await self.db.execute(stmt_workout)).scalars().first()
            
            if not refreshed_workout_with_exercises:
                # This should not happen if commit succeeded
                raise Exception("Failed to retrieve workout after creation")

            return Workout.from_orm(refreshed_workout_with_exercises)

        except Exception as e:
            await self.db.rollback() # Ensure rollback on any error during the process
            logger.error(f"Error in workout creation for user {user_id}: {str(e)}", exc_info=True)
            raise

    async def update_workout_async(
        self,
        workout_id: UUID,
        user_id: UUID,
        workout_data_in: WorkoutUpdate,
        exercises_in: Optional[List[ExerciseCreate]] = None
    ) -> Workout:
        """Update a workout and its exercises asynchronously."""
        workout = await super().get_async(id=workout_id, options=[selectinload(Workout.exercises)])
        if not workout:
            raise NotFoundException("Workout not found")
        if workout.user_id != user_id:
            raise AuthorizationError("Not authorized to update this workout")

        # Update workout fields using BaseService
        updated_workout = await super().update_async(db_obj=workout, obj_in=workout_data_in)

        if exercises_in is not None:
            # Delete existing exercises
            for existing_exercise in updated_workout.exercises:
                await self.db.delete(existing_exercise)
            await self.db.flush()

            # Create new exercises
            new_exercise_objs = []
            for ex_in in exercises_in:
                ex_dict = ex_in.model_dump()
                ex_dict["workout_id"] = updated_workout.id
                exercise_obj = Exercise(**ex_dict)
                self.db.add(exercise_obj)
                new_exercise_objs.append(exercise_obj)
            await self.db.flush()
            for ex_obj in new_exercise_objs:
                await self.db.refresh(ex_obj)
        
        await self.db.refresh(updated_workout)
        # Manually reload exercises to be sure they are current after operations
        stmt = select(Workout).options(selectinload(Workout.exercises)).where(Workout.id == updated_workout.id)
        final_workout = (await self.db.execute(stmt)).scalars().first()

        return Workout.from_orm(final_workout if final_workout else updated_workout)

    async def get_user_workouts_async(
        self,
        user_id: UUID,
        page: int = 1,
        per_page: int = 10,
        search: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Workout]:
        """Get user's workouts with filtering and search asynchronously."""
        offset = (page - 1) * per_page
        query = select(self.model).filter(self.model.user_id == user_id)

        if search:
            query = query.filter(or_(self.model.name.ilike(f"%{search}%"), self.model.description.ilike(f"%{search}%")))
        if start_date:
            query = query.filter(self.model.created_at >= start_date)
        if end_date:
            query = query.filter(self.model.created_at <= end_date)
        
        query = query.order_by(desc(self.model.created_at)).offset(offset).limit(per_page)
        query = query.options(selectinload(Workout.exercises))
        
        result = await self.db.execute(query)
        workouts = result.scalars().all()
        return [Workout.from_orm(wo) for wo in workouts]

    async def get_workout_details_async(self, workout_id: UUID, user_id: UUID) -> Optional[Workout]:
        """Get workout details by ID, ensuring user ownership."""
        # Eager load exercises and plans
        options = [selectinload(Workout.exercises), selectinload(Workout.workout_plans)]
        workout = await super().get_async(id=workout_id, options=options)
        if not workout:
            return None
        if workout.user_id != user_id:
            # This check could also be done by BaseService if user_id is part of common filters
            raise AuthorizationError("Not authorized to view this workout")
        return Workout.from_orm(workout)

    async def delete_workout_async(self, workout_id: UUID, user_id: UUID) -> bool:
        """Delete a workout, ensuring user ownership."""
        workout = await super().get_async(id=workout_id)
        if not workout:
            return False
        if workout.user_id != user_id:
            raise AuthorizationError("Not authorized to delete this workout")
        
        # BaseService.delete_async expects id or the object. Let's pass id.
        # Exercises related to this workout will be deleted by cascade if DB schema is set up, otherwise manually.
        # Assuming cascade delete for Exercises. If not, delete them manually first.
        # Example: await self.db.execute(delete(Exercise).where(Exercise.workout_id == workout_id))
        return await super().delete_async(id=workout_id)

    async def create_workout_plan_async(
        self,
        user_id: UUID,
        workout_id: UUID,
        plan_data_in: WorkoutPlanCreate
    ) -> WorkoutPlan:
        """Create a workout plan asynchronously."""
        workout = await super().get_async(id=workout_id)
        if not workout or workout.user_id != user_id:
            raise AuthorizationError("Not authorized to use this workout for a plan, or workout not found.")

        plan_dict = plan_data_in.model_dump()
        plan_dict["user_id"] = user_id
        plan_dict["workout_id"] = workout_id
        
        new_plan = WorkoutPlan(**plan_dict)
        self.db.add(new_plan)
        await self.db.commit()
        await self.db.refresh(new_plan)
        return WorkoutPlan.from_orm(new_plan)

    async def get_active_plans_async(self, user_id: UUID) -> List[WorkoutPlan]:
        """Get user's active workout plans asynchronously."""
        now = datetime.utcnow()
        stmt = select(WorkoutPlan).filter(
            WorkoutPlan.user_id == user_id,
            WorkoutPlan.start_date <= now,
            WorkoutPlan.end_date >= now
        ).order_by(WorkoutPlan.start_date).options(selectinload(WorkoutPlan.workout))
        
        result = await self.db.execute(stmt)
        plans = result.scalars().all()
        return [WorkoutPlan.from_orm(plan) for plan in plans]

    async def get_upcoming_planned_workouts_async(self, user_id: UUID, days: int = 7) -> List[WorkoutPlan]:
        """Get upcoming scheduled workout plans asynchronously."""
        now = datetime.utcnow()
        end_date_filter = now + timedelta(days=days)
        stmt = select(WorkoutPlan).filter(
            WorkoutPlan.user_id == user_id,
            WorkoutPlan.start_date >= now,
            WorkoutPlan.start_date <= end_date_filter
        ).order_by(WorkoutPlan.start_date).options(selectinload(WorkoutPlan.workout))
        
        result = await self.db.execute(stmt)
        plans = result.scalars().all()
        return [WorkoutPlan.from_orm(plan) for plan in plans]

# Dependency injectors
def get_workout_service(
    # db: Session = Depends(get_db), # Comment out/remove original Depends here
    # app_settings: Settings = Depends(get_settings) # Comment out/remove original Depends here
) -> WorkoutService:
    from app.core.deps import get_db, get_settings # Import locally
    db_session: Session = Depends(get_db)
    current_app_settings: Settings = Depends(get_settings)
    logger.warning("Instantiating WorkoutService with a synchronous DB session. Most methods are async and will error.")
    return WorkoutService(db=db_session, app_settings=current_app_settings)

async def get_async_workout_service(
    # db: AsyncSession = Depends(get_async_db), # Comment out/remove original Depends here
    # app_settings: Settings = Depends(get_settings) # Comment out/remove original Depends here
) -> WorkoutService:
    from app.core.deps import get_async_db, get_settings # Import locally
    db_session: AsyncSession = Depends(get_async_db)
    current_app_settings: Settings = Depends(get_settings)
    return WorkoutService(db=db_session, app_settings=current_app_settings) 