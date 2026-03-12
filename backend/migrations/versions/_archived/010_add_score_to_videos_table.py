"""add score to videos table

Revision ID: 010_add_score_to_videos
Revises: 009_add_fps_to_videos
Create Date: """ # Date will be auto-filled by Alembic

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '010_add_score_to_videos'
down_revision = '009_add_fps_to_videos'
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table('videos', schema=None) as batch_op:
        batch_op.add_column(sa.Column('score', sa.Float(), nullable=True))

def downgrade():
    with op.batch_alter_table('videos', schema=None) as batch_op:
        batch_op.drop_column('score') 