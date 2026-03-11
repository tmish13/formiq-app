"""Add fitness_goal, preferred_exercises, fitness_level, profile_image_url to users.

Revision ID: 0003_add_profile_fields
Revises: 0002_add_social_auth_fields
Create Date: 2026-02-20
"""

from alembic import op
import sqlalchemy as sa

revision = '0003_add_profile_fields'
down_revision = '0002_add_social_auth_fields'
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


def upgrade() -> None:
    for col_name, col_def in [
        ("fitness_goal",        sa.Column("fitness_goal",        sa.String(100), nullable=True)),
        ("preferred_exercises", sa.Column("preferred_exercises", sa.JSON,        nullable=True)),
        ("fitness_level",       sa.Column("fitness_level",       sa.String(50),  nullable=True)),
        ("profile_image_url",   sa.Column("profile_image_url",   sa.String(512), nullable=True)),
    ]:
        if not _column_exists("users", col_name):
            op.add_column("users", col_def)


def downgrade() -> None:
    for col in ("profile_image_url", "fitness_level", "preferred_exercises", "fitness_goal"):
        op.drop_column("users", col)
