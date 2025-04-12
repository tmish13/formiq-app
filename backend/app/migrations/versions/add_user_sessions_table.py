"""Add user sessions table

Revision ID: add_user_sessions_table
Revises: add_user_verification_fields
Create Date: 2024-01-20 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid

# revision identifiers, used by Alembic.
revision = 'add_user_sessions_table'
down_revision = 'add_user_verification_fields'
branch_labels = None
depends_on = None

def upgrade():
    """Create user sessions table."""
    op.create_table(
        'user_sessions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('session_id', sa.String(length=64), unique=True, nullable=False),
        sa.Column('device_info', JSONB, nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('last_activity', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        
        # Indexes
        sa.Index('ix_user_sessions_user_id', 'user_id'),
        sa.Index('ix_user_sessions_session_id', 'session_id'),
        sa.Index('ix_user_sessions_is_active', 'is_active'),
        sa.Index('ix_user_sessions_expires_at', 'expires_at')
    )

def downgrade():
    """Drop user sessions table."""
    op.drop_table('user_sessions') 