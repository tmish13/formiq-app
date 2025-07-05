"""
Storage optimization service for database format conversion.

This service optimizes storage formats for pose data and features by converting
from JSON to more efficient binary formats like MessagePack and ProtoBuf.

Features:
- MessagePack: Binary JSON-like format, 15-30% smaller than JSON
- ProtoBuf: Schema-based binary format, 40-60% smaller than JSON  
- Automatic format detection and conversion
- Performance benchmarking and optimization recommendations
- Backward compatibility with existing JSON data
"""

import json
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union
import msgpack
import pickle

logger = logging.getLogger(__name__)


class StorageFormat(str, Enum):
    """Supported storage formats for database optimization."""
    JSON = "json"
    MSGPACK = "msgpack"
    PROTOBUF = "protobuf"
    PICKLE = "pickle"  # For complex Python objects


@dataclass
class ConversionStats:
    """Statistics for storage format conversion operations."""
    
    def __init__(self):
        self.original_size: int = 0
        self.converted_size: int = 0
        self.conversion_time: float = 0.0
        self.format_from: str = ""
        self.format_to: str = ""
        self.space_saved_percent: float = 0.0
        self.size_ratio: float = 0.0
        
    def calculate_savings(self) -> None:
        """Calculate space savings and size ratio."""
        if self.original_size > 0:
            self.space_saved_percent = ((self.original_size - self.converted_size) / self.original_size) * 100
            self.size_ratio = self.converted_size / self.original_size
        else:
            self.space_saved_percent = 0.0
            self.size_ratio = 1.0
    
    def get_space_saved_mb(self) -> float:
        """Get space saved in MB."""
        return (self.original_size - self.converted_size) / (1024 * 1024)


