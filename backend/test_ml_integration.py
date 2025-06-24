#!/usr/bin/env python3
"""
Test script for ML model integration.

This script validates that the ML pipeline is working correctly:
1. Model loading
2. Feature extraction
3. ML inference
4. AIService integration
"""

import sys
import os
import asyncio
import logging
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# Set up basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_ml_integration():
    """Test the complete ML integration pipeline."""
    
    logger.info("=== FormIQ ML Integration Test ===")
    
    try:
        # Test 1: Model Loading
        logger.info("\n1. Testing ML Model Loading...")
        from app.core.config import Settings
        from app.services.ml_model_service import MLModelService
        
        settings = Settings()
        ml_service = MLModelService(settings)
        squat_model = ml_service.get_squat_model()
        
        if squat_model.is_model_available():
            logger.info("✅ ML Model loaded successfully")
            metadata = squat_model.get_model_metadata()
            logger.info(f"   Model version: {metadata.get('version', 'unknown')}")
            logger.info(f"   Model type: {metadata.get('model_type', 'unknown')}")
            logger.info(f"   Features: {metadata.get('features_count', 'unknown')}")
        else:
            logger.error("❌ ML Model failed to load")
            return False
        
        # Test 2: Feature Extraction
        logger.info("\n2. Testing Feature Extraction...")
        from app.services.feature_extraction_service import SquatFeatureExtractor
        
        # Create sample pose data (MediaPipe format)
        sample_pose_data = []
        for frame_idx in range(10):  # 10 frames
            frame_landmarks = []
            for landmark_idx in range(33):  # 33 MediaPipe landmarks
                landmark = {
                    'x': 0.5 + 0.1 * (landmark_idx % 5) / 5,  # Sample x coordinate
                    'y': 0.3 + 0.4 * (landmark_idx % 7) / 7,  # Sample y coordinate
                    'z': 0.0,
                    'visibility': 0.8 + 0.2 * (landmark_idx % 3) / 3  # Sample confidence
                }
                frame_landmarks.append(landmark)
            sample_pose_data.append(frame_landmarks)
        
        extractor = SquatFeatureExtractor()
        features = extractor.extract_features(sample_pose_data)
        
        if features and len(features) == 23:
            logger.info("✅ Feature extraction successful")
            logger.info(f"   Extracted {len(features)} features")
            logger.info(f"   Sample features: depth_flag={features.get('depth_flag', 'N/A')}, "
                       f"posture_score={features.get('posture_score', 'N/A'):.1f}")
        else:
            logger.error(f"❌ Feature extraction failed. Got {len(features) if features else 0} features, expected 23")
            return False
        
        # Test 3: ML Inference
        logger.info("\n3. Testing ML Inference...")
        try:
            is_good_form, confidence, prediction_details = squat_model.predict_form_quality(features)
            logger.info("✅ ML Inference successful")
            logger.info(f"   Prediction: {'Good form' if is_good_form else 'Poor form'}")
            logger.info(f"   Confidence: {confidence:.3f}")
            logger.info(f"   Model version: {prediction_details.get('model_version', 'unknown')}")
        except Exception as e:
            logger.error(f"❌ ML Inference failed: {e}")
            return False
        
        # Test 4: AIService Integration
        logger.info("\n4. Testing AIService Integration...")
        from app.services.ai_service import AIService
        
        ai_service = AIService(settings)
        
        # Convert sample data to AIService expected format
        sample_landmarks = sample_pose_data[5]  # Use middle frame
        
        try:
            result = await ai_service.analyze_form(landmarks=sample_landmarks, exercise_type='squat')
            
            if result and 'score' in result:
                logger.info("✅ AIService integration successful")
                logger.info(f"   Analysis method: {result.get('analysis_method', 'unknown')}")
                logger.info(f"   Score: {result.get('score', 0):.1f}")
                logger.info(f"   Risk level: {result.get('risk_level', 'unknown')}")
                logger.info(f"   Feedback items: {len(result.get('feedback_structured', []))}")
            else:
                logger.error("❌ AIService integration failed - no valid result")
                return False
                
        except Exception as e:
            logger.error(f"❌ AIService integration failed: {e}")
            return False
        
        # Test 5: Health Check
        logger.info("\n5. Testing ML Service Health Check...")
        health_status = ml_service.health_check()
        logger.info("✅ Health check completed")
        logger.info(f"   Squat model available: {health_status.get('squat_model_available', False)}")
        
        logger.info("\n🎉 All tests passed! ML integration is working correctly.")
        return True
        
    except Exception as e:
        logger.error(f"\n💥 Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_feature_extractor_edge_cases():
    """Test feature extractor with edge cases."""
    
    logger.info("\n=== Feature Extractor Edge Cases ===")
    
    from app.services.feature_extraction_service import SquatFeatureExtractor
    extractor = SquatFeatureExtractor()
    
    # Test with empty sequence
    features = extractor.extract_features([])
    if features:
        logger.info("✅ Empty sequence handled correctly")
    else:
        logger.error("❌ Empty sequence test failed")
        return False
    
    # Test with incomplete pose data
    incomplete_pose = [[{'x': 0.5, 'y': 0.5, 'visibility': 0.8}]]  # Only one landmark
    features = extractor.extract_features(incomplete_pose)
    if features:
        logger.info("✅ Incomplete pose data handled correctly")
    else:
        logger.error("❌ Incomplete pose data test failed")
        return False
    
    logger.info("✅ Edge case tests passed")
    return True

if __name__ == "__main__":
    async def main():
        success = await test_ml_integration()
        edge_case_success = await test_feature_extractor_edge_cases()
        
        if success and edge_case_success:
            logger.info("\n🚀 All integration tests passed! Ready for production.")
            sys.exit(0)
        else:
            logger.error("\n❌ Some tests failed. Check the logs above.")
            sys.exit(1)
    
    asyncio.run(main())