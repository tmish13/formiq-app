"""Exercise model module."""
from sqlalchemy import Column, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.models.base import BaseModel


class ExerciseTemplate(BaseModel):
    """Exercise template model for storing exercise definitions."""

    __tablename__ = "exercise_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    video_url = Column(String)
    difficulty = Column(String)
    muscle_group = Column(String)
    equipment = Column(String)

    # Relationships
    form_checks = relationship("FormCheck", back_populates="exercise", cascade="all, delete-orphan", lazy="select") 