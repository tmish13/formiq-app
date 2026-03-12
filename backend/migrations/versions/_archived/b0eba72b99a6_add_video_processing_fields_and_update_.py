"""add_video_processing_fields_and_update_status_enum

Revision ID: b0eba72b99a6
Revises: c7ffd09cdc07
Create Date: 2025-05-09 02:05:14.516759

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql # For postgresql.ENUM

# Import your application's VideoStatus enum
# This path needs to be correct for Alembic's execution context.
# Typically, a project's root is added to sys.path in alembic/env.py.
from app.models.enums import VideoStatus as AppVideoStatusEnum

NEW_VIDEO_STATUS_ENUM_NAME = 'videostatus_new' 

# revision identifiers, used by Alembic.
revision = 'b0eba72b99a6'
down_revision = 'c7ffd09cdc07' # Ensure this is the ID of your previous migration
branch_labels = None
depends_on = None


def upgrade() -> None:
    # op.execute("DROP TYPE IF EXISTS videostatus_new;") # Temporarily ensure it's clean

    # Step 1: Add new columns for processed frame information
    op.add_column('videos', sa.Column('processed_frame_paths', sa.JSON(), nullable=True))
    op.add_column('videos', sa.Column('processed_frame_count', sa.Integer(), nullable=True))

    # Step 2: Drop the existing 'status' column
    # This assumes that any data in the old status column is not needed or will be repopulated.
    op.drop_column('videos', 'status')

    # Step 3: Define AND EXPLICITLY CREATE the new ENUM type for PostgreSQL using values from AppVideoStatusEnum
    video_status_new_enum = postgresql.ENUM(
        'uploaded', 'processing', 'processed', 'failed', 'archived', 'transcoding_failed',
        name=NEW_VIDEO_STATUS_ENUM_NAME, 
        create_type=False # Set to False as we will create it manually
    )
    video_status_new_enum.create(op.get_bind(), checkfirst=True) # EXPLICITLY CREATE IT
    
    # Step 4: Add the new 'status' column using the newly defined ENUM type
    op.add_column('videos', sa.Column(
        'status', 
        video_status_new_enum, 
        server_default=AppVideoStatusEnum.UPLOADED.value,
        nullable=False
    ))


def downgrade() -> None:
    # Step 1: Drop the new 'status' column that was added in this migration
    op.drop_column('videos', 'status')
    
    # Step 2: Define the ENUM type and drop the ENUM type created in this migration from PostgreSQL
    video_status_new_enum_to_drop = postgresql.ENUM(
        'uploaded', 'processing', 'processed', 'failed', 'archived', 'transcoding_failed',
        name=NEW_VIDEO_STATUS_ENUM_NAME,
        create_type=False # It should already exist or this op is a no-op if checkfirst=True
    )
    video_status_new_enum_to_drop.drop(op.get_bind(), checkfirst=True)

    # Step 3: Drop the other columns added in this migration
    op.drop_column('videos', 'processed_frame_count')
    op.drop_column('videos', 'processed_frame_paths')

    # Note: This downgrade follows the "dev-only" strategy and does not 
    # attempt to restore the original 'status' column or its specific old enum type.
    # It only reverses the changes made by this particular upgrade script. 