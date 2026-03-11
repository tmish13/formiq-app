"""add_object_key_to_videos_table_take_4

Revision ID: a79158613924
Revises: 9815775ecbd4
Create Date: 2025-05-11 15:36:48.456527

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a79158613924'
down_revision = '9815775ecbd4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('videos', schema=None) as batch_op:
        batch_op.add_column(sa.Column('object_key', sa.String(), nullable=True))
        # For batch mode, unique constraints are often defined directly on the column
        # or created within the batch operation context.
        # The create_unique_constraint method is available on batch_op.
        batch_op.create_unique_constraint('uq_videos_object_key', ['object_key'])


def downgrade() -> None:
    with op.batch_alter_table('videos', schema=None) as batch_op:
        batch_op.drop_constraint('uq_videos_object_key', type_='unique')
        batch_op.drop_column('object_key') 