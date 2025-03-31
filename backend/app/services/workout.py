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

    def create_workout(self, user: User, workout_data: Dict[str, Any]) -> Workout:
        """Create a new workout."""
        try:
            workout = Workout(
                user_id=user.id,
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
            logger.info(f"Created workout {workout.id} for user {user.id}")
            return workout
        except Exception as e:
            logger.error(f"Failed to create workout: {str(e)}")
            self.db.rollback()
            raise ValidationError(f"Failed to create workout: {str(e)}")

    def get_workout(self, workout_id: int, user_id: int) -> Workout:
        """Get a workout by ID."""
        workout = self.db.query(Workout).filter(
            Workout.id == workout_id,
            Workout.user_id == user_id
        ).first()
        if not workout:
            raise NotFoundError(f"Workout {workout_id} not found")
        return workout

    def get_user_workouts(self, user_id: int) -> List[Workout]:
        """Get all workouts for a user."""
        return self.db.query(Workout).filter(Workout.user_id == user_id).all()

    def update_workout(self, workout_id: int, user_id: int, workout_data: Dict[str, Any]) -> Workout:
        """Update a workout."""
        workout = self.get_workout(workout_id, user_id)
        try:
            for key, value in workout_data.items():
                if hasattr(workout, key):
                    setattr(workout, key, value)
            workout.updated_at = datetime.now()
            self.db.commit()
            self.db.refresh(workout)
            logger.info(f"Updated workout {workout_id}")
            return workout
        except Exception as e:
            logger.error(f"Failed to update workout: {str(e)}")
            self.db.rollback()
            raise ValidationError(f"Failed to update workout: {str(e)}")

    def delete_workout(self, workout_id: int, user_id: int) -> None:
        """Delete a workout."""
        workout = self.get_workout(workout_id, user_id)
        try:
            self.db.delete(workout)
            self.db.commit()
            logger.info(f"Deleted workout {workout_id}")
        except Exception as e:
            logger.error(f"Failed to delete workout: {str(e)}")
            self.db.rollback()
            raise ValidationError(f"Failed to delete workout: {str(e)}")

    def validate_workout_data(self, workout_data: Dict[str, Any]) -> None:
        """Validate workout data."""
        required_fields = ["name", "duration", "difficulty"]
        for field in required_fields:
            if field not in workout_data:
                raise ValidationError(f"Missing required field: {field}")
        
        if not isinstance(workout_data["duration"], (int, float)) or workout_data["duration"] <= 0:
            raise ValidationError("Duration must be a positive number")
        
        if workout_data["difficulty"] not in ["beginner", "intermediate", "advanced"]:
            raise ValidationError("Invalid difficulty level")

    def validate_workout_plan_data(self, plan_data: Dict[str, Any]) -> None:
        """Validate workout plan data."""
        required_fields = ["name", "duration_weeks", "difficulty"]
        for field in required_fields:
            if field not in plan_data:
                raise ValidationError(f"Missing required field: {field}")
        
        if not isinstance(plan_data["duration_weeks"], int) or plan_data["duration_weeks"] <= 0:
            raise ValidationError("Duration weeks must be a positive integer")
        
        if plan_data["difficulty"] not in ["beginner", "intermediate", "advanced"]:
            raise ValidationError("Invalid difficulty level")

    def create_workout_plan(self, user: User, plan_data: Dict[str, Any]) -> WorkoutPlan:
        """Create a new workout plan."""
        try:
            self.validate_workout_plan_data(plan_data)
            plan = WorkoutPlan(
                user_id=user.id,
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
            logger.info(f"Created workout plan {plan.id} for user {user.id}")
            return plan
        except Exception as e:
            logger.error(f"Failed to create workout plan: {str(e)}")
            self.db.rollback()
            raise ValidationError(f"Failed to create workout plan: {str(e)}")

    def get_workout_plan(self, plan_id: int, user_id: int) -> WorkoutPlan:
        """Get a workout plan by ID."""
        plan = self.db.query(WorkoutPlan).filter(
            WorkoutPlan.id == plan_id,
            WorkoutPlan.user_id == user_id
        ).first()
        if not plan:
            raise NotFoundError(f"Workout plan {plan_id} not found")
        return plan

    def get_user_workout_plans(self, user_id: int) -> List[WorkoutPlan]:
        """Get all workout plans for a user."""
        return self.db.query(WorkoutPlan).filter(WorkoutPlan.user_id == user_id).all()

    def update_workout_plan(self, plan_id: int, user_id: int, plan_data: Dict[str, Any]) -> WorkoutPlan:
        """Update a workout plan."""
        plan = self.get_workout_plan(plan_id, user_id)
        try:
            self.validate_workout_plan_data(plan_data)
            for key, value in plan_data.items():
                if hasattr(plan, key):
                    setattr(plan, key, value)
            plan.updated_at = datetime.now()
            self.db.commit()
            self.db.refresh(plan)
            logger.info(f"Updated workout plan {plan_id}")
            return plan
        except Exception as e:
            logger.error(f"Failed to update workout plan: {str(e)}")
            self.db.rollback()
            raise ValidationError(f"Failed to update workout plan: {str(e)}")

    def delete_workout_plan(self, plan_id: int, user_id: int) -> None:
        """Delete a workout plan."""
        plan = self.get_workout_plan(plan_id, user_id)
        try:
            self.db.delete(plan)
            self.db.commit()
            logger.info(f"Deleted workout plan {plan_id}")
        except Exception as e:
            logger.error(f"Failed to delete workout plan: {str(e)}")
            self.db.rollback()
            raise ValidationError(f"Failed to delete workout plan: {str(e)}")

    def add_workout_to_plan(self, plan_id: int, user_id: int, workout_data: Dict[str, Any]) -> WorkoutPlan:
        """Add a workout to a workout plan."""
        try:
            plan = self.get_workout_plan(plan_id, user_id)
            workout = self.get_workout(workout_data["workout_id"], user_id)
            
            # Add workout to plan
            plan.workouts.append(workout)
            self.db.commit()
            self.db.refresh(plan)
            logger.info(f"Added workout {workout.id} to plan {plan_id}")
            return plan
        except Exception as e:
            logger.error(f"Failed to add workout to plan: {str(e)}")
            self.db.rollback()
            raise ValidationError(f"Failed to add workout to plan: {str(e)}")

    def remove_workout_from_plan(self, plan_id: int, user_id: int, workout_id: int) -> WorkoutPlan:
        """Remove a workout from a workout plan."""
        try:
            plan = self.get_workout_plan(plan_id, user_id)
            workout = self.get_workout(workout_id, user_id)
            
            # Remove workout from plan
            plan.workouts.remove(workout)
            self.db.commit()
            self.db.refresh(plan)
            logger.info(f"Removed workout {workout_id} from plan {plan_id}")
            return plan
        except Exception as e:
            logger.error(f"Failed to remove workout from plan: {str(e)}")
            self.db.rollback()
            raise ValidationError(f"Failed to remove workout from plan: {str(e)}") 