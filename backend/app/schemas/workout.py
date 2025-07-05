"""Workout schema models."""
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, date
from uuid import UUID
from enum import Enum

class WorkoutLevel(str, Enum):
    """Workout difficulty level enum."""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate" 
    ADVANCED = "advanced"

class ExerciseBase(BaseModel):
    """Base exercise schema."""
    name: str
    sets: int
    reps: int
    rest_seconds: int = 60
    notes: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

class Exercise(ExerciseBase):
    """Exercise schema with ID."""
    id: UUID
    workout_id: UUID
    created_at: datetime
    updated_at: datetime

class ExerciseCreate(ExerciseBase):
    """Schema for creating an exercise."""
    workout_id: UUID

class ExerciseUpdate(BaseModel):
    """Schema for updating an exercise."""
    name: Optional[str] = None
    sets: Optional[int] = None
    reps: Optional[int] = None
    rest_seconds: Optional[int] = None
    notes: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

class WorkoutBase(BaseModel):
    """Base workout schema."""
    name: str
    description: Optional[str] = None
    level: WorkoutLevel = WorkoutLevel.BEGINNER
    duration_minutes: Optional[int] = None
    
    model_config = ConfigDict(from_attributes=True)

class Workout(WorkoutBase):
    """Workout schema with ID and related exercises."""
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime
    exercises: List[Exercise] = []

class WorkoutCreate(WorkoutBase):
    """Schema for creating a workout."""
    exercises: Optional[List[ExerciseBase]] = None

class WorkoutUpdate(BaseModel):
    """Schema for updating a workout."""
    name: Optional[str] = None
    description: Optional[str] = None
    level: Optional[WorkoutLevel] = None
    duration_minutes: Optional[int] = None
    
    model_config = ConfigDict(from_attributes=True)

class WorkoutRead(WorkoutBase):
    """Schema for reading a workout."""
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class WorkoutWithExercises(WorkoutRead):
    """Workout schema with associated exercises."""
    exercises: List[Exercise] = []

# Additional schemas for workout plans

class WorkoutPlanBase(BaseModel):
    """Base workout plan schema."""
    name: str
    description: Optional[str] = None
    duration_weeks: int
    level: WorkoutLevel = WorkoutLevel.BEGINNER

class WorkoutPlan(WorkoutPlanBase):
    """Workout plan schema with ID and related workouts."""
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime
    workouts: List[Workout] = []

class WorkoutPlanCreate(WorkoutPlanBase):
    """Schema for creating a workout plan."""
    workout_ids: Optional[List[UUID]] = None

class WorkoutPlanUpdate(BaseModel):
    """Schema for updating a workout plan."""
    name: Optional[str] = None
    description: Optional[str] = None
    duration_weeks: Optional[int] = None
    level: Optional[WorkoutLevel] = None
    workout_ids: Optional[List[UUID]] = None
    
    model_config = ConfigDict(from_attributes=True)

class WorkoutPlanRead(WorkoutPlanBase):
    """Schema for reading a workout plan."""
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class WorkoutPlanWithExercises(WorkoutPlanRead):
    """Workout plan schema with associated workouts."""
    workouts: List[WorkoutRead] = []

class WorkoutShare(BaseModel):
    """Schema for sharing a workout."""
    share_with_email: str
    message: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

class WorkoutShareResponse(BaseModel):
    """Response schema for workout sharing."""
    success: bool
    message: str
    shared_with: str
    
    model_config = ConfigDict(from_attributes=True)

class ExerciseProgressResponse(BaseModel):
    """Exercise progress response schema."""
    date: datetime
    exercise_name: str
    sets: int
    reps: int
    weight: Optional[float] = None
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True) 