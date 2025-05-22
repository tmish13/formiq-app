"""Consolidate object_key column and remove old s3_object_key.

Revision ID: 012_consolidate_object_key
Revises: 011_add_rep_count_to_videos
Create Date: """ # Date will be auto-filled by Alembic

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '012_consolidate_object_key'
down_revision = '011_add_rep_count_to_videos'
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table('videos', schema=None) as batch_op:
        # Drop the old s3_object_key column
        # The new 'object_key' column (nullable=True, unique=True) should already exist
        # from migration a79158613924_add_object_key_to_videos_table_take_4.py
        try:
            batch_op.drop_column('s3_object_key')
        except Exception as e:
            print(f"Could not drop s3_object_key, it might have been already removed: {e}")
            # If it doesn't exist, we can ignore the error, as the goal is to ensure it's gone.


def downgrade():
    with op.batch_alter_table('videos', schema=None) as batch_op:
        # Re-add the s3_object_key column as it was in 001_initial.py
        batch_op.add_column(sa.Column('s3_object_key', sa.String(length=1024), nullable=False))
        # Note: If data was in 'object_key', this downgrade doesn't migrate it back.
        # Also, the unique constraint on 'object_key' is not removed here, which might differ from original state if only s3_object_key existed. 