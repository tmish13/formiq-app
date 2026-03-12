"""Add social_provider and social_id columns to users table.

Revision ID: 0002_add_social_auth_fields
Revises: 0001_baseline
Create Date: 2026-02-19

Both columns are nullable so all existing email/password users are
unaffected.  A composite unique constraint on (social_provider, social_id)
prevents duplicate accounts from the same provider account while still
allowing many NULL rows (NULLs are excluded from unique constraints in
PostgreSQL).
"""

from alembic import op
import sqlalchemy as sa

revision = '0002_add_social_auth_fields'
down_revision = '0001_baseline'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('social_provider', sa.String(32), nullable=True))
    op.add_column('users', sa.Column('social_id', sa.String(255), nullable=True))

    # Index for fast provider-based lookups
    op.create_index('ix_users_social_provider', 'users', ['social_provider'])
    op.create_index('ix_users_social_id', 'users', ['social_id'])

    # Composite unique constraint — PostgreSQL ignores rows where either value
    # is NULL, so email/password users (both NULL) are unaffected.
    op.create_unique_constraint(
        'uq_users_social_provider_social_id',
        'users',
        ['social_provider', 'social_id'],
    )


def downgrade() -> None:
    op.drop_constraint('uq_users_social_provider_social_id', 'users', type_='unique')
    op.drop_index('ix_users_social_id', table_name='users')
    op.drop_index('ix_users_social_provider', table_name='users')
    op.drop_column('users', 'social_id')
    op.drop_column('users', 'social_provider')
