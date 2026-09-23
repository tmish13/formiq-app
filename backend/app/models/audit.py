"""The decision trail: what was decided, by which checker, from which inputs.

WHY THESE TABLES EXIST
----------------------
Today the only record of a verdict is `posture_v1_inference_logs` (103 rows),
which is PostureV1-specific and carries no run id, no content hash, no feature
spec, no user, no task id and no attempt counter. Nothing records when an
analysis completed. A verdict cannot be reconstructed or explained after the
fact, which makes every claim about the pipeline unfalsifiable.

Two tables, deliberately shaped differently:

`analysis_runs` -- one row per task ATTEMPT, append-only. Holds the identity of
the computation: content_hash (what bytes), model_version (which weights),
spec_hash (which feature spec), rules_spec_hash (which rule constants) and
pose_pass_id (which MediaPipe extraction). All five are needed. The last one is
not bookkeeping: two passes over the same 221 videos moved 33 PostureV1
verdicts, 14.9%, while the paired CI on aggregate F1 spanned zero
(bench/results/2026-09-23-pose-pass-verdict-instability.md). Without it, one
verdict in seven is unexplainable.

`checker_decisions` -- one row per (run, checker, target). Holds what a named
checker concluded and the evidence it concluded it from.

NO FOREIGN KEY FROM analysis_runs
---------------------------------
`form_check_id`, `video_id` and `user_id` are plain columns. An audit row must
not change when its subject is deleted. `posture_v1_inference_logs` uses
`ON DELETE SET NULL`, so deleting a form check silently orphans its telemetry
from the thing it describes -- the row survives but can no longer be joined to
anything, which is the worst of both outcomes. `checker_decisions.run_id` IS a
real FK with CASCADE, because a checker decision is a part of its run and has
no meaning without it.

These inherit `Base`, not `BaseModel`. `BaseModel.__init__` silently filters
unknown kwargs, which is the same class of bug as the phantom `summary` and
`error_details` columns: a typo becomes a dropped field instead of an error.
An audit table is the last place that should happen.
"""
import uuid

