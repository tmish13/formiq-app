#!/usr/bin/env python3
"""
Debug feature extraction step-by-step to ensure correct ML parameter usage.
"""
import asyncio
import sys
import os
import json
import numpy as np
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.video_processing_service import VideoProcessingService
from app.services.ai_service import AIService
from app.services.ml_model_service import MLModelService
from app.services.feature_extraction_service import SquatFeatureExtractor
from app.models.enums import ExerciseType
from app.core.config import Settings

async def debug_feature_extraction_step_by_step():
    """Debug each step of feature extraction in detail."""
    
    video_path = '/Users/tarpanmishra/FORMIQ Form Analysis Model/data/clipped_videos/squat/bad_form/hypertrophy_faults_1/depth_fault_3_hypertrophy_fault_1.mp4'
    
    print("🔍 **DEBUGGING FEATURE EXTRACTION STEP-BY-STEP**")
    print(f"📁 Video: {os.path.basename(video_path)}")
    print(f"📋 Expected: BAD FORM with depth_fault_3 and hypertrophy_fault_1")
    print("=" * 80)
    
    if not os.path.exists(video_path):
        print(f"❌ Video not found: {video_path}")
        return False
    
    try:
        settings = Settings()
        
        # Step 1: Get pose data
        print("\n🎥 **STEP 1: VIDEO PROCESSING & POSE DETECTION**")
        video_processor = VideoProcessingService(app_settings=settings)
        ai_service = AIService(app_settings=settings)
        
        with open(video_path, 'rb') as f:
            video_data = f.read()
        
        result = await video_processor.process_video(
            video_data=video_data,
            exercise_type=ExerciseType.SQUAT,
            save_processed_frames=False
        )
        
        frames = result['frame_paths']
        print(f"   ✅ Frames extracted: {len(frames)}")
        
        pose_results = await ai_service.process_frames_for_pose(
            frames_data_np=frames,
            min_pose_confidence_threshold=0.5
        )
        
        valid_poses = [result for result in pose_results if result is not None]
        print(f"   ✅ Valid poses: {len(valid_poses)}")
        
        # Step 2: Examine pose data structure
        print("\n🤖 **STEP 2: POSE DATA STRUCTURE ANALYSIS**")
        if valid_poses:
            sample_pose = valid_poses[0]
            print(f"   📊 Keypoints per frame: {len(sample_pose)}")
            print(f"   📋 Sample keypoints (first 5):")
            
            for i in range(min(5, len(sample_pose))):
                kp = sample_pose[i]
                if kp:
                    print(f"      [{i}] x={kp.get('x', 0):.3f}, y={kp.get('y', 0):.3f}, z={kp.get('z', 0):.3f}, vis={kp.get('visibility', 0):.3f}")
                else:
                    print(f"      [{i}] None")
        
        # Step 3: Initialize feature extractor and examine its logic
        print("\n🧮 **STEP 3: FEATURE EXTRACTOR INITIALIZATION**")
        extractor = SquatFeatureExtractor()
        print(f"   ✅ SquatFeatureExtractor initialized")
        
        # Check if extractor has the expected methods
        extractor_methods = [method for method in dir(extractor) if not method.startswith('_')]
        print(f"   📋 Available methods: {extractor_methods}")
        
        # Step 4: Extract features with detailed logging
        print("\n⚙️ **STEP 4: FEATURE EXTRACTION WITH DEBUGGING**")
        
        print(f"   📊 Input pose sequence: {len(valid_poses)} frames")
        print(f"   📋 Processing poses...")
        
        # Extract features
        features = extractor.extract_features(valid_poses)
        print(f"   ✅ Feature extraction completed")
        print(f"   📊 Total features: {len(features)}")
        
        # Step 5: Analyze extracted features in detail
        print("\n📋 **STEP 5: DETAILED FEATURE ANALYSIS**")
        
        # Load expected feature names from model
        with open('app/ml_models/squat/feature_names.json', 'r') as f:
            expected_features = json.load(f)
        
        print(f"   📊 Expected features: {len(expected_features)}")
        print(f"   📊 Extracted features: {len(features)}")
        
        # Check if all expected features are present
        missing_features = []
        extra_features = []
        
        for feature_name in expected_features:
            if feature_name not in features:
                missing_features.append(feature_name)
        
        for feature_name in features:
            if feature_name not in expected_features:
                extra_features.append(feature_name)
        
        print(f"   ⚠️ Missing features: {len(missing_features)}")
        for feat in missing_features:
            print(f"      • {feat}")
        
        print(f"   ⚠️ Extra features: {len(extra_features)}")
        for feat in extra_features:
            print(f"      • {feat}")
        
        # Analyze critical features for depth fault
        print(f"\n🔍 **STEP 6: CRITICAL FEATURE ANALYSIS FOR DEPTH FAULT**")
        
        depth_related_features = {
            'depth_flag': features.get('depth_flag', 'N/A'),
            'relative_hip_depth': features.get('relative_hip_depth', 'N/A'),
            'hip_rom_sufficient': features.get('hip_rom_sufficient', 'N/A'),
            'min_knee_angle': features.get('min_knee_angle', 'N/A'),
            'max_knee_angle': features.get('max_knee_angle', 'N/A'),
            'knee_flexion_rom': features.get('knee_flexion_rom', 'N/A'),
        }
        
        print(f"   📊 Depth-related features:")
        for name, value in depth_related_features.items():
            if value != 'N/A':
                # Analyze if value indicates fault
                fault_indicator = ""
                if name == 'depth_flag' and value == 0:
                    fault_indicator = " ❌ (Should be 1 for depth fault)"
                elif name == 'relative_hip_depth' and value > 0.05:
                    fault_indicator = " ✅ (Good depth)"
                elif name == 'relative_hip_depth' and value < 0.05:
                    fault_indicator = " ❌ (Insufficient depth)"
                elif name == 'min_knee_angle' and value > 90:
                    fault_indicator = " ❌ (Not deep enough - should be <90°)"
                elif name == 'hip_rom_sufficient' and value == 0:
                    fault_indicator = " ❌ (Insufficient hip ROM)"
                
                print(f"      {name}: {value:.3f}{fault_indicator}")
            else:
                print(f"      {name}: NOT EXTRACTED")
        
        # Analyze posture-related features
        print(f"\n🏃 **STEP 7: POSTURE-RELATED FEATURE ANALYSIS**")
        
        posture_features = {
            'posture_score': features.get('posture_score', 'N/A'),
            'max_torso_lean_angle': features.get('max_torso_lean_angle', 'N/A'),
            'torso_control_flag': features.get('torso_control_flag', 'N/A'),
            'excessive_forward_lean': features.get('excessive_forward_lean', 'N/A'),
            'torso_stability_std': features.get('torso_stability_std', 'N/A'),
        }
        
        print(f"   📊 Posture-related features:")
        for name, value in posture_features.items():
            if value != 'N/A':
                fault_indicator = ""
                if name == 'posture_score' and value > 90:
                    fault_indicator = " ❌ (Too high for bad form video)"
                elif name == 'max_torso_lean_angle' and value > 30:
                    fault_indicator = " ❌ (Excessive lean)"
                elif name == 'torso_control_flag' and value == 1:
                    fault_indicator = " ❌ (Control issue detected)"
                elif name == 'excessive_forward_lean' and value == 1:
                    fault_indicator = " ❌ (Forward lean detected)"
                
                print(f"      {name}: {value:.3f}{fault_indicator}")
            else:
                print(f"      {name}: NOT EXTRACTED")
        
        # Step 6: Test with ML model
        print(f"\n🧠 **STEP 8: ML MODEL PREDICTION WITH EXTRACTED FEATURES**")
        
        ml_service = MLModelService(settings)
        squat_model = ml_service.get_squat_model()
        
        if squat_model.is_model_available():
            is_good_form, confidence, details = squat_model.predict_form_quality(features)
            
            print(f"   📊 ML Model Results:")
            print(f"      Classification: {'GOOD FORM' if is_good_form else 'BAD FORM'}")
            print(f"      Confidence: {confidence:.3f} ({confidence*100:.1f}%)")
            print(f"      Raw probabilities: {details.get('raw_probabilities', {})}")
            print(f"      Threshold used: {details.get('optimal_threshold', 0.5)}")
            
            # Analyze why model made this decision
            print(f"\n🔬 **STEP 9: DECISION ANALYSIS**")
            
            # Check which features most influence the model
            high_risk_features = []
            low_risk_features = []
            
            for name, value in features.items():
                if 'flag' in name and value == 1:
                    high_risk_features.append(f"{name}: {value}")
                elif 'score' in name and value < 70:
                    high_risk_features.append(f"{name}: {value}")
                elif 'score' in name and value > 90:
                    low_risk_features.append(f"{name}: {value}")
            
            print(f"   ⚠️ High-risk indicators ({len(high_risk_features)}):")
            for feat in high_risk_features[:5]:  # Show top 5
                print(f"      • {feat}")
            
            print(f"   ✅ Low-risk indicators ({len(low_risk_features)}):")
            for feat in low_risk_features[:5]:  # Show top 5
                print(f"      • {feat}")
            
            # Final assessment
            expected_bad = True  # We know this should be bad form
            actual_bad = not is_good_form
            
            print(f"\n🎯 **STEP 10: FINAL ASSESSMENT**")
            print(f"   Expected result: BAD FORM (based on filename)")
            print(f"   Actual result: {'BAD FORM' if actual_bad else 'GOOD FORM'}")
            print(f"   Accuracy: {'✅ CORRECT' if expected_bad == actual_bad else '❌ INCORRECT'}")
            
            if expected_bad != actual_bad:
                print(f"\n🔧 **ROOT CAUSE ANALYSIS:**")
                
                # Check if depth features are wrong
                if features.get('depth_flag', 0) == 0:
                    print(f"   • ISSUE: depth_flag = 0 but video has 'depth_fault_3'")
                    print(f"   • LIKELY CAUSE: Feature extraction not detecting depth issues")
                
                if features.get('posture_score', 0) > 90:
                    print(f"   • ISSUE: posture_score = {features.get('posture_score', 0):.1f} (too high)")
                    print(f"   • LIKELY CAUSE: Posture analysis not detecting form issues")
                
                dominant_score = max(details.get('raw_probabilities', {}).values())
                if dominant_score > 0.8:
                    print(f"   • ISSUE: Model very confident ({dominant_score:.1%}) in wrong prediction")
                    print(f"   • LIKELY CAUSE: Feature extraction giving misleading strong signals")
            
            return expected_bad == actual_bad
        
        else:
            print(f"   ❌ ML model not available")
            return False
        
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run comprehensive feature extraction debugging."""
    print("🔍 **COMPREHENSIVE FEATURE EXTRACTION DEBUG**")
    print("=" * 80)
    
    success = await debug_feature_extraction_step_by_step()
    
    print("=" * 80)
    if success:
        print("✅ **FEATURE EXTRACTION IS WORKING CORRECTLY**")
    else:
        print("❌ **FEATURE EXTRACTION HAS ISSUES - NEEDS FIXING**")
    
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)