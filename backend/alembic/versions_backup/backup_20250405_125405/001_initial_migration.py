"""Initial migration

Revision ID: 001
Revises: 
Create Date: 2023-07-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create user table
    op.create_table(
        'user',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('role', sa.String(length=50), nullable=False, default='user'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    
    # Create exercise table
    op.create_table(
        'exercise',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('difficulty', sa.String(length=50), nullable=False),
        sa.Column('body_part', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    
    # Create workout table
    op.create_table(
        'workout',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('date', sa.DateTime(), nullable=False),
        sa.Column('duration', sa.Integer(), nullable=True),  # in minutes
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create workout_exercise table (many-to-many relationship)
    op.create_table(
        'workout_exercise',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('workout_id', sa.Integer(), nullable=False),
        sa.Column('exercise_id', sa.Integer(), nullable=False),
        sa.Column('sets', sa.Integer(), nullable=True),
        sa.Column('reps', sa.Integer(), nullable=True),
        sa.Column('weight', sa.Float(), nullable=True),
        sa.Column('duration', sa.Integer(), nullable=True),  # in seconds
        sa.Column('notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['exercise_id'], ['exercise.id'], ),
        sa.ForeignKeyConstraint(['workout_id'], ['workout.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create analysis table
    op.create_table(
        'analysis',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('exercise_id', sa.Integer(), nullable=False),
        sa.Column('video_url', sa.String(length=1024), nullable=True),
        sa.Column('score', sa.Integer(), nullable=False),
        sa.Column('feedback', sa.Text(), nullable=True),
        sa.Column('total_reps', sa.Integer(), nullable=True),
        sa.Column('complete_reps', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['exercise_id'], ['exercise.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('analysis')
    op.drop_table('workout_exercise')
    op.drop_table('workout')
    op.drop_table('exercise')
    op.drop_table('user') 