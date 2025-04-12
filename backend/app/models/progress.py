"""Database models for progress tracking."""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class ExerciseProgress(Base):
    """Model for tracking exercise progress."""
    __tablename__ = "exercise_progress"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    exercise_type = Column(String(50), nullable=False)
    form_score = Column(Float, nullable=False, default=0.0)
    consistency_score = Column(Float, nullable=False, default=0.0)
    total_reps = Column(Integer, nullable=False, default=0)
    improvement_areas = Column(Text, nullable=False, default="[]")  # JSON string
    last_updated = Column(DateTime, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="exercise_progress")
    
    class Config:
        """Pydantic config."""
        orm_mode = True

class ProgressSnapshot(Base):
    """Model for storing progress snapshots."""
    __tablename__ = "progress_snapshots"
    
    id = Column(Integer, primary_key=True, index=True)
    progress_id = Column(Integer, ForeignKey("exercise_progress.id"), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    form_score = Column(Float, nullable=False)
    consistency_score = Column(Float, nullable=False)
    reps = Column(Integer, nullable=False)
    notes = Column(Text, nullable=True)
    
    # Relationships
    progress = relationship("ExerciseProgress", backref="snapshots")
    
    class Config:
        """Pydantic config."""
        orm_mode = True 