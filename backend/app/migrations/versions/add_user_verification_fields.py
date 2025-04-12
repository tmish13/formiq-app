"""Add user verification fields

Revision ID: add_user_verification_fields
Revises: previous_revision
Create Date: 2024-01-20 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers, used by Alembic.
revision = 'add_user_verification_fields'
down_revision = 'previous_revision'  # Update this to your previous migration
branch_labels = None
depends_on = None

def upgrade():
    """Add user verification fields."""
    # Add new columns
    op.add_column('users', sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('users', sa.Column('verified_at', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')))
    op.add_column('users', sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')))
    op.add_column('users', sa.Column('last_login', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('failed_login_attempts', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('users', sa.Column('locked_until', sa.DateTime(), nullable=True))

def downgrade():
    """Remove user verification fields."""
    # Remove columns in reverse order
    op.drop_column('users', 'locked_until')
    op.drop_column('users', 'failed_login_attempts')
    op.drop_column('users', 'last_login')
    op.drop_column('users', 'updated_at')
    op.drop_column('users', 'created_at')
    op.drop_column('users', 'verified_at')
    op.drop_column('users', 'is_verified') 