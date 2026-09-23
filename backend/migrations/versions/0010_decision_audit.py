"""The decision trail: analysis_runs + checker_decisions.

Revision ID: 0010_decision_audit
Revises: 0009_content_hash_idempotency
Create Date: 2026-09-23

One row per task ATTEMPT (`analysis_runs`), one per (run, checker, target)
(`checker_decisions`). Today the only record of a verdict is
`posture_v1_inference_logs`: PostureV1-only, no run id, no content hash, no
user, no attempt counter, and nothing recording when analysis finished.

Five identity columns on the run, not three. `content_hash` (which bytes),
`model_version` (which weights), `spec_hash` (which feature spec),
`rules_spec_hash` (which rule constants) and `pose_pass_id` (which MediaPipe
extraction). The last is carried because it was measured to matter: two passes
over the same 221 videos moved 33 PostureV1 verdicts -- 14.9%, a third of them
starting more than 0.10 from the threshold -- while the paired 95% CI on
aggregate F1 spanned zero. See
bench/results/2026-09-23-pose-pass-verdict-instability.md.

`analysis_runs` has NO foreign keys. An audit row must not change when its
subject is deleted. `posture_v1_inference_logs` uses ON DELETE SET NULL, so
deleting a form check leaves telemetry that survives but can no longer be
joined to anything. `checker_decisions.run_id` IS a real FK with CASCADE,
because a decision is a part of its run.

The unique constraint on (run_id, checker_name, target) is what makes the write
path idempotent under retry: a task that dies after writing its checker rows
and is redelivered cannot double-insert them.

Guards follow 0004_v1_stabilization.py:18,30 -- this repo's established pattern
for migrations that may meet a partially-migrated database.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# NOTE: alembic_version.version_num is varchar(32); a longer id fails the final
# UPDATE *after* the DDL has run. This is 19 characters.
revision = "0010_decision_audit"
down_revision = "0009_content_hash_idempotency"
branch_labels = None
depends_on = None

_RUNS = "analysis_runs"
_DECISIONS = "checker_decisions"


def _table_exists(table: str) -> bool:
    conn = op.get_bind()
    return conn.execute(
        sa.text("SELECT 1 FROM information_schema.tables WHERE table_name=:t"),
        {"t": table},
    ).fetchone() is not None


def _index_exists(index_name: str) -> bool:
    conn = op.get_bind()
    return conn.execute(
        sa.text("SELECT 1 FROM pg_indexes WHERE indexname=:i"),
        {"i": index_name},
    ).fetchone() is not None


def _uuid():
    return postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    if not _table_exists(_RUNS):
        op.create_table(
            _RUNS,
            sa.Column("id", _uuid(), primary_key=True, nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True),
                      server_default=sa.func.now(), nullable=False),

            # Subject. Deliberately not foreign keys -- see module docstring.
            sa.Column("form_check_id", _uuid(), nullable=True),
            sa.Column("video_id", _uuid(), nullable=True),
            sa.Column("user_id", _uuid(), nullable=True),

            # Execution.
            sa.Column("celery_task_id", sa.String(64), nullable=True),
            sa.Column("attempt", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("worker_hostname", sa.String(255), nullable=True),
            sa.Column("status", sa.String(20), nullable=False,
                      server_default="running"),
            sa.Column("outcome_status", sa.String(32), nullable=True),

            # Identity of the computation.
            sa.Column("content_hash", sa.String(64), nullable=True),
            sa.Column("model_version", sa.String(50), nullable=True),
            sa.Column("spec_hash", sa.String(64), nullable=True),
            sa.Column("rules_spec_hash", sa.String(64), nullable=True),
            sa.Column("pose_pass_id", sa.String(32), nullable=True),
            sa.Column("combiner_version", sa.String(32), nullable=True),
            sa.Column("code_version", sa.String(64), nullable=True),

            # Inputs as observed.
            sa.Column("pose_source", sa.String(32), nullable=True),
            sa.Column("n_frames", sa.Integer(), nullable=True),
            sa.Column("fps", sa.Float(), nullable=True),
            sa.Column("duration_sec", sa.Float(), nullable=True),
            sa.Column("settings_snapshot", sa.JSON(), nullable=True),

            # Outcome.
            sa.Column("final_decision", sa.String(32), nullable=True),
            sa.Column("final_score", sa.Float(), nullable=True),
            sa.Column("error_type", sa.String(64), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),

            sa.Column("latency_ms", sa.Float(), nullable=True),
            sa.Column("started_at", sa.DateTime(timezone=True),
                      server_default=sa.func.now(), nullable=False),
            sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        )

    for name, cols in (
        ("ix_analysis_runs_created_at", ["created_at"]),
        ("ix_analysis_runs_form_check_id", ["form_check_id"]),
        ("ix_analysis_runs_user_id", ["user_id"]),
        ("ix_analysis_runs_celery_task_id", ["celery_task_id"]),
        ("ix_analysis_runs_content_hash", ["content_hash"]),
        # The reaper scans this every sweep: unclosed runs, oldest first.
        ("ix_analysis_runs_status_started_at", ["status", "started_at"]),
    ):
        if not _index_exists(name):
            op.create_index(name, _RUNS, cols)

    if not _table_exists(_DECISIONS):
        op.create_table(
            _DECISIONS,
            sa.Column("id", _uuid(), primary_key=True, nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True),
                      server_default=sa.func.now(), nullable=False),

            sa.Column("run_id", _uuid(), nullable=False),
            # Denormalised so evaluation joins decisions to labels without
            # touching form_checks. Labels are keyed on content hash precisely
            # so they survive re-analysis; joining through a mutable table
            # would defeat that.
            sa.Column("form_check_id", _uuid(), nullable=True),
            sa.Column("content_hash", sa.String(64), nullable=True),

            sa.Column("checker_name", sa.String(64), nullable=False),
            sa.Column("checker_kind", sa.String(32), nullable=True),
            sa.Column("checker_version", sa.String(64), nullable=True),
            # False = the checker's constants were never fitted to data. On the
            # row, not only in the params artifact, so nothing reading the
            # database can mistake a hand-set constant for a calibrated one.
            sa.Column("fitted", sa.Boolean(), nullable=False,
                      server_default=sa.false()),
            sa.Column("advisory", sa.Boolean(), nullable=False,
                      server_default=sa.false()),

            sa.Column("target", sa.String(32), nullable=False),
            sa.Column("decision", sa.String(32), nullable=False),
            sa.Column("abstained", sa.Boolean(), nullable=False,
                      server_default=sa.false()),
            sa.Column("abstain_reason", sa.String(64), nullable=True),

            sa.Column("score", sa.Float(), nullable=True),
            sa.Column("prob", sa.Float(), nullable=True),
            sa.Column("confidence", sa.Float(), nullable=True),
            sa.Column("coverage", sa.Float(), nullable=True),
            sa.Column("threshold", sa.Float(), nullable=True),

            sa.Column("indicators", sa.JSON(), nullable=True),
            sa.Column("quality", sa.JSON(), nullable=True),
            sa.Column("inputs_digest", sa.String(64), nullable=True),

            sa.Column("latency_ms", sa.Float(), nullable=True),
            sa.Column("error", sa.Text(), nullable=True),

            sa.ForeignKeyConstraint(["run_id"], [f"{_RUNS}.id"],
                                    ondelete="CASCADE"),
            sa.UniqueConstraint("run_id", "checker_name", "target",
                                name="uq_checker_decisions_run_checker_target"),
        )

    for name, cols in (
        ("ix_checker_decisions_created_at", ["created_at"]),
        ("ix_checker_decisions_run_id", ["run_id"]),
        ("ix_checker_decisions_form_check_id", ["form_check_id"]),
        ("ix_checker_decisions_content_hash", ["content_hash"]),
        ("ix_checker_decisions_content_target", ["content_hash", "target"]),
    ):
        if not _index_exists(name):
            op.create_index(name, _DECISIONS, cols)


def downgrade() -> None:
    # checker_decisions first: its FK depends on analysis_runs.
    if _table_exists(_DECISIONS):
        op.drop_table(_DECISIONS)
    if _table_exists(_RUNS):
        op.drop_table(_RUNS)
