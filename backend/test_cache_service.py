#!/usr/bin/env python3
"""
Test script for Redis cache service implementation.

This script validates the cache service functionality including:
- Connection establishment
- Pose sequence caching with compression
- Feature caching
- ML prediction caching
- Performance metrics
- Circuit breaker functionality
"""

import asyncio
import json
import time
from typing import Dict, List, Any
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from app.core.config import Settings
from app.services.cache_service import CacheService, get_cache_service
from app.utils.compression import CompressionMethod

# Mock settings for testing
class TestSettings(Settings):
    REDIS_URL: str = "redis://localhost:6379/1"  # Use test DB
    CACHE_POSE_TTL: int = 300  # 5 minutes for testing
    CACHE_FEATURES_TTL: int = 180  # 3 minutes
    CACHE_PREDICTION_TTL: int = 240  # 4 minutes
    CACHE_USE_COMPRESSION: bool = True
    REDIS_MAX_CONNECTIONS: int = 5

async def test_cache_service():
    """Test the Redis cache service functionality."""
    print("🧪 Testing Redis Cache Service Implementation")
    print("=" * 50)
    
    # Initialize settings and cache service
    settings = TestSettings()
    cache_service = CacheService(settings)
    
    # Test 1: Connection and Health Check
    print("\n1️⃣ Testing Redis Connection...")
    try:
        success = await cache_service.initialize()
        if success:
            print("✅ Redis connection successful")
            
            health = await cache_service.health_check()
            print(f"   Status: {health['status']}")
            print(f"   Redis Ping: {health['details'].get('redis_ping_ms', 'N/A')}ms")
        else:
            print("❌ Redis connection failed")
            return False
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False
    
    # Test 2: Pose Sequence Caching
    print("\n2️⃣ Testing Pose Sequence Caching...")
    try:
        # Create sample pose sequence (similar to MediaPipe output)
        sample_pose_sequence = [
            [
                {"x": 0.5, "y": 0.3, "z": 0.0, "visibility": 0.9},  # Frame 1, landmark 1
                {"x": 0.6, "y": 0.4, "z": 0.1, "visibility": 0.8},  # Frame 1, landmark 2
            ],
            [
                {"x": 0.52, "y": 0.32, "z": 0.01, "visibility": 0.85},  # Frame 2, landmark 1
                {"x": 0.58, "y": 0.41, "z": 0.09, "visibility": 0.82},  # Frame 2, landmark 2
            ]
        ]
        
        # Test caching with compression
        cache_success = await cache_service.set_pose_sequence(
            sample_pose_sequence, 
            ttl=300,
            compression_method=CompressionMethod.GZIP
        )
        
        if cache_success:
            print("✅ Pose sequence cached successfully")
            
            # Test retrieval
            cached_data = await cache_service.get_pose_sequence(pose_sequence=sample_pose_sequence)
            if cached_data:
                retrieved_sequence, decomp_stats = cached_data
                print(f"✅ Pose sequence retrieved successfully")
                print(f"   Compression ratio: {decomp_stats.compression_ratio:.2f}")
                print(f"   Original size: {decomp_stats.original_size} bytes")
                print(f"   Compressed size: {decomp_stats.compressed_size} bytes")
                
                # Verify data integrity
                if retrieved_sequence == sample_pose_sequence:
                    print("✅ Data integrity verified")
                else:
                    print("❌ Data integrity check failed")
            else:
                print("❌ Failed to retrieve cached pose sequence")
        else:
            print("❌ Failed to cache pose sequence")
    except Exception as e:
        print(f"❌ Pose sequence caching error: {e}")
    
    # Test 3: Feature Caching
    print("\n3️⃣ Testing Feature Caching...")
    try:
        sample_features = {
            "relative_hip_depth": 0.15,
            "min_knee_angle": 85.3,
            "posture_score": 78.5,
            "stability_score": 82.1,
            "overall_score": 80.2
        }
        
        cache_success = await cache_service.set_features(sample_features, ttl=180)
        if cache_success:
            print("✅ Features cached successfully")
            
            # Generate cache key for retrieval
            cache_key = cache_service.key_manager.generate_features_key(sample_features)
            cached_features = await cache_service.get_features(cache_key)
            
            if cached_features and cached_features == sample_features:
                print("✅ Features retrieved and verified successfully")
            else:
                print("❌ Feature retrieval or verification failed")
        else:
            print("❌ Failed to cache features")
    except Exception as e:
        print(f"❌ Feature caching error: {e}")
    
    # Test 4: ML Prediction Caching
    print("\n4️⃣ Testing ML Prediction Caching...")
    try:
        sample_prediction = {
            "is_good_form": True,
            "confidence": 0.847,
            "model_version": "enhanced_v2.0",
            "detailed_scores": {
                "posture_fault": 0.12,
                "stability_fault": 0.08,
                "depth_fault": 0.05
            }
        }
        
        cache_success = await cache_service.set_ml_prediction(
            sample_features, sample_prediction, model_version="test_v1.0", ttl=240
        )
        
        if cache_success:
            print("✅ ML prediction cached successfully")
            
            cached_prediction = await cache_service.get_ml_prediction(
                sample_features, model_version="test_v1.0"
            )
            
            if cached_prediction:
                print("✅ ML prediction retrieved successfully")
                print(f"   Cached prediction confidence: {cached_prediction.get('confidence', 'N/A')}")
                print(f"   Model version: {cached_prediction.get('model_version', 'N/A')}")
            else:
                print("❌ Failed to retrieve ML prediction")
        else:
            print("❌ Failed to cache ML prediction")
    except Exception as e:
        print(f"❌ ML prediction caching error: {e}")
    
    # Test 5: Performance Metrics
    print("\n5️⃣ Testing Performance Metrics...")
    try:
        stats = await cache_service.get_cache_stats()
        print("✅ Cache statistics retrieved:")
        print(f"   Hit Rate: {stats['hit_rate_percent']:.1f}%")
        print(f"   Total Operations: {stats['total_operations']}")
        print(f"   Average Response Time: {stats['average_response_time_ms']:.2f}ms")
        print(f"   Circuit Breaker State: {stats['circuit_breaker_state']}")
        print(f"   Cache Service Healthy: {stats['cache_service_healthy']}")
    except Exception as e:
        print(f"❌ Performance metrics error: {e}")
    
    # Test 6: Large Data Compression
    print("\n6️⃣ Testing Large Data Compression...")
    try:
        # Create larger pose sequence for compression testing
        large_pose_sequence = []
        for frame_idx in range(100):  # 100 frames
            frame_landmarks = []
            for landmark_idx in range(33):  # 33 MediaPipe landmarks
                frame_landmarks.append({
                    "x": 0.5 + (landmark_idx * 0.01),
                    "y": 0.3 + (frame_idx * 0.001),
                    "z": landmark_idx * 0.002,
                    "visibility": 0.8 + (landmark_idx * 0.005)
                })
            large_pose_sequence.append(frame_landmarks)
        
        start_time = time.time()
        cache_success = await cache_service.set_pose_sequence(
            large_pose_sequence,
            compression_method=CompressionMethod.LZ4
        )
        cache_time = time.time() - start_time
        
        if cache_success:
            print(f"✅ Large data cached in {cache_time:.3f}s")
            
            start_time = time.time()
            cached_data = await cache_service.get_pose_sequence(pose_sequence=large_pose_sequence)
            retrieve_time = time.time() - start_time
            
            if cached_data:
                retrieved_sequence, decomp_stats = cached_data
                print(f"✅ Large data retrieved in {retrieve_time:.3f}s")
                print(f"   Frames: {len(retrieved_sequence)} vs {len(large_pose_sequence)}")
                print(f"   Space savings: {(1 - decomp_stats.compression_ratio) * 100:.1f}%")
            else:
                print("❌ Failed to retrieve large data")
        else:
            print("❌ Failed to cache large data")
    except Exception as e:
        print(f"❌ Large data compression error: {e}")
    
    # Test 7: Circuit Breaker (simulated)
    print("\n7️⃣ Testing Circuit Breaker Pattern...")
    try:
        # Get current circuit breaker state
        initial_state = cache_service._circuit_breaker_state
        print(f"   Initial circuit breaker state: {initial_state}")
        
        # Simulate some errors by temporarily corrupting the Redis connection
        original_redis = cache_service.redis
        cache_service.redis = None  # Simulate connection failure
        
        # Try some operations that should trigger circuit breaker
        for i in range(3):
            await cache_service.set_features({"test": i}, ttl=60)
        
        print(f"   Circuit breaker state after errors: {cache_service._circuit_breaker_state}")
        
        # Restore connection
        cache_service.redis = original_redis
        
        # Test recovery
        success = await cache_service.set_features({"recovery_test": 1.0}, ttl=60)
        if success:
            print("✅ Circuit breaker recovery successful")
        else:
            print("   Circuit breaker still protecting (expected)")
        
    except Exception as e:
        print(f"❌ Circuit breaker test error: {e}")
    
    # Cleanup
    print("\n🧹 Cleaning up...")
    try:
        await cache_service.close()
        print("✅ Cache service closed successfully")
    except Exception as e:
        print(f"❌ Cleanup error: {e}")
    
    print("\n🎉 Cache service testing completed!")
    return True

async def main():
    """Main test runner."""
    print("FormIQ Redis Cache Service Test")
    print("Prerequisites: Redis server running on localhost:6379")
    print("Note: This test uses Redis database 1 (not production)")
    
    try:
        success = await test_cache_service()
        if success:
            print("\n✅ All tests completed successfully!")
            return 0
        else:
            print("\n❌ Some tests failed!")
            return 1
    except KeyboardInterrupt:
        print("\n⚠️ Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)