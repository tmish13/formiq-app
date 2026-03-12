'''add_filename_to_videos_table

Revision ID: 003_add_filename_to_videos
Revises: a79158613924
Create Date: 2025-05-13 20:30:00.000000

'''
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '003_add_filename_to_videos'
down_revision = 'a79158613924' # This was the last revision before the deleted one.
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('videos', schema=None) as batch_op:
        batch_op.add_column(sa.Column('filename', sa.String(), nullable=False, server_default='__unknown__'))

    # Remove the server_default after the column is added and populated for existing rows
    with op.batch_alter_table('videos', schema=None) as batch_op:
        batch_op.alter_column('filename', server_default=None)


def downgrade() -> None:
    with op.batch_alter_table('videos', schema=None) as batch_op:
        batch_op.drop_column('filename') 