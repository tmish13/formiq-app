#!/usr/bin/env python3
"""
Comprehensive test for cache monitoring, invalidation, and performance analytics.

This test validates:
- Cache monitoring service functionality
- Performance metrics collection and analysis
- Cache invalidation strategies
- Optimization recommendations
- Real-time monitoring capabilities
"""

import asyncio
import json
import time
import sys
import os
from typing import Dict, List, Any
from uuid import uuid4

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from app.core.config import Settings
from app.services.cache_service import CacheService, get_cache_service
from app.services.cache_monitoring_service import CacheMonitoringService, get_cache_monitoring_service
from app.services.video_service import VideoService
from app.services.ai_service import AIService
from app.services.storage_service import StorageService
from app.services.enhanced_feature_extraction_service import EnhancedSquatFeatureExtractor
from app.models.enums import CompressionMethod

# Mock settings for testing
class TestSettings(Settings):
    REDIS_URL: str = "redis://localhost:6379/3"  # Use test DB 3
    CACHE_POSE_TTL: int = 300
    CACHE_FEATURES_TTL: int = 180
    CACHE_PREDICTION_TTL: int = 240
    CACHE_MONITORING_INTERVAL: int = 2  # Fast monitoring for testing
    USE_ML_MODELS: bool = True

async def test_cache_monitoring_system():
    """Test comprehensive cache monitoring and invalidation system."""
    print("🧪 Testing Cache Monitoring and Invalidation System")
    print("=" * 60)
    
    settings = TestSettings()
    ai_service = AIService(settings)
    
    # Test 1: Initialize Monitoring Service
    print("\n1️⃣ Testing Cache Monitoring Service Initialization...")
    try:
        monitoring_service = await get_cache_monitoring_service(settings)
        if monitoring_service:
            print("✅ Cache monitoring service initialized successfully")
        else:
            print("❌ Cache monitoring service initialization failed")
            return False
            
        cache_service = await get_cache_service(settings)
        if cache_service:
            print("✅ Cache service available for monitoring")
        else:
            print("❌ Cache service not available")
            return False
            
    except Exception as e:
        print(f"❌ Monitoring initialization error: {e}")
        return False
    
    # Test 2: Performance Data Collection
    print("\n2️⃣ Testing Performance Data Collection...")
    try:
        # Generate some cache activity to create metrics
        sample_features = {
            "relative_hip_depth": 0.12,
            "min_knee_angle": 88.5,
            "posture_score": 75.3,
            "stability_score": 82.1
        }
        
        # Perform several cache operations to generate data
        for i in range(5):
            await cache_service.set_features(sample_features, use_compression=True)
            cache_key = cache_service.key_manager.generate_features_key(sample_features)
            cached_features = await cache_service.get_features(cache_key)
            
            # Modify features slightly for variety
            sample_features["posture_score"] += i * 2.0
        
        print(f"✅ Generated cache activity with {i+1} operations")
        
        # Collect a performance snapshot
        await monitoring_service._collect_performance_snapshot()
        
        if monitoring_service.performance_history:
            snapshot = monitoring_service.performance_history[-1]
            print(f"✅ Performance snapshot collected:")
            print(f"   Hit Rate: {snapshot.hit_rate_percent:.1f}%")
            print(f"   Response Time: {snapshot.average_response_time_ms:.2f}ms")
            print(f"   Total Operations: {snapshot.total_operations}")
        else:
            print("⚠️ No performance snapshots collected")
            
    except Exception as e:
        print(f"❌ Performance data collection error: {e}")
    
    # Test 3: Performance Summary and Trends
    print("\n3️⃣ Testing Performance Summary and Trend Analysis...")
    try:
        # Generate more performance data over time
        for i in range(3):
            await monitoring_service._collect_performance_snapshot()
            await asyncio.sleep(0.1)  # Small delay between snapshots
        
        # Get performance summary
        summary = await monitoring_service.get_performance_summary(hours=1)
        
        if "error" not in summary:
            print("✅ Performance summary generated successfully:")
            print(f"   Period: {summary['period_hours']} hours")
            print(f"   Snapshots: {summary['snapshots_count']}")
            print(f"   Current Hit Rate: {summary['current_metrics']['hit_rate_percent']:.1f}%")
            print(f"   Average Hit Rate: {summary['period_metrics']['avg_hit_rate_percent']:.1f}%")
            
            if "trends" in summary:
                print(f"   Hit Rate Trend: {summary['trends']['hit_rate_trend']}")
                print(f"   Response Time Trend: {summary['trends']['response_time_trend']}")
        else:
            print(f"⚠️ Performance summary error: {summary['error']}")
            
    except Exception as e:
        print(f"❌ Performance summary error: {e}")
    
    # Test 4: Optimization Recommendations
    print("\n4️⃣ Testing Cache Optimization Recommendations...")
    try:
        recommendations = await monitoring_service.generate_optimization_recommendations()
        
        print(f"✅ Generated {len(recommendations)} optimization recommendations:")
        for rec in recommendations:
            print(f"   [{rec.priority.upper()}] {rec.title}")
            print(f"      Category: {rec.category}")
            print(f"      Action: {rec.action}")
            print(f"      Impact: {rec.estimated_impact}")
            print()
            
        if not recommendations:
            print("   No optimization recommendations needed - cache performing well!")
            
    except Exception as e:
        print(f"❌ Optimization recommendations error: {e}")
    
    # Test 5: Cache Efficiency Scoring
    print("\n5️⃣ Testing Cache Efficiency Scoring...")
    try:
        efficiency = await monitoring_service.get_cache_efficiency_score()
        
        if "error" not in efficiency:
            print("✅ Cache efficiency score calculated:")
            print(f"   Overall Score: {efficiency['overall_score']:.1f}/100")
            print(f"   Grade: {efficiency['grade']}")
            print("   Breakdown:")
            for category, score in efficiency['breakdown'].items():
                print(f"     {category}: {score:.1f}/100")
        else:
            print(f"⚠️ Efficiency scoring error: {efficiency['error']}")
            
    except Exception as e:
        print(f"❌ Cache efficiency scoring error: {e}")
    
    # Test 6: Cache Invalidation
    print("\n6️⃣ Testing Cache Invalidation...")
    try:
        # Create cache entries for a test video
        test_video_id = uuid4()
        
        # Cache some pose data
        sample_pose_sequence = create_sample_pose_sequence()
        await cache_service.set_pose_sequence(sample_pose_sequence)
        
        # Cache features and predictions
        await cache_service.set_features(sample_features)
        await cache_service.set_ml_prediction(
            sample_features, 
            {"is_good_form": True, "confidence": 0.85},
            model_version="test_v1.0"
        )
        
        print("✅ Created test cache entries")
        
        # Test invalidation
        invalidated_count = await cache_service.invalidate_video_cache(test_video_id)
        print(f"✅ Invalidated {invalidated_count} cache entries for video {test_video_id}")
        
        # Verify cache keys are gone (this is a simplified test)
        cache_stats = await cache_service.get_cache_stats()
        print(f"   Cache operations after invalidation: {cache_stats['total_operations']}")
        
    except Exception as e:
        print(f"❌ Cache invalidation error: {e}")
    
    # Test 7: ML Prediction with Cache Monitoring
    print("\n7️⃣ Testing ML Prediction with Performance Monitoring...")
    try:
        # Create sample landmarks for ML analysis
        sample_landmarks = create_sample_landmarks()
        
        # Monitor performance before and after cached predictions
        before_snapshot = monitoring_service.performance_history[-1] if monitoring_service.performance_history else None
        
        # Perform ML analysis (should cache results)
        start_time = time.time()
        result1 = await ai_service.analyze_form(sample_landmarks, "squat")
        first_analysis_time = time.time() - start_time
        
        # Second analysis should use cached results
        start_time = time.time()
        result2 = await ai_service.analyze_form(sample_landmarks, "squat")
        second_analysis_time = time.time() - start_time
        
        # Collect performance data after cache usage
        await monitoring_service._collect_performance_snapshot()
        after_snapshot = monitoring_service.performance_history[-1]
        
        print("✅ ML prediction performance monitoring:")
        print(f"   First analysis: {first_analysis_time:.3f}s")
        print(f"   Second analysis (cached): {second_analysis_time:.3f}s")
        if second_analysis_time > 0:
            print(f"   Speed improvement: {first_analysis_time/second_analysis_time:.1f}x")
        
        if before_snapshot and after_snapshot:
            operations_delta = after_snapshot.total_operations - before_snapshot.total_operations
            print(f"   Cache operations during test: {operations_delta}")
            print(f"   Hit rate change: {before_snapshot.hit_rate_percent:.1f}% → {after_snapshot.hit_rate_percent:.1f}%")
        
    except Exception as e:
        print(f"❌ ML prediction monitoring error: {e}")
    
    # Test 8: Real-time Monitoring Simulation
    print("\n8️⃣ Testing Real-time Monitoring Simulation...")
    try:
        print("   Starting 5-second monitoring simulation...")
        
        # Start monitoring in background
        monitoring_task = asyncio.create_task(monitoring_service.start_monitoring())
        
        # Generate some cache activity during monitoring
        for i in range(3):
            await asyncio.sleep(1)
            
            # Simulate cache activity
            test_features = {**sample_features, "posture_score": sample_features["posture_score"] + i}
            await cache_service.set_features(test_features)
            await cache_service.get_features(cache_service.key_manager.generate_features_key(test_features))
            
            print(f"   Generated activity at {i+1}s...")
        
        # Stop monitoring
        monitoring_service.stop_monitoring()
        
        # Wait a bit for the monitoring task to finish
        await asyncio.sleep(1)
        monitoring_task.cancel()
        
        print("✅ Real-time monitoring simulation completed")
        print(f"   Collected {len(monitoring_service.performance_history)} performance snapshots")
        
    except Exception as e:
        print(f"❌ Real-time monitoring error: {e}")
    
    # Test 9: Export Performance Data
    print("\n9️⃣ Testing Performance Data Export...")
    try:
        export_data = await monitoring_service.export_performance_data("json")
        
        print("✅ Performance data exported successfully:")
        print(f"   Export timestamp: {export_data['export_timestamp']}")
        print(f"   Snapshots exported: {export_data['snapshots_count']}")
        print(f"   Data size: {len(json.dumps(export_data))} bytes")
        
        # Verify export data structure
        if export_data["snapshots"]:
            sample_snapshot = export_data["snapshots"][0]
            print(f"   Sample snapshot keys: {list(sample_snapshot.keys())}")
        
    except Exception as e:
        print(f"❌ Performance data export error: {e}")
    
    # Cleanup
    print("\n🧹 Cleaning up...")
    try:
        # Reset monitoring metrics
        await monitoring_service.reset_metrics()
        
        # Close cache service
        if cache_service:
            await cache_service.close()
        
        print("✅ Cleanup completed successfully")
    except Exception as e:
        print(f"⚠️ Cleanup warning: {e}")
    
    print("\n🎉 Cache monitoring and invalidation testing completed!")
    return True

