"""Video upload schemas for validation."""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, validator, constr
from fastapi import UploadFile
from datetime import datetime

from app.core.config import settings

class VideoUploadBase(BaseModel):
    """Base schema for video upload."""
    title: constr(min_length=3, max_length=100) = Field(..., description="Video title")
    description: Optional[constr(max_length=500)] = Field(None, description="Video description")
    exercise_type: constr(min_length=1) = Field(..., description="Type of exercise being performed")
    
    @validator("title")
    def validate_title(cls, v):
        """Validate video title."""
        if not v.strip():
            raise ValueError("Title cannot be empty or just whitespace")
        return v.strip()

class VideoCreate(VideoUploadBase):
    """Schema for creating a video record."""
    user_id: str = Field(..., description="ID of the user who uploaded the video")
    url: str = Field(..., description="URL where the video is stored")
    filename: str = Field(..., description="Original filename of the video")
    
    class Config:
        """Pydantic configuration."""
        from_attributes = True

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

class VideoUploadRequest(VideoUploadBase):
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

class VideoUploadResponse(VideoUploadBase):
    """Schema for video upload response."""
    id: str = Field(..., description="Unique identifier for the uploaded video")
    url: str = Field(..., description="URL where the video can be accessed")
    status: str = Field("processing", description="Processing status of the video")
    created_at: str = Field(..., description="Timestamp when the video was uploaded")
    
    class Config:
        """Pydantic configuration."""
        from_attributes = True 