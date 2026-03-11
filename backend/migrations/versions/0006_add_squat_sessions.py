"""Add squat_sessions table.

Revision ID: 0006_add_squat_sessions
Revises: 0005_add_user_profile_fields
Create Date: 2026-03-07
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = '0006_add_squat_sessions'
down_revision = '0005_add_user_profile_fields'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'squat_sessions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('form_check_id', UUID(as_uuid=True), sa.ForeignKey('form_checks.id', ondelete='SET NULL'), nullable=True),
        sa.Column('date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('working_weight_lb', sa.Float(), nullable=False),
        sa.Column('overall_score', sa.Float(), nullable=False),
        sa.Column('torso_stability', sa.Float(), nullable=False),
        sa.Column('knee_symmetry', sa.Float(), nullable=False),
        sa.Column('bottom_control', sa.Float(), nullable=False),
        sa.Column('forward_lean', sa.Float(), nullable=False),
        sa.Column('primary_limiter', sa.String(50), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('sets_json', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_squat_sessions_user_id', 'squat_sessions', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_squat_sessions_user_id', table_name='squat_sessions')
    op.drop_table('squat_sessions')
