"""Exercise model module."""
from sqlalchemy import Column, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.models.base import BaseModel, SQLiteUUID


class ExerciseTemplate(BaseModel):
    """
    Exercise template model for storing exercise definitions.
    
    This model defines the basic information about each exercise type,
    which can be used as templates for workout exercises.
    
    Attributes:
        name (str): Name of the exercise
        description (str): Description of the exercise
        difficulty (str): Difficulty level (e.g., Beginner, Intermediate, Advanced)
        muscle_group (str): Primary muscle group worked
        equipment (str): Equipment required, if any
    """

    __tablename__ = "exercise_templates"

    id = Column(SQLiteUUID(), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    video_url = Column(String)
    difficulty = Column(String, nullable=False)
    muscle_group = Column(String, nullable=False)
    equipment = Column(String, nullable=True)

    # Relationships
    form_checks = relationship("FormCheck", back_populates="exercise", cascade="all, delete-orphan", lazy="select")
    exercise_configs = relationship("ExerciseConfig", back_populates="exercise", cascade="all, delete-orphan", lazy="select") 