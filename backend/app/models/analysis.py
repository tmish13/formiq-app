"""Analysis models module."""
from enum import Enum
from sqlalchemy import Column, String, ForeignKey, DateTime, Float, JSON, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models.base import BaseModel, SQLiteUUID
import uuid

class AnalysisStatus(str, Enum):
    """Analysis status enum."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class Analysis(BaseModel):
    """Analysis model for storing form analysis results."""
    
    __tablename__ = "analyses"

    id = Column(SQLiteUUID(), primary_key=True, default=uuid.uuid4, index=True)
    video_id = Column(SQLiteUUID(), ForeignKey("videos.id"), nullable=False)
    user_id = Column(SQLiteUUID(), ForeignKey("users.id"), nullable=False)
    status = Column(SQLEnum(AnalysisStatus), default=AnalysisStatus.PENDING)
    score = Column(Float, nullable=True)
    feedback = Column(JSON, nullable=True)
    joint_angles = Column(JSON, nullable=True)
    spine_alignment = Column(Float, nullable=True)
    analysis_metadata = Column(JSON, nullable=True)
    error_message = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    video = relationship("Video", back_populates="analyses")
    user = relationship("User", back_populates="analyses")

    def __repr__(self) -> str:
        """String representation of the analysis."""
        return f"<Analysis {self.id}: {self.status}>" 