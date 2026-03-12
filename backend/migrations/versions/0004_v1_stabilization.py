"""V1 Stabilization: add video_key, exercise_type, weight_kg, reps to form_checks.

Revision ID: 0004_v1_stabilization
Revises: 0003_add_profile_fields
Create Date: 2026-02-25
"""

from alembic import op
import sqlalchemy as sa

revision = '0004_v1_stabilization'
down_revision = '0003_add_profile_fields'
branch_labels = None
depends_on = None


def _column_exists(table: str, column: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name=:t AND column_name=:c"
        ),
        {"t": table, "c": column},
    )
    return result.fetchone() is not None


def _index_exists(index_name: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM pg_indexes WHERE indexname=:i"
        ),
        {"i": index_name},
    )
    return result.fetchone() is not None


def upgrade() -> None:
    for col_name, col_def in [
        ("video_key",      sa.Column("video_key",      sa.String(),  nullable=True)),
        ("exercise_type",  sa.Column("exercise_type",  sa.String(),  nullable=True)),
        ("weight_kg",      sa.Column("weight_kg",      sa.Float(),   nullable=True)),
        ("reps",           sa.Column("reps",           sa.Integer(), nullable=True)),
    ]:
        if not _column_exists("form_checks", col_name):
            op.add_column("form_checks", col_def)

    if not _index_exists("ix_form_checks_exercise_type"):
        op.create_index("ix_form_checks_exercise_type", "form_checks", ["exercise_type"])


def downgrade() -> None:
    if _index_exists("ix_form_checks_exercise_type"):
        op.drop_index("ix_form_checks_exercise_type", "form_checks")
    for col in ("reps", "weight_kg", "exercise_type", "video_key"):
        if _column_exists("form_checks", col):
            op.drop_column("form_checks", col)
