"""Video model module."""
from typing import Optional
from sqlalchemy import Column, String, ForeignKey, DateTime, Integer, Float, JSON, Boolean, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models.base import BaseModel, SQLiteUUID
import uuid
import enum

class VideoStatus(str, enum.Enum):
    """Video processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class Video(BaseModel):
    """Video model for storing video metadata and processing status."""
    
    __tablename__ = "videos"

    id = Column(SQLiteUUID(), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(SQLiteUUID(), ForeignKey("users.id"), nullable=False)
    filename = Column(String, nullable=False)
    url = Column(String, nullable=True)
    status = Column(Enum(VideoStatus), default=VideoStatus.PENDING)  # pending, processing, completed, failed
    duration = Column(Float, nullable=True)
    size = Column(Integer, nullable=True)  # in bytes
    mime_type = Column(String, nullable=True)
    video_metadata = Column(JSON, nullable=True)
    is_processed = Column(Boolean, default=False)
    error_message = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="videos")
    form_checks = relationship("FormCheck", back_populates="video", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        """String representation of the video."""
        return f"<Video {self.id}: {self.filename}>" 