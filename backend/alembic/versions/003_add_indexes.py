"""Add performance indexes to database tables

Revision ID: 002
Revises: 001
Create Date: 2024-04-03 05:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add indexes for user queries
    op.create_index('ix_users_email', 'users', ['email'])
    op.create_index('ix_users_username', 'users', ['username'])
    op.create_index('ix_users_is_active', 'users', ['is_active'])
    
    # Add indexes for subscription queries
    op.create_index('ix_subscriptions_user_id', 'subscriptions', ['user_id'])
    op.create_index('ix_subscriptions_plan_type', 'subscriptions', ['plan_type'])
    op.create_index('ix_subscriptions_status', 'subscriptions', ['status'])
    op.create_index('ix_subscriptions_end_date', 'subscriptions', ['end_date'])
    
    # Add indexes for form_checks queries
    op.create_index('ix_form_checks_user_id', 'form_checks', ['user_id'])
    op.create_index('ix_form_checks_status', 'form_checks', ['status'])
    op.create_index('ix_form_checks_created_at', 'form_checks', ['created_at'])
    
    # Add indexes for workouts queries
    op.create_index('ix_workouts_user_id', 'workouts', ['user_id'])
    op.create_index('ix_workouts_name', 'workouts', ['name'])
    op.create_index('ix_workouts_difficulty', 'workouts', ['difficulty'])
    
    # Add indexes for exercises queries
    op.create_index('ix_exercises_name', 'exercises', ['name'])
    op.create_index('ix_exercises_muscle_group', 'exercises', ['muscle_group'])
    op.create_index('ix_exercises_difficulty', 'exercises', ['difficulty'])
    
    # Add indexes for many-to-many relationships
    op.create_index('ix_workout_exercises_workout_id', 'workout_exercises', ['workout_id'])
    op.create_index('ix_workout_exercises_exercise_id', 'workout_exercises', ['exercise_id'])
    
    op.create_index('ix_workout_plan_workouts_workout_plan_id', 'workout_plan_workouts', ['workout_plan_id'])
    op.create_index('ix_workout_plan_workouts_workout_id', 'workout_plan_workouts', ['workout_id'])
    
    # Add indexes for workout_plans queries
    op.create_index('ix_workout_plans_user_id', 'workout_plans', ['user_id'])
    op.create_index('ix_workout_plans_name', 'workout_plans', ['name'])
    op.create_index('ix_workout_plans_difficulty', 'workout_plans', ['difficulty'])


def downgrade() -> None:
    # Drop indexes in reverse order
    
    # Drop workout_plans indexes
    op.drop_index('ix_workout_plans_difficulty', 'workout_plans')
    op.drop_index('ix_workout_plans_name', 'workout_plans')
    op.drop_index('ix_workout_plans_user_id', 'workout_plans')
    
    # Drop workout_plan_workouts indexes
    op.drop_index('ix_workout_plan_workouts_workout_id', 'workout_plan_workouts')
    op.drop_index('ix_workout_plan_workouts_workout_plan_id', 'workout_plan_workouts')
    
    # Drop workout_exercises indexes
    op.drop_index('ix_workout_exercises_exercise_id', 'workout_exercises')
    op.drop_index('ix_workout_exercises_workout_id', 'workout_exercises')
    
    # Drop exercises indexes
    op.drop_index('ix_exercises_difficulty', 'exercises')
    op.drop_index('ix_exercises_muscle_group', 'exercises')
    op.drop_index('ix_exercises_name', 'exercises')
    
    # Drop workouts indexes
    op.drop_index('ix_workouts_difficulty', 'workouts')
    op.drop_index('ix_workouts_name', 'workouts')
    op.drop_index('ix_workouts_user_id', 'workouts')
    
    # Drop form_checks indexes
    op.drop_index('ix_form_checks_created_at', 'form_checks')
    op.drop_index('ix_form_checks_status', 'form_checks')
    op.drop_index('ix_form_checks_user_id', 'form_checks')
    
    # Drop subscriptions indexes
    op.drop_index('ix_subscriptions_end_date', 'subscriptions')
    op.drop_index('ix_subscriptions_status', 'subscriptions')
    op.drop_index('ix_subscriptions_plan_type', 'subscriptions')
    op.drop_index('ix_subscriptions_user_id', 'subscriptions')
    
    # Drop users indexes
    op.drop_index('ix_users_is_active', 'users')
    op.drop_index('ix_users_username', 'users')
    op.drop_index('ix_users_email', 'users') 