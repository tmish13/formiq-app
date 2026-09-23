"""Labels, keyed on content_hash so they survive re-analysis.

Revision ID: 0012_label_store
Revises: 0011_phantom_columns
Create Date: 2026-09-23

A label is a statement about BYTES, not about one scoring attempt. Keyed on
`form_check_id` it would die the moment a video is re-analysed under a new
model -- exactly when the old ground truth is most wanted.

`content_hash` therefore joins three tables written at different times by
different processes: `form_checks` (idempotency), `analysis_runs` (which bytes
a decision was about) and this one. app/core/hashing.py is the single
definition of that key, shared with the upload path, because a disagreement
about chunking would make every join silently return nothing -- which looks
like "no labels yet" rather than "the key is wrong".

The unique key includes `source` and `source_ref`, so a re-import upserts its
own rows and an expert review never overwrites the dataset label it disagrees
with. Both are kept; resolution is the reader's job.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# alembic_version.version_num is varchar(32). This is 17 characters.
revision = "0012_label_store"
down_revision = "0011_phantom_columns"
branch_labels = None
depends_on = None

_TABLE = "labels"


def _table_exists(table: str) -> bool:
    conn = op.get_bind()
    return conn.execute(
        sa.text("SELECT 1 FROM information_schema.tables WHERE table_name=:t"),
        {"t": table},
    ).fetchone() is not None


def _index_exists(name: str) -> bool:
    conn = op.get_bind()
    return conn.execute(
        sa.text("SELECT 1 FROM pg_indexes WHERE indexname=:i"), {"i": name},
    ).fetchone() is not None


def upgrade() -> None:
    if not _table_exists(_TABLE):
        op.create_table(
            _TABLE,
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                      nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True),
                      server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True),
                      server_default=sa.func.now(), nullable=False),

            sa.Column("content_hash", sa.String(64), nullable=False),
            sa.Column("video_name", sa.String(255), nullable=True),
            # The splits are user-level, so no SUBJECT spans splits. Storing
            # the subject makes "is this evaluation leaking?" a query instead
            # of a cross-reference against a JSON file on somebody's desktop.
            #
            # Necessary, not sufficient: 45 byte-identical videos DO span
            # splits under different user ids (G-44). The content_hash column
            # is the identifier that catches that; subject_id cannot.
            sa.Column("subject_id", sa.String(64), nullable=True),
            sa.Column("split", sa.String(16), nullable=True),

            sa.Column("target", sa.String(32), nullable=False),
            sa.Column("value", sa.Integer(), nullable=True),
            sa.Column("usable", sa.Boolean(), nullable=False,
                      server_default=sa.true()),

            sa.Column("source", sa.String(32), nullable=False),
            sa.Column("source_ref", sa.String(255), nullable=False,
                      server_default=""),
            sa.Column("trust", sa.Float(), nullable=False, server_default="0.6"),
            sa.Column("labeled_by", sa.String(128), nullable=True),
            sa.Column("labeled_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),

            sa.UniqueConstraint("content_hash", "target", "source", "source_ref",
                                name="uq_labels_hash_target_source_ref"),
        )

    for name, cols in (
        ("ix_labels_created_at", ["created_at"]),
        ("ix_labels_content_hash", ["content_hash"]),
        ("ix_labels_video_name", ["video_name"]),
        ("ix_labels_subject_id", ["subject_id"]),
        ("ix_labels_split", ["split"]),
        ("ix_labels_target_split", ["target", "split"]),
    ):
        if not _index_exists(name):
            op.create_index(name, _TABLE, cols)


def downgrade() -> None:
    if _table_exists(_TABLE):
        op.drop_table(_TABLE)
