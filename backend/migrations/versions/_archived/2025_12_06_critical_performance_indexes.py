"""Add critical performance indexes for core queries

Revision ID: 2025_12_06_critical_performance_indexes  
Revises: 2025_07_05_add_temporal_pose_indexes
Create Date: 2025-12-06 05:00:00.000000

This migration adds critical missing indexes identified during performance audit:
- Foreign key indexes for Videos, FormChecks, FeedbackItems
- Composite indexes for common query patterns
- Status filtering indexes
- Unique constraints for data integrity

All indexes are created CONCURRENTLY to avoid locking during deployment.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '2025_12_06_critical_performance_indexes'
down_revision = '2025_07_05_add_temporal_pose_indexes'
branch_labels = None
depends_on = None

def upgrade() -> None:
    """Add critical performance indexes."""
    
    # =============================================================================
    # Video Model Critical Indexes
    # =============================================================================
    
    # Foreign key index for video-user associations (critical for performance)
    op.create_index(
        'ix_videos_user_id',
        'videos',
        ['user_id'],
        postgresql_concurrently=True
    )
    
    # Status filtering index (high frequency queries in video processing)
    op.create_index(
        'ix_videos_status',
        'videos', 
        ['status'],
        postgresql_concurrently=True
    )
    
    # Exercise type filtering for analysis queries
    op.create_index(
        'ix_videos_exercise_type',
        'videos',
        ['exercise_type'],
        postgresql_where=sa.text("exercise_type IS NOT NULL"),
        postgresql_concurrently=True
    )
    
    # Celery task tracking for async processing status
    op.create_index(
        'ix_videos_celery_task_id',
        'videos',
        ['celery_task_id'],
        postgresql_where=sa.text("celery_task_id IS NOT NULL"),
        postgresql_concurrently=True
    )
    
    # Unique constraint on object_key for S3 storage integrity
    op.create_index(
        'ix_videos_object_key_unique',
        'videos',
        ['object_key'],
        unique=True,
        postgresql_where=sa.text("object_key IS NOT NULL"),
        postgresql_concurrently=True
    )
    
    # Composite index for user video listing with status
    op.create_index(
        'ix_videos_user_status_created',
        'videos',
        ['user_id', 'status', 'created_at'],
        postgresql_concurrently=True
    )
    
    # =============================================================================
    # FormCheck Model Critical Indexes  
    # =============================================================================
    
    # Foreign key index for form_check-video associations
    op.create_index(
        'ix_form_checks_video_id',
        'form_checks',
        ['video_id'],
        postgresql_where=sa.text("video_id IS NOT NULL"),
        postgresql_concurrently=True
    )
    
    # Foreign key index for configuration associations
    op.create_index(
        'ix_form_checks_configuration_id',
        'form_checks',
        ['configuration_id'],
        postgresql_where=sa.text("configuration_id IS NOT NULL"),
        postgresql_concurrently=True
    )
    
    # Composite index for user + status queries (common pattern)
    op.create_index(
        'ix_form_checks_user_status',
        'form_checks',
        ['user_id', 'status'],
        postgresql_concurrently=True
    )
    
    # Updated timestamp index for change tracking
    op.create_index(
        'ix_form_checks_updated_at',
        'form_checks',
        [sa.text('updated_at DESC')],
        postgresql_concurrently=True
    )
    
    # =============================================================================
    # FeedbackItem Model Critical Indexes
    # =============================================================================
    
    # Foreign key index for feedback-form_check associations (critical)
    op.create_index(
        'ix_feedback_items_form_check_id',
        'feedback_items',
        ['form_check_id'],
        postgresql_concurrently=True
    )
    
    # Timestamp index for temporal feedback queries
    op.create_index(
        'ix_feedback_items_timestamp',
        'feedback_items',
        ['timestamp'],
        postgresql_concurrently=True
    )
    
    # Severity filtering for feedback importance
    op.create_index(
        'ix_feedback_items_severity',
        'feedback_items',
        ['severity'],
        postgresql_concurrently=True
    )
    
    # Type filtering for feedback categorization
    op.create_index(
        'ix_feedback_items_type',
        'feedback_items',
        ['type'],
        postgresql_concurrently=True
    )
    
    # Composite index for feedback retrieval (common query pattern)
    op.create_index(
        'ix_feedback_items_form_check_timestamp',
        'feedback_items',
        ['form_check_id', 'timestamp'],
        postgresql_concurrently=True
    )
    
    # =============================================================================
    # User Model Optimization Indexes
    # =============================================================================
    
    # Composite index for authentication queries (email + active status)
    op.create_index(
        'ix_users_email_active',
        'users',
        ['email', 'is_active'],
        postgresql_where=sa.text("is_active = true"),
        postgresql_concurrently=True
    )
    
    # Subscription tier filtering for access control
    op.create_index(
        'ix_users_subscription_tier',
        'users',
        ['subscription_tier'],
        postgresql_concurrently=True
    )
    
    # Verification status queries
    op.create_index(
        'ix_users_verified_active',
        'users',
        ['is_verified', 'is_active'],
        postgresql_concurrently=True
    )
    
    # Onboarding status tracking
    op.create_index(
        'ix_users_onboarding_status',
        'users',
        ['has_completed_onboarding', 'created_at'],
        postgresql_concurrently=True
    )
    
    # =============================================================================
    # UserSession Model Critical Indexes
    # =============================================================================
    
    # Session lookup index (critical for authentication)
    op.create_index(
        'ix_user_sessions_session_id',
        'user_sessions',
        ['session_id'],
        postgresql_concurrently=True
    )
    
    # User session cleanup and management
    op.create_index(
        'ix_user_sessions_user_expires',
        'user_sessions',
        ['user_id', 'expires_at'],
        postgresql_concurrently=True
    )
    
    # Active session tracking for analytics
    op.create_index(
        'ix_user_sessions_last_active',
        'user_sessions',
        [sa.text('last_active DESC')],
        postgresql_concurrently=True
    )

def downgrade() -> None:
    """Remove critical performance indexes."""
    
    # UserSession indexes
    op.drop_index('ix_user_sessions_last_active', 'user_sessions', postgresql_concurrently=True)
    op.drop_index('ix_user_sessions_user_expires', 'user_sessions', postgresql_concurrently=True)
    op.drop_index('ix_user_sessions_session_id', 'user_sessions', postgresql_concurrently=True)
    
    # User optimization indexes
    op.drop_index('ix_users_onboarding_status', 'users', postgresql_concurrently=True)
    op.drop_index('ix_users_verified_active', 'users', postgresql_concurrently=True)
    op.drop_index('ix_users_subscription_tier', 'users', postgresql_concurrently=True)
    op.drop_index('ix_users_email_active', 'users', postgresql_concurrently=True)
    
    # FeedbackItem indexes
    op.drop_index('ix_feedback_items_form_check_timestamp', 'feedback_items', postgresql_concurrently=True)
    op.drop_index('ix_feedback_items_type', 'feedback_items', postgresql_concurrently=True)
    op.drop_index('ix_feedback_items_severity', 'feedback_items', postgresql_concurrently=True)
    op.drop_index('ix_feedback_items_timestamp', 'feedback_items', postgresql_concurrently=True)
    op.drop_index('ix_feedback_items_form_check_id', 'feedback_items', postgresql_concurrently=True)
    
    # FormCheck indexes
    op.drop_index('ix_form_checks_updated_at', 'form_checks', postgresql_concurrently=True)
    op.drop_index('ix_form_checks_user_status', 'form_checks', postgresql_concurrently=True)
    op.drop_index('ix_form_checks_configuration_id', 'form_checks', postgresql_concurrently=True)
    op.drop_index('ix_form_checks_video_id', 'form_checks', postgresql_concurrently=True)
    
    # Video indexes
    op.drop_index('ix_videos_user_status_created', 'videos', postgresql_concurrently=True)
    op.drop_index('ix_videos_object_key_unique', 'videos', postgresql_concurrently=True)
    op.drop_index('ix_videos_celery_task_id', 'videos', postgresql_concurrently=True)
    op.drop_index('ix_videos_exercise_type', 'videos', postgresql_concurrently=True)
    op.drop_index('ix_videos_status', 'videos', postgresql_concurrently=True)
    op.drop_index('ix_videos_user_id', 'videos', postgresql_concurrently=True)