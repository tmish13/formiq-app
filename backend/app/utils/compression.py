"""
Compression utilities for pose sequence data optimization.

This module provides efficient compression/decompression for pose sequences
to reduce storage requirements and improve transfer speeds.

Supported compression methods:
- GZIP: Standard compression, good balance of speed and compression ratio
- LZ4: Ultra-fast compression, lower ratio but excellent for real-time use
- ZSTD: Modern compression, excellent ratio and speed

Expected compression ratios for pose data:
- JSON pose sequences: 60-80% size reduction
- Feature vectors: 40-60% size reduction
"""

import gzip
import json
import logging
import time
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union
import lz4.frame
import zstandard as zstd

logger = logging.getLogger(__name__)


class CompressionMethod(str, Enum):
    """Supported compression methods."""
    NONE = "none"
    GZIP = "gzip"
    LZ4 = "lz4"
    ZSTD = "zstd"


class CompressionStats:
    """Statistics for compression operations."""
    
    def __init__(self):
        self.original_size: int = 0
        self.compressed_size: int = 0
        self.compression_time: float = 0.0
        self.decompression_time: float = 0.0
        self.compression_ratio: float = 0.0
        
    def calculate_ratio(self) -> float:
        """Calculate compression ratio (0.0 to 1.0, lower is better)."""
        if self.original_size == 0:
            return 1.0
        self.compression_ratio = self.compressed_size / self.original_size
        return self.compression_ratio
        
    def get_space_saved_mb(self) -> float:
        """Get space saved in MB."""
        return (self.original_size - self.compressed_size) / (1024 * 1024)
        
    def get_space_saved_percent(self) -> float:
        """Get space saved as percentage."""
        if self.original_size == 0:
            return 0.0
        return ((self.original_size - self.compressed_size) / self.original_size) * 100


