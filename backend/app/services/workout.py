"""Service for managing workouts and workout plans."""
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.workout import Workout, Exercise, WorkoutPlan
from app.models.user import User
from app.core.exceptions import NotFoundError, ValidationError
from app.core.logging import get_logger
from app.core.database import get_db

logger = get_logger(__name__)

class WorkoutService:
    """Service for managing workouts and workout plans."""
    
    def __init__(self, db: Session):
        """Initialize workout service with database session."""
        self.db = db

    def create_workout(self, user_id: int, workout_data: Dict[str, Any]) -> Workout:
        """Create a new workout."""
        try:
            workout = Workout(
                user_id=user_id,
                name=workout_data["name"],
                description=workout_data.get("description"),
                duration=workout_data["duration"],
                difficulty=workout_data["difficulty"],
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            self.db.add(workout)
            self.db.commit()
            self.db.refresh(workout)
            logger.info(f"Created workout {workout.id} for user {user_id}")
            return workout
        except Exception as e:
            logger.error(f"Failed to create workout: {str(e)}")
            self.db.rollback()
            raise ValidationError(f"Failed to create workout: {str(e)}")

    def add_exercise(self, workout_id: int, exercise_data: Dict[str, Any]) -> Exercise:
        """Add an exercise to a workout."""
        try:
            workout = self.db.query(Workout).filter(Workout.id == workout_id).first()
            if not workout:
                raise NotFoundError(f"Workout {workout_id} not found")

            exercise = Exercise(
                workout_id=workout_id,
                exercise_id=exercise_data["exercise_id"],
                sets=exercise_data["sets"],
                reps=exercise_data["reps"],
                weight=exercise_data.get("weight"),
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            self.db.add(exercise)
            self.db.commit()
            self.db.refresh(exercise)
            logger.info(f"Added exercise to workout {workout_id}")
            return exercise
        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to add exercise: {str(e)}")
            self.db.rollback()
            raise ValidationError(f"Failed to add exercise: {str(e)}")

    def create_workout_plan(self, user_id: int, plan_data: Dict[str, Any]) -> WorkoutPlan:
        """Create a new workout plan."""
        try:
            plan = WorkoutPlan(
                user_id=user_id,
                name=plan_data["name"],
                description=plan_data.get("description"),
                duration_weeks=plan_data["duration_weeks"],
                difficulty=plan_data["difficulty"],
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            self.db.add(plan)
            self.db.commit()
            self.db.refresh(plan)
            logger.info(f"Created workout plan {plan.id} for user {user_id}")
            return plan
        except Exception as e:
            logger.error(f"Failed to create workout plan: {str(e)}")
            self.db.rollback()
            raise ValidationError(f"Failed to create workout plan: {str(e)}")

    def add_workout_to_plan(self, plan_id: int, workout_data: Dict[str, Any]) -> WorkoutPlan:
        """Add a workout to a workout plan."""
        try:
            plan = self.db.query(WorkoutPlan).filter(WorkoutPlan.id == plan_id).first()
            if not plan:
                raise NotFoundError(f"Workout plan {plan_id} not found")

            workout = self.db.query(Workout).filter(Workout.id == workout_data["workout_id"]).first()
            if not workout:
                raise NotFoundError(f"Workout {workout_data['workout_id']} not found")

            plan.workouts.append(workout)
            plan.updated_at = datetime.now()
            self.db.commit()
            self.db.refresh(plan)
            logger.info(f"Added workout {workout.id} to plan {plan_id}")
            return plan
        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to add workout to plan: {str(e)}")
            self.db.rollback()
            raise ValidationError(f"Failed to add workout to plan: {str(e)}")

    def get_workout(self, workout_id: int) -> Workout:
        """Get workout by ID."""
        workout = self.db.query(Workout).filter(Workout.id == workout_id).first()
        if not workout:
            raise NotFoundError(f"Workout {workout_id} not found")
        return workout

    def get_workout_plan(self, plan_id: int) -> WorkoutPlan:
        """Get workout plan by ID."""
        plan = self.db.query(WorkoutPlan).filter(WorkoutPlan.id == plan_id).first()
        if not plan:
            raise NotFoundError(f"Workout plan {plan_id} not found")
        return plan 