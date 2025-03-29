"""Workout repository implementation with optimized queries and caching."""
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import desc, and_, or_
from app.models.workout import Workout, Exercise, WorkoutPlan
from app.repositories.base import BaseRepository

class WorkoutRepository(BaseRepository[Workout]):
    """
    Repository for workout operations with optimized queries.
    
    Features:
    - Optimized relationship loading
    - Exercise management
    - Plan integration
    - Advanced search capabilities
    """
    
    def __init__(self):
        super().__init__(Workout)

    def get_by_user(
        self,
        db: Session,
        *,
        user_id: UUID,
        skip: int = 0,
        limit: int = 100,
        include_relations: List[str] = None,
        order_by: List[str] = None
    ) -> List[Workout]:
        """
        Get workouts for a specific user.
        
        Args:
            db: Database session
            user_id: User's UUID
            skip: Number of records to skip
            limit: Maximum number of records to return
            include_relations: Optional list of relationships to eager load
            order_by: Optional list of fields to order by
        """
        try:
            filters = {"user_id": user_id}
            return self.get_multi(
                db,
                skip=skip,
                limit=limit,
                filters=filters,
                include_relations=include_relations or ["exercises"],
                order_by=order_by or ["-created_at"]
            )
        except Exception as e:
            self._handle_error(e, "get_by_user")

    def create_with_exercises(
        self,
        db: Session,
        *,
        workout_data: Dict[str, Any],
        exercises: List[Dict[str, Any]]
    ) -> Workout:
        """
        Create a workout with exercises in a single transaction.
        
        Args:
            db: Database session
            workout_data: Workout details
            exercises: List of exercise details
        """
        try:
            self._ensure_transaction(db)
            
            # Create workout
            workout = self.create(db, obj_in=workout_data)
            
            # Create exercises
            exercise_objs = []
            for exercise_data in exercises:
                exercise_data["workout_id"] = workout.id
                exercise = Exercise(**exercise_data)
                db.add(exercise)
                exercise_objs.append(exercise)
            
            db.commit()
            for obj in exercise_objs:
                db.refresh(obj)
            db.refresh(workout)
            
            return workout
        except Exception as e:
            db.rollback()
            self._handle_error(e, "create_with_exercises")

    def update_with_exercises(
        self,
        db: Session,
        *,
        workout: Workout,
        workout_data: Dict[str, Any],
        exercises: List[Dict[str, Any]]
    ) -> Workout:
        """
        Update a workout and its exercises in a single transaction.
        
        Args:
            db: Database session
            workout: Workout object to update
            workout_data: Updated workout details
            exercises: List of updated exercise details
        """
        try:
            self._ensure_transaction(db)
            
            # Update workout
            updated_workout = self.update(db, db_obj=workout, obj_in=workout_data)
            
            # Delete existing exercises
            for exercise in workout.exercises:
                db.delete(exercise)
            
            # Create new exercises
            exercise_objs = []
            for exercise_data in exercises:
                exercise_data["workout_id"] = workout.id
                exercise = Exercise(**exercise_data)
                db.add(exercise)
                exercise_objs.append(exercise)
            
            db.commit()
            for obj in exercise_objs:
                db.refresh(obj)
            db.refresh(updated_workout)
            
            return updated_workout
        except Exception as e:
            db.rollback()
            self._handle_error(e, "update_with_exercises")

    def get_with_plan(
        self,
        db: Session,
        *,
        workout_id: UUID,
        include_relations: List[str] = None
    ) -> Optional[Workout]:
        """
        Get a workout with its plan details.
        
        Args:
            db: Database session
            workout_id: Workout's UUID
            include_relations: Optional list of relationships to eager load
        """
        try:
            return self.get(
                db,
                id=workout_id,
                include_relations=include_relations or ["exercises", "workout_plans"]
            )
        except Exception as e:
            self._handle_error(e, "get_with_plan")

    def search_workouts(
        self,
        db: Session,
        *,
        user_id: UUID,
        query: str,
        skip: int = 0,
        limit: int = 10,
        include_relations: List[str] = None
    ) -> List[Workout]:
        """
        Search workouts by name or description.
        
        Args:
            db: Database session
            user_id: User's UUID
            query: Search query string
            skip: Number of records to skip
            limit: Maximum number of records to return
            include_relations: Optional list of relationships to eager load
        """
        try:
            db_query = db.query(self.model).filter(self.model.user_id == user_id)
            
            if include_relations:
                for relation in include_relations:
                    db_query = db_query.options(selectinload(getattr(self.model, relation)))
            
            search_filter = or_(
                self.model.name.ilike(f"%{query}%"),
                self.model.description.ilike(f"%{query}%")
            )
            
            return (
                db_query.filter(search_filter)
                .order_by(desc(self.model.created_at))
                .offset(skip)
                .limit(limit)
                .all()
            )
        except Exception as e:
            self._handle_error(e, "search_workouts")

class WorkoutPlanRepository(BaseRepository[WorkoutPlan]):
    """
    Repository for workout plan operations with optimized queries.
    
    Features:
    - Plan scheduling
    - Workout integration
    - Advanced filtering
    """
    
    def __init__(self):
        super().__init__(WorkoutPlan)

    def get_active_plans(
        self,
        db: Session,
        *,
        user_id: UUID,
        include_relations: List[str] = None
    ) -> List[WorkoutPlan]:
        """
        Get active workout plans for a user.
        
        Args:
            db: Database session
            user_id: User's UUID
            include_relations: Optional list of relationships to eager load
        """
        try:
            now = datetime.utcnow()
            filters = {
                "user_id": user_id,
                "start_date__lte": now,
                "end_date__gte": now
            }
            return self.get_multi(
                db,
                filters=filters,
                include_relations=include_relations or ["workout"],
                order_by=["start_date"]
            )
        except Exception as e:
            self._handle_error(e, "get_active_plans")

    def get_upcoming_plans(
        self,
        db: Session,
        *,
        user_id: UUID,
        days: int = 7,
        include_relations: List[str] = None
    ) -> List[WorkoutPlan]:
        """
        Get upcoming workout plans for a user.
        
        Args:
            db: Database session
            user_id: User's UUID
            days: Number of days to look ahead
            include_relations: Optional list of relationships to eager load
        """
        try:
            now = datetime.utcnow()
            filters = {
                "user_id": user_id,
                "start_date__gte": now,
                "start_date__lte": now + datetime.timedelta(days=days)
            }
            return self.get_multi(
                db,
                filters=filters,
                include_relations=include_relations or ["workout"],
                order_by=["start_date"]
            )
        except Exception as e:
            self._handle_error(e, "get_upcoming_plans") 