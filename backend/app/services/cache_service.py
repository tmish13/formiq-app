"""
Redis caching service for FormIQ pose processing optimization.

This service provides intelligent caching for pose sequences, extracted features,
and ML predictions to dramatically improve processing performance.

Key Features:
- Smart cache key generation based on data hashes
- Pose data serialization with compression support
- Configurable TTL policies for different data types
- Connection pooling and error handling
- Performance monitoring and metrics
- Circuit breaker pattern for reliability
"""

import asyncio
import hashlib
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import UUID
import numpy as np

import redis.asyncio as redis
from redis.asyncio import ConnectionPool
from redis.exceptions import ConnectionError, TimeoutError, RedisError

from app.core.config import Settings
from app.core.exceptions import ServerErrorException
from app.utils.compression import (
    compress_pose_sequence, decompress_pose_sequence, 
    compress_features, decompress_features,
    CompressionMethod, CompressionStats
)

logger = logging.getLogger(__name__)


class CacheKeyManager:
    """Manages cache key generation and organization."""
    
    # Key prefixes for different data types
    POSE_SEQUENCE_PREFIX = "pose_seq"
    FEATURES_PREFIX = "features"
    ML_PREDICTION_PREFIX = "ml_pred"
    VIDEO_METADATA_PREFIX = "video_meta"
    
    # Key separators
    SEPARATOR = ":"
    
    @classmethod
    def generate_pose_sequence_key(cls, pose_sequence: List) -> str:
        """Generate cache key for pose sequence data."""
        # Create hash of pose sequence for consistent caching
        pose_hash = cls._generate_data_hash(pose_sequence)
        return f"{cls.POSE_SEQUENCE_PREFIX}{cls.SEPARATOR}{pose_hash}"
    
    @classmethod
    def generate_features_key(cls, features: Dict[str, float]) -> str:
        """Generate cache key for extracted features."""
        # Sort features for consistent hashing
        sorted_features = dict(sorted(features.items()))
        features_hash = cls._generate_data_hash(sorted_features)
        return f"{cls.FEATURES_PREFIX}{cls.SEPARATOR}{features_hash}"
    
    @classmethod
    def generate_ml_prediction_key(cls, features: Dict[str, float], model_version: str = "default") -> str:
        """Generate cache key for ML prediction results."""
        # Include model version in key for cache invalidation on model updates
        sorted_features = dict(sorted(features.items()))
        features_hash = cls._generate_data_hash(sorted_features)
        return f"{cls.ML_PREDICTION_PREFIX}{cls.SEPARATOR}{model_version}{cls.SEPARATOR}{features_hash}"
    
    @classmethod
    def generate_video_metadata_key(cls, video_id: UUID) -> str:
        """Generate cache key for video metadata."""
        return f"{cls.VIDEO_METADATA_PREFIX}{cls.SEPARATOR}{str(video_id)}"
    
    @classmethod
    def _generate_data_hash(cls, data: Any) -> str:
        """Generate consistent hash for any data structure."""
        try:
            # Convert data to JSON string for consistent hashing
            json_str = json.dumps(data, sort_keys=True, separators=(',', ':'))
            # Use SHA-256 for consistent hashing
            return hashlib.sha256(json_str.encode('utf-8')).hexdigest()[:16]  # 16 chars for brevity
        except Exception as e:
            logger.warning(f"Failed to generate hash for data: {e}")
            # Fallback to timestamp-based key (will not cache effectively)
            return f"fallback_{int(time.time())}"


class CacheMetrics:
    """Tracks cache performance metrics."""
    
    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.errors = 0
        self.total_response_time = 0.0
        self.operations = 0
        self.last_reset = datetime.utcnow()
    
    def record_hit(self, response_time: float):
        """Record a cache hit with response time."""
        self.hits += 1
        self.total_response_time += response_time
        self.operations += 1
    
    def record_miss(self, response_time: float):
        """Record a cache miss with response time."""
        self.misses += 1
        self.total_response_time += response_time
        self.operations += 1
    
    def record_error(self):
        """Record a cache error."""
        self.errors += 1
        self.operations += 1
    
    def get_hit_rate(self) -> float:
        """Calculate cache hit rate as percentage."""
        total_attempts = self.hits + self.misses
        return (self.hits / total_attempts * 100) if total_attempts > 0 else 0.0
    
    def get_average_response_time(self) -> float:
        """Calculate average response time in milliseconds."""
        return (self.total_response_time / self.operations * 1000) if self.operations > 0 else 0.0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        total_attempts = self.hits + self.misses
        uptime = (datetime.utcnow() - self.last_reset).total_seconds()
        
        return {
            "hits": self.hits,
            "misses": self.misses,
            "errors": self.errors,
            "total_operations": self.operations,
            "hit_rate_percent": self.get_hit_rate(),
            "average_response_time_ms": self.get_average_response_time(),
            "operations_per_second": self.operations / uptime if uptime > 0 else 0.0,
            "uptime_seconds": uptime,
            "last_reset": self.last_reset.isoformat()
        }
    
    def reset(self):
        """Reset all metrics."""
        self.hits = 0
        self.misses = 0
        self.errors = 0
        self.total_response_time = 0.0
        self.operations = 0
        self.last_reset = datetime.utcnow()


