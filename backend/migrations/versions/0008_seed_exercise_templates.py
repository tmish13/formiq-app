"""Seed exercise_templates with the Squat entry required by the submission pipeline.

Revision ID: 0008_seed_exercise_templates
Revises: 0007_add_training_sessions
Create Date: 2026-03-15

The form-check submission endpoint performs a case-insensitive name lookup:
    SELECT * FROM exercise_templates WHERE LOWER(name) = 'squat'
This query returns nothing on a fresh database (the baseline migration creates
the table but inserts no rows), causing every squat submission to 404.

This migration inserts the canonical Squat template with a fixed UUID.
The INSERT is wrapped in WHERE NOT EXISTS so it is fully idempotent — running
`alembic upgrade head` on a database that already has a Squat template is safe.

Down: removes the row only if it still carries the seeded UUID (preserves any
row that was manually inserted with a different UUID).
"""

from alembic import op
import sqlalchemy as sa

revision = "0008_seed_exercise_templates"
down_revision = "0007_add_training_sessions"
branch_labels = None
depends_on = None

# Deterministic UUID for the canonical Squat exercise template.
# Using a fixed value means the seed is idempotent across environments and
# the Celery task can rely on a stable exercise_id if needed.
SQUAT_TEMPLATE_UUID = "a1b2c3d4-e5f6-4a1b-8c3d-000000000001"


def upgrade() -> None:
    # Only insert if no row with LOWER(name) = 'squat' already exists.
    # This handles both a completely empty table and any environment where
    # a Squat template was manually created with a different UUID.
    op.execute(
        sa.text(
            """
            INSERT INTO exercise_templates
                (id, name, description, difficulty, muscle_group, created_at, updated_at)
            SELECT
                :uuid,
                'Squat',
                'Barbell back squat — primary lower-body compound movement.',
                'Beginner',
                'Legs',
                NOW(),
                NOW()
            WHERE NOT EXISTS (
                SELECT 1
                FROM exercise_templates
                WHERE LOWER(name) = 'squat'
            )
            """
        ).bindparams(uuid=SQUAT_TEMPLATE_UUID)
    )


def downgrade() -> None:
    # Remove only the row seeded by this migration.  Any Squat template that
    # existed before (different UUID) is left untouched.
    op.execute(
        sa.text(
            "DELETE FROM exercise_templates WHERE id = :uuid"
        ).bindparams(uuid=SQUAT_TEMPLATE_UUID)
    )
