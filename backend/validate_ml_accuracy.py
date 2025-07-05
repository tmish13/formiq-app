#!/usr/bin/env python3
"""
Validate ML model accuracy and feature extraction correctness.
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
from app.services.feature_extraction_service import SquatFeatureExtractor
from app.models.enums import ExerciseType
from app.core.config import Settings

async def validate_feature_extraction_accuracy():
    """Test if feature extraction correctly identifies faults."""
    
    video_path = '/Users/tarpanmishra/FORMIQ Form Analysis Model/data/clipped_videos/squat/bad_form/hypertrophy_faults_1/depth_fault_3_hypertrophy_fault_1.mp4'
    
    print("🔍 **VALIDATING FEATURE EXTRACTION ACCURACY**")
    print(f"📁 Testing video: {os.path.basename(video_path)}")
    print(f"📋 Expected: BAD FORM with depth fault and hypertrophy fault")
    
    if not os.path.exists(video_path):
        print(f"❌ Video not found: {video_path}")
        return False
    
    try:
        settings = Settings()
        
        # Step 1: Process video and get poses
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
        pose_results = await ai_service.process_frames_for_pose(
            frames_data_np=frames,
            min_pose_confidence_threshold=0.5
        )
        
        valid_poses = [result for result in pose_results if result is not None]
        print(f"✅ Poses detected: {len(valid_poses)} frames")
        
        # Step 2: Extract features and validate
        extractor = SquatFeatureExtractor()
        features = extractor.extract_features(valid_poses)
        
        print(f"\n🧮 **FEATURE ANALYSIS**")
        print(f"📊 Total features extracted: {len(features)}")
        
        # Check critical fault indicators
        critical_features = {
            'depth_flag': features.get('depth_flag', 0),
            'posture_score': features.get('posture_score', 0),
            'min_knee_angle': features.get('min_knee_angle', 0),
            'hip_rom_sufficient': features.get('hip_rom_sufficient', 0),
            'relative_hip_depth': features.get('relative_hip_depth', 0),
            'overall_score': features.get('overall_score', 0)
        }
        
        print(f"\n🔍 **CRITICAL FAULT INDICATORS**")
        for name, value in critical_features.items():
            status = "❌ ISSUE" if name == 'depth_flag' and value == 0 else "✅ OK"
            print(f"   {name}: {value:.3f} {status}")
        
        # Analyze if features match expected bad form
        issues_found = []
        
        if features.get('posture_score', 0) > 90:
            issues_found.append(f"Posture score too high: {features.get('posture_score', 0):.1f} (expected <80 for bad form)")
        
        if features.get('depth_flag', 1) == 0:
            issues_found.append(f"Depth flag is 0 but video has 'depth_fault_3' in name")
        
        if features.get('overall_score', 0) > 85:
            issues_found.append(f"Overall score too high: {features.get('overall_score', 0):.1f} (expected <75 for bad form)")
        
        print(f"\n⚠️ **FEATURE EXTRACTION ISSUES FOUND: {len(issues_found)}**")
        for issue in issues_found:
            print(f"   • {issue}")
        
        return features, issues_found
        
    except Exception as e:
        print(f"❌ Feature validation failed: {e}")
        import traceback
        traceback.print_exc()
        return None, ["Feature extraction crashed"]

async def validate_ml_model_accuracy():
    """Test if ML model correctly classifies known bad form."""
    
    print(f"\n🧠 **VALIDATING ML MODEL ACCURACY**")
    
    try:
        settings = Settings()
        ml_service = MLModelService(settings)
        squat_model = ml_service.get_squat_model()
        
        if not squat_model.is_model_available():
            print(f"❌ ML model not available")
            return False
        
        # Load model metadata
        with open('app/ml_models/squat/production_metadata.json', 'r') as f:
            metadata = json.load(f)
        
        print(f"📊 **MODEL PERFORMANCE METRICS**")
        print(f"   Binary accuracy: {metadata['binary']['balanced_accuracy']:.1%}")
        print(f"   Posture accuracy: {metadata['posture']['balanced_accuracy']:.1%}")
        print(f"   Stability accuracy: {metadata['stability']['balanced_accuracy']:.1%}")
        
        # Test with known bad form features (based on video name)
        bad_form_features = {
            'posture_score': 60.0,  # Low posture score
            'max_torso_lean_angle': 40.0,  # High lean angle
            'torso_control_flag': 1.0,  # Control issue flag
            'excessive_forward_lean': 1.0,  # Forward lean flag
            'asymmetry_flag': 0.0,
            'torso_stability_std': 12.0,  # High instability
            'knee_valgus_flag': 1.0,  # Knee issue
            'ascent_duration': 2.5,  # Slow ascent
            'tempo_ratio': 0.4,  # Poor tempo
            'overall_score': 55.0,  # Low overall
            'depth_flag': 1.0,  # Depth issue (matching video name)
            'relative_hip_depth': 0.05  # Insufficient depth
        }
        
        # Add any missing features
        with open('app/ml_models/squat/feature_names.json', 'r') as f:
            feature_names = json.load(f)
        
        for feature_name in feature_names:
            if feature_name not in bad_form_features:
                bad_form_features[feature_name] = 0.0
        
        print(f"\n🧪 **TESTING WITH KNOWN BAD FORM FEATURES**")
        
        is_good_form, confidence, details = squat_model.predict_form_quality(bad_form_features)
        
        print(f"   Input features suggest: BAD FORM")
        print(f"   Model prediction: {'GOOD FORM' if is_good_form else 'BAD FORM'}")
        print(f"   Confidence: {confidence:.3f} ({confidence*100:.1f}%)")
        print(f"   Raw probabilities: {details.get('raw_probabilities', {})}")
        
        # Validate prediction
        model_correct = not is_good_form  # Should predict bad form
        
        if model_correct:
            print(f"   ✅ Model correctly identified bad form")
        else:
            print(f"   ❌ Model INCORRECTLY classified bad form as good")
        
        return model_correct, confidence, details
        
    except Exception as e:
        print(f"❌ ML model validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False, 0, {}

async def validate_end_to_end_accuracy():
    """Test the complete pipeline with known bad form video."""
    
    print(f"\n🔄 **VALIDATING END-TO-END ACCURACY**")
    
    # Run feature extraction validation
    features, feature_issues = await validate_feature_extraction_accuracy()
    
    if features is None:
        print(f"❌ Cannot proceed - feature extraction failed")
        return False
    
    # Run ML model validation
    model_correct, confidence, details = await validate_ml_model_accuracy()
    
    # Test the actual extracted features with the model
    print(f"\n🔬 **TESTING ACTUAL EXTRACTED FEATURES**")
    
    try:
        settings = Settings()
        ml_service = MLModelService(settings)
        squat_model = ml_service.get_squat_model()
        
        is_good_form, confidence, details = squat_model.predict_form_quality(features)
        
        print(f"   Real video features → Model prediction: {'GOOD' if is_good_form else 'BAD'}")
        print(f"   Expected: BAD (video has depth_fault_3_hypertrophy_fault_1)")
        print(f"   Confidence: {confidence:.3f}")
        
        end_to_end_correct = not is_good_form
        
        print(f"\n📊 **VALIDATION SUMMARY**")
        print(f"   Feature extraction issues: {len(feature_issues)}")
        print(f"   ML model accuracy (controlled test): {'✅ PASS' if model_correct else '❌ FAIL'}")
        print(f"   End-to-end accuracy (real video): {'✅ PASS' if end_to_end_correct else '❌ FAIL'}")
        
        overall_working = len(feature_issues) == 0 and model_correct and end_to_end_correct
        
        print(f"\n🎯 **OVERALL PIPELINE STATUS: {'✅ WORKING' if overall_working else '❌ NEEDS FIXES'}**")
        
        if not overall_working:
            print(f"\n🔧 **ISSUES TO INVESTIGATE**")
            if feature_issues:
                print(f"   📊 Feature Extraction:")
                for issue in feature_issues:
                    print(f"      • {issue}")
            
            if not model_correct:
                print(f"   🧠 ML Model: Not correctly classifying known bad form")
            
            if not end_to_end_correct:
                print(f"   🔄 Pipeline: Real video misclassified")
        
        return overall_working
        
    except Exception as e:
        print(f"❌ End-to-end validation failed: {e}")
        return False

async def main():
    """Run comprehensive validation."""
    print("🧪 **COMPREHENSIVE PIPELINE VALIDATION**")
    print("=" * 60)
    
    success = await validate_end_to_end_accuracy()
    
    print("=" * 60)
    if success:
        print("🎉 **PIPELINE IS FULLY WORKING AND ACCURATE**")
    else:
        print("⚠️ **PIPELINE HAS ACCURACY ISSUES - NOT READY FOR PRODUCTION**")
    
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)