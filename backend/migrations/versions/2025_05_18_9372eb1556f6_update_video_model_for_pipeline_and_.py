"""update_video_model_for_pipeline_and_thumbnails

Revision ID: 9372eb1556f6
Revises: 202505190001
Create Date: 2025-05-18 22:38:56.819709

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '9372eb1556f6'
down_revision = '202505190001'
branch_labels = None
depends_on = None

# Define the enum type and new values for VideoStatus
video_status_enum_name = 'videostatus'
new_video_status_values = [
    'ANGLE_CALCULATION_PENDING',
    'ANGLE_CALCULATION_IN_PROGRESS',
    'ANGLES_CALCULATED',
    'ANGLE_CALCULATION_FAILED',
    'FORM_ANALYSIS_PENDING',
    'FORM_ANALYSIS_IN_PROGRESS',
    'FORM_ANALYSIS_COMPLETE',
    'FORM_ANALYSIS_FAILED',
    'FRAMES_EXTRACTED',
    'FRAMES_EXTRACTION_FAILED'
]

def upgrade() -> None:
    bind = op.get_bind()
    is_postgresql = bind.dialect.name == 'postgresql'

    if is_postgresql:
        # Add new values to the existing VideoStatus enum type
        # Ensure to add them one by one and use IF NOT EXISTS if supported, or handle errors if they already exist.
        # The most robust way is to add them if they don't exist.
        # However, standard SQL `ALTER TYPE ... ADD VALUE IF NOT EXISTS` is for PostgreSQL v10+
        # Assuming we might be on a version that supports it, or this command is idempotent.
        for value in new_video_status_values:
            op.execute(f"ALTER TYPE {video_status_enum_name} ADD VALUE IF NOT EXISTS '{value}'")

    # Rename column processed_frame_s3_keys to frame_s3_keys in videos table
    op.alter_column('videos', 'processed_frame_s3_keys', new_column_name='frame_s3_keys', existing_type=sa.JSON(), nullable=True)
    
    # Add new columns thumbnail_s3_key and thumbnail_url to videos table
    op.add_column('videos', sa.Column('thumbnail_s3_key', sa.String(), nullable=True))
    op.add_column('videos', sa.Column('thumbnail_url', sa.String(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    is_postgresql = bind.dialect.name == 'postgresql'

    # Revert column rename
    op.alter_column('videos', 'frame_s3_keys', new_column_name='processed_frame_s3_keys', existing_type=sa.JSON(), nullable=True)
    
    # Drop added columns
    op.drop_column('videos', 'thumbnail_url')
    op.drop_column('videos', 'thumbnail_s3_key')

    # Downgrading ENUM values is complex and often destructive.
    # For this migration, we will not attempt to remove the added enum values during downgrade
    # as it can cause issues if data using these new enum values exists.
    # It's generally safer to leave the enum more permissive on downgrade.
    # If removal is strictly necessary, it requires careful data migration and type recreation.
    if is_postgresql:
        # Placeholder: op.execute("COMMENT ON COLUMN videos.status IS 'Downgrade did not remove new enum values from videostatus type to preserve data integrity.'")
        pass 