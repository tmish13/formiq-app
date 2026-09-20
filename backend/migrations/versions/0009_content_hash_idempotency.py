"""Content-hash idempotency for form checks, plus an index for the reaper.

Revision ID: 0009_content_hash_idempotency
Revises: 0008_seed_exercise_templates
Create Date: 2026-09-20

Adds the identity a duplicate submission is judged on:

    (user_id, content_hash, model_version, spec_hash)

Same user, same bytes, same model, same feature spec -> the same answer, so
return the existing row instead of paying for the inference again. A model or
feature-spec upgrade changes the key, so the same video is legitimately
re-analysed under the new version. No time window, and never shared across
users -- one user's upload must not be observable through another's submission.

The unique index is PARTIAL (WHERE content_hash IS NOT NULL). Postgres treats
NULLs as distinct in a unique index anyway, but saying so explicitly keeps every
pre-existing row -- all of which have NULL content_hash -- permanently out of the
constraint, and makes that intent readable rather than a quirk to rediscover.

Also adds (status, updated_at), which the stuck-row reaper scans every 60s. No
such index exists today, so without it that beat task is a sequential scan of
form_checks once a minute.

Guards copied from 0004_v1_stabilization.py:18,30 -- the established pattern in
this repo for migrations that may meet a partially-migrated database.
"""

from alembic import op
import sqlalchemy as sa

# NOTE: alembic_version.version_num is varchar(32); a longer id fails the
# final UPDATE *after* the DDL has run. Keep this under 32 characters.
revision = "0009_content_hash_idempotency"
down_revision = "0008_seed_exercise_templates"
branch_labels = None
depends_on = None

_UNIQUE_INDEX = "uq_form_checks_user_content_model_spec"
_REAPER_INDEX = "ix_form_checks_status_updated_at"


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
        sa.text("SELECT 1 FROM pg_indexes WHERE indexname=:i"),
        {"i": index_name},
    )
    return result.fetchone() is not None


def upgrade() -> None:
    for col_name, col_def in [
        # sha256 of the uploaded bytes, hex -> 64 chars.
        ("content_hash", sa.Column("content_hash", sa.String(64), nullable=True)),
        # Which model produced (or will produce) this row's verdict.
        ("model_version", sa.Column("model_version", sa.String(50), nullable=True)),
        # Which feature spec that model was fed.
        ("spec_hash", sa.Column("spec_hash", sa.String(64), nullable=True)),
    ]:
        if not _column_exists("form_checks", col_name):
            op.add_column("form_checks", col_def)

    if not _index_exists(_UNIQUE_INDEX):
        op.create_index(
            _UNIQUE_INDEX,
            "form_checks",
            ["user_id", "content_hash", "model_version", "spec_hash"],
            unique=True,
            postgresql_where=sa.text("content_hash IS NOT NULL"),
        )

    if not _index_exists(_REAPER_INDEX):
        op.create_index(
            _REAPER_INDEX,
            "form_checks",
            ["status", "updated_at"],
        )


def downgrade() -> None:
    if _index_exists(_REAPER_INDEX):
        op.drop_index(_REAPER_INDEX, table_name="form_checks")
    if _index_exists(_UNIQUE_INDEX):
        op.drop_index(_UNIQUE_INDEX, table_name="form_checks")
    for col_name in ("spec_hash", "model_version", "content_hash"):
        if _column_exists("form_checks", col_name):
            op.drop_column("form_checks", col_name)