class PoseDataCompressor:
    """
    High-performance compressor for pose sequence data.
    
    Optimized for the specific characteristics of pose data:
    - Repetitive coordinate structures
    - Floating point precision requirements
    - Temporal sequence patterns
    """
    
    def __init__(self, default_method: CompressionMethod = CompressionMethod.GZIP):
        self.default_method = default_method
        self._zstd_compressor = zstd.ZstdCompressor(level=3)  # Balanced speed/ratio
        self._zstd_decompressor = zstd.ZstdDecompressor()
        
    def compress_pose_sequence(
        self, 
        pose_sequence: List[Optional[List[Optional[Dict[str, Any]]]]], 
        method: Optional[CompressionMethod] = None
    ) -> Tuple[bytes, CompressionStats]:
        """
        Compress a pose sequence with performance tracking.
        
        Args:
            pose_sequence: MediaPipe pose sequence data
            method: Compression method to use
            
        Returns:
            Tuple of (compressed_data, compression_stats)
        """
        method = method or self.default_method
        stats = CompressionStats()
        
        try:
            # Serialize to JSON first
            json_data = json.dumps(pose_sequence, separators=(',', ':'))
            json_bytes = json_data.encode('utf-8')
            stats.original_size = len(json_bytes)
            
            # Compress based on method
            start_time = time.time()
            
            if method == CompressionMethod.NONE:
                compressed_data = json_bytes
            elif method == CompressionMethod.GZIP:
                compressed_data = gzip.compress(json_bytes, compresslevel=6)
            elif method == CompressionMethod.LZ4:
                compressed_data = lz4.frame.compress(json_bytes, compression_level=4)
            elif method == CompressionMethod.ZSTD:
                compressed_data = self._zstd_compressor.compress(json_bytes)
            else:
                raise ValueError(f"Unsupported compression method: {method}")
                
            stats.compression_time = time.time() - start_time
            stats.compressed_size = len(compressed_data)
            stats.calculate_ratio()
            
            logger.debug(
                f"Compressed pose sequence: {stats.original_size} -> {stats.compressed_size} bytes "
                f"({stats.compression_ratio:.3f} ratio, {stats.compression_time:.3f}s) "
                f"using {method}"
            )
            
            return compressed_data, stats
            
        except Exception as e:
            logger.error(f"Pose sequence compression failed: {e}", exc_info=True)
            raise
    
    def decompress_pose_sequence(
        self, 
        compressed_data: bytes, 
        method: CompressionMethod
    ) -> Tuple[List[Optional[List[Optional[Dict[str, Any]]]]], CompressionStats]:
        """
        Decompress a pose sequence with performance tracking.
        
        Args:
            compressed_data: Compressed pose sequence bytes
            method: Compression method used
            
        Returns:
            Tuple of (pose_sequence, decompression_stats)
        """
        stats = CompressionStats()
        stats.compressed_size = len(compressed_data)
        
        try:
            start_time = time.time()
            
            # Decompress based on method
            if method == CompressionMethod.NONE:
                json_bytes = compressed_data
            elif method == CompressionMethod.GZIP:
                json_bytes = gzip.decompress(compressed_data)
            elif method == CompressionMethod.LZ4:
                json_bytes = lz4.frame.decompress(compressed_data)
            elif method == CompressionMethod.ZSTD:
                json_bytes = self._zstd_decompressor.decompress(compressed_data)
            else:
                raise ValueError(f"Unsupported compression method: {method}")
                
            stats.decompression_time = time.time() - start_time
            stats.original_size = len(json_bytes)
            stats.calculate_ratio()
            
            # Parse JSON back to pose sequence
            json_data = json_bytes.decode('utf-8')
            pose_sequence = json.loads(json_data)
            
            logger.debug(
                f"Decompressed pose sequence: {stats.compressed_size} -> {stats.original_size} bytes "
                f"({stats.decompression_time:.3f}s) using {method}"
            )
            
            return pose_sequence, stats
            
        except Exception as e:
            logger.error(f"Pose sequence decompression failed: {e}", exc_info=True)
            raise
    
    def compress_features(
        self, 
        features: Dict[str, float], 
        method: Optional[CompressionMethod] = None
    ) -> Tuple[bytes, CompressionStats]:
        """
        Compress extracted features with optimized settings.
        
        Args:
            features: Dictionary of extracted biomechanical features
            method: Compression method to use
            
        Returns:
            Tuple of (compressed_data, compression_stats)
        """
        method = method or self.default_method
        stats = CompressionStats()
        
        try:
            # Use compact JSON for features (smaller keys, rounded values)
            compact_features = {
                k: round(v, 4) if isinstance(v, float) else v 
                for k, v in features.items()
            }
            
            json_data = json.dumps(compact_features, separators=(',', ':'))
            json_bytes = json_data.encode('utf-8')
            stats.original_size = len(json_bytes)
            
            start_time = time.time()
            
            if method == CompressionMethod.NONE:
                compressed_data = json_bytes
            elif method == CompressionMethod.GZIP:
                compressed_data = gzip.compress(json_bytes, compresslevel=9)  # Higher compression for small data
            elif method == CompressionMethod.LZ4:
                compressed_data = lz4.frame.compress(json_bytes, compression_level=6)
            elif method == CompressionMethod.ZSTD:
                compressed_data = self._zstd_compressor.compress(json_bytes)
            else:
                raise ValueError(f"Unsupported compression method: {method}")
                
            stats.compression_time = time.time() - start_time
            stats.compressed_size = len(compressed_data)
            stats.calculate_ratio()
            
            return compressed_data, stats
            
        except Exception as e:
            logger.error(f"Feature compression failed: {e}", exc_info=True)
            raise
    
    def decompress_features(
        self, 
        compressed_data: bytes, 
        method: CompressionMethod
    ) -> Tuple[Dict[str, float], CompressionStats]:
        """
        Decompress extracted features.
        
        Args:
            compressed_data: Compressed feature bytes
            method: Compression method used
            
        Returns:
            Tuple of (features_dict, decompression_stats)
        """
        stats = CompressionStats()
        stats.compressed_size = len(compressed_data)
        
        try:
            start_time = time.time()
            
            if method == CompressionMethod.NONE:
                json_bytes = compressed_data
            elif method == CompressionMethod.GZIP:
                json_bytes = gzip.decompress(compressed_data)
            elif method == CompressionMethod.LZ4:
                json_bytes = lz4.frame.decompress(compressed_data)
            elif method == CompressionMethod.ZSTD:
                json_bytes = self._zstd_decompressor.decompress(compressed_data)
            else:
                raise ValueError(f"Unsupported compression method: {method}")
                
            stats.decompression_time = time.time() - start_time
            stats.original_size = len(json_bytes)
            stats.calculate_ratio()
            
            json_data = json_bytes.decode('utf-8')
            features = json.loads(json_data)
            
            return features, stats
            
        except Exception as e:
            logger.error(f"Feature decompression failed: {e}", exc_info=True)
            raise


