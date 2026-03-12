"""Add compression support for pose data storage

Revision ID: add_compression_support
Revises: 2025_07_03_6d00e8e4809c
Create Date: 2025-07-05 03:15:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_compression_support'
down_revision = '2025_07_03_6d00e8e4809c'
branch_labels = None
depends_on = None

# Create compression method enum
compression_method_enum = postgresql.ENUM(
    'none', 'gzip', 'lz4', 'zstd',
    name='compression_method'
)


def upgrade():
    """Add compression support fields to videos table."""
    
    # Create compression method enum
    compression_method_enum.create(op.get_bind())
    
    # Add compression fields to videos table
    op.add_column('videos', sa.Column(
        'compressed_pose_data', 
        sa.LargeBinary, 
        nullable=True,
        comment='Compressed pose sequence data'
    ))
    
    op.add_column('videos', sa.Column(
        'pose_compression_method', 
        compression_method_enum,
        nullable=True,
        default='gzip',
        comment='Compression method used for pose data'
    ))
    
    op.add_column('videos', sa.Column(
        'compressed_features', 
        sa.LargeBinary, 
        nullable=True,
        comment='Compressed extracted features'
    ))
    
    op.add_column('videos', sa.Column(
        'features_compression_method', 
        compression_method_enum,
        nullable=True,
        default='gzip',
        comment='Compression method used for features'
    ))
    
    op.add_column('videos', sa.Column(
        'original_pose_size', 
        sa.Integer, 
        nullable=True,
        comment='Original size of pose data in bytes'
    ))
    
    op.add_column('videos', sa.Column(
        'compressed_pose_size', 
        sa.Integer, 
        nullable=True,
        comment='Compressed size of pose data in bytes'
    ))
    
    op.add_column('videos', sa.Column(
        'compression_ratio', 
        sa.Float, 
        nullable=True,
        comment='Compression ratio (compressed/original)'
    ))
    
    op.add_column('videos', sa.Column(
        'compression_stats', 
        sa.JSON, 
        nullable=True,
        comment='Detailed compression performance statistics'
    ))
    
    # Add index for compression method queries
    op.create_index(
        'idx_videos_pose_compression_method', 
        'videos', 
        ['pose_compression_method']
    )
    
    # Add index for compression ratio analysis
    op.create_index(
        'idx_videos_compression_ratio', 
        'videos', 
        ['compression_ratio']
    )


def downgrade():
    """Remove compression support fields."""
    
    # Drop indexes
    op.drop_index('idx_videos_compression_ratio', table_name='videos')
    op.drop_index('idx_videos_pose_compression_method', table_name='videos')
    
    # Drop columns
    op.drop_column('videos', 'compression_stats')
    op.drop_column('videos', 'compression_ratio')
    op.drop_column('videos', 'compressed_pose_size')
    op.drop_column('videos', 'original_pose_size')
    op.drop_column('videos', 'features_compression_method')
    op.drop_column('videos', 'compressed_features')
    op.drop_column('videos', 'pose_compression_method')
    op.drop_column('videos', 'compressed_pose_data')
    
    # Drop enum
    compression_method_enum.drop(op.get_bind())