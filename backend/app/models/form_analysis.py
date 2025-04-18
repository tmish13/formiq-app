from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from fastapi import UploadFile
from datetime import datetime
from uuid import UUID

class FormAnalysisMetrics(BaseModel):
    alignment: float = Field(..., ge=0.0, le=1.0)
    stability: float = Field(..., ge=0.0, le=1.0)
    symmetry: float = Field(..., ge=0.0, le=1.0)
    consistency: float = Field(..., ge=0.0, le=1.0)
    joint_accuracy: float = Field(..., ge=0.0, le=1.0)
    movement_quality: float = Field(..., ge=0.0, le=1.0)

    model_config = ConfigDict(arbitrary_types_allowed=True)

class FormAnalysisRequest(BaseModel):
    """Form analysis request model."""
    
    video_id: UUID
    exercise_type: str = Field(..., description="Type of exercise being analyzed")
    user_id: Optional[UUID] = None
    settings: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

class FormAnalysisResult(BaseModel):
    """Form analysis result model."""
    
    video_id: UUID
    score: float = Field(..., ge=0, le=100)
    feedback: str
    joint_angles: Dict[str, float]
    spine_alignment: float = Field(..., ge=0, le=1)
    symmetry_score: float = Field(..., ge=0, le=1)
    risk_level: str = Field(..., pattern="^(low|medium|high)$")
    confidence_score: float = Field(..., ge=0, le=1)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

class FormAnalysisHistory(BaseModel):
    id: str
    exercise_type: Optional[str] = None
    confidence: float
    risk_level: str
    comparison_score: Optional[float] = None
    created_at: datetime
    summary: Optional[str] = None

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        json_encoders={datetime: lambda v: v.isoformat()}
    )

class FormAnalysisDB(FormAnalysisResult):
    user_id: str
    video_url: str

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        from_attributes=True
    )

class FormAnalysis(BaseModel):
    """Form analysis model."""
    
    id: UUID
    request: FormAnalysisRequest
    result: FormAnalysisResult
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        json_encoders={datetime: lambda v: v.isoformat()}
    ) 