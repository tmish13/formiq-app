"""Workout schemas."""
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

class ExerciseBase(BaseModel):
    """Base exercise schema."""
    name: str
    sets: int
    reps: int
    weight: Optional[float] = None
    notes: Optional[str] = None

class ExerciseCreate(ExerciseBase):
    """Exercise creation schema."""
    pass

class ExerciseResponse(ExerciseBase):
    """Exercise response schema."""
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class WorkoutBase(BaseModel):
    """Base workout schema."""
    name: str
    description: Optional[str] = None
    duration: Optional[int] = None  # in minutes
    difficulty: Optional[str] = None
    notes: Optional[str] = None

class WorkoutCreate(WorkoutBase):
    """Workout creation schema."""
    pass

class WorkoutUpdate(WorkoutBase):
    """Workout update schema."""
    name: Optional[str] = None
    description: Optional[str] = None
    duration: Optional[int] = None
    difficulty: Optional[str] = None
    notes: Optional[str] = None

class WorkoutResponse(WorkoutBase):
    """Workout response schema."""
    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime
    exercises: List[ExerciseResponse] = []

    class Config:
        orm_mode = True

class WorkoutPlanBase(BaseModel):
    """Base workout plan schema."""
    name: str
    description: Optional[str] = None
    frequency: str  # e.g., "3x per week"
    duration: int  # in weeks
    notes: Optional[str] = None

class WorkoutPlanCreate(WorkoutPlanBase):
    """Workout plan creation schema."""
    pass

class WorkoutPlanResponse(WorkoutPlanBase):
    """Workout plan response schema."""
    id: str
    user_id: str
    workout_id: str
    created_at: datetime
    updated_at: datetime
    next_workout: Optional[datetime] = None

    class Config:
        orm_mode = True

class ExerciseProgressResponse(BaseModel):
    """Exercise progress response schema."""
    date: datetime
    exercise_name: str
    sets: int
    reps: int
    weight: Optional[float] = None
    notes: Optional[str] = None

    class Config:
        orm_mode = True 