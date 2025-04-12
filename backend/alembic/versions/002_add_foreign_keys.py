"""Add missing foreign key constraints

Revision ID: 001
Revises: None
Create Date: 2024-04-03 05:15:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '001'
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add foreign key constraints that might be missing in the initial schema
    
    # Add foreign key constraint for subscriptions.user_id if not exists
    op.create_foreign_key(
        'fk_subscriptions_user_id',
        'subscriptions', 'users',
        ['user_id'], ['id'],
        ondelete='CASCADE',
        source_schema=None,
        referent_schema=None
    )
    
    # Add foreign key constraint for form_checks.user_id if not exists
    op.create_foreign_key(
        'fk_form_checks_user_id',
        'form_checks', 'users',
        ['user_id'], ['id'],
        ondelete='CASCADE',
        source_schema=None,
        referent_schema=None
    )
    
    # Add foreign key constraints for workout relationships
    op.create_foreign_key(
        'fk_workouts_user_id',
        'workouts', 'users',
        ['user_id'], ['id'],
        ondelete='CASCADE',
        source_schema=None,
        referent_schema=None
    )
    
    # Add foreign key constraints for workout_exercises relationships
    op.create_foreign_key(
        'fk_workout_exercises_workout_id',
        'workout_exercises', 'workouts',
        ['workout_id'], ['id'],
        ondelete='CASCADE',
        source_schema=None,
        referent_schema=None
    )
    
    op.create_foreign_key(
        'fk_workout_exercises_exercise_id',
        'workout_exercises', 'exercises',
        ['exercise_id'], ['id'],
        ondelete='CASCADE',
        source_schema=None,
        referent_schema=None
    )
    
    # Add foreign key constraints for workout_plans relationships
    op.create_foreign_key(
        'fk_workout_plans_user_id',
        'workout_plans', 'users',
        ['user_id'], ['id'],
        ondelete='CASCADE',
        source_schema=None,
        referent_schema=None
    )
    
    # Add foreign key constraints for workout_plan_workouts relationships
    op.create_foreign_key(
        'fk_workout_plan_workouts_workout_plan_id',
        'workout_plan_workouts', 'workout_plans',
        ['workout_plan_id'], ['id'],
        ondelete='CASCADE',
        source_schema=None,
        referent_schema=None
    )
    
    op.create_foreign_key(
        'fk_workout_plan_workouts_workout_id',
        'workout_plan_workouts', 'workouts',
        ['workout_id'], ['id'],
        ondelete='CASCADE',
        source_schema=None,
        referent_schema=None
    )


def downgrade() -> None:
    # Remove foreign key constraints
    op.drop_constraint('fk_subscriptions_user_id', 'subscriptions', type_='foreignkey')
    op.drop_constraint('fk_form_checks_user_id', 'form_checks', type_='foreignkey')
    op.drop_constraint('fk_workouts_user_id', 'workouts', type_='foreignkey')
    op.drop_constraint('fk_workout_exercises_workout_id', 'workout_exercises', type_='foreignkey')
    op.drop_constraint('fk_workout_exercises_exercise_id', 'workout_exercises', type_='foreignkey')
    op.drop_constraint('fk_workout_plans_user_id', 'workout_plans', type_='foreignkey')
    op.drop_constraint('fk_workout_plan_workouts_workout_plan_id', 'workout_plan_workouts', type_='foreignkey')
    op.drop_constraint('fk_workout_plan_workouts_workout_id', 'workout_plan_workouts', type_='foreignkey') 