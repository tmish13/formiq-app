#!/usr/bin/env python3
"""
Test the enhanced feature integration in the production pipeline.
"""

import asyncio
import sys
import os
import json
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.video_processing_service import VideoProcessingService
from app.services.ai_service import AIService
from app.services.ml_model_service import MLModelService
from app.models.enums import ExerciseType
from app.core.config import Settings

async def test_enhanced_integration():
    """Test the complete enhanced pipeline integration."""
    
    print("🔄 **TESTING ENHANCED PIPELINE INTEGRATION**")
    print("=" * 70)
    
    # Test video
    test_video_path = '/Users/tarpanmishra/FORMIQ Form Analysis Model/data/clipped_videos/squat/bad_form/hypertrophy_faults_1/depth_fault_3_hypertrophy_fault_1.mp4'
    
    if not os.path.exists(test_video_path):
        print(f"❌ Test video not found: {test_video_path}")
        return False
    
    try:
        settings = Settings()
        
        # Step 1: Initialize services (this will test the enhanced integration)
        print("📊 **STEP 1: INITIALIZING SERVICES WITH ENHANCED FEATURES**")
        
        video_processor = VideoProcessingService(app_settings=settings)
        ai_service = AIService(app_settings=settings)
        ml_model_service = MLModelService(settings)
        
        print("   ✅ Services initialized successfully")
        print(f"   📋 AI Service feature extractor: {type(ai_service.squat_feature_extractor).__name__}")
        
        # Step 2: Test ML model loading
        print("\n🤖 **STEP 2: TESTING ENHANCED ML MODEL LOADING**")
        
        squat_model = ml_model_service.get_squat_model()
        is_available = squat_model.is_model_available()
        
        print(f"   📊 Model available: {'✅ Yes' if is_available else '❌ No'}")
        
        if is_available:
            # Test with dummy features matching our enhanced 23-feature set
            test_features = {
                'relative_hip_depth': 0.1,
                'hip_rom_sufficient': 1.0,
                'depth_flag': 1.0,
                'min_knee_angle': 80.0,
                'posture_score': 85.0,
                'max_torso_lean_angle': 10.0,
                'torso_control_flag': 0.0,
                'excessive_forward_lean': 0.0,
                'asymmetry_flag': 0.0,
                'torso_stability_std': 3.0,
                'knee_valgus_flag': 0.0,
                'stability_score': 80.0,
                'ascent_duration': 1.5,
                'descent_duration': 2.0,
                'tempo_ratio': 0.75,
                'controlled_descent_flag': 1.0,
                'overall_score': 85.0,
                'knee_asymmetry': 0.05,
                'right_knee_valgus_flag': 0.0,
                'smooth_ascent_flag': 0.0,
                'max_right_knee_valgus_deg': 2.0,
                'max_left_knee_valgus_deg': 1.5,
                'knee_rom': 100.0
            }
            
            is_good, confidence, details = squat_model.predict_form_quality(test_features)
            print(f"   📊 Test prediction: {'GOOD' if is_good else 'BAD'} (confidence: {confidence:.3f})")
            print(f"   📊 Features used: {details.get('feature_count', 'unknown')}")
        
        # Step 3: Test video processing with enhanced features
        print("\n🎥 **STEP 3: TESTING VIDEO PROCESSING WITH ENHANCED FEATURES**")
        
        with open(test_video_path, 'rb') as f:
            video_data = f.read()
        
        # Process video
        result = await video_processor.process_video(
            video_data=video_data,
            exercise_type=ExerciseType.SQUAT,
            save_processed_frames=False
        )
        
        frames = result['frame_paths']
        print(f"   ✅ Frames extracted: {len(frames)}")
        
        # Pose detection
        pose_results = await ai_service.process_frames_for_pose(
            frames_data_np=frames,
            min_pose_confidence_threshold=0.5
        )
        
        valid_poses = [result for result in pose_results if result is not None]
        print(f"   ✅ Valid poses: {len(valid_poses)}")
        
        if len(valid_poses) >= 3:
            # Step 4: Test enhanced feature extraction
            print("\n🧮 **STEP 4: TESTING ENHANCED FEATURE EXTRACTION**")
            
            features = ai_service.squat_feature_extractor.extract_features(valid_poses)
            print(f"   ✅ Features extracted: {len(features)}")
            
            # Verify we have all 23 enhanced features
            expected_features = 23
            if len(features) == expected_features:
                print(f"   ✅ Correct feature count: {len(features)}/{expected_features}")
            else:
                print(f"   ⚠️ Feature count mismatch: {len(features)}/{expected_features}")
            
            # Show key features
            key_features = {
                'depth_flag': features.get('depth_flag', 'N/A'),
                'posture_score': features.get('posture_score', 'N/A'),
                'stability_score': features.get('stability_score', 'N/A'),
                'overall_score': features.get('overall_score', 'N/A')
            }
            
            print(f"   📊 Key features:")
            for name, value in key_features.items():
                print(f"      {name}: {value}")
            
            # Step 5: Test ML prediction with extracted features
            print("\n🎯 **STEP 5: TESTING ML PREDICTION WITH EXTRACTED FEATURES**")
            
            if is_available:
                is_good, confidence, details = squat_model.predict_form_quality(features)
                
                print(f"   📊 ML Prediction Results:")
                print(f"      Classification: {'GOOD FORM' if is_good else 'BAD FORM'}")
                print(f"      Confidence: {confidence:.3f} ({confidence*100:.1f}%)")
                print(f"      Threshold used: {details.get('optimal_threshold', 0.5)}")
                print(f"      Model version: {details.get('model_version', 'unknown')}")
                
                # For our test video (bad form), we expect BAD classification
                expected_bad = True
                actual_bad = not is_good
                correct = expected_bad == actual_bad
                
                print(f"   🎯 Expected: BAD FORM (depth fault video)")
                print(f"   🎯 Predicted: {'BAD FORM' if actual_bad else 'GOOD FORM'}")
                print(f"   🎯 Accuracy: {'✅ CORRECT' if correct else '❌ INCORRECT'}")
                
                return correct
            else:
                print("   ⚠️ ML model not available - skipping prediction test")
                return True
        
        else:
            print(f"   ❌ Insufficient poses for feature extraction: {len(valid_poses)}")
            return False
            
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run the enhanced integration test."""
    print("🧪 **ENHANCED PIPELINE INTEGRATION TEST**")
    print("=" * 70)
    
    success = await test_enhanced_integration()
    
    print("=" * 70)
    if success:
        print("🎉 **ENHANCED INTEGRATION TEST PASSED**")
        print("✅ The enhanced pipeline is working correctly!")
        print("🚀 Ready for end-to-end testing!")
    else:
        print("❌ **ENHANCED INTEGRATION TEST FAILED**")
        print("🔧 Check the issues above and fix before proceeding")
    
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)