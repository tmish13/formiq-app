"""Pydantic schemas for progress tracking."""
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class ProgressMetrics(BaseModel):
    """Schema for progress metrics."""
    form_score: float = Field(..., ge=0.0, le=1.0)
    consistency_score: float = Field(..., ge=0.0, le=1.0)
    reps: int = Field(..., ge=0)
    improvement_areas: List[str] = Field(default_factory=list)

class ProgressUpdate(BaseModel):
    """Schema for progress update request."""
    exercise_type: str
    metrics: ProgressMetrics

class ProgressResponse(BaseModel):
    """Schema for progress response."""
    exercise_type: str
    form_score: float
    consistency_score: float
    total_reps: int
    improvement_areas: List[str]
    last_updated: datetime
    
    model_config = ConfigDict(from_attributes=True)

class ProgressSnapshot(BaseModel):
    """Schema for progress snapshot."""
    timestamp: datetime
    form_score: float
    consistency_score: float
    reps: int
    notes: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

class ProgressSummary(BaseModel):
    """Schema for progress summary."""
    total_exercises: int
    total_reps: int
    average_form_score: float
    average_consistency_score: float
    exercises: dict[str, dict]
    
    model_config = ConfigDict(from_attributes=True) 