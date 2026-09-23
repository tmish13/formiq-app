"""Give `summary` and `analysis_completed_at` somewhere to land.

Revision ID: 0011_phantom_columns
Revises: 0010_decision_audit
Create Date: 2026-09-23

`finalize_form_check_analysis_async` has always written both
(form_check_service.py:421,423) and `:483` already reads `.summary`. Neither is
a column -- not on the model, not in `form_checks` -- so SQLAlchemy's bare
`setattr` loop in `BaseService.update_async` accepted them and dropped them.
Same class of bug as `error_details` (G-37), which meant every FAILED form
check was reason-less for the life of the project.

Adding the columns needs no call-site change: the writers and the reader are
already there and have been running against nothing.

The structural half of this fix is in `BaseService.update_async`, which now
raises outside production on an attribute the model does not have. The column
closes two instances; the guard closes the class.
"""

from alembic import op
import sqlalchemy as sa

# alembic_version.version_num is varchar(32). This is 21 characters.
revision = "0011_phantom_columns"
down_revision = "0010_decision_audit"
branch_labels = None
depends_on = None

_TABLE = "form_checks"


def _column_exists(table: str, column: str) -> bool:
    conn = op.get_bind()
    return conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name=:t AND column_name=:c"
        ),
        {"t": table, "c": column},
    ).fetchone() is not None


def upgrade() -> None:
    if not _column_exists(_TABLE, "summary"):
        op.add_column(_TABLE, sa.Column("summary", sa.Text(), nullable=True))
    if not _column_exists(_TABLE, "analysis_completed_at"):
        op.add_column(
            _TABLE,
            sa.Column("analysis_completed_at", sa.DateTime(timezone=True),
                      nullable=True),
        )


def downgrade() -> None:
    if _column_exists(_TABLE, "analysis_completed_at"):
        op.drop_column(_TABLE, "analysis_completed_at")
    if _column_exists(_TABLE, "summary"):
        op.drop_column(_TABLE, "summary")
