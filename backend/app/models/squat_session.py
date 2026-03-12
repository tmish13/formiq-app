"""SquatSession model for storing user squat training sessions with ML scores."""
from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, Float, ForeignKey, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class SquatSession(BaseModel):
    """
    Stores a user's logged squat training session, including ML-derived component scores.

    Relationships:
    - Many-to-one with User
    - Many-to-one with FormCheck (nullable — session may be logged manually)
    """
    __tablename__ = "squat_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    form_check_id = Column(
        UUID(as_uuid=True),
        ForeignKey("form_checks.id", ondelete="SET NULL"),
        nullable=True,
    )

    date = Column(DateTime(timezone=True), nullable=False)
    working_weight_lb = Column(Float, nullable=False)
    overall_score = Column(Float, nullable=False)

    # ML component scores (0–100)
    torso_stability = Column(Float, nullable=False)
    knee_symmetry = Column(Float, nullable=False)
    bottom_control = Column(Float, nullable=False)
    forward_lean = Column(Float, nullable=False)

    primary_limiter = Column(String(50), nullable=False)
    notes = Column(Text, nullable=True)
    sets_json = Column(JSON, nullable=False, default=list)  # List[SquatTrainingSet]

    user = relationship("User", back_populates="squat_sessions")
    form_check = relationship("FormCheck")
