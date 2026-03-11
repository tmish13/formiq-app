"""add_onboarding_fields_to_user_table

Revision ID: 6d00e8e4809c
Revises: 5c2e8f9a1b4d
Create Date: 2025-07-03 14:12:19.190110

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6d00e8e4809c'
down_revision = '5c2e8f9a1b4d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add onboarding fields to users table
    op.add_column('users', sa.Column('has_completed_onboarding', sa.Boolean(), nullable=False, default=False))
    op.add_column('users', sa.Column('onboarding_completed_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    # Remove onboarding fields from users table
    op.drop_column('users', 'onboarding_completed_at')
    op.drop_column('users', 'has_completed_onboarding') 