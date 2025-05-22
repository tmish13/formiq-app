from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '005_add_mime_type_to_videos'
down_revision = '004_add_urls_to_videos'
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table('videos', schema=None) as batch_op:
        batch_op.add_column(sa.Column('mime_type', sa.String(), nullable=False, server_default='application/octet-stream'))

    with op.batch_alter_table('videos', schema=None) as batch_op:
        batch_op.alter_column('mime_type', server_default=None)

def downgrade():
    with op.batch_alter_table('videos', schema=None) as batch_op:
        batch_op.drop_column('mime_type') 