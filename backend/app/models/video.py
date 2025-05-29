"""Video model module."""
from typing import Optional, List, Dict, Any
from sqlalchemy import Column, String, ForeignKey, DateTime, Integer, Float, JSON, Boolean, Enum as SQLAEnum, BigInteger, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models.base import BaseModel, SQLiteUUID
import uuid
from app.models.enums import VideoStatus
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func

class Video(BaseModel):
    """Video model for storing video metadata and processing status."""
    
    __tablename__ = "videos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String, nullable=False)
    object_key = Column(String, nullable=True, unique=True)
    url = Column(String, nullable=True)
    processed_url = Column(String, nullable=True)  # URL to processed video
    exercise_type = Column(String, nullable=True)  # Type of exercise in the video
    mime_type = Column(String, nullable=False)
    size = Column(BigInteger, nullable=True)
    duration = Column(Float, nullable=True)  # Duration in seconds
    resolution = Column(String, nullable=True)  # Resolution, e.g., "1280x720"
    fps = Column(Float, nullable=True)  # Frames per second
    status = Column(SQLAEnum(VideoStatus), default=VideoStatus.UPLOADED, nullable=False)
    processing_errors = Column(JSON, nullable=True) # Store detailed error information, potentially structured
    error_message = Column(Text, nullable=True) # For simple, top-level error messages
    processed_object_key = Column(String, nullable=True) # S3 key for the processed/normalized video
    frame_s3_keys = Column(JSON, nullable=True) # S3 keys for processed frames
    processed_frame_count = Column(Integer, nullable=True)
    thumbnail_s3_key = Column(String, nullable=True) # S3 key for the video thumbnail
    thumbnail_url = Column(String, nullable=True) # URL for the video thumbnail
    additional_metadata = Column(JSON, nullable=True)  # Renamed from metadata - General metadata
    pose_data = Column(JSON, nullable=True)  # Pose keypoints data
    pose_visualizations = Column(JSON, nullable=True)  # URLs to pose visualization frames
    analysis_results = Column(JSON, nullable=True)  # Form analysis results
    stats = Column(JSON, nullable=True)  # Processing statistics
    score = Column(Float, nullable=True)  # Overall form score
    rep_count = Column(Integer, nullable=True)  # Number of repetitions detected
    feedback = Column(JSON, nullable=True)  # Feedback items for the user
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    # AI Processing Results
    raw_pose_data = Column(JSON, nullable=True) # Stores list of landmarks (or None) for each frame
    # analysis_results = Column(JSONB, nullable=True) # For future detailed analysis output

    # Added for AI Pipeline Step 1.3
    calculated_angles = Column(JSON, nullable=True)

    celery_task_id = Column(String, nullable=True) # Added field for Celery task ID

    # Relationships
    user = relationship("User", back_populates="videos")
    form_checks = relationship("FormCheck", back_populates="video", cascade="all, delete-orphan", foreign_keys="FormCheck.video_id")

    def __repr__(self) -> str:
        """String representation of the video."""
        return f"<Video(id={self.id}, user_id={self.user_id}, filename={self.filename}, status={self.status})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the model to a dictionary."""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "filename": self.filename,
            "object_key": self.object_key,
            "url": self.url,
            "processed_url": self.processed_url,
            "exercise_type": self.exercise_type,
            "mime_type": self.mime_type,
            "size": self.size,
            "duration": self.duration,
            "resolution": self.resolution,
            "fps": self.fps,
            "status": self.status.value if self.status else None,
            "processing_errors": self.processing_errors,
            "processed_object_key": self.processed_object_key,
            "frame_s3_keys": self.frame_s3_keys,
            "processed_frame_count": self.processed_frame_count,
            "thumbnail_s3_key": self.thumbnail_s3_key,
            "thumbnail_url": self.thumbnail_url,
            "score": self.score,
            "rep_count": self.rep_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            # Exclude large fields: pose_data, pose_visualizations, analysis_results, stats, feedback
        } 