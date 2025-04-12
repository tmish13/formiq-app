"""Form analysis schemas."""
from datetime import datetime
from typing import List, Optional, Dict, Union
from pydantic import BaseModel, Field, UUID4, validator, constr, confloat
from uuid import UUID

from app.models.enums import ExerciseType

class FeedbackItem(BaseModel):
    """Individual feedback item for form analysis."""
    type: str = Field(
        ...,
        description="Type of feedback",
        example="warning",
        pattern="^(success|warning|error)$"
    )
    message: str = Field(
        ...,
        description="Feedback message",
        example="Knees going too far forward",
        min_length=1,
        max_length=200
    )
    timestamp: Optional[float] = Field(
        None,
        description="Timestamp in video where issue occurs (seconds)",
        example=12.5,
        ge=0
    )

class JointAngle(BaseModel):
    """Joint angle measurement."""
    joint: str = Field(
        ...,
        description="Name of the joint",
        example="knee",
        pattern="^(knee|hip|ankle|elbow|shoulder|wrist)$"
    )
    angle: float = Field(
        ...,
        description="Angle in degrees",
        example=85.5,
        ge=0,
        le=360
    )
    timestamp: float = Field(
        ...,
        description="Timestamp in video (seconds)",
        example=12.5,
        ge=0
    )

class FormAnalysisCreate(BaseModel):
    """Schema for creating a new form analysis."""
    exercise_type: str = Field(
        ...,
        description="Type of exercise being analyzed",
        example="squat",
        min_length=1,
        max_length=50
    )
    video_url: str = Field(
        ...,
        description="URL of the uploaded video",
        example="https://storage.formiq.com/videos/exercise_123.mp4"
    )

class FormAnalysisResponse(BaseModel):
    """Schema for form analysis response."""
    id: UUID4 = Field(
        ...,
        description="Unique identifier for the analysis",
        example="123e4567-e89b-12d3-a456-426614174000"
    )
    user_id: UUID4 = Field(
        ...,
        description="ID of the user who submitted the video",
        example="123e4567-e89b-12d3-a456-426614174001"
    )
    exercise_type: str = Field(
        ...,
        description="Type of exercise analyzed",
        example="squat"
    )
    score: float = Field(
        ...,
        description="Overall form score (0-100)",
        example=85.5,
        ge=0,
        le=100
    )
    feedback: List[FeedbackItem] = Field(
        ...,
        description="List of feedback items",
        min_items=1
    )
    joint_angles: Optional[List[JointAngle]] = Field(
        None,
        description="List of joint angle measurements"
    )
    video_url: str = Field(
        ...,
        description="URL to access the analyzed video",
        example="https://storage.formiq.com/videos/exercise_123.mp4"
    )
    thumbnail_url: Optional[str] = Field(
        None,
        description="URL of the video thumbnail",
        example="https://storage.formiq.com/thumbnails/exercise_123.jpg"
    )
    created_at: datetime = Field(
        ...,
        description="When the analysis was created",
        example="2024-01-20T10:30:00Z"
    )
    updated_at: Optional[datetime] = Field(
        None,
        description="When the analysis was last updated",
        example="2024-01-20T10:35:00Z"
    )

    class Config:
        """Pydantic model configuration."""
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "user_id": "123e4567-e89b-12d3-a456-426614174001",
                "exercise_type": "squat",
                "score": 85.5,
                "feedback": [
                    {
                        "type": "success",
                        "message": "Good depth achieved",
                        "timestamp": 12.5
                    },
                    {
                        "type": "warning",
                        "message": "Slight knee valgus detected",
                        "timestamp": 15.2
                    }
                ],
                "joint_angles": [
                    {
                        "joint": "knee",
                        "angle": 85.5,
                        "timestamp": 12.5
                    }
                ],
                "video_url": "https://storage.formiq.com/videos/exercise_123.mp4",
                "thumbnail_url": "https://storage.formiq.com/thumbnails/exercise_123.jpg",
                "created_at": "2024-01-20T10:30:00Z",
                "updated_at": "2024-01-20T10:35:00Z"
            }
        }

class FormAnalysisRequest(BaseModel):
    """Schema for form analysis request."""
    video_file: str = Field(..., description="Path to uploaded video file")
    exercise_type: ExerciseType = Field(..., description="Type of exercise being analyzed")
    user_id: UUID = Field(..., description="ID of the user submitting the analysis")
    notes: Optional[str] = Field(None, max_length=500, description="Additional notes about the exercise")

    @validator("exercise_type")
    def validate_exercise_type(cls, v):
        """Validate exercise type is supported."""
        if v not in ExerciseType.__members__:
            raise ValueError(f"Exercise type must be one of: {', '.join(ExerciseType.__members__.keys())}")
        return v

class FormAnalysisMetrics(BaseModel):
    """Schema for form analysis metrics."""
    alignment: confloat(ge=0.0, le=1.0) = Field(..., description="Body alignment score")
    stability: confloat(ge=0.0, le=1.0) = Field(..., description="Movement stability score")
    symmetry: confloat(ge=0.0, le=1.0) = Field(..., description="Left-right symmetry score")
    consistency: confloat(ge=0.0, le=1.0) = Field(..., description="Movement consistency score")
    joint_accuracy: confloat(ge=0.0, le=1.0) = Field(..., description="Joint positioning accuracy")
    movement_quality: confloat(ge=0.0, le=1.0) = Field(..., description="Overall movement quality")

class FormAnalysisResult(BaseModel):
    """Schema for form analysis result."""
    id: UUID = Field(..., description="Unique identifier for the analysis")
    exercise_type: ExerciseType = Field(..., description="Type of exercise analyzed")
    confidence: confloat(ge=0.0, le=1.0) = Field(..., description="Model confidence score")
    metrics: FormAnalysisMetrics = Field(..., description="Detailed form metrics")
    feedback: List[str] = Field(..., description="List of feedback messages")
    suggestions: List[str] = Field(..., description="List of improvement suggestions")
    risk_level: str = Field(..., description="Exercise risk level assessment")
    comparison_score: Optional[float] = Field(None, description="Score compared to previous attempts")
    joint_analysis: Optional[Dict[str, float]] = Field(None, description="Joint angle analysis")
    movement_analysis: Optional[Dict[str, List[float]]] = Field(None, description="Movement velocity analysis")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Analysis timestamp")

    @validator("risk_level")
    def validate_risk_level(cls, v):
        """Validate risk level value."""
        valid_levels = ["low", "medium", "high"]
        if v not in valid_levels:
            raise ValueError(f"Risk level must be one of: {', '.join(valid_levels)}")
        return v

class FormAnalysisHistoryRequest(BaseModel):
    """Schema for requesting form analysis history."""
    user_id: UUID = Field(..., description="User ID to get history for")
    exercise_type: Optional[ExerciseType] = Field(None, description="Filter by exercise type")
    start_date: Optional[datetime] = Field(None, description="Start date for history range")
    end_date: Optional[datetime] = Field(None, description="End date for history range")
    limit: Optional[int] = Field(10, ge=1, le=100, description="Maximum number of results")
    offset: Optional[int] = Field(0, ge=0, description="Number of results to skip")

    @validator("end_date")
    def validate_date_range(cls, v, values):
        """Validate end_date is after start_date if both are provided."""
        if v and "start_date" in values and values["start_date"]:
            if v <= values["start_date"]:
                raise ValueError("End date must be after start date")
        return v 