"""Initial migration

Revision ID: 001
Revises: None
Create Date: 2024-03-14 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
import uuid

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_superuser', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )

    # Create subscriptions table
    op.create_table(
        'subscriptions',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('plan_type', sa.String(50), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('start_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )

    # Create exercises table
    op.create_table(
        'exercises',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('video_url', sa.String(length=255), nullable=True),
        sa.Column('difficulty', sa.String(length=50), nullable=False),
        sa.Column('muscle_group', sa.String(length=100), nullable=False),
        sa.Column('equipment', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # Create workouts table
    op.create_table(
        'workouts',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('difficulty', sa.String(length=50), nullable=False),
        sa.Column('duration', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )

    # Create workout_exercises table (many-to-many relationship)
    op.create_table(
        'workout_exercises',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('workout_id', sa.String(36), nullable=False),
        sa.Column('exercise_id', sa.String(36), nullable=False),
        sa.Column('sets', sa.Integer(), nullable=False),
        sa.Column('reps', sa.Integer(), nullable=False),
        sa.Column('weight', sa.Float(), nullable=True),
        sa.Column('order', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['workout_id'], ['workouts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['exercise_id'], ['exercises.id'], ondelete='CASCADE')
    )

    # Create workout_plans table
    op.create_table(
        'workout_plans',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('difficulty', sa.String(length=50), nullable=False),
        sa.Column('duration_weeks', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )

    # Create workout_plan_workouts table (many-to-many relationship)
    op.create_table(
        'workout_plan_workouts',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('workout_plan_id', sa.String(36), nullable=False),
        sa.Column('workout_id', sa.String(36), nullable=False),
        sa.Column('day_of_week', sa.Integer(), nullable=False),
        sa.Column('week_number', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['workout_plan_id'], ['workout_plans.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workout_id'], ['workouts.id'], ondelete='CASCADE')
    )

    # Create form_checks table
    op.create_table(
        'form_checks',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('video_url', sa.String(length=255), nullable=False),
        sa.Column('exercise_id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('feedback', sa.Text(), nullable=True),
        sa.Column('score', sa.Float(), nullable=True),
        sa.Column('keypoints', sa.JSON().with_variant(sa.Text(), 'sqlite'), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['exercise_id'], ['exercises.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )


def downgrade() -> None:
    op.drop_table('form_checks')
    op.drop_table('workout_plan_workouts')
    op.drop_table('workout_plans')
    op.drop_table('workout_exercises')
    op.drop_table('workouts')
    op.drop_table('exercises')
    op.drop_table('subscriptions')
    op.drop_table('users') 