def benchmark_compression_methods(
    test_data: Union[List, Dict], 
    iterations: int = 5
) -> Dict[str, Dict[str, float]]:
    """
    Benchmark all compression methods on test data.
    
    Args:
        test_data: Test pose sequence or feature data
        iterations: Number of benchmark iterations
        
    Returns:
        Dictionary with performance metrics for each method
    """
    compressor = PoseDataCompressor()
    results = {}
    
    methods = [CompressionMethod.GZIP, CompressionMethod.LZ4, CompressionMethod.ZSTD]
    
    for method in methods:
        compression_times = []
        decompression_times = []
        compression_ratios = []
        
        for _ in range(iterations):
            if isinstance(test_data, list):
                compressed_data, comp_stats = compressor.compress_pose_sequence(test_data, method)
                _, decomp_stats = compressor.decompress_pose_sequence(compressed_data, method)
            else:
                compressed_data, comp_stats = compressor.compress_features(test_data, method)
                _, decomp_stats = compressor.decompress_features(compressed_data, method)
            
            compression_times.append(comp_stats.compression_time)
            decompression_times.append(decomp_stats.decompression_time)
            compression_ratios.append(comp_stats.compression_ratio)
        
        results[method.value] = {
            "avg_compression_time_ms": sum(compression_times) / len(compression_times) * 1000,
            "avg_decompression_time_ms": sum(decompression_times) / len(decompression_times) * 1000,
            "avg_compression_ratio": sum(compression_ratios) / len(compression_ratios),
            "avg_space_saved_percent": (1 - sum(compression_ratios) / len(compression_ratios)) * 100,
            "original_size_kb": comp_stats.original_size / 1024,
            "compressed_size_kb": comp_stats.compressed_size / 1024
        }
    
    return results


# Global compressor instance for easy access
default_compressor = PoseDataCompressor()

# Convenience functions
def compress_pose_sequence(
    pose_sequence: List[Optional[List[Optional[Dict[str, Any]]]]],
    method: CompressionMethod = CompressionMethod.GZIP
) -> Tuple[bytes, CompressionStats]:
    """Convenience function for pose sequence compression."""
    return default_compressor.compress_pose_sequence(pose_sequence, method)


def decompress_pose_sequence(
    compressed_data: bytes,
    method: CompressionMethod
) -> Tuple[List[Optional[List[Optional[Dict[str, Any]]]]], CompressionStats]:
    """Convenience function for pose sequence decompression."""
    return default_compressor.decompress_pose_sequence(compressed_data, method)


def compress_features(
    features: Dict[str, float],
    method: CompressionMethod = CompressionMethod.GZIP
) -> Tuple[bytes, CompressionStats]:
    """Convenience function for feature compression."""
    return default_compressor.compress_features(features, method)


def decompress_features(
    compressed_data: bytes,
    method: CompressionMethod
) -> Tuple[Dict[str, float], CompressionStats]:
    """Convenience function for feature decompression."""
    return default_compressor.decompress_features(compressed_data, method)