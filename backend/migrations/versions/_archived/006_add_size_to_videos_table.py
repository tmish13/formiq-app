from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '006_add_size_to_videos'
down_revision = '005_add_mime_type_to_videos'
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table('videos', schema=None) as batch_op:
        batch_op.add_column(sa.Column('size', sa.BigInteger(), nullable=True))

def downgrade():
    with op.batch_alter_table('videos', schema=None) as batch_op:
        batch_op.drop_column('size') 