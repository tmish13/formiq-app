"""Workout models for managing exercise routines and plans."""
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Float, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, validates
from app.models.base import BaseModel
from app.core.exceptions import ValidationError

class Workout(BaseModel):
    """
    Model for storing workout information.
    
    This model handles:
    - Workout metadata
    - Exercise tracking
    - Performance metrics
    
    Relationships:
    - Many-to-one with User
    - One-to-many with Exercise
    - Many-to-many with WorkoutPlan
    
    Attributes:
        user_id (UUID): ID of the user who created the workout
        name (str): Name of the workout
        description (str): Detailed workout description
        duration (int): Duration in minutes
        calories_burned (int): Estimated calories burned
        workout_metadata (dict): Additional workout data
    """
    __tablename__ = "workouts"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(String(1024))
    duration = Column(Integer)  # Duration in minutes
    calories_burned = Column(Integer)
    workout_metadata = Column(JSON)

    # Relationships
    user = relationship(
        "User",
        back_populates="workouts",
        lazy="select"
    )
    exercises = relationship(
        "Exercise",
        back_populates="workout",
        cascade="all, delete-orphan",
        lazy="select"
    )
    workout_plans = relationship(
        "WorkoutPlan",
        back_populates="workout",
        lazy="select"
    )

    @validates('name')
    def validate_name(self, key: str, name: str) -> str:
        """Validate workout name."""
        if not name:
            raise ValidationError("Workout name is required")
        if len(name) > 255:
            raise ValidationError("Workout name is too long")
        return name

    @validates('description')
    def validate_description(self, key: str, description: Optional[str]) -> Optional[str]:
        """Validate workout description."""
        if description and len(description) > 1024:
            raise ValidationError("Workout description is too long")
        return description

    @validates('duration', 'calories_burned')
    def validate_metrics(self, key: str, value: Optional[int]) -> Optional[int]:
        """Validate workout metrics."""
        if value is not None and value < 0:
            raise ValidationError(f"{key} cannot be negative")
        return value

class Exercise(BaseModel):
    """
    Model for storing exercise information.
    
    This model handles:
    - Exercise details
    - Set and rep tracking
    - Weight and duration tracking
    
    Relationships:
    - Many-to-one with Workout
    
    Attributes:
        workout_id (UUID): ID of the parent workout
        name (str): Name of the exercise
        description (str): Exercise description
        sets (int): Number of sets
        reps (int): Number of reps per set
        weight (float): Weight in kg
        duration (int): Duration in seconds
        rest_time (int): Rest time in seconds
        exercise_metadata (dict): Additional exercise data
    """
    __tablename__ = "exercises"

    workout_id = Column(UUID(as_uuid=True), ForeignKey("workouts.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(String(1024))
    sets = Column(Integer)
    reps = Column(Integer)
    weight = Column(Float)  # Weight in kg
    duration = Column(Integer)  # Duration in seconds
    rest_time = Column(Integer)  # Rest time in seconds
    exercise_metadata = Column(JSON)

    # Relationships
    workout = relationship(
        "Workout",
        back_populates="exercises",
        lazy="select"
    )

    @validates('name')
    def validate_name(self, key: str, name: str) -> str:
        """Validate exercise name."""
        if not name:
            raise ValidationError("Exercise name is required")
        if len(name) > 255:
            raise ValidationError("Exercise name is too long")
        return name

    @validates('description')
    def validate_description(self, key: str, description: Optional[str]) -> Optional[str]:
        """Validate exercise description."""
        if description and len(description) > 1024:
            raise ValidationError("Exercise description is too long")
        return description

    @validates('sets', 'reps', 'duration', 'rest_time')
    def validate_numbers(self, key: str, value: Optional[int]) -> Optional[int]:
        """Validate numeric values."""
        if value is not None and value < 0:
            raise ValidationError(f"{key} cannot be negative")
        return value

    @validates('weight')
    def validate_weight(self, key: str, weight: Optional[float]) -> Optional[float]:
        """Validate weight value."""
        if weight is not None and weight < 0:
            raise ValidationError("Weight cannot be negative")
        return weight

class WorkoutPlan(BaseModel):
    """
    Model for storing workout plans.
    
    This model handles:
    - Workout scheduling
    - Plan management
    - Progress tracking
    
    Relationships:
    - Many-to-one with User
    - Many-to-one with Workout
    
    Attributes:
        user_id (UUID): ID of the user who created the plan
        workout_id (UUID): ID of the workout in the plan
        name (str): Name of the plan
        description (str): Plan description
        frequency (str): Workout frequency
        start_date (datetime): Plan start date
        end_date (datetime): Plan end date
        plan_metadata (dict): Additional plan data
    """
    __tablename__ = "workout_plans"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    workout_id = Column(UUID(as_uuid=True), ForeignKey("workouts.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(String(1024))
    frequency = Column(String(50))  # e.g., "daily", "weekly", "monthly"
    start_date = Column(DateTime(timezone=True))
    end_date = Column(DateTime(timezone=True))
    plan_metadata = Column(JSON)

    # Relationships
    user = relationship(
        "User",
        back_populates="workout_plans",
        lazy="select"
    )
    workout = relationship(
        "Workout",
        back_populates="workout_plans",
        lazy="select"
    )

    @validates('name')
    def validate_name(self, key: str, name: str) -> str:
        """Validate plan name."""
        if not name:
            raise ValidationError("Plan name is required")
        if len(name) > 255:
            raise ValidationError("Plan name is too long")
        return name

    @validates('description')
    def validate_description(self, key: str, description: Optional[str]) -> Optional[str]:
        """Validate plan description."""
        if description and len(description) > 1024:
            raise ValidationError("Plan description is too long")
        return description

    @validates('frequency')
    def validate_frequency(self, key: str, frequency: Optional[str]) -> Optional[str]:
        """Validate workout frequency."""
        valid_frequencies = {'daily', 'weekly', 'monthly', 'custom'}
        if frequency and frequency not in valid_frequencies:
            raise ValidationError("Invalid workout frequency")
        return frequency

    @validates('start_date', 'end_date')
    def validate_dates(self, key: str, value: Optional[datetime]) -> Optional[datetime]:
        """Validate plan dates."""
        if not value:
            return value

        if key == 'end_date' and self.start_date and value <= self.start_date:
            raise ValidationError("End date must be after start date")

        return value

    def validate(self) -> None:
        """Validate all fields in the model."""
        super().validate()
        self.validate_name('name', self.name)
        if self.description:
            self.validate_description('description', self.description)
        if self.frequency:
            self.validate_frequency('frequency', self.frequency)
        if self.start_date:
            self.validate_dates('start_date', self.start_date)
        if self.end_date:
            self.validate_dates('end_date', self.end_date) 