"""add performance indexes

Revision ID: 001_add_indexes
Create Date: 2024-03-20
"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    # Add index on users table for email lookups
    op.create_index('idx_users_email', 'users', ['email'])
    
    # Add index on form_checks table for user_id and created_at
    op.create_index('idx_form_checks_user_created', 'form_checks', ['user_id', 'created_at'])
    
    # Add index on form_checks table for exercise_type
    op.create_index('idx_form_checks_exercise', 'form_checks', ['exercise_type'])

def downgrade():
    # Remove indexes in reverse order
    op.drop_index('idx_form_checks_exercise')
    op.drop_index('idx_form_checks_user_created')
    op.drop_index('idx_users_email') 