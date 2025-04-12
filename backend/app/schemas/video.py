"""Video upload schemas for validation."""
from typing import Optional
from pydantic import BaseModel, Field, validator, constr
from fastapi import UploadFile

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