"""TrainingSession model — generic workout session log for Train Analysis persistence."""
from sqlalchemy import Column, DateTime, JSON, String, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class TrainingSession(Base):
    """
    Stores a user's completed workout session from Train Analysis (WorkoutsPage).

    Uses a String primary key so the client-generated UUID from makeId() is used
    as the row ID.  This makes POST idempotent: retrying after a network error
    returns the existing row rather than inserting a duplicate.

    sets_json stores the full SetLog[] array verbatim from the frontend types.
    No squat-specific columns — this table is exercise-agnostic.
    """
    __tablename__ = "training_sessions"

    # Client-generated UUID string from makeId() / crypto.randomUUID()
    id = Column(String, primary_key=True)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    started_at = Column(DateTime(timezone=True), nullable=False)
    goal = Column(String(20), nullable=False)        # "strength" | "hypertrophy" | "general"
    sets_json = Column(JSON, nullable=False, default=list)  # List[SetLog] verbatim
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    user = relationship("User")
