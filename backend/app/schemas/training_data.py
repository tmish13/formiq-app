from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from app.models.enums import ExerciseType

class TrainingDataSubmission(BaseModel):
    """Schema for training data submission from external sources like Zapier."""
    
    exercise_type: str = Field(..., description="The type of exercise (e.g., squat, pushup)")
    source: str = Field(..., description="Source of the training data (e.g., google_form, youtube)")
    expert_score: float = Field(..., description="Expert-assigned form score (0.0-1.0)")
    feedback: List[str] = Field(default=[], description="Feedback points for the exercise")
    metadata: Dict[str, Any] = Field(default={}, description="Additional metadata about the submission")
    
    # Optional fields
    video_url: Optional[str] = Field(None, description="URL to the video (if available)")
    keypoints: Optional[List[Dict[str, Any]]] = Field(None, description="Pre-extracted pose keypoints (if available)")
    user_height_cm: Optional[float] = Field(None, description="User height in centimeters (if available)")
    user_weight_kg: Optional[float] = Field(None, description="User weight in kilograms (if available)")
    
    class Config:
        schema_extra = {
            "example": {
                "exercise_type": "squat",
                "source": "google_form",
                "expert_score": 0.85,
                "feedback": ["Knees tracking too far forward", "Good depth"],
                "metadata": {
                    "trainer_id": "T12345",
                    "training_session": "advanced_form_review",
                    "date_recorded": "2025-04-10"
                },
                "video_url": "https://storage.example.com/videos/squat_training_123.mp4",
                "user_height_cm": 175,
                "user_weight_kg": 70
            }
        }

class TrainingDataResponse(BaseModel):
    """Response schema for training data submission."""
    
    success: bool = Field(..., description="Whether the submission was successful")
    message: str = Field(..., description="Message about the submission")
    submission_id: Optional[str] = Field(None, description="ID of the submission for tracking") 