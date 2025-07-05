"""Add storage optimization fields to video table

Revision ID: 2025_07_05_storage_optimization
Revises: 2025_07_03_6d00e8e4809c_add_onboarding_fields_to_user_table
Create Date: 2025-07-05 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '2025_07_05_storage_optimization'
down_revision = '2025_07_03_6d00e8e4809c_add_onboarding_fields_to_user_table'
branch_labels = None
depends_on = None


def upgrade():
    """Add storage optimization fields to support MessagePack/ProtoBuf storage formats."""
    
    # Create enum type for storage formats
    storage_format_enum = postgresql.ENUM('json', 'msgpack', 'protobuf', 'pickle', name='storageformat')
    storage_format_enum.create(op.get_bind())
    
    # Add storage optimization fields to videos table
    op.add_column('videos', sa.Column('optimized_pose_data', sa.LargeBinary(), nullable=True,
                                    comment='Optimized pose data in MessagePack/ProtoBuf format'))
    op.add_column('videos', sa.Column('pose_storage_format', storage_format_enum, nullable=True,
                                    comment='Storage format used for optimized pose data'))
    op.add_column('videos', sa.Column('optimized_features', sa.LargeBinary(), nullable=True,
                                    comment='Optimized features in MessagePack/ProtoBuf format'))
    op.add_column('videos', sa.Column('features_storage_format', storage_format_enum, nullable=True,
                                    comment='Storage format used for optimized features'))
    op.add_column('videos', sa.Column('original_json_size', sa.Integer(), nullable=True,
                                    comment='Original JSON size in bytes before optimization'))
    op.add_column('videos', sa.Column('optimized_size', sa.Integer(), nullable=True,
                                    comment='Optimized storage size in bytes'))
    op.add_column('videos', sa.Column('storage_optimization_ratio', sa.Float(), nullable=True,
                                    comment='Storage optimization ratio (optimized/original)'))
    op.add_column('videos', sa.Column('storage_optimization_stats', sa.JSON(), nullable=True,
                                    comment='Detailed storage optimization performance statistics'))


def downgrade():
    """Remove storage optimization fields."""
    
    # Remove storage optimization fields from videos table
    op.drop_column('videos', 'storage_optimization_stats')
    op.drop_column('videos', 'storage_optimization_ratio')
    op.drop_column('videos', 'optimized_size')
    op.drop_column('videos', 'original_json_size')
    op.drop_column('videos', 'features_storage_format')
    op.drop_column('videos', 'optimized_features')
    op.drop_column('videos', 'pose_storage_format')
    op.drop_column('videos', 'optimized_pose_data')
    
    # Drop the enum type
    storage_format_enum = postgresql.ENUM('json', 'msgpack', 'protobuf', 'pickle', name='storageformat')
    storage_format_enum.drop(op.get_bind())