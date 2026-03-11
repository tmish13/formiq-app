from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '009_add_fps_to_videos'
down_revision = '008_add_resolution_to_videos'
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table('videos', schema=None) as batch_op:
        batch_op.add_column(sa.Column('fps', sa.Float(), nullable=True))

def downgrade():
    with op.batch_alter_table('videos', schema=None) as batch_op:
        batch_op.drop_column('fps') 