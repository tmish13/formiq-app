"""Video upload schemas for validation."""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, validator, constr
from fastapi import UploadFile
from datetime import datetime
from uuid import UUID

from app.models.enums import VideoStatus
from app.core.config import settings

class AngleDataItem(BaseModel):
    """Schema for a single calculated angle data point."""
    angle_name: str = Field(..., description="Name of the calculated angle")
    value: float = Field(..., description="Value of the calculated angle")

class VideoBase(BaseModel):
    """Base Video schema."""
    filename: str
    mime_type: str
    size: Optional[int] = None
    url: Optional[str] = None

class VideoCreate(VideoBase):
    """Schema for creating a new video."""
    user_id: UUID
    status: str = "pending"
    object_key: Optional[str] = None
    exercise_type: Optional[str] = None

    @validator("mime_type")
    def validate_mime_type(cls, v):
        if not v.startswith("video/"):
            raise ValueError("MIME type must be a video format")
        return v

class VideoUpdate(BaseModel):
    """Schema for updating an existing video."""
    filename: Optional[constr(max_length=255)] = None
    mime_type: Optional[constr(max_length=100)] = None
    size: Optional[int] = None
    url: Optional[constr(max_length=2048)] = None
    status: Optional[VideoStatus] = None
    processed_url: Optional[constr(max_length=2048)] = None
    exercise_type: Optional[constr(max_length=100)] = None
    duration: Optional[float] = None
    resolution: Optional[constr(max_length=50)] = None
    fps: Optional[float] = None
    error_message: Optional[str] = None
    score: Optional[float] = None
    rep_count: Optional[int] = None
    pose_data: Optional[List[Optional[Dict[str, Any]]]] = None
    calculated_angles: Optional[List[Optional[AngleDataItem]]] = None

    @validator("mime_type", check_fields=False)
    def validate_update_mime_type(cls, v):
        if v is not None and not v.startswith("video/"):
            raise ValueError("MIME type must be a video format")
        return v

class VideoResponse(VideoBase):
    """Schema for returning video information."""
    id: UUID
    user_id: UUID
    status: str
    created_at: datetime
    updated_at: datetime
    celery_task_id: Optional[str] = None
    processed_url: Optional[str] = None
    exercise_type: Optional[str] = None
    duration: Optional[float] = None
    resolution: Optional[str] = None
    fps: Optional[float] = None
    error_message: Optional[str] = None
    score: Optional[float] = None
    rep_count: Optional[int] = None

    class Config:
        orm_mode = True
        from_attributes = True

class VideoAnalysisRequest(BaseModel):
    """Schema for requesting video analysis."""
    video_id: UUID = Field(..., description="ID of the video to analyze")
    # Add other analysis parameters here if needed in the future, e.g.:
    # analysis_type: Optional[str] = None
    # requested_metrics: Optional[List[str]] = None

class VideoFeedbackItem(BaseModel):
    """Schema for a feedback item."""
    joint: str
    phase: str
    message: str
    severity: str
    frame_examples: List[int] = []

class VideoAnalysisResult(BaseModel):
    """Schema for video analysis results."""
    video_id: str
    score: float = Field(..., ge=0, le=10, description="Overall form score")
    rep_count: int = Field(0, ge=0, description="Number of repetitions detected")
    feedback: List[VideoFeedbackItem] = []
    phases: List[Dict[str, Any]] = []
    issues: List[Dict[str, Any]] = []

class VideoAnalysis(BaseModel):
    """Schema for video analysis results."""
    video_id: str = Field(..., description="ID of the analyzed video")
    score: float = Field(..., ge=0, le=100, description="Overall form score")
    feedback: List[str] = Field(default_factory=list, description="List of feedback points")
    joint_angles: Dict[str, float] = Field(default_factory=dict, description="Joint angles detected")
    spine_alignment: float = Field(..., ge=0, le=1, description="Spine alignment score")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional analysis metadata")
    
    class Config:
        """Pydantic configuration."""
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class VideoUploadRequest(VideoBase):
    """Schema for video upload request."""
    file: UploadFile = Field(..., description="Video file to upload")
    
    @validator("file")
    def validate_file(cls, v):
        """Validate video file."""
        # Get allowed types from settings
        allowed_types = settings.ALLOWED_VIDEO_TYPES
        max_size = settings.MAX_VIDEO_SIZE
        
        # Check content type
        content_type = v.content_type
        if not content_type or not any(t in content_type for t in allowed_types):
            raise ValueError(f"Invalid file type. Allowed types: {', '.join(allowed_types)}")
        
        # Check file size
        if hasattr(v.file, 'seek') and hasattr(v.file, 'tell'):
            pos = v.file.tell()
            v.file.seek(0, 2)  # Seek to end
            size = v.file.tell()
            v.file.seek(pos)  # Back to original position
            
            if size > max_size:
                raise ValueError(f"File size exceeds maximum allowed size of {max_size/1024/1024:.1f}MB")
        
        return v

class VideoUploadResponse(BaseModel):
    """Schema for video upload response."""
    upload_url: str
    video_id: str
    object_key: str
    expires_in: int
    fields: Dict[str, Any] = {} 