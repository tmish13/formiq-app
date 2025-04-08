"""Initial schema

Revision ID: 001
Revises: 
Create Date: 2024-03-28 22:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('full_name', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('is_superuser', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime(), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )

    # Create form_checks table
    op.create_table(
        'form_checks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('video_path', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('feedback', sa.Text(), nullable=True),
        sa.Column('keypoints', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime(), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create subscriptions table
    op.create_table(
        'subscriptions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('plan_type', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('start_date', sa.DateTime(), nullable=False),
        sa.Column('end_date', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime(), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create workouts table
    op.create_table(
        'workouts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('duration', sa.Integer(), nullable=True),
        sa.Column('difficulty', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime(), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create exercises table
    op.create_table(
        'exercises',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('muscle_group', sa.String(), nullable=True),
        sa.Column('difficulty', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime(), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow),
        sa.PrimaryKeyConstraint('id')
    )

    # Create workout_exercises table (many-to-many relationship)
    op.create_table(
        'workout_exercises',
        sa.Column('workout_id', sa.Integer(), nullable=False),
        sa.Column('exercise_id', sa.Integer(), nullable=False),
        sa.Column('sets', sa.Integer(), nullable=True),
        sa.Column('reps', sa.Integer(), nullable=True),
        sa.Column('duration', sa.Integer(), nullable=True),
        sa.Column('order', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['workout_id'], ['workouts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['exercise_id'], ['exercises.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('workout_id', 'exercise_id')
    )

    # Create workout_plans table
    op.create_table(
        'workout_plans',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('duration_weeks', sa.Integer(), nullable=True),
        sa.Column('difficulty', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime(), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create workout_plan_workouts table (many-to-many relationship)
    op.create_table(
        'workout_plan_workouts',
        sa.Column('workout_plan_id', sa.Integer(), nullable=False),
        sa.Column('workout_id', sa.Integer(), nullable=False),
        sa.Column('day_of_week', sa.Integer(), nullable=True),
        sa.Column('order', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['workout_plan_id'], ['workout_plans.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workout_id'], ['workouts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('workout_plan_id', 'workout_id')
    )

def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('workout_plan_workouts')
    op.drop_table('workout_plans')
    op.drop_table('workout_exercises')
    op.drop_table('exercises')
    op.drop_table('workouts')
    op.drop_table('subscriptions')
    op.drop_table('form_checks')
    op.drop_table('users') 