from sqlalchemy import (
    Column, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text,
    Boolean, UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base_class import Base
from app.models.base import SQLiteUUID

#: Terminal and non-terminal states of a run. `running` with
#: `finished_at IS NULL` is what a SIGKILLed worker leaves behind; the reaper
#: sweeps those to `abandoned`.
RUN_STATUS_RUNNING = "running"
RUN_STATUS_COMPLETED = "completed"
RUN_STATUS_FAILED = "failed"
RUN_STATUS_RELEASED = "released"      # transient error; the row went back to PENDING
RUN_STATUS_ABANDONED = "abandoned"    # never closed itself; the reaper closed it

RUN_STATUSES = (
    RUN_STATUS_RUNNING, RUN_STATUS_COMPLETED, RUN_STATUS_FAILED,
    RUN_STATUS_RELEASED, RUN_STATUS_ABANDONED,
)


class AnalysisRun(Base):
    """One attempt at analysing one video. Append-only; never updated except
    to close it out (status, outcome, timings)."""

    __tablename__ = "analysis_runs"

    id = Column(SQLiteUUID(), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime(timezone=True), server_default=func.now(),
                        nullable=False, index=True)

    # --- subject (no FK, on purpose -- see module docstring) ---
    form_check_id = Column(SQLiteUUID(), nullable=True, index=True)
    video_id = Column(SQLiteUUID(), nullable=True)
    user_id = Column(SQLiteUUID(), nullable=True, index=True)

    # --- execution ---
    celery_task_id = Column(String(64), nullable=True, index=True)
    attempt = Column(Integer, nullable=False, default=0)
    worker_hostname = Column(String(255), nullable=True)
    status = Column(String(20), nullable=False, default=RUN_STATUS_RUNNING)
    outcome_status = Column(String(32), nullable=True)   # the FormCheckStatus written

    # --- identity of the computation. All five, or the verdict is not explicable. ---
    content_hash = Column(String(64), nullable=True, index=True)
    model_version = Column(String(50), nullable=True)
    spec_hash = Column(String(64), nullable=True)
    rules_spec_hash = Column(String(64), nullable=True)
    pose_pass_id = Column(String(32), nullable=True)
    combiner_version = Column(String(32), nullable=True)
    code_version = Column(String(64), nullable=True)

    # --- inputs as observed ---
    pose_source = Column(String(32), nullable=True)
    n_frames = Column(Integer, nullable=True)
    fps = Column(Float, nullable=True)
    duration_sec = Column(Float, nullable=True)
    settings_snapshot = Column(JSON, nullable=True)

    # --- outcome ---
    final_decision = Column(String(32), nullable=True)
    final_score = Column(Float, nullable=True)
    error_type = Column(String(64), nullable=True)
    error_message = Column(Text, nullable=True)

    latency_ms = Column(Float, nullable=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now(),
                        nullable=False)
    finished_at = Column(DateTime(timezone=True), nullable=True)

    decisions = relationship(
        "CheckerDecision", back_populates="run", lazy="select",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        # The reaper's scan: unclosed runs, oldest first.
        Index("ix_analysis_runs_status_started_at", "status", "started_at"),
    )

    def __repr__(self) -> str:
        return f"<AnalysisRun {self.id} {self.status} fc={self.form_check_id}>"


class CheckerDecision(Base):
    """What one named checker concluded about one target, and from what.

    `form_check_id` and `content_hash` are denormalised onto this row so that
    evaluation can join decisions to labels without touching `form_checks` --
    labels are keyed on content hash precisely so they survive re-analysis, and
    a join through a mutable table would defeat that.
    """

    __tablename__ = "checker_decisions"

    id = Column(SQLiteUUID(), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime(timezone=True), server_default=func.now(),
                        nullable=False, index=True)

    run_id = Column(
        SQLiteUUID(),
        ForeignKey("analysis_runs.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    form_check_id = Column(SQLiteUUID(), nullable=True, index=True)
    content_hash = Column(String(64), nullable=True, index=True)

    # --- who decided ---
    checker_name = Column(String(64), nullable=False)
    checker_kind = Column(String(32), nullable=True)     # model | rule | heuristic
    checker_version = Column(String(64), nullable=True)
    #: False means the checker's constants were never fitted to data. The
    #: combiner treats such a checker as ADVISORY: it contributes evidence and
    #: can never set a verdict on its own. Stored on the row, not only in the
    #: params artifact, so nothing downstream that reads the database can
    #: mistake a hand-set constant for a calibrated one.
    fitted = Column(Boolean, nullable=False, default=False)
    advisory = Column(Boolean, nullable=False, default=False)

    # --- what was decided ---
    target = Column(String(32), nullable=False)          # depth | posture | ...
    decision = Column(String(32), nullable=False)        # or "uncertain"
    abstained = Column(Boolean, nullable=False, default=False)
    abstain_reason = Column(String(64), nullable=True)

    score = Column(Float, nullable=True)
    prob = Column(Float, nullable=True)
    confidence = Column(Float, nullable=True)
    coverage = Column(Float, nullable=True)
    threshold = Column(Float, nullable=True)

    # --- from what ---
    indicators = Column(JSON, nullable=True)   # per-indicator value/normalised/weight
    quality = Column(JSON, nullable=True)
    #: sha256 of the exact keypoint array the checker saw. Makes the
    #: determinism claim auditable after the fact instead of asserted: the same
    #: digest through the same checker version must give the same decision.
    inputs_digest = Column(String(64), nullable=True)

    latency_ms = Column(Float, nullable=True)
    error = Column(Text, nullable=True)

    run = relationship("AnalysisRun", back_populates="decisions", lazy="select")

    __table_args__ = (
        # A retried write must not double-insert. One verdict per checker per
        # target per run.
        UniqueConstraint("run_id", "checker_name", "target",
                         name="uq_checker_decisions_run_checker_target"),
        Index("ix_checker_decisions_content_target", "content_hash", "target"),
    )

    def __repr__(self) -> str:
        return (f"<CheckerDecision {self.checker_name}/{self.target}="
                f"{self.decision} run={self.run_id}>")
