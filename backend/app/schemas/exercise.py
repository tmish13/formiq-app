"""Exercise schemas for validation."""
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, validator, constr

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
    
    @validator("muscle_groups")
    def validate_muscle_groups(cls, v):
        """Validate muscle groups list."""
        if not v:
            raise ValueError("At least one muscle group must be specified")
        if len(v) > 5:
            raise ValueError("Maximum 5 muscle groups allowed")
        return v
    
    @validator("instructions")
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
    
    @validator("muscle_groups")
    def validate_muscle_groups(cls, v):
        """Validate muscle groups list."""
        if v is not None:
            if not v:
                raise ValueError("At least one muscle group must be specified")
            if len(v) > 5:
                raise ValueError("Maximum 5 muscle groups allowed")
        return v
    
    @validator("instructions")
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
    
    class Config:
        """Pydantic configuration."""
        from_attributes = True 