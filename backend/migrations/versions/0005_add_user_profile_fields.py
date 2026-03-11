"""Add weight_kg, age, height_cm, training_experience to users table.

Revision ID: 0005_add_user_profile_fields
Revises: 0004_v1_stabilization
Create Date: 2026-03-07
"""

from alembic import op
import sqlalchemy as sa

revision = '0005_add_user_profile_fields'
down_revision = '0004_v1_stabilization'
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
        ("weight_kg",           sa.Column("weight_kg",           sa.Float(),       nullable=True)),
        ("age",                 sa.Column("age",                 sa.Integer(),     nullable=True)),
        ("height_cm",           sa.Column("height_cm",           sa.Float(),       nullable=True)),
        ("training_experience", sa.Column("training_experience", sa.String(50),    nullable=True)),
    ]:
        if not _column_exists("users", col_name):
            op.add_column("users", col_def)


def downgrade() -> None:
    for col in ("training_experience", "height_cm", "age", "weight_kg"):
        if _column_exists("users", col):
            op.drop_column("users", col)