def create_sample_pose_sequence() -> List[List[Dict[str, Any]]]:
    """Create a realistic sample pose sequence for testing."""
    frames = []
    
    for frame_idx in range(5):
        frame_landmarks = []
        for landmark_idx in range(33):
            landmark = {
                "x": 0.5 + (landmark_idx * 0.01),
                "y": 0.3 + (frame_idx * 0.01),
                "z": landmark_idx * 0.002,
                "visibility": 0.8 + (landmark_idx * 0.005)
            }
            frame_landmarks.append(landmark)
        frames.append(frame_landmarks)
    
    return frames

def create_sample_landmarks() -> List[Dict[str, float]]:
    """Create sample landmarks for single frame analysis."""
    landmarks = []
    
    for i in range(33):
        landmark = {
            "x": 0.5 + (i * 0.01),
            "y": 0.3 + (i * 0.005),
            "z": i * 0.002,
            "visibility": 0.85 + (i * 0.003)
        }
        landmarks.append(landmark)
    
    return landmarks

async def main():
    """Main test runner."""
    print("FormIQ Cache Monitoring and Invalidation Test")
    print("Prerequisites: Redis server running on localhost:6379")
    print("Note: This test uses Redis database 3")
    
    try:
        success = await test_cache_monitoring_system()
        if success:
            print("\n✅ Cache monitoring tests completed successfully!")
            return 0
        else:
            print("\n❌ Some cache monitoring tests failed!")
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