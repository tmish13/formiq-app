"""Baseline migration — creates all tables from current models.

Revision ID: 0001_baseline
Revises: None
Create Date: 2026-02-14

This replaces 41 accumulated incremental migrations with a single
baseline that matches the current SQLAlchemy model definitions.
Archived originals are in migrations/versions/_archived/.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = '0001_baseline'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enum types are created automatically by SQLAlchemy model metadata
    # when env.py imports the models. Using create_type=False on all inline
    # Enum references below to avoid duplicate creation attempts.

    # --- Independent tables (no FKs to other app tables) ---

    op.create_table(
        'exercise_templates',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String, nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('video_url', sa.String),
        sa.Column('difficulty', sa.String, nullable=False),
        sa.Column('muscle_group', sa.String, nullable=False),
        sa.Column('equipment', sa.String),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        'users',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String, nullable=False),
        sa.Column('username', sa.String, nullable=False),
        sa.Column('hashed_password', sa.String, nullable=False),
        sa.Column('full_name', sa.String),
        sa.Column('is_active', sa.Boolean),
        sa.Column('subscription_tier', sa.Enum('FREE', 'BASIC', 'PRO', 'ENTERPRISE', 'PREMIUM', name='subscriptiontier', create_type=False), nullable=False),
        sa.Column('subscription_end_date', sa.DateTime(timezone=True)),
        sa.Column('stripe_customer_id', sa.String(255), unique=True),
        sa.Column('stripe_subscription_id', sa.String(255), unique=True),
        sa.Column('is_email_verified', sa.Boolean, nullable=False),
        sa.Column('verification_token', sa.String(255)),
        sa.Column('is_verified', sa.Boolean, nullable=False),
        sa.Column('is_superuser', sa.Boolean, nullable=False),
        sa.Column('verified_at', sa.DateTime),
        sa.Column('has_completed_onboarding', sa.Boolean, nullable=False),
        sa.Column('onboarding_completed_at', sa.DateTime),
        sa.Column('created_at', sa.DateTime),
        sa.Column('updated_at', sa.DateTime),
        sa.Column('last_login', sa.DateTime),
        sa.Column('failed_login_attempts', sa.Integer),
        sa.Column('locked_until', sa.DateTime),
    )

    # --- Tables with FK to users or exercise_templates ---

    op.create_table(
        'exercise_configs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('exercise_id', UUID(as_uuid=True), sa.ForeignKey('exercise_templates.id'), nullable=False),
        sa.Column('version', sa.Integer),
        sa.Column('is_active', sa.Boolean),
        sa.Column('joint_angle_rules', sa.JSON, nullable=False),
        sa.Column('movement_phases', sa.JSON, nullable=False),
        sa.Column('feedback_templates', sa.JSON, nullable=False),
        sa.Column('classification_metadata', sa.JSON),
        sa.Column('rom_rules', sa.JSON),
        sa.Column('posture_rules', sa.JSON),
        sa.Column('symmetry_rules', sa.JSON),
        sa.Column('reference_pose_data', sa.JSON),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
    )

    op.create_table(
        'exercise_progress',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('exercise_type', sa.String(50), nullable=False),
        sa.Column('form_score', sa.Float, nullable=False),
        sa.Column('consistency_score', sa.Float, nullable=False),
        sa.Column('total_reps', sa.Integer, nullable=False),
        sa.Column('improvement_areas', sa.Text, nullable=False),
        sa.Column('last_updated', sa.DateTime, nullable=False),
    )

    op.create_table(
        'subscriptions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('tier', sa.Enum('FREE', 'BASIC', 'PRO', 'ENTERPRISE', 'PREMIUM', name='subscriptiontier', create_type=False), nullable=False),
        sa.Column('start_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_date', sa.DateTime(timezone=True)),
        sa.Column('stripe_subscription_id', sa.String(255), unique=True),
        sa.Column('stripe_customer_id', sa.String(255)),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('cancel_at_period_end', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        'user_sessions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('session_id', UUID(as_uuid=True), nullable=False),
        sa.Column('user_agent', sa.String),
        sa.Column('ip_address', sa.String),
        sa.Column('auth_method', sa.String),
        sa.Column('device_token', sa.String),
        sa.Column('expires_at', sa.DateTime),
        sa.Column('last_active', sa.DateTime),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        'user_settings',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('notifications', sa.JSON),
        sa.Column('privacy', sa.JSON),
        sa.Column('theme', sa.String),
        sa.Column('language', sa.String),
        sa.Column('exercise_preferences', sa.JSON),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        'videos',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('filename', sa.String, nullable=False),
        sa.Column('object_key', sa.String, unique=True),
        sa.Column('url', sa.String),
        sa.Column('processed_url', sa.String),
        sa.Column('exercise_type', sa.String),
        sa.Column('mime_type', sa.String, nullable=False),
        sa.Column('size', sa.BigInteger),
        sa.Column('duration', sa.Float),
        sa.Column('resolution', sa.String),
        sa.Column('fps', sa.Float),
        sa.Column('status', sa.Enum(
            'PENDING_UPLOAD', 'UPLOADED', 'PROCESSING', 'PROCESSED',
            'PROCESSING_FAILED', 'PENDING_ANALYSIS', 'ANALYZING',
            'ANALYSIS_COMPLETE', 'ANALYSIS_FAILED', 'PUBLISHED', 'ARCHIVED',
            'ERROR', 'VIDEO_PROCESSING_FAILED',
            'POSE_DETECTION_PENDING', 'POSE_DETECTION_IN_PROGRESS',
            'POSE_DETECTED', 'POSE_DETECTION_FAILED',
            'ANGLE_CALCULATION_PENDING', 'ANGLE_CALCULATION_IN_PROGRESS',
            'ANGLES_CALCULATED', 'ANGLE_CALCULATION_FAILED',
            'FORM_ANALYSIS_PENDING', 'FORM_ANALYSIS_IN_PROGRESS',
            'FORM_ANALYSIS_COMPLETE', 'FORM_ANALYSIS_FAILED',
            'FRAMES_EXTRACTED', 'FRAMES_EXTRACTION_FAILED',
            name='videostatus', create_type=False,
        ), nullable=False),
        sa.Column('processing_errors', sa.JSON),
        sa.Column('error_message', sa.Text),
        sa.Column('processed_object_key', sa.String),
        sa.Column('frame_s3_keys', sa.JSON),
        sa.Column('processed_frame_count', sa.Integer),
        sa.Column('thumbnail_s3_key', sa.String),
        sa.Column('thumbnail_url', sa.String),
        sa.Column('additional_metadata', sa.JSON),
        sa.Column('pose_data', sa.JSON),
        sa.Column('pose_visualizations', sa.JSON),
        sa.Column('analysis_results', sa.JSON),
        sa.Column('stats', sa.JSON),
        sa.Column('score', sa.Float),
        sa.Column('rep_count', sa.Integer),
        sa.Column('feedback', sa.JSON),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
        sa.Column('raw_pose_data', sa.JSON),
        sa.Column('calculated_angles', sa.JSON),
        sa.Column('celery_task_id', sa.String),
        sa.Column('compressed_pose_data', sa.LargeBinary),
        sa.Column('pose_compression_method', sa.Enum('NONE', 'GZIP', 'LZ4', 'ZSTD', name='compressionmethod', create_type=False)),
        sa.Column('compressed_features', sa.LargeBinary),
        sa.Column('features_compression_method', sa.Enum('NONE', 'GZIP', 'LZ4', 'ZSTD', name='compressionmethod', create_type=False)),
        sa.Column('original_pose_size', sa.Integer),
        sa.Column('compressed_pose_size', sa.Integer),
        sa.Column('compression_ratio', sa.Float),
        sa.Column('compression_stats', sa.JSON),
        sa.Column('optimized_pose_data', sa.LargeBinary),
        sa.Column('pose_storage_format', sa.Enum('JSON', 'MSGPACK', 'PROTOBUF', 'PICKLE', name='storageformat', create_type=False)),
        sa.Column('optimized_features', sa.LargeBinary),
        sa.Column('features_storage_format', sa.Enum('JSON', 'MSGPACK', 'PROTOBUF', 'PICKLE', name='storageformat', create_type=False)),
        sa.Column('original_json_size', sa.Integer),
        sa.Column('optimized_size', sa.Integer),
        sa.Column('storage_optimization_ratio', sa.Float),
        sa.Column('storage_optimization_stats', sa.JSON),
    )

    op.create_table(
        'workouts',
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.String(1024)),
        sa.Column('duration', sa.Integer),
        sa.Column('calories_burned', sa.Integer),
        sa.Column('workout_metadata', sa.JSON),
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # --- Tables with deeper FK chains ---

    op.create_table(
        'exercises',
        sa.Column('workout_id', UUID(as_uuid=True), sa.ForeignKey('workouts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.String(1024)),
        sa.Column('sets', sa.Integer),
        sa.Column('reps', sa.Integer),
        sa.Column('weight', sa.Float),
        sa.Column('duration', sa.Integer),
        sa.Column('rest_time', sa.Integer),
        sa.Column('exercise_metadata', sa.JSON),
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        'form_checks',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('video_url', sa.String, nullable=False),
        sa.Column('exercise_id', UUID(as_uuid=True), sa.ForeignKey('exercise_templates.id'), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('video_id', UUID(as_uuid=True), sa.ForeignKey('videos.id')),
        sa.Column('feedback', sa.String),
        sa.Column('score', sa.Float),
        sa.Column('keypoints', sa.JSON),
        sa.Column('status', sa.Enum('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'CANCELLED', name='formcheckstatus', create_type=False), nullable=False),
        sa.Column('analysis_url', sa.String(1024)),
        sa.Column('overall_feedback', sa.String(2048)),
        sa.Column('issues', sa.JSON),
        sa.Column('processing_time', sa.Float),
        sa.Column('confidence_score', sa.Float),
        sa.Column('form_metadata', sa.JSON),
        sa.Column('results', sa.JSON),
        sa.Column('details', sa.JSON),
        sa.Column('configuration_id', UUID(as_uuid=True), sa.ForeignKey('exercise_configs.id', ondelete='SET NULL'), index=True),
        sa.Column('reps_per_minute', sa.Float),
        sa.Column('reps_detected', sa.Integer),
        sa.Column('classified_exercise_slug', sa.String),
        sa.Column('classification_confidence', sa.Float),
        sa.Column('posture_score', sa.Float),
        sa.Column('stability_score', sa.Float),
        sa.Column('depth_score', sa.Float),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
    )

    op.create_table(
        'progress_snapshots',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('progress_id', sa.Integer, sa.ForeignKey('exercise_progress.id'), nullable=False),
        sa.Column('timestamp', sa.DateTime, nullable=False),
        sa.Column('form_score', sa.Float, nullable=False),
        sa.Column('consistency_score', sa.Float, nullable=False),
        sa.Column('reps', sa.Integer, nullable=False),
        sa.Column('notes', sa.Text),
    )

    op.create_table(
        'workout_plans',
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('workout_id', UUID(as_uuid=True), sa.ForeignKey('workouts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.String(1024)),
        sa.Column('frequency', sa.String(50)),
        sa.Column('start_date', sa.DateTime(timezone=True)),
        sa.Column('end_date', sa.DateTime(timezone=True)),
        sa.Column('plan_metadata', sa.JSON),
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        'feedback_items',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('form_check_id', UUID(as_uuid=True), sa.ForeignKey('form_checks.id', ondelete='CASCADE'), nullable=False),
        sa.Column('type', sa.Enum(
            'SUCCESS', 'WARNING', 'ERROR', 'FORM', 'TECHNIQUE', 'POSTURE',
            'RANGE', 'RANGE_OF_MOTION', 'SPEED', 'BALANCE', 'JOINT_ANGLE',
            'ALIGNMENT', 'GUIDANCE', 'FORM_CORRECTION',
            name='feedbacktype', create_type=False,
        ), nullable=False),
        sa.Column('message', sa.String(1024), nullable=False),
        sa.Column('timestamp', sa.Float, nullable=False),
        sa.Column('severity', sa.Enum('LOW', 'MEDIUM', 'HIGH', 'CRITICAL', 'INFO', name='feedbackseverity', create_type=False), nullable=False),
        sa.Column('joint_angles', sa.JSON),
        sa.Column('suggestions', sa.JSON),
        sa.Column('details_payload', sa.JSON),
        sa.Column('issue_specific_timestamp', sa.Float),
        sa.Column('rep_index', sa.Integer),
        sa.Column('movement_phase', sa.String),
        sa.Column('joint_name', sa.String),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        'posture_v1_inference_logs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, index=True),
        sa.Column('form_check_id', UUID(as_uuid=True), sa.ForeignKey('form_checks.id', ondelete='SET NULL'), index=True),
        sa.Column('video_id', UUID(as_uuid=True)),
        sa.Column('decision', sa.String(20), nullable=False),
        sa.Column('prob_fault', sa.Float),
        sa.Column('confidence', sa.Float),
        sa.Column('threshold', sa.Float),
        sa.Column('threshold_mode', sa.String(20)),
        sa.Column('posture_v1_mode', sa.String(10)),
        sa.Column('sequence_length', sa.Integer),
        sa.Column('missing_ratio', sa.Float),
        sa.Column('outlier_z_gt3', sa.Integer),
        sa.Column('outlier_z_gt6', sa.Integer),
        sa.Column('angle_validity', sa.JSON),
        sa.Column('gate_flags', sa.JSON),
        sa.Column('top_signals', sa.JSON),
        sa.Column('named_scores', sa.JSON),
        sa.Column('model_version', sa.String(50)),
        sa.Column('latency_ms', sa.Float),
        sa.Column('error', sa.Text),
    )

    # --- Indexes ---
    op.create_index('ix_form_checks_user_id', 'form_checks', ['user_id'])
    op.create_index('ix_form_checks_video_id', 'form_checks', ['video_id'])
    op.create_index('ix_form_checks_status', 'form_checks', ['status'])
    op.create_index('ix_form_checks_created_at', 'form_checks', ['created_at'])
    op.create_index('ix_videos_user_id', 'videos', ['user_id'])
    op.create_index('ix_videos_status', 'videos', ['status'])
    op.create_index('ix_feedback_items_form_check_id', 'feedback_items', ['form_check_id'])


def downgrade() -> None:
    op.drop_table('posture_v1_inference_logs')
    op.drop_table('feedback_items')
    op.drop_table('workout_plans')
    op.drop_table('progress_snapshots')
    op.drop_table('form_checks')
    op.drop_table('exercises')
    op.drop_table('workouts')
    op.drop_table('videos')
    op.drop_table('user_settings')
    op.drop_table('user_sessions')
    op.drop_table('subscriptions')
    op.drop_table('exercise_progress')
    op.drop_table('exercise_configs')
    op.drop_table('users')
    op.drop_table('exercise_templates')

    # Drop enum types
    for name in ['storageformat', 'compressionmethod', 'feedbackseverity',
                 'feedbacktype', 'videostatus', 'formcheckstatus', 'subscriptiontier']:
        sa.Enum(name=name).drop(op.get_bind(), checkfirst=True)
