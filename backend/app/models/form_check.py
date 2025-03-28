from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database import Base
from .enums import FormCheckStatus

class FormCheck(Base):
    __tablename__ = "form_checks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    exercise_type = Column(String, nullable=False)
    video_url = Column(String, nullable=False)
    analysis_url = Column(String)  # URL to the analyzed video with overlays
    score = Column(Float, nullable=False)
    overall_feedback = Column(String, nullable=False)
    issues = Column(JSON, nullable=False)  # Stored as JSON
    status = Column(String, default=FormCheckStatus.PENDING, nullable=False)
    processing_time = Column(Float, nullable=True)  # Time taken to process the video
    confidence_score = Column(Float, nullable=True)  # AI model confidence score
    metadata = Column(JSON, nullable=True)  # Additional metadata about the form check
    results = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    user = relationship("User", back_populates="form_checks")
    feedback_items = relationship("FeedbackItem", back_populates="form_check", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<FormCheck {self.id} - {self.exercise_type}>"

class FeedbackItem(Base):
    __tablename__ = "feedback_items"

    id = Column(Integer, primary_key=True, index=True)
    form_check_id = Column(Integer, ForeignKey("form_checks.id", ondelete="CASCADE"), nullable=False)
    type = Column(String, nullable=False)  # success, warning, error
    message = Column(String, nullable=False)
    timestamp = Column(Float, nullable=False)  # Timestamp in the video where this feedback applies
    severity = Column(String, nullable=False)  # low, medium, high
    joint_angles = Column(JSON, nullable=True)  # Joint angles at this timestamp
    suggestions = Column(JSON, nullable=True)  # Improvement suggestions

    form_check = relationship("FormCheck", back_populates="feedback_items")

    def __repr__(self):
        return f"<FeedbackItem {self.id} - {self.type}>" 