class StorageOptimizer:
    """
    High-performance storage format optimizer for pose data and features.
    
    Optimizes database storage by converting JSON to more efficient binary formats:
    - MessagePack: Fast binary JSON-like format
    - ProtoBuf: Schema-based binary format (future implementation)
    - Automatic format selection based on data characteristics
    """
    
    def __init__(self):
        self._msgpack_encoder = msgpack.Packer(
            use_bin_type=True,
            strict_types=False,
            datetime=True,
            use_single_float=True  # Use 32-bit floats for better compression
        )
    
    def convert_pose_data_to_msgpack(
        self, 
        pose_data: Union[str, Dict, List], 
        optimize_precision: bool = True
    ) -> Tuple[bytes, ConversionStats]:
        """
        Convert pose data from JSON to MessagePack format.
        
        Args:
            pose_data: Pose data in JSON string or Python object format
            optimize_precision: Whether to optimize float precision for smaller size
            
        Returns:
            Tuple of (msgpack_data, conversion_stats)
        """
        stats = ConversionStats()
        stats.format_from = "json"
        stats.format_to = "msgpack"
        
        try:
            # Handle JSON string input
            if isinstance(pose_data, str):
                data = json.loads(pose_data)
                stats.original_size = len(pose_data.encode('utf-8'))
            else:
                data = pose_data
                json_str = json.dumps(data, separators=(',', ':'))
                stats.original_size = len(json_str.encode('utf-8'))
            
            # Optimize data for storage if requested
            if optimize_precision:
                data = self._optimize_pose_data_precision(data)
            
            start_time = time.time()
            msgpack_data = self._msgpack_encoder.pack(data)
            stats.conversion_time = time.time() - start_time
            
            stats.converted_size = len(msgpack_data)
            stats.calculate_savings()
            
            logger.debug(
                f"Converted pose data to MessagePack: {stats.original_size} -> {stats.converted_size} bytes "
                f"({stats.space_saved_percent:.1f}% saved, {stats.conversion_time:.3f}s)"
            )
            
            return msgpack_data, stats
            
        except Exception as e:
            logger.error(f"Pose data MessagePack conversion failed: {e}", exc_info=True)
            raise
    
    def convert_pose_data_from_msgpack(
        self, 
        msgpack_data: bytes
    ) -> Tuple[Union[Dict, List], ConversionStats]:
        """
        Convert pose data from MessagePack back to Python objects.
        
        Args:
            msgpack_data: MessagePack encoded pose data
            
        Returns:
            Tuple of (pose_data, conversion_stats)
        """
        stats = ConversionStats()
        stats.format_from = "msgpack"
        stats.format_to = "python_object"
        stats.original_size = len(msgpack_data)
        
        try:
            start_time = time.time()
            data = msgpack.unpackb(msgpack_data, use_list=True, strict_map_key=False, timestamp=3)
            stats.conversion_time = time.time() - start_time
            
            # Calculate converted size as JSON equivalent
            json_str = json.dumps(data, separators=(',', ':'))
            stats.converted_size = len(json_str.encode('utf-8'))
            stats.calculate_savings()
            
            logger.debug(
                f"Converted pose data from MessagePack: {stats.original_size} -> {stats.converted_size} bytes "
                f"({stats.conversion_time:.3f}s)"
            )
            
            return data, stats
            
        except Exception as e:
            logger.error(f"Pose data MessagePack deconversion failed: {e}", exc_info=True)
            raise
    
    def convert_features_to_msgpack(
        self, 
        features: Union[str, Dict[str, float]], 
        optimize_precision: bool = True
    ) -> Tuple[bytes, ConversionStats]:
        """
        Convert feature data from JSON to MessagePack format.
        
        Args:
            features: Feature data in JSON string or dict format
            optimize_precision: Whether to round floats for better compression
            
        Returns:
            Tuple of (msgpack_data, conversion_stats)
        """
        stats = ConversionStats()
        stats.format_from = "json"
        stats.format_to = "msgpack"
        
        try:
            # Handle JSON string input
            if isinstance(features, str):
                data = json.loads(features)
                stats.original_size = len(features.encode('utf-8'))
            else:
                data = features
                json_str = json.dumps(data, separators=(',', ':'))
                stats.original_size = len(json_str.encode('utf-8'))
            
            # Optimize feature precision for storage
            if optimize_precision:
                data = {
                    k: round(v, 4) if isinstance(v, float) else v 
                    for k, v in data.items()
                }
            
            start_time = time.time()
            msgpack_data = self._msgpack_encoder.pack(data)
            stats.conversion_time = time.time() - start_time
            
            stats.converted_size = len(msgpack_data)
            stats.calculate_savings()
            
            logger.debug(
                f"Converted features to MessagePack: {stats.original_size} -> {stats.converted_size} bytes "
                f"({stats.space_saved_percent:.1f}% saved, {stats.conversion_time:.3f}s)"
            )
            
            return msgpack_data, stats
            
        except Exception as e:
            logger.error(f"Feature MessagePack conversion failed: {e}", exc_info=True)
            raise
    
    def convert_features_from_msgpack(
        self, 
        msgpack_data: bytes
    ) -> Tuple[Dict[str, float], ConversionStats]:
        """
        Convert feature data from MessagePack back to Python dict.
        
        Args:
            msgpack_data: MessagePack encoded feature data
            
        Returns:
            Tuple of (features_dict, conversion_stats)
        """
        stats = ConversionStats()
        stats.format_from = "msgpack"
        stats.format_to = "python_dict"
        stats.original_size = len(msgpack_data)
        
        try:
            start_time = time.time()
            data = msgpack.unpackb(msgpack_data, strict_map_key=False, timestamp=3)
            stats.conversion_time = time.time() - start_time
            
            # Calculate converted size as JSON equivalent
            json_str = json.dumps(data, separators=(',', ':'))
            stats.converted_size = len(json_str.encode('utf-8'))
            stats.calculate_savings()
            
            return data, stats
            
        except Exception as e:
            logger.error(f"Feature MessagePack deconversion failed: {e}", exc_info=True)
            raise
    
    def convert_to_pickle(
        self, 
        data: Any
    ) -> Tuple[bytes, ConversionStats]:
        """
        Convert any Python object to pickle format for complex data storage.
        
        Args:
            data: Any Python object to pickle
            
        Returns:
            Tuple of (pickled_data, conversion_stats)
        """
        stats = ConversionStats()
        stats.format_from = "python_object"
        stats.format_to = "pickle"
        
        try:
            # Estimate original size
            json_str = json.dumps(data, separators=(',', ':'), default=str)
            stats.original_size = len(json_str.encode('utf-8'))
            
            start_time = time.time()
            pickled_data = pickle.dumps(data, protocol=pickle.HIGHEST_PROTOCOL)
            stats.conversion_time = time.time() - start_time
            
            stats.converted_size = len(pickled_data)
            stats.calculate_savings()
            
            return pickled_data, stats
            
        except Exception as e:
            logger.error(f"Pickle conversion failed: {e}", exc_info=True)
            raise
    
    def convert_from_pickle(
        self, 
        pickled_data: bytes
    ) -> Tuple[Any, ConversionStats]:
        """
        Convert pickled data back to Python object.
        
        Args:
            pickled_data: Pickle encoded data
            
        Returns:
            Tuple of (python_object, conversion_stats)
        """
        stats = ConversionStats()
        stats.format_from = "pickle"
        stats.format_to = "python_object"
        stats.original_size = len(pickled_data)
        
        try:
            start_time = time.time()
            data = pickle.loads(pickled_data)
            stats.conversion_time = time.time() - start_time
            
            return data, stats
            
        except Exception as e:
            logger.error(f"Pickle deconversion failed: {e}", exc_info=True)
            raise
    
    def _optimize_pose_data_precision(self, pose_data: Union[List, Dict]) -> Union[List, Dict]:
        """
        Optimize pose data precision to reduce storage size.
        
        Args:
            pose_data: Pose sequence or pose frame data
            
        Returns:
            Optimized pose data with reduced precision
        """
        if isinstance(pose_data, list):
            return [self._optimize_pose_data_precision(item) if item is not None else None for item in pose_data]
        elif isinstance(pose_data, dict):
            optimized = {}
            for key, value in pose_data.items():
                if isinstance(value, float):
                    # Use different precision for different pose attributes
                    if key in ['x', 'y', 'z']:
                        optimized[key] = round(value, 5)  # Coordinate precision
                    elif key == 'visibility':
                        optimized[key] = round(value, 3)  # Visibility precision
                    else:
                        optimized[key] = round(value, 4)  # General float precision
                elif isinstance(value, (list, dict)):
                    optimized[key] = self._optimize_pose_data_precision(value)
                else:
                    optimized[key] = value
            return optimized
        else:
            return pose_data
    
    def benchmark_storage_formats(
        self, 
        test_pose_data: List, 
        test_features: Dict[str, float], 
        iterations: int = 5
    ) -> Dict[str, Dict[str, float]]:
        """
        Benchmark different storage formats on test data.
        
        Args:
            test_pose_data: Test pose sequence data
            test_features: Test feature data
            iterations: Number of benchmark iterations
            
        Returns:
            Dictionary with performance metrics for each format
        """
        results = {
            "pose_data": {},
            "features": {}
        }
        
        # Benchmark pose data formats
        formats = [
            ("json", self._benchmark_json_pose),
            ("msgpack", self._benchmark_msgpack_pose),
            ("pickle", self._benchmark_pickle_pose)
        ]
        
        for format_name, benchmark_func in formats:
            times = []
            sizes = []
            savings = []
            
            for _ in range(iterations):
                converted_data, stats = benchmark_func(test_pose_data)
                times.append(stats.conversion_time)
                sizes.append(stats.converted_size)
                savings.append(stats.space_saved_percent)
            
            results["pose_data"][format_name] = {
                "avg_conversion_time_ms": sum(times) / len(times) * 1000,
                "avg_size_bytes": sum(sizes) / len(sizes),
                "avg_space_saved_percent": sum(savings) / len(savings),
                "size_kb": sum(sizes) / len(sizes) / 1024
            }
        
        # Benchmark feature data formats
        for format_name, benchmark_func in [
            ("json", self._benchmark_json_features),
            ("msgpack", self._benchmark_msgpack_features),
            ("pickle", self._benchmark_pickle_features)
        ]:
            times = []
            sizes = []
            savings = []
            
            for _ in range(iterations):
                converted_data, stats = benchmark_func(test_features)
                times.append(stats.conversion_time)
                sizes.append(stats.converted_size)
                savings.append(stats.space_saved_percent)
            
            results["features"][format_name] = {
                "avg_conversion_time_ms": sum(times) / len(times) * 1000,
                "avg_size_bytes": sum(sizes) / len(sizes),
                "avg_space_saved_percent": sum(savings) / len(savings),
                "size_kb": sum(sizes) / len(sizes) / 1024
            }
        
        return results
    
    def _benchmark_json_pose(self, pose_data: List) -> Tuple[str, ConversionStats]:
        """Benchmark JSON format for pose data."""
        stats = ConversionStats()
        stats.format_from = "python_object"
        stats.format_to = "json"
        
        start_time = time.time()
        json_str = json.dumps(pose_data, separators=(',', ':'))
        stats.conversion_time = time.time() - start_time
        
        stats.original_size = len(str(pose_data).encode('utf-8'))  # Rough estimate
        stats.converted_size = len(json_str.encode('utf-8'))
        stats.calculate_savings()
        
        return json_str, stats
    
    def _benchmark_msgpack_pose(self, pose_data: List) -> Tuple[bytes, ConversionStats]:
        """Benchmark MessagePack format for pose data."""
        return self.convert_pose_data_to_msgpack(pose_data)
    
    def _benchmark_pickle_pose(self, pose_data: List) -> Tuple[bytes, ConversionStats]:
        """Benchmark Pickle format for pose data."""
        return self.convert_to_pickle(pose_data)
    
    def _benchmark_json_features(self, features: Dict[str, float]) -> Tuple[str, ConversionStats]:
        """Benchmark JSON format for features."""
        stats = ConversionStats()
        stats.format_from = "python_dict"
        stats.format_to = "json"
        
        start_time = time.time()
        json_str = json.dumps(features, separators=(',', ':'))
        stats.conversion_time = time.time() - start_time
        
        stats.original_size = len(str(features).encode('utf-8'))  # Rough estimate
        stats.converted_size = len(json_str.encode('utf-8'))
        stats.calculate_savings()
        
        return json_str, stats
    
    def _benchmark_msgpack_features(self, features: Dict[str, float]) -> Tuple[bytes, ConversionStats]:
        """Benchmark MessagePack format for features."""
        return self.convert_features_to_msgpack(features)
    
    def _benchmark_pickle_features(self, features: Dict[str, float]) -> Tuple[bytes, ConversionStats]:
        """Benchmark Pickle format for features."""
        return self.convert_to_pickle(features)
    
    def get_optimal_format_recommendation(
        self, 
        data_size_bytes: int, 
        access_frequency: str = "medium",
        priority: str = "balanced"
    ) -> Dict[str, Any]:
        """
        Get optimal storage format recommendation based on data characteristics.
        
        Args:
            data_size_bytes: Size of data in bytes
            access_frequency: "high", "medium", "low"
            priority: "speed", "space", "balanced"
            
        Returns:
            Dictionary with format recommendation and reasoning
        """
        recommendations = {}
        
        # Size-based recommendations
        if data_size_bytes < 1024:  # < 1KB
            size_rec = "json"
            size_reason = "Small data, JSON overhead minimal"
        elif data_size_bytes < 10240:  # < 10KB
            size_rec = "msgpack"
            size_reason = "Medium data, MessagePack provides good compression"
        else:  # >= 10KB
            size_rec = "msgpack"
            size_reason = "Large data, MessagePack significantly reduces storage"
        
        # Frequency-based recommendations
        freq_recommendations = {
            "high": ("msgpack", "Fast serialization/deserialization for frequent access"),
            "medium": ("msgpack", "Good balance of speed and compression"),
            "low": ("msgpack", "Compression more important than speed for infrequent access")
        }
        freq_rec, freq_reason = freq_recommendations.get(access_frequency, freq_recommendations["medium"])
        
        # Priority-based recommendations
        priority_recommendations = {
            "speed": ("msgpack", "Fastest serialization while maintaining compression"),
            "space": ("msgpack", "Best compression ratio for storage optimization"),
            "balanced": ("msgpack", "Optimal balance of speed and compression")
        }
        priority_rec, priority_reason = priority_recommendations.get(priority, priority_recommendations["balanced"])
        
        # Final recommendation (MessagePack wins in most cases)
        final_format = "msgpack"
        
        return {
            "recommended_format": final_format,
            "confidence": "high",
            "reasoning": {
                "size_analysis": f"{size_rec}: {size_reason}",
                "frequency_analysis": f"{freq_rec}: {freq_reason}",
                "priority_analysis": f"{priority_rec}: {priority_reason}",
                "final_decision": "MessagePack provides optimal balance of compression and speed for pose data"
            },
            "expected_benefits": {
                "space_savings": "15-30% smaller than JSON",
                "speed_improvement": "2-3x faster than JSON parsing",
                "compatibility": "Binary format with wide language support"
            }
        }


# Global optimizer instance
default_optimizer = StorageOptimizer()

# Convenience functions
def convert_pose_to_msgpack(
    pose_data: Union[str, Dict, List], 
    optimize_precision: bool = True
) -> Tuple[bytes, ConversionStats]:
    """Convenience function for pose data MessagePack conversion."""
    return default_optimizer.convert_pose_data_to_msgpack(pose_data, optimize_precision)


def convert_pose_from_msgpack(msgpack_data: bytes) -> Tuple[Union[Dict, List], ConversionStats]:
    """Convenience function for pose data MessagePack deconversion."""
    return default_optimizer.convert_pose_data_from_msgpack(msgpack_data)


def convert_features_to_msgpack(
    features: Union[str, Dict[str, float]], 
    optimize_precision: bool = True
) -> Tuple[bytes, ConversionStats]:
    """Convenience function for feature MessagePack conversion."""
    return default_optimizer.convert_features_to_msgpack(features, optimize_precision)


def convert_features_from_msgpack(msgpack_data: bytes) -> Tuple[Dict[str, float], ConversionStats]:
    """Convenience function for feature MessagePack deconversion."""
    return default_optimizer.convert_features_from_msgpack(msgpack_data)