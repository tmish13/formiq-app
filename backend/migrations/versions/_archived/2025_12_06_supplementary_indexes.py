"""Add supplementary performance indexes for analytics and reporting

Revision ID: 2025_12_06_supplementary_indexes
Revises: 2025_12_06_critical_performance_indexes  
Create Date: 2025-12-06 05:30:00.000000

This migration adds supplementary indexes for analytics, reporting, 
and advanced query patterns that provide additional performance benefits
beyond the critical indexes.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '2025_12_06_supplementary_indexes'
down_revision = '2025_12_06_critical_performance_indexes'
branch_labels = None
depends_on = None

def upgrade() -> None:
    """Add supplementary performance indexes."""
    
    # =============================================================================
    # Analytics and Reporting Indexes
    # =============================================================================
    
    # Video analytics: completion rates by exercise type
    op.create_index(
        'ix_videos_exercise_status_created',
        'videos',
        ['exercise_type', 'status', 'created_at'],
        postgresql_where=sa.text("exercise_type IS NOT NULL"),
        postgresql_concurrently=True
    )
    
    # Form check analytics: success rates by user and date
    op.create_index(
        'ix_form_checks_user_created_overall_score',
        'form_checks',
        ['user_id', 'created_at', 'overall_score'],
        postgresql_where=sa.text("overall_score IS NOT NULL"),
        postgresql_concurrently=True
    )
    
    # Video processing performance monitoring
    op.create_index(
        'ix_videos_processing_duration',
        'videos',
        ['status', 'processing_duration'],
        postgresql_where=sa.text("processing_duration IS NOT NULL"),
        postgresql_concurrently=True
    )
    
    # =============================================================================
    # ML Model Performance Indexes
    # =============================================================================
    
    # ML score analysis for form checks
    op.create_index(
        'ix_form_checks_ml_scores',
        'form_checks',
        ['posture_score', 'stability_score', 'depth_score'],
        postgresql_where=sa.text("posture_score IS NOT NULL AND stability_score IS NOT NULL AND depth_score IS NOT NULL"),
        postgresql_concurrently=True
    )
    
    # Exercise classification accuracy tracking
    op.create_index(
        'ix_form_checks_classified_exercise',
        'form_checks',
        ['classified_exercise_type', 'exercise_id'],
        postgresql_where=sa.text("classified_exercise_type IS NOT NULL"),
        postgresql_concurrently=True
    )
    
    # =============================================================================
    # Video Storage and Processing Indexes  
    # =============================================================================
    
    # Storage optimization queries
    op.create_index(
        'ix_videos_file_size_created',
        'videos',
        ['file_size', 'created_at'],
        postgresql_where=sa.text("file_size IS NOT NULL"),
        postgresql_concurrently=True
    )
    
    # Video quality and resolution analysis
    op.create_index(
        'ix_videos_resolution_fps',
        'videos',
        ['width', 'height', 'fps'],
        postgresql_where=sa.text("width IS NOT NULL AND height IS NOT NULL"),
        postgresql_concurrently=True
    )
    
    # Compression and storage efficiency tracking
    op.create_index(
        'ix_videos_compression_ratio',
        'videos', 
        ['compression_method', 'compression_ratio'],
        postgresql_where=sa.text("compression_method IS NOT NULL AND compression_ratio IS NOT NULL"),
        postgresql_concurrently=True
    )
    
    # =============================================================================
    # User Behavior and Engagement Indexes
    # =============================================================================
    
    # User activity patterns for engagement analysis
    op.create_index(
        'ix_users_last_login_tier',
        'users',
        ['last_login', 'subscription_tier'],
        postgresql_where=sa.text("last_login IS NOT NULL"),
        postgresql_concurrently=True
    )
    
    # User session duration and activity analysis
    op.create_index(
        'ix_user_sessions_duration',
        'user_sessions',
        ['user_id', 'last_active', 'created_at'],
        postgresql_concurrently=True
    )
    
    # =============================================================================
    # Feedback and Quality Assurance Indexes
    # =============================================================================
    
    # Feedback quality and relevance tracking
    op.create_index(
        'ix_feedback_items_severity_type_timestamp',
        'feedback_items',
        ['severity', 'type', 'timestamp'],
        postgresql_concurrently=True
    )
    
    # Exercise configuration effectiveness analysis
    op.create_index(
        'ix_exercise_configs_updated_at',
        'exercise_configs',
        ['updated_at'],
        postgresql_concurrently=True
    )
    
    # =============================================================================
    # Error Tracking and Debugging Indexes
    # =============================================================================
    
    # Video processing error analysis
    op.create_index(
        'ix_videos_error_message',
        'videos',
        ['status'],
        postgresql_where=sa.text("error_message IS NOT NULL"),
        postgresql_concurrently=True
    )
    
    # Form check error patterns
    op.create_index(
        'ix_form_checks_error_status',
        'form_checks',
        ['status', 'updated_at'],
        postgresql_where=sa.text("status IN ('ERROR', 'FAILED')"),
        postgresql_concurrently=True
    )

def downgrade() -> None:
    """Remove supplementary performance indexes."""
    
    # Error tracking indexes
    op.drop_index('ix_form_checks_error_status', 'form_checks', postgresql_concurrently=True)
    op.drop_index('ix_videos_error_message', 'videos', postgresql_concurrently=True)
    
    # Feedback and QA indexes
    op.drop_index('ix_exercise_configs_updated_at', 'exercise_configs', postgresql_concurrently=True)
    op.drop_index('ix_feedback_items_severity_type_timestamp', 'feedback_items', postgresql_concurrently=True)
    
    # User behavior indexes
    op.drop_index('ix_user_sessions_duration', 'user_sessions', postgresql_concurrently=True)
    op.drop_index('ix_users_last_login_tier', 'users', postgresql_concurrently=True)
    
    # Video storage indexes
    op.drop_index('ix_videos_compression_ratio', 'videos', postgresql_concurrently=True)
    op.drop_index('ix_videos_resolution_fps', 'videos', postgresql_concurrently=True) 
    op.drop_index('ix_videos_file_size_created', 'videos', postgresql_concurrently=True)
    
    # ML model indexes
    op.drop_index('ix_form_checks_classified_exercise', 'form_checks', postgresql_concurrently=True)
    op.drop_index('ix_form_checks_ml_scores', 'form_checks', postgresql_concurrently=True)
    
    # Analytics indexes
    op.drop_index('ix_videos_processing_duration', 'videos', postgresql_concurrently=True)
    op.drop_index('ix_form_checks_user_created_overall_score', 'form_checks', postgresql_concurrently=True)
    op.drop_index('ix_videos_exercise_status_created', 'videos', postgresql_concurrently=True)