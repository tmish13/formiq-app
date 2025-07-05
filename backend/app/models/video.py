"""Video model module."""
from typing import Optional, List, Dict, Any
from sqlalchemy import Column, String, ForeignKey, DateTime, Integer, Float, JSON, Boolean, Enum as SQLAEnum, BigInteger, Text, LargeBinary
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models.base import BaseModel, SQLiteUUID
import uuid
from app.models.enums import VideoStatus, CompressionMethod, StorageFormat
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func

class Video(BaseModel):
    """Video model for storing video metadata and processing status."""
    
    __tablename__ = "videos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String, nullable=False)
    object_key = Column(String, nullable=True, unique=True)
    url = Column(String, nullable=True)
    processed_url = Column(String, nullable=True)  # URL to processed video
    exercise_type = Column(String, nullable=True)  # Type of exercise in the video
    mime_type = Column(String, nullable=False)
    size = Column(BigInteger, nullable=True)
    duration = Column(Float, nullable=True)  # Duration in seconds
    resolution = Column(String, nullable=True)  # Resolution, e.g., "1280x720"
    fps = Column(Float, nullable=True)  # Frames per second
    status = Column(SQLAEnum(VideoStatus), default=VideoStatus.UPLOADED, nullable=False)
    processing_errors = Column(JSON, nullable=True) # Store detailed error information, potentially structured
    error_message = Column(Text, nullable=True) # For simple, top-level error messages
    processed_object_key = Column(String, nullable=True) # S3 key for the processed/normalized video
    frame_s3_keys = Column(JSON, nullable=True) # S3 keys for processed frames
    processed_frame_count = Column(Integer, nullable=True)
    thumbnail_s3_key = Column(String, nullable=True) # S3 key for the video thumbnail
    thumbnail_url = Column(String, nullable=True) # URL for the video thumbnail
    additional_metadata = Column(JSON, nullable=True)  # Renamed from metadata - General metadata
    pose_data = Column(JSON, nullable=True)  # Pose keypoints data
    pose_visualizations = Column(JSON, nullable=True)  # URLs to pose visualization frames
    analysis_results = Column(JSON, nullable=True)  # Form analysis results
    stats = Column(JSON, nullable=True)  # Processing statistics
    score = Column(Float, nullable=True)  # Overall form score
    rep_count = Column(Integer, nullable=True)  # Number of repetitions detected
    feedback = Column(JSON, nullable=True)  # Feedback items for the user
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    # AI Processing Results
    raw_pose_data = Column(JSON, nullable=True) # Stores list of landmarks (or None) for each frame
    # analysis_results = Column(JSONB, nullable=True) # For future detailed analysis output

    # Added for AI Pipeline Step 1.3
    calculated_angles = Column(JSON, nullable=True)

    celery_task_id = Column(String, nullable=True) # Added field for Celery task ID

    # Compression fields for storage optimization
    compressed_pose_data = Column(LargeBinary, nullable=True, comment="Compressed pose sequence data")
    pose_compression_method = Column(SQLAEnum(CompressionMethod), nullable=True, default=CompressionMethod.GZIP, comment="Compression method used for pose data")
    compressed_features = Column(LargeBinary, nullable=True, comment="Compressed extracted features")
    features_compression_method = Column(SQLAEnum(CompressionMethod), nullable=True, default=CompressionMethod.GZIP, comment="Compression method used for features")
    original_pose_size = Column(Integer, nullable=True, comment="Original size of pose data in bytes")
    compressed_pose_size = Column(Integer, nullable=True, comment="Compressed size of pose data in bytes")
    compression_ratio = Column(Float, nullable=True, comment="Compression ratio (compressed/original)")
    compression_stats = Column(JSON, nullable=True, comment="Detailed compression performance statistics")
    
    # Storage format optimization fields (Phase 3.3.1)
    optimized_pose_data = Column(LargeBinary, nullable=True, comment="Optimized pose data in MessagePack/ProtoBuf format")
    pose_storage_format = Column(SQLAEnum(StorageFormat), nullable=True, default=StorageFormat.MSGPACK, comment="Storage format used for optimized pose data")
    optimized_features = Column(LargeBinary, nullable=True, comment="Optimized features in MessagePack/ProtoBuf format")
    features_storage_format = Column(SQLAEnum(StorageFormat), nullable=True, default=StorageFormat.MSGPACK, comment="Storage format used for optimized features")
    original_json_size = Column(Integer, nullable=True, comment="Original JSON size in bytes before optimization")
    optimized_size = Column(Integer, nullable=True, comment="Optimized storage size in bytes")
    storage_optimization_ratio = Column(Float, nullable=True, comment="Storage optimization ratio (optimized/original)")
    storage_optimization_stats = Column(JSON, nullable=True, comment="Detailed storage optimization performance statistics")

    # Relationships
    user = relationship("User", back_populates="videos")
    form_checks = relationship("FormCheck", back_populates="video", cascade="all, delete-orphan", foreign_keys="FormCheck.video_id")

    def __repr__(self) -> str:
        """String representation of the video."""
        return f"<Video(id={self.id}, user_id={self.user_id}, filename={self.filename}, status={self.status})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the model to a dictionary."""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "filename": self.filename,
            "object_key": self.object_key,
            "url": self.url,
            "processed_url": self.processed_url,
            "exercise_type": self.exercise_type,
            "mime_type": self.mime_type,
            "size": self.size,
            "duration": self.duration,
            "resolution": self.resolution,
            "fps": self.fps,
            "status": self.status.value if self.status else None,
            "processing_errors": self.processing_errors,
            "processed_object_key": self.processed_object_key,
            "frame_s3_keys": self.frame_s3_keys,
            "processed_frame_count": self.processed_frame_count,
            "thumbnail_s3_key": self.thumbnail_s3_key,
            "thumbnail_url": self.thumbnail_url,
            "score": self.score,
            "rep_count": self.rep_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            # Compression info (non-sensitive metadata)
            "compression_ratio": self.compression_ratio,
            "pose_compression_method": self.pose_compression_method.value if self.pose_compression_method else None,
            "original_pose_size": self.original_pose_size,
            "compressed_pose_size": self.compressed_pose_size,
            # Exclude large fields: pose_data, pose_visualizations, analysis_results, stats, feedback, compressed_pose_data
        }
    
    def get_pose_data_decompressed(self) -> Optional[List[Optional[List[Optional[Dict[str, Any]]]]]]:
        """
        Get decompressed pose data.
        
        Returns:
            Decompressed pose sequence or None if no compressed data exists
        """
        if not self.compressed_pose_data or not self.pose_compression_method:
            return None
            
        try:
            from app.utils.compression import decompress_pose_sequence, CompressionMethod as CompMethod
            
            # Convert enum to compression module enum
            method = CompMethod(self.pose_compression_method.value)
            pose_sequence, _ = decompress_pose_sequence(self.compressed_pose_data, method)
            return pose_sequence
            
        except Exception as e:
            from app.core.logging import get_logger
            logger = get_logger(__name__)
            logger.error(f"Failed to decompress pose data for video {self.id}: {e}")
            return None
    
    def get_features_decompressed(self) -> Optional[Dict[str, float]]:
        """
        Get decompressed feature data.
        
        Returns:
            Decompressed features or None if no compressed data exists
        """
        if not self.compressed_features or not self.features_compression_method:
            return None
            
        try:
            from app.utils.compression import decompress_features, CompressionMethod as CompMethod
            
            # Convert enum to compression module enum
            method = CompMethod(self.features_compression_method.value)
            features, _ = decompress_features(self.compressed_features, method)
            return features
            
        except Exception as e:
            from app.core.logging import get_logger
            logger = get_logger(__name__)
            logger.error(f"Failed to decompress features for video {self.id}: {e}")
            return None
    
    def set_compressed_pose_data(
        self, 
        pose_sequence: List[Optional[List[Optional[Dict[str, Any]]]]], 
        compression_method: Optional[CompressionMethod] = None
    ) -> bool:
        """
        Compress and store pose sequence data.
        
        Args:
            pose_sequence: The pose sequence to compress and store
            compression_method: Compression method to use (defaults to GZIP)
            
        Returns:
            True if compression and storage succeeded, False otherwise
        """
        try:
            from app.utils.compression import compress_pose_sequence, CompressionMethod as CompMethod
            
            method = compression_method or CompressionMethod.GZIP
            comp_method = CompMethod(method.value)
            
            compressed_data, stats = compress_pose_sequence(pose_sequence, comp_method)
            
            # Store compressed data and metadata
            self.compressed_pose_data = compressed_data
            self.pose_compression_method = method
            self.original_pose_size = stats.original_size
            self.compressed_pose_size = stats.compressed_size
            self.compression_ratio = stats.compression_ratio
            
            # Store compression statistics
            self.compression_stats = {
                "pose_compression_time_ms": stats.compression_time * 1000,
                "pose_space_saved_percent": stats.get_space_saved_percent(),
                "pose_space_saved_mb": stats.get_space_saved_mb(),
                "compression_timestamp": datetime.utcnow().isoformat()
            }
            
            return True
            
        except Exception as e:
            from app.core.logging import get_logger
            logger = get_logger(__name__)
            logger.error(f"Failed to compress pose data for video {self.id}: {e}")
            return False
    
    def set_compressed_features(
        self, 
        features: Dict[str, float], 
        compression_method: Optional[CompressionMethod] = None
    ) -> bool:
        """
        Compress and store feature data.
        
        Args:
            features: The features to compress and store
            compression_method: Compression method to use (defaults to GZIP)
            
        Returns:
            True if compression and storage succeeded, False otherwise
        """
        try:
            from app.utils.compression import compress_features, CompressionMethod as CompMethod
            
            method = compression_method or CompressionMethod.GZIP
            comp_method = CompMethod(method.value)
            
            compressed_data, stats = compress_features(features, comp_method)
            
            # Store compressed data and metadata
            self.compressed_features = compressed_data
            self.features_compression_method = method
            
            # Update compression statistics
            if not self.compression_stats:
                self.compression_stats = {}
            
            self.compression_stats.update({
                "features_compression_time_ms": stats.compression_time * 1000,
                "features_original_size": stats.original_size,
                "features_compressed_size": stats.compressed_size,
                "features_compression_ratio": stats.compression_ratio,
                "features_space_saved_percent": stats.get_space_saved_percent()
            })
            
            return True
            
        except Exception as e:
            from app.core.logging import get_logger
            logger = get_logger(__name__)
            logger.error(f"Failed to compress features for video {self.id}: {e}")
            return False
    
    def set_optimized_pose_data(
        self, 
        pose_sequence: List[Optional[List[Optional[Dict[str, Any]]]]], 
        storage_format: Optional[StorageFormat] = None
    ) -> bool:
        """
        Optimize and store pose sequence data in MessagePack/ProtoBuf format.
        
        Args:
            pose_sequence: The pose sequence to optimize and store
            storage_format: Storage format to use (defaults to MSGPACK)
            
        Returns:
            True if optimization and storage succeeded, False otherwise
        """
        try:
            from app.services.storage_optimization_service import convert_pose_to_msgpack
            
            format = storage_format or StorageFormat.MSGPACK
            
            if format == StorageFormat.MSGPACK:
                optimized_data, stats = convert_pose_to_msgpack(pose_sequence, optimize_precision=True)
            else:
                # For future ProtoBuf support
                raise ValueError(f"Storage format {format} not yet implemented")
            
            # Store optimized data and metadata
            self.optimized_pose_data = optimized_data
            self.pose_storage_format = format
            self.original_json_size = stats.original_size
            self.optimized_size = stats.converted_size
            self.storage_optimization_ratio = stats.size_ratio
            
            # Store optimization statistics
            if not self.storage_optimization_stats:
                self.storage_optimization_stats = {}
            
            self.storage_optimization_stats.update({
                "pose_optimization_time_ms": stats.conversion_time * 1000,
                "pose_space_saved_percent": stats.space_saved_percent,
                "pose_space_saved_mb": stats.get_space_saved_mb(),
                "pose_format": format.value,
                "optimization_timestamp": datetime.utcnow().isoformat()
            })
            
            return True
            
        except Exception as e:
            from app.core.logging import get_logger
            logger = get_logger(__name__)
            logger.error(f"Failed to optimize pose data for video {self.id}: {e}")
            return False
    
    def get_optimized_pose_data(self) -> Optional[List[Optional[List[Optional[Dict[str, Any]]]]]]:
        """
        Get deoptimized pose data from MessagePack/ProtoBuf format.
        
        Returns:
            Deoptimized pose sequence or None if no optimized data exists
        """
        if not self.optimized_pose_data or not self.pose_storage_format:
            return None
            
        try:
            from app.services.storage_optimization_service import convert_pose_from_msgpack
            
            if self.pose_storage_format == StorageFormat.MSGPACK:
                pose_sequence, _ = convert_pose_from_msgpack(self.optimized_pose_data)
                return pose_sequence
            else:
                # For future ProtoBuf support
                raise ValueError(f"Storage format {self.pose_storage_format} not yet implemented")
            
        except Exception as e:
            from app.core.logging import get_logger
            logger = get_logger(__name__)
            logger.error(f"Failed to deoptimize pose data for video {self.id}: {e}")
            return None
    
    def set_optimized_features(
        self, 
        features: Dict[str, float], 
        storage_format: Optional[StorageFormat] = None
    ) -> bool:
        """
        Optimize and store feature data in MessagePack/ProtoBuf format.
        
        Args:
            features: The features to optimize and store
            storage_format: Storage format to use (defaults to MSGPACK)
            
        Returns:
            True if optimization and storage succeeded, False otherwise
        """
        try:
            from app.services.storage_optimization_service import convert_features_to_msgpack
            
            format = storage_format or StorageFormat.MSGPACK
            
            if format == StorageFormat.MSGPACK:
                optimized_data, stats = convert_features_to_msgpack(features, optimize_precision=True)
            else:
                # For future ProtoBuf support
                raise ValueError(f"Storage format {format} not yet implemented")
            
            # Store optimized data and metadata
            self.optimized_features = optimized_data
            self.features_storage_format = format
            
            # Update optimization statistics
            if not self.storage_optimization_stats:
                self.storage_optimization_stats = {}
            
            self.storage_optimization_stats.update({
                "features_optimization_time_ms": stats.conversion_time * 1000,
                "features_original_size": stats.original_size,
                "features_optimized_size": stats.converted_size,
                "features_optimization_ratio": stats.size_ratio,
                "features_space_saved_percent": stats.space_saved_percent,
                "features_format": format.value
            })
            
            return True
            
        except Exception as e:
            from app.core.logging import get_logger
            logger = get_logger(__name__)
            logger.error(f"Failed to optimize features for video {self.id}: {e}")
            return False
    
    def get_optimized_features(self) -> Optional[Dict[str, float]]:
        """
        Get deoptimized feature data from MessagePack/ProtoBuf format.
        
        Returns:
            Deoptimized features or None if no optimized data exists
        """
        if not self.optimized_features or not self.features_storage_format:
            return None
            
        try:
            from app.services.storage_optimization_service import convert_features_from_msgpack
            
            if self.features_storage_format == StorageFormat.MSGPACK:
                features, _ = convert_features_from_msgpack(self.optimized_features)
                return features
            else:
                # For future ProtoBuf support
                raise ValueError(f"Storage format {self.features_storage_format} not yet implemented")
            
        except Exception as e:
            from app.core.logging import get_logger
            logger = get_logger(__name__)
            logger.error(f"Failed to deoptimize features for video {self.id}: {e}")
            return None 