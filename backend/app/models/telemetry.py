"""Telemetry models for ML inference logging."""
import uuid
from sqlalchemy import Column, String, Integer, Float, Text, DateTime, JSON, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.models.base import SQLiteUUID
from app.db.base_class import Base


class PostureV1InferenceLog(Base):
    """
    Stores telemetry for every PostureV1 inference run.

    This table is append-only and used for debugging, monitoring,
    and shadow-mode analysis. Writes are best-effort — a failure
    to log must never break the main processing pipeline.
    """
    __tablename__ = "posture_v1_inference_logs"

    id = Column(SQLiteUUID(), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    form_check_id = Column(
        SQLiteUUID(),
        ForeignKey("form_checks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    video_id = Column(SQLiteUUID(), nullable=True)

    # Inference outcome
    decision = Column(String(20), nullable=False)
    prob_fault = Column(Float, nullable=True)
    confidence = Column(Float, nullable=True)
    threshold = Column(Float, nullable=True)
    threshold_mode = Column(String(20), nullable=True)
    posture_v1_mode = Column(String(10), nullable=True)  # "active" or "shadow"

    # Data quality
    sequence_length = Column(Integer, nullable=True)
    missing_ratio = Column(Float, nullable=True)
    outlier_z_gt3 = Column(Integer, nullable=True)
    outlier_z_gt6 = Column(Integer, nullable=True)
    angle_validity = Column(JSON, nullable=True)
    gate_flags = Column(JSON, nullable=True)

    # Scoring details
    top_signals = Column(JSON, nullable=True)
    named_scores = Column(JSON, nullable=True)

    # Model metadata
    model_version = Column(String(50), nullable=True)
    latency_ms = Column(Float, nullable=True)

    # Error tracking
    error = Column(Text, nullable=True)

    form_check = relationship("FormCheck", lazy="select")