class CacheService:
    """
    High-performance Redis caching service for FormIQ pose processing.
    
    Features:
    - Intelligent cache key management
    - Compressed data storage for large pose sequences
    - Configurable TTL policies
    - Performance monitoring and metrics
    - Circuit breaker pattern for reliability
    - Async operations for optimal performance
    """
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.pool: Optional[ConnectionPool] = None
        self.redis: Optional[redis.Redis] = None
        self.metrics = CacheMetrics()
        self.key_manager = CacheKeyManager()
        
        # Cache configuration
        self.default_ttl = getattr(settings, 'CACHE_DEFAULT_TTL', 3600)  # 1 hour
        self.pose_ttl = getattr(settings, 'CACHE_POSE_TTL', 7200)  # 2 hours
        self.features_ttl = getattr(settings, 'CACHE_FEATURES_TTL', 1800)  # 30 minutes
        self.prediction_ttl = getattr(settings, 'CACHE_PREDICTION_TTL', 3600)  # 1 hour
        
        # Connection settings
        self.redis_url = getattr(settings, 'REDIS_URL', 'redis://localhost:6379/0')
        self.max_connections = getattr(settings, 'REDIS_MAX_CONNECTIONS', 20)
        self.connection_timeout = getattr(settings, 'REDIS_CONNECTION_TIMEOUT', 5.0)
        
        # Performance settings
        self.use_compression = getattr(settings, 'CACHE_USE_COMPRESSION', True)
        self.compression_threshold = getattr(settings, 'CACHE_COMPRESSION_THRESHOLD', 1024)  # bytes
        
        # Circuit breaker settings
        self.circuit_breaker_enabled = getattr(settings, 'CACHE_CIRCUIT_BREAKER', True)
        self.error_threshold = 5  # errors before opening circuit
        self.error_window = 60  # seconds
        self.circuit_recovery_timeout = 30  # seconds
        
        self._circuit_breaker_state = "closed"  # closed, open, half-open
        self._error_count = 0
        self._last_error_time = 0
        self._circuit_opened_time = 0
    
    def _convert_numpy_types(self, obj: Any) -> Any:
        """Convert numpy types to native Python types for JSON serialization."""
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.bool_):
            return bool(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, dict):
            return {k: self._convert_numpy_types(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_numpy_types(item) for item in obj]
        elif isinstance(obj, tuple):
            return tuple(self._convert_numpy_types(item) for item in obj)
        else:
            return obj
    
    async def initialize(self) -> bool:
        """
        Initialize Redis connection pool and test connectivity.
        
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            # Create connection pool
            self.pool = ConnectionPool.from_url(
                self.redis_url,
                max_connections=self.max_connections,
                socket_connect_timeout=self.connection_timeout,
                socket_timeout=self.connection_timeout,
                decode_responses=False  # Keep binary data as bytes
            )
            
            # Create Redis client
            self.redis = redis.Redis(connection_pool=self.pool)
            
            # Test connection
            await self.redis.ping()
            
            logger.info(f"Redis cache service initialized successfully: {self.redis_url}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Redis cache service: {e}")
            self.redis = None
            self.pool = None
            return False
    
    async def close(self):
        """Close Redis connections and cleanup resources."""
        if self.redis:
            await self.redis.close()
        if self.pool:
            await self.pool.disconnect()
        logger.info("Redis cache service closed")
    
    def _is_circuit_open(self) -> bool:
        """Check if circuit breaker is open."""
        if not self.circuit_breaker_enabled:
            return False
        
        current_time = time.time()
        
        # Check if circuit should recover
        if (self._circuit_breaker_state == "open" and 
            current_time - self._circuit_opened_time > self.circuit_recovery_timeout):
            self._circuit_breaker_state = "half-open"
            logger.info("Cache circuit breaker moved to half-open state")
        
        return self._circuit_breaker_state == "open"
    
    def _record_success(self):
        """Record successful operation for circuit breaker."""
        if self._circuit_breaker_state == "half-open":
            self._circuit_breaker_state = "closed"
            self._error_count = 0
            logger.info("Cache circuit breaker closed after successful operation")
    
    def _record_error(self):
        """Record error for circuit breaker."""
        current_time = time.time()
        
        # Reset error count if outside error window
        if current_time - self._last_error_time > self.error_window:
            self._error_count = 0
        
        self._error_count += 1
        self._last_error_time = current_time
        
        # Open circuit if error threshold exceeded
        if self._error_count >= self.error_threshold and self._circuit_breaker_state == "closed":
            self._circuit_breaker_state = "open"
            self._circuit_opened_time = current_time
            logger.warning(f"Cache circuit breaker opened after {self._error_count} errors")
    
    async def _execute_with_circuit_breaker(self, operation_func, *args, **kwargs):
        """Execute Redis operation with circuit breaker protection."""
        if self._is_circuit_open():
            logger.debug("Cache operation skipped - circuit breaker is open")
            return None
        
        try:
            result = await operation_func(*args, **kwargs)
            self._record_success()
            return result
        except Exception as e:
            self._record_error()
            self.metrics.record_error()
            logger.warning(f"Cache operation failed: {e}")
            return None
    
    async def get_pose_sequence(
        self, 
        pose_sequence_key: Optional[str] = None,
        pose_sequence: Optional[List] = None
    ) -> Optional[Tuple[List, CompressionStats]]:
        """
        Retrieve cached pose sequence data.
        
        Args:
            pose_sequence_key: Pre-generated cache key
            pose_sequence: Pose sequence to generate key from
            
        Returns:
            Tuple of (pose_sequence, decompression_stats) or None if not found
        """
        if not self.redis:
            return None
        
        start_time = time.time()
        
        try:
            # Generate key if not provided
            if pose_sequence_key is None:
                if pose_sequence is None:
                    logger.warning("Either pose_sequence_key or pose_sequence must be provided")
                    return None
                pose_sequence_key = self.key_manager.generate_pose_sequence_key(pose_sequence)
            
            # Get from cache
            cached_data = await self._execute_with_circuit_breaker(
                self.redis.get, pose_sequence_key
            )
            
            response_time = time.time() - start_time
            
            if cached_data is None:
                self.metrics.record_miss(response_time)
                return None
            
            # Deserialize cached data
            try:
                cache_entry = json.loads(cached_data.decode('utf-8'))
                compressed_data = bytes.fromhex(cache_entry['data'])
                compression_method = CompressionMethod(cache_entry['method'])
                
                # Decompress
                decompressed_sequence, decomp_stats = decompress_pose_sequence(
                    compressed_data, compression_method
                )
                
                self.metrics.record_hit(response_time)
                logger.debug(f"Cache hit for pose sequence: {pose_sequence_key}")
                return decompressed_sequence, decomp_stats
                
            except Exception as e:
                logger.warning(f"Failed to deserialize cached pose sequence: {e}")
                self.metrics.record_miss(response_time)
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving pose sequence from cache: {e}")
            self.metrics.record_error()
            return None
    
    async def set_pose_sequence(
        self,
        pose_sequence: List,
        ttl: Optional[int] = None,
        compression_method: Optional[CompressionMethod] = None
    ) -> bool:
        """
        Cache pose sequence data with compression.
        
        Args:
            pose_sequence: Pose sequence to cache
            ttl: Time to live in seconds (default: settings.CACHE_POSE_TTL)
            compression_method: Compression method to use
            
        Returns:
            True if cached successfully, False otherwise
        """
        if not self.redis:
            return False
        
        try:
            # Generate cache key
            cache_key = self.key_manager.generate_pose_sequence_key(pose_sequence)
            
            # Auto-select compression method if not specified
            if compression_method is None and self.use_compression:
                estimated_size = len(json.dumps(pose_sequence).encode('utf-8'))
                if estimated_size > self.compression_threshold:
                    estimated_size_kb = estimated_size / 1024
                    # Select compression method based on size
                    if estimated_size_kb > 100:
                        compression_method = CompressionMethod.LZ4  # Fast compression for large data
                    elif estimated_size_kb > 10:
                        compression_method = CompressionMethod.GZIP  # Good balance
                    else:
                        compression_method = CompressionMethod.GZIP  # Default compression
                else:
                    compression_method = CompressionMethod.NONE
            elif compression_method is None:
                compression_method = CompressionMethod.NONE
            
            # Compress data
            compressed_data, comp_stats = compress_pose_sequence(pose_sequence, compression_method)
            
            # Create cache entry
            cache_entry = {
                'data': compressed_data.hex(),
                'method': compression_method.value,
                'original_size': comp_stats.original_size,
                'compressed_size': comp_stats.compressed_size,
                'compression_ratio': comp_stats.compression_ratio,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Store in cache
            ttl = ttl or self.pose_ttl
            success = await self._execute_with_circuit_breaker(
                self.redis.setex, cache_key, ttl, json.dumps(cache_entry)
            )
            
            if success:
                logger.debug(f"Cached pose sequence: {cache_key} "
                           f"({comp_stats.original_size} → {comp_stats.compressed_size} bytes, "
                           f"TTL: {ttl}s)")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error caching pose sequence: {e}")
            return False
    
    async def get_features(self, features_key: str) -> Optional[Dict[str, float]]:
        """Retrieve cached feature data."""
        if not self.redis:
            return None
        
        start_time = time.time()
        
        try:
            cached_data = await self._execute_with_circuit_breaker(
                self.redis.get, features_key
            )
            
            response_time = time.time() - start_time
            
            if cached_data is None:
                self.metrics.record_miss(response_time)
                return None
            
            # Deserialize features
            try:
                cache_entry = json.loads(cached_data.decode('utf-8'))
                
                if cache_entry.get('compressed', False):
                    compressed_data = bytes.fromhex(cache_entry['data'])
                    compression_method = CompressionMethod(cache_entry['method'])
                    features, _ = decompress_features(compressed_data, compression_method)
                else:
                    features = cache_entry['data']
                
                self.metrics.record_hit(response_time)
                logger.debug(f"Cache hit for features: {features_key}")
                return features
                
            except Exception as e:
                logger.warning(f"Failed to deserialize cached features: {e}")
                self.metrics.record_miss(response_time)
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving features from cache: {e}")
            self.metrics.record_error()
            return None
    
    async def set_features(
        self,
        features: Dict[str, float],
        ttl: Optional[int] = None,
        use_compression: Optional[bool] = None
    ) -> bool:
        """Cache extracted features."""
        if not self.redis:
            return False
        
        try:
            # Convert numpy types to native Python types
            clean_features = self._convert_numpy_types(features)
            cache_key = self.key_manager.generate_features_key(clean_features)
            
            # Determine if compression should be used
            if use_compression is None:
                use_compression = self.use_compression
            
            if use_compression:
                # Compress features
                compressed_data, comp_stats = compress_features(clean_features, CompressionMethod.GZIP)
                cache_entry = {
                    'data': compressed_data.hex(),
                    'method': CompressionMethod.GZIP.value,
                    'compressed': True,
                    'original_size': comp_stats.original_size,
                    'timestamp': datetime.utcnow().isoformat()
                }
            else:
                # Store uncompressed
                cache_entry = {
                    'data': clean_features,
                    'compressed': False,
                    'timestamp': datetime.utcnow().isoformat()
                }
            
            ttl = ttl or self.features_ttl
            success = await self._execute_with_circuit_breaker(
                self.redis.setex, cache_key, ttl, json.dumps(cache_entry)
            )
            
            if success:
                logger.debug(f"Cached features: {cache_key} (TTL: {ttl}s)")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error caching features: {e}")
            return False
    
    async def get_ml_prediction(
        self, 
        features: Dict[str, float],
        model_version: str = "default"
    ) -> Optional[Dict[str, Any]]:
        """Retrieve cached ML prediction results."""
        if not self.redis:
            return None
        
        start_time = time.time()
        
        try:
            cache_key = self.key_manager.generate_ml_prediction_key(features, model_version)
            cached_data = await self._execute_with_circuit_breaker(
                self.redis.get, cache_key
            )
            
            response_time = time.time() - start_time
            
            if cached_data is None:
                self.metrics.record_miss(response_time)
                return None
            
            try:
                prediction_result = json.loads(cached_data.decode('utf-8'))
                self.metrics.record_hit(response_time)
                logger.debug(f"Cache hit for ML prediction: {cache_key}")
                return prediction_result
                
            except Exception as e:
                logger.warning(f"Failed to deserialize cached ML prediction: {e}")
                self.metrics.record_miss(response_time)
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving ML prediction from cache: {e}")
            self.metrics.record_error()
            return None
    
    async def set_ml_prediction(
        self,
        features: Dict[str, float],
        prediction_result: Dict[str, Any],
        model_version: str = "default",
        ttl: Optional[int] = None
    ) -> bool:
        """Cache ML prediction results."""
        if not self.redis:
            return False
        
        try:
            cache_key = self.key_manager.generate_ml_prediction_key(features, model_version)
            
            # Convert numpy types to native Python types for JSON serialization
            clean_prediction_result = self._convert_numpy_types(prediction_result)
            
            # Add metadata to prediction result
            cache_entry = {
                **clean_prediction_result,
                'cached_at': datetime.utcnow().isoformat(),
                'model_version': model_version
            }
            
            ttl = ttl or self.prediction_ttl
            success = await self._execute_with_circuit_breaker(
                self.redis.setex, cache_key, ttl, json.dumps(cache_entry)
            )
            
            if success:
                logger.debug(f"Cached ML prediction: {cache_key} (TTL: {ttl}s)")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error caching ML prediction: {e}")
            return False
    
    async def invalidate_video_cache(self, video_id: UUID) -> int:
        """
        Invalidate all cached data related to a video.
        
        Returns:
            Number of keys deleted
        """
        if not self.redis:
            return 0
        
        try:
            # Get all keys related to this video
            video_pattern = f"*{str(video_id)}*"
            keys = await self._execute_with_circuit_breaker(
                self.redis.keys, video_pattern
            )
            
            if keys:
                deleted = await self._execute_with_circuit_breaker(
                    self.redis.delete, *keys
                )
                logger.info(f"Invalidated {deleted} cache keys for video {video_id}")
                return deleted or 0
            
            return 0
            
        except Exception as e:
            logger.error(f"Error invalidating video cache: {e}")
            return 0
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        stats = self.metrics.get_stats()
        
        # Add Redis info if available
        if self.redis:
            try:
                redis_info = await self._execute_with_circuit_breaker(
                    self.redis.info, "memory"
                )
                if redis_info:
                    stats.update({
                        'redis_memory_used': redis_info.get('used_memory_human', 'N/A'),
                        'redis_memory_peak': redis_info.get('used_memory_peak_human', 'N/A'),
                        'redis_connected_clients': redis_info.get('connected_clients', 0)
                    })
            except Exception as e:
                logger.warning(f"Failed to get Redis info: {e}")
        
        # Add circuit breaker status
        stats.update({
            'circuit_breaker_state': self._circuit_breaker_state,
            'circuit_breaker_errors': self._error_count,
            'cache_service_healthy': self.redis is not None and self._circuit_breaker_state != "open"
        })
        
        return stats
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform cache service health check."""
        health_status = {
            'service': 'cache',
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'details': {}
        }
        
        try:
            if not self.redis:
                health_status['status'] = 'unhealthy'
                health_status['details']['error'] = 'Redis client not initialized'
                return health_status
            
            # Test Redis connectivity
            start_time = time.time()
            ping_result = await self._execute_with_circuit_breaker(self.redis.ping)
            response_time = (time.time() - start_time) * 1000
            
            if ping_result:
                health_status['details']['redis_ping_ms'] = round(response_time, 2)
                health_status['details']['circuit_breaker'] = self._circuit_breaker_state
            else:
                health_status['status'] = 'degraded'
                health_status['details']['error'] = 'Redis ping failed or circuit breaker open'
            
            # Add performance metrics
            stats = self.metrics.get_stats()
            health_status['details']['performance'] = {
                'hit_rate_percent': stats['hit_rate_percent'],
                'average_response_time_ms': stats['average_response_time_ms'],
                'total_operations': stats['total_operations']
            }
            
        except Exception as e:
            health_status['status'] = 'unhealthy'
            health_status['details']['error'] = str(e)
        
        return health_status


# Global cache service instance
cache_service: Optional[CacheService] = None


async def get_cache_service(settings: Settings) -> Optional[CacheService]:
    """Get or create the global cache service instance."""
    global cache_service
    
    if cache_service is None:
        cache_service = CacheService(settings)
        success = await cache_service.initialize()
        if not success:
            cache_service = None
            logger.warning("Cache service initialization failed, operating without cache")
    
    return cache_service


async def cleanup_cache_service():
    """Cleanup the global cache service instance."""
    global cache_service
    
    if cache_service:
        await cache_service.close()
        cache_service = None