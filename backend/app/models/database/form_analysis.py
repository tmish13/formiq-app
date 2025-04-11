from sqlalchemy import Column, String, Float, JSON, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from ..database import Base

class FormAnalysis(Base):
    __tablename__ = "form_analyses"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    exercise_type = Column(String, nullable=True)
    video_url = Column(String, nullable=False)
    confidence = Column(Float, nullable=False)
    keypoints = Column(JSON, nullable=False)
    metrics = Column(JSON, nullable=False)
    feedback = Column(JSON, nullable=False)  # List of strings
    suggestions = Column(JSON, nullable=False)  # List of strings
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="form_analyses")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "exercise_type": self.exercise_type,
            "video_url": self.video_url,
            "confidence": self.confidence,
            "keypoints": self.keypoints,
            "metrics": self.metrics,
            "feedback": self.feedback,
            "suggestions": self.suggestions,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        } 