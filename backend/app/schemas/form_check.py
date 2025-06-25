"""Form check schema module."""
from datetime import datetime
from typing import Dict, List, Optional, Literal, Any, Union
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, HttpUrl, constr, confloat, ConfigDict
from app.models.enums import FeedbackType, FeedbackSeverity, FormCheckStatus, ExerciseType


class FormCheckBase(BaseModel):
    """
    Base model for form check data.
    
    Attributes:
        video_url: URL to the uploaded video file
        exercise_id: Reference to the exercise template
        feedback: Optional textual feedback on the form check
        score: Optional score from 0-100 representing form quality
        keypoints: Optional list of keypoint data from pose detection
        status: Current processing status of the form check
    """
    video_url: str = Field(..., description="URL to the uploaded video file")
    exercise_id: UUID = Field(..., description="Reference to the exercise template")
    feedback: Optional[str] = Field(None, description="DEPRECATED: Use overall_feedback for summary and FeedbackItem for specifics.")
    score: Optional[float] = Field(None, description="Score from 0-100 representing form quality")
    keypoints: Optional[List[Dict[str, float]]] = Field(None, description="List of keypoint data from pose detection")
    status: FormCheckStatus = Field(FormCheckStatus.PENDING, description="Current processing status")
    
    @field_validator("video_url")
    @classmethod
    def validate_video_url(cls, v: Optional[str]) -> Optional[str]:
        """
        Validate that the video URL is properly formatted.
        
        Args:
            v: Video URL value
            
        Returns:
            str: Valid video URL or None
        """
        if v is None:
            return v
        
        if not v.startswith(("http://", "https://", "s3://")):
            raise ValueError("Video URL must be a valid HTTP, HTTPS, or S3 URL")
        return v
    
    @field_validator("score")
    @classmethod
    def validate_score(cls, v: Optional[float]) -> Optional[float]:
        """
        Validate that the score is between 0 and 100.
        
        Args:
            v: Score value
            
        Returns:
            float: Valid score or None
        """
        if v is None:
            return v
        
        if not (0 <= v <= 100):
            raise ValueError("Score must be between 0 and 100")
        return v


class FormCheckCreate(BaseModel):
    """Schema for creating a new form check."""
    user_id: UUID = Field(..., description="ID of the user submitting the form check")
    exercise_id: UUID = Field(..., description="ID of the exercise template")
    video_url: str = Field(..., description="URL to the uploaded video")
    notes: Optional[str] = Field(None, description="Optional user notes for the form check")
    status: FormCheckStatus = Field(FormCheckStatus.PENDING, description="Initial status of the form check")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "4e059a37-95ac-4a40-8a0d-6690864d9890",
                "exercise_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "video_url": "https://example.com/video.mp4",
                "notes": "Checking my squat depth.",
                "status": "pending"
            }
        }
    )


class FormCheckUpdate(BaseModel):
    """
    Schema for updating an existing form check.
    
    All fields are optional to allow partial updates.
    """
    video_url: Optional[str] = None
    exercise_id: Optional[UUID] = None
    status: Optional[FormCheckStatus] = None
    overall_feedback: Optional[str] = None
    score: Optional[float] = Field(None, ge=0, le=100, description="Score from 0-100")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional details or metadata from analysis")
    classified_exercise_slug: Optional[str] = Field(None, description="AI-classified exercise slug")
    classification_confidence: Optional[float] = Field(None, ge=0, le=1, description="Confidence of AI exercise classification")


class FormCheckResponse(BaseModel):
    """
    Schema for form check response.
    """
    id: str = Field(..., description="Form check ID")
    user_id: str = Field(..., description="User ID")
    exercise_id: str = Field(..., description="Exercise ID")
    video_url: str = Field(..., description="URL to the uploaded video")
    status: str = Field(..., description="Processing status")
    created_at: datetime = Field(..., description="Creation timestamp")
    classified_exercise_slug: Optional[str] = Field(None, description="AI-classified exercise slug")
    classification_confidence: Optional[float] = Field(None, description="Confidence of AI exercise classification")
    form_metadata: Optional[Dict[str, Any]] = Field(None, description="Aggregated scores, issues, and summary stats for UI.")
    feedback: Optional[str] = Field(None, description="DEPRECATED: Use overall_feedback and FeedbackItem.details_payload")
    issues: Optional[Any] = Field(None, description="DEPRECATED: Use FeedbackItem.details_payload")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "user_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "exercise_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "video_url": "https://example.com/video.mp4",
                "status": "pending",
                "created_at": "2023-01-01T00:00:00Z",
                "classified_exercise_slug": "squat",
                "classification_confidence": 0.95,
                "form_metadata": {
                    "total_form_checks": 10,
                    "pending_form_checks": 2,
                    "completed_form_checks": 8,
                    "average_score": 85.5,
                    "best_exercise": "Squat",
                    "worst_exercise": "Squat"
                },
                "feedback": "Your form is mostly good, with 2 minor issues to fine-tune.",
                "issues": {
                    "leftKnee": "Knees are going too far forward",
                    "rightKnee": "Knees are going too far forward"
                }
            }
        }
    )


class FormCheckListResponse(BaseModel):
    """
    Schema for form check list response, includes summary information.
    """
    id: str = Field(..., description="Form check ID")
    user_id: str = Field(..., description="User ID")
    exercise_id: str = Field(..., description="Exercise ID")
    video_url: str = Field(..., description="URL to the uploaded video")
    status: str = Field(..., description="Processing status")
    score: Optional[float] = Field(None, description="Overall form score (0-100)")
    overall_feedback: Optional[str] = Field(None, description="Summary feedback")
    created_at: datetime = Field(..., description="Creation timestamp")
    exercise_name: Optional[str] = Field(None, description="Name of the exercise")
    configuration_id: Optional[str] = Field(None, description="ID of the configuration used")
    configuration_name: Optional[str] = Field(None, description="Name of the configuration used")
    classified_exercise_slug: Optional[str] = Field(None, description="AI-classified exercise slug")
    classification_confidence: Optional[float] = Field(None, description="Confidence of AI exercise classification")
    form_metadata: Optional[Dict[str, Any]] = Field(None, description="Aggregated scores, issues, and summary stats for UI.")
    issues: Optional[Any] = Field(None, description="DEPRECATED: Use FeedbackItem.details_payload")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "user_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "exercise_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "video_url": "https://example.com/video.mp4",
                "status": "completed",
                "score": 85.5,
                "overall_feedback": "Your form is mostly good, with 2 minor issues to fine-tune.",
                "created_at": "2023-01-01T00:00:00Z",
                "exercise_name": "Squat",
                "configuration_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "configuration_name": "Squat Standard Configuration",
                "classified_exercise_slug": "squat",
                "classification_confidence": 0.95,
                "form_metadata": {
                    "total_form_checks": 10,
                    "pending_form_checks": 2,
                    "completed_form_checks": 8,
                    "average_score": 85.5,
                    "best_exercise": "Squat",
                    "worst_exercise": "Squat"
                },
                "issues": {
                    "leftKnee": "Knees are going too far forward",
                    "rightKnee": "Knees are going too far forward"
                }
            }
        }
    )


class FeedbackItemResponse(BaseModel):
    """
    Schema for feedback item response.
    """
    id: int = Field(..., description="Feedback item ID")
    form_check_id: str = Field(..., description="Form check ID")
    type: str = Field(..., description="Type of feedback")
    message: str = Field(..., description="Feedback message")
    timestamp: float = Field(..., description="Video timestamp in seconds")
    severity: str = Field(..., description="Feedback severity level")
    joint_angles: Optional[Dict[str, float]] = Field(None, description="Joint angle measurements")
    suggestions: Optional[List[str]] = Field(None, description="Improvement suggestions")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "form_check_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "type": "form",
                "message": "Your knees are going too far forward",
                "timestamp": 2.5,
                "severity": "medium",
                "joint_angles": {"leftKnee": 85.2, "rightKnee": 87.5},
                "suggestions": ["Keep your knees aligned with your toes"]
            }
        }
    )


class FormCheckDetailedResponse(FormCheckListResponse):
    """
    Schema for detailed form check response, including ML scores, feedback items, and visual overlay data.
    """
    # ML Model Scores (0-100 scale)
    posture_score: Optional[float] = Field(None, description="Posture score from ML model (0-100)")
    stability_score: Optional[float] = Field(None, description="Stability score from ML model (0-100)")
    depth_score: Optional[float] = Field(None, description="Depth/range of motion score from ML model (0-100)")
    
    # Visual Overlay Data
    feedback_items: Optional[List[FeedbackItemResponse]] = Field(None, description="List of detailed feedback items")
    reference_pose_data: Optional[Dict[str, Any]] = Field(None, description="Reference pose data for visual overlays")
    visual_overlay_data: Optional[Dict[str, Any]] = Field(None, description="Data for rendering pose comparison overlays")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "user_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "exercise_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "video_url": "https://example.com/video.mp4",
                "status": "completed",
                "score": 85.5,
                "overall_feedback": "Your form is mostly good, with 2 minor issues to fine-tune.",
                "created_at": "2023-01-01T00:00:00Z",
                "exercise_name": "Squat",
                "configuration_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "configuration_name": "Squat Standard Configuration",
                "classified_exercise_slug": "squat",
                "classification_confidence": 0.95,
                "posture_score": 88.5,
                "stability_score": 82.0,
                "depth_score": 90.5,
                "form_metadata": {
                    "total_form_checks": 10,
                    "pending_form_checks": 2,
                    "completed_form_checks": 8,
                    "average_score": 85.5,
                    "best_exercise": "Squat",
                    "worst_exercise": "Squat"
                },
                "issues": {
                    "leftKnee": "Knees are going too far forward",
                    "rightKnee": "Knees are going too far forward"
                },
                "feedback_items": [
                    {
                        "id": 1,
                        "form_check_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                        "type": "form",
                        "message": "Your knees are going too far forward",
                        "timestamp": 2.5,
                        "severity": "medium",
                        "joint_angles": {"leftKnee": 85.2, "rightKnee": 87.5},
                        "suggestions": ["Keep your knees aligned with your toes"]
                    }
                ],
                "reference_pose_data": {
                    "pose_sequence": [...],
                    "key_poses": {"setup": {...}, "bottom": {...}},
                    "metadata": {"exercise_type": "squat"}
                },
                "visual_overlay_data": {
                    "similarity_score": 0.82,
                    "alignment_quality": "good",
                    "joint_colors": {"left_knee": {"color": "#4CAF50", "similarity": 0.85}},
                    "deviation_highlights": [],
                    "connection_lines": []
                }
            }
        }
    )


class FeedbackItemBase(BaseModel):
    """
    Base model for feedback item data.
    
    Attributes:
        feedback_type: Type of feedback (form, technique, etc.)
        description: Detailed feedback message
        timestamp: Timestamp in the video where feedback applies
        severity: Severity level of the feedback
        suggestions: List of improvement suggestions
    """
    feedback_type: FeedbackType = Field(..., description="Type of feedback")
    description: constr(min_length=10, max_length=1000) = Field(..., description="Detailed feedback message")
    timestamp: confloat(ge=0.0) = Field(..., description="Timestamp in the video where feedback applies (seconds)")
    severity: FeedbackSeverity = Field(..., description="Severity level of the feedback")
    suggestions: Optional[List[constr(max_length=500)]] = Field(None, description="List of improvement suggestions")
    is_ai_generated: bool = Field(False, description="Whether this feedback was generated by AI")
    joint_angles: Optional[Dict[str, float]] = Field(None, description="Joint angle measurements")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "feedback_type": "FORM",
                "description": "Your knees are caving inward during the descent phase of the squat.",
                "timestamp": 15.5,
                "severity": "MEDIUM",
                "suggestions": ["Focus on pushing knees outward", "Try a slightly wider stance"],
                "is_ai_generated": True,
                "joint_angles": {
                    "left_knee": 85.3,
                    "right_knee": 82.7
                }
            }
        }
    )

    @field_validator("suggestions")
    @classmethod
    def validate_suggestions(cls, v: Optional[List[constr(max_length=500)]]) -> Optional[List[constr(max_length=500)]]:
        """Validate suggestions list."""
        if v is None:
            return v
        
        if not isinstance(v, list):
            raise ValueError("Suggestions must be a list")
        
        if any(not isinstance(s, str) for s in v):
            raise ValueError("All suggestions must be strings")
        
        if len(v) > 10:
            raise ValueError("Maximum 10 suggestions allowed")
        
        return v
    
    @field_validator("joint_angles")
    @classmethod
    def validate_joint_angles(cls, v: Optional[Dict[str, float]]) -> Optional[Dict[str, float]]:
        """Validate joint angles dictionary."""
        if v is None:
            return v
        
        if not isinstance(v, dict):
            raise ValueError("Joint angles must be a dictionary")
        
        for key, value in v.items():
            if not isinstance(key, str):
                raise ValueError("Joint angle keys must be strings")
            
            if not isinstance(value, (int, float)):
                raise ValueError("Joint angle values must be numbers")
        
        return v


class FeedbackItemCreate(BaseModel):
    """
    Schema for creating a feedback item.
    """
    form_check_id: UUID = Field(..., description="Form check ID")
    type: FeedbackType = Field(..., description="Type of feedback")
    message: str = Field(..., description="Feedback message")
    timestamp: float = Field(..., description="Video timestamp in seconds")
    severity: FeedbackSeverity = Field(..., description="Feedback severity level")
    joint_angles: Optional[Dict[str, float]] = Field(None, description="Joint angle measurements")
    suggestions: Optional[List[str]] = Field(None, description="Improvement suggestions")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "form_check_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "type": "form",
                "message": "Your knees are going too far forward",
                "timestamp": 2.5,
                "severity": "medium",
                "joint_angles": {"leftKnee": 85.2, "rightKnee": 87.5},
                "suggestions": ["Keep your knees aligned with your toes"]
            }
        }
    )


class FeedbackItemUpdate(BaseModel):
    """
    Schema for updating an existing feedback item.
    
    All fields are optional to allow partial updates.
    """
    feedback_type: Optional[FeedbackType] = None
    description: Optional[constr(min_length=10, max_length=1000)] = None
    timestamp: Optional[confloat(ge=0.0)] = None
    severity: Optional[FeedbackSeverity] = None
    suggestions: Optional[List[constr(max_length=500)]] = None
    joint_angles: Optional[Dict[str, float]] = None


class FormCheckCompleteRequest(BaseModel):
    """
    Schema for completing a form check analysis.
    """
    summary: constr(min_length=10, max_length=2000) = Field(..., description="Overall feedback summary")
    overall_score: confloat(ge=0.0, le=10.0) = Field(..., description="Score from 0-10")


class FormCheckSummaryStats(BaseModel):
    """
    Schema for form check summary statistics.
    """
    total_form_checks: int
    pending_form_checks: int
    completed_form_checks: int
    average_score: Optional[float] = None
    best_exercise: Optional[str] = None
    worst_exercise: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True) 