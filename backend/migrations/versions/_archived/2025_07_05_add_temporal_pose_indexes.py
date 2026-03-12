"""Add temporal pose sequence indexes for query optimization

Revision ID: 2025_07_05_temporal_indexes
Revises: 2025_07_05_storage_optimization
Create Date: 2025-07-05 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '2025_07_05_temporal_indexes'
down_revision = '2025_07_05_storage_optimization'
branch_labels = None
depends_on = None


def upgrade():
    """Add temporal pose sequence indexes for optimized query performance."""
    
    # Core temporal indexes for Videos table
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_videos_temporal_user 
        ON videos (user_id, created_at DESC)
    """)
    
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_videos_exercise_temporal 
        ON videos (exercise_type, created_at DESC)
        WHERE exercise_type IS NOT NULL
    """)
    
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_videos_status_temporal 
        ON videos (status, updated_at DESC)
    """)
    
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_videos_user_exercise_temporal 
        ON videos (user_id, exercise_type, created_at DESC)
        WHERE exercise_type IS NOT NULL
    """)
    
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_videos_processing_temporal 
        ON videos (status, created_at DESC)
        WHERE status IN ('uploaded', 'processing', 'processed', 'analyzing')
    """)
    
    # Form check temporal indexes
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_form_checks_temporal_user 
        ON form_checks (user_id, created_at DESC)
    """)
    
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_form_checks_video_temporal 
        ON form_checks (video_id, created_at DESC)
        WHERE video_id IS NOT NULL
    """)
    
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_form_checks_exercise_temporal 
        ON form_checks (exercise_id, created_at DESC)
    """)
    
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_form_checks_status_temporal 
        ON form_checks (status, updated_at DESC)
    """)
    
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_form_checks_scores_temporal 
        ON form_checks (user_id, score DESC, created_at DESC)
        WHERE score IS NOT NULL
    """)
    
    # Feedback items temporal indexes
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_feedback_temporal 
        ON feedback_items (form_check_id, timestamp)
    """)
    
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_feedback_severity_temporal 
        ON feedback_items (form_check_id, severity, timestamp)
    """)
    
    # JSON data GIN indexes (PostgreSQL specific)
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_videos_pose_data_gin 
        ON videos USING gin (pose_data)
    """)
    
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_videos_analysis_results_gin 
        ON videos USING gin (analysis_results)
    """)
    
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_form_checks_results_gin 
        ON form_checks USING gin (results)
    """)
    
    # Performance optimization indexes
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_videos_size_temporal 
        ON videos (size DESC, created_at DESC)
        WHERE size IS NOT NULL
    """)
    
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_videos_duration_temporal 
        ON videos (duration DESC, created_at DESC)
        WHERE duration IS NOT NULL
    """)
    
    # Storage optimization indexes
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_videos_compression_stats 
        ON videos (compression_ratio, original_pose_size DESC)
        WHERE compression_ratio IS NOT NULL
    """)
    
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_videos_storage_format 
        ON videos (pose_storage_format, storage_optimization_ratio DESC)
        WHERE pose_storage_format IS NOT NULL
    """)


def downgrade():
    """Remove temporal pose sequence indexes."""
    
    # Drop all created indexes
    indexes_to_drop = [
        "idx_videos_temporal_user",
        "idx_videos_exercise_temporal", 
        "idx_videos_status_temporal",
        "idx_videos_user_exercise_temporal",
        "idx_videos_processing_temporal",
        "idx_form_checks_temporal_user",
        "idx_form_checks_video_temporal",
        "idx_form_checks_exercise_temporal", 
        "idx_form_checks_status_temporal",
        "idx_form_checks_scores_temporal",
        "idx_feedback_temporal",
        "idx_feedback_severity_temporal",
        "idx_videos_pose_data_gin",
        "idx_videos_analysis_results_gin",
        "idx_form_checks_results_gin",
        "idx_videos_size_temporal",
        "idx_videos_duration_temporal",
        "idx_videos_compression_stats",
        "idx_videos_storage_format"
    ]
    
    for index_name in indexes_to_drop:
        op.execute(f"DROP INDEX CONCURRENTLY IF EXISTS {index_name}")