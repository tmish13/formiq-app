'''add_url_and_processed_url_to_videos_table

Revision ID: 004_add_urls_to_videos
Revises: 003_add_filename_to_videos
Create Date: 2025-05-13 20:35:00.000000

'''
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '004_add_urls_to_videos'
down_revision = '003_add_filename_to_videos'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('videos', schema=None) as batch_op:
        batch_op.add_column(sa.Column('url', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('processed_url', sa.String(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('videos', schema=None) as batch_op:
        batch_op.drop_column('processed_url')
        batch_op.drop_column('url') 