"""Exercise schemas for validation."""
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, field_validator, constr, ConfigDict

from app.models.enums import ExerciseType, MuscleGroup, Difficulty

class ExerciseCreate(BaseModel):
    """Schema for creating a new exercise."""
    name: constr(min_length=3, max_length=100) = Field(..., description="Exercise name")
    exercise_type: ExerciseType = Field(..., description="Type of exercise")
    description: constr(min_length=10, max_length=1000) = Field(..., description="Exercise description")
    difficulty: Difficulty = Field(..., description="Exercise difficulty level")
    muscle_groups: List[MuscleGroup] = Field(..., description="Primary muscle groups targeted")
    instructions: List[constr(min_length=10, max_length=500)] = Field(..., description="Step-by-step instructions")
    tips: Optional[List[constr(max_length=200)]] = Field(None, description="Exercise tips and cues")
    video_url: Optional[str] = Field(None, description="Reference video URL")
    
    @field_validator("muscle_groups")
    @classmethod
    def validate_muscle_groups(cls, v):
        """Validate muscle groups list."""
        if not v:
            raise ValueError("At least one muscle group must be specified")
        if len(v) > 5:
            raise ValueError("Maximum 5 muscle groups allowed")
        return v
    
    @field_validator("instructions")
    @classmethod
    def validate_instructions(cls, v):
        """Validate instructions list."""
        if not v:
            raise ValueError("At least one instruction must be provided")
        if len(v) > 10:
            raise ValueError("Maximum 10 instructions allowed")
        return v

class ExerciseUpdate(BaseModel):
    """Schema for updating an existing exercise."""
    name: Optional[constr(min_length=3, max_length=100)] = None
    exercise_type: Optional[ExerciseType] = None
    description: Optional[constr(min_length=10, max_length=1000)] = None
    difficulty: Optional[Difficulty] = None
    muscle_groups: Optional[List[MuscleGroup]] = None
    instructions: Optional[List[constr(min_length=10, max_length=500)]] = None
    tips: Optional[List[constr(max_length=200)]] = None
    video_url: Optional[str] = None
    
    @field_validator("muscle_groups")
    @classmethod
    def validate_muscle_groups(cls, v):
        """Validate muscle groups list."""
        if v is not None:
            if not v:
                raise ValueError("At least one muscle group must be specified")
            if len(v) > 5:
                raise ValueError("Maximum 5 muscle groups allowed")
        return v
    
    @field_validator("instructions")
    @classmethod
    def validate_instructions(cls, v):
        """Validate instructions list."""
        if v is not None:
            if not v:
                raise ValueError("At least one instruction must be provided")
            if len(v) > 10:
                raise ValueError("Maximum 10 instructions allowed")
        return v

class ExerciseResponse(BaseModel):
    """Schema for exercise responses."""
    id: UUID
    name: str
    exercise_type: ExerciseType
    description: str
    difficulty: Difficulty
    muscle_groups: List[MuscleGroup]
    instructions: List[str]
    tips: Optional[List[str]] = None
    video_url: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class ExerciseProgressCreate(BaseModel):
    """Schema for creating exercise progress."""
    exercise_name: str = Field(..., description="Name of the exercise")
    metrics: Dict[str, Any] = Field(..., description="Progress metrics")
    notes: Optional[str] = Field(None, description="Optional notes")


class ExerciseSetCreate(BaseModel):
    """Schema for creating an exercise set."""
    reps: int = Field(..., ge=1, le=100, description="Number of repetitions")
    weight: Optional[float] = Field(None, ge=0, description="Weight used (optional)")
    duration: Optional[int] = Field(None, ge=1, description="Duration in seconds (for time-based exercises)")
    distance: Optional[float] = Field(None, ge=0, description="Distance (for cardio exercises)")
    notes: Optional[str] = Field(None, max_length=500, description="Optional notes")


class ExerciseSetUpdate(BaseModel):
    """Schema for updating an exercise set."""
    reps: Optional[int] = Field(None, ge=1, le=100, description="Number of repetitions")
    weight: Optional[float] = Field(None, ge=0, description="Weight used")
    duration: Optional[int] = Field(None, ge=1, description="Duration in seconds")
    distance: Optional[float] = Field(None, ge=0, description="Distance")
    notes: Optional[str] = Field(None, max_length=500, description="Optional notes")


class ExerciseSetResponse(BaseModel):
    """Schema for exercise set responses."""
    id: int = Field(..., description="Set ID")
    exercise_id: int = Field(..., description="Exercise ID")
    reps: int = Field(..., description="Number of repetitions")
    weight: Optional[float] = Field(None, description="Weight used")
    duration: Optional[int] = Field(None, description="Duration in seconds")
    distance: Optional[float] = Field(None, description="Distance")
    notes: Optional[str] = Field(None, description="Notes")
    created_at: datetime = Field(..., description="Creation timestamp")
    
    model_config = ConfigDict(from_attributes=True)


class ExerciseProgressResponse(BaseModel):
    """Schema for exercise progress responses."""
    id: UUID = Field(..., description="Progress ID")
    exercise_name: str = Field(..., description="Exercise name")
    metrics: Dict[str, Any] = Field(..., description="Progress metrics")
    notes: Optional[str] = Field(None, description="Notes")
    created_at: datetime = Field(..., description="Creation timestamp")
    
    model_config = ConfigDict(from_attributes=True) 