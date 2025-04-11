from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from fastapi import UploadFile
from datetime import datetime

class FormAnalysisMetrics(BaseModel):
    alignment: float = Field(..., ge=0.0, le=1.0)
    stability: float = Field(..., ge=0.0, le=1.0)
    symmetry: float = Field(..., ge=0.0, le=1.0)
    consistency: float = Field(..., ge=0.0, le=1.0)
    joint_accuracy: float = Field(..., ge=0.0, le=1.0)
    movement_quality: float = Field(..., ge=0.0, le=1.0)

class FormAnalysisRequest(BaseModel):
    video: UploadFile
    keypoints: List[Dict[str, Any]]
    exercise_type: Optional[str] = None
    duration: float
    user_id: str

class FormAnalysisResult(BaseModel):
    id: str
    exercise_type: Optional[str] = None
    confidence: float = Field(..., ge=0.0, le=1.0)
    keypoints: List[Dict[str, Any]]
    metrics: FormAnalysisMetrics
    feedback: List[str]
    suggestions: List[str]
    risk_level: str = Field(..., regex="^(low|medium|high)$")
    comparison_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    joint_analysis: Optional[List[float]] = None
    movement_analysis: Optional[List[float]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class FormAnalysisHistory(BaseModel):
    id: str
    exercise_type: Optional[str] = None
    confidence: float
    risk_level: str
    comparison_score: Optional[float] = None
    created_at: datetime
    summary: Optional[str] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class FormAnalysisDB(FormAnalysisResult):
    user_id: str
    video_url: str

    class Config:
        orm_mode = True 