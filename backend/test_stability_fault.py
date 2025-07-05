#!/usr/bin/env python3
"""
Test stability fault detection with a video that should trigger stability-related features.
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

async def test_stability_fault_detection():
    """Test stability fault detection with a stability fault video."""
    
    video_path = '/Users/tarpanmishra/FORMIQ Form Analysis Model/data/clipped_videos/squat/bad_form/stability_faults/1692_stability_fault_1.mp4'
    
    print("🧪 **TESTING STABILITY FAULT DETECTION**")
    print(f"📁 Video: {os.path.basename(video_path)}")
    print(f"📋 Expected: BAD FORM with stability_fault_1")
    print("=" * 80)
    
    if not os.path.exists(video_path):
        print(f"❌ Video not found: {video_path}")
        return False
    
    try:
        settings = Settings()
        
        # Step 1: Process video and get poses
        print("\n🎥 **STEP 1: VIDEO PROCESSING & POSE DETECTION**")
        video_processor = VideoProcessingService(app_settings=settings)
        ai_service = AIService(app_settings=settings)
        
        with open(video_path, 'rb') as f:
            video_data = f.read()
        
        file_size = len(video_data)
        print(f"   📊 Video size: {file_size:,} bytes")
        
        result = await video_processor.process_video(
            video_data=video_data,
            exercise_type=ExerciseType.SQUAT,
            save_processed_frames=False
        )
        
        frames = result['frame_paths']
        print(f"   ✅ Frames extracted: {len(frames)}")
        print(f"   📊 Video metadata: {result.get('video_metadata', {})}")
        
        pose_results = await ai_service.process_frames_for_pose(
            frames_data_np=frames,
            min_pose_confidence_threshold=0.5
        )
        
        valid_poses = [result for result in pose_results if result is not None]
        print(f"   ✅ Valid poses detected: {len(valid_poses)}")
        
        if not valid_poses:
            print(f"   ❌ No valid poses detected")
            return False
        
        # Step 2: Extract features with focus on stability
        print("\n🧮 **STEP 2: FEATURE EXTRACTION - STABILITY FOCUS**")
        extractor = SquatFeatureExtractor()
        features = extractor.extract_features(valid_poses)
        
        print(f"   ✅ Feature extraction completed")
        print(f"   📊 Total features: {len(features)}")
        
        # Load model's expected features
        with open('app/ml_models/squat/feature_names.json', 'r') as f:
            model_features = json.load(f)
        
        # Focus on stability-related features that the model actually uses
        stability_features = {
            'torso_stability_std': features.get('torso_stability_std', 'N/A'),
            'asymmetry_flag': features.get('asymmetry_flag', 'N/A'),
            'torso_control_flag': features.get('torso_control_flag', 'N/A'),
            'knee_valgus_flag': features.get('knee_valgus_flag', 'N/A'),
            'posture_score': features.get('posture_score', 'N/A'),
            'max_torso_lean_angle': features.get('max_torso_lean_angle', 'N/A'),
            'overall_score': features.get('overall_score', 'N/A')
        }
        
        print(f"\n🔍 **STABILITY-RELATED FEATURES ANALYSIS**")
        for name, value in stability_features.items():
            if value != 'N/A':
                # Analyze if value indicates stability fault
                fault_indicator = ""
                if name == 'torso_stability_std' and value > 5.0:
                    fault_indicator = " ❌ (High instability - fault detected)"
                elif name == 'torso_stability_std' and value <= 5.0:
                    fault_indicator = " ✅ (Low instability - stable)"
                elif name == 'asymmetry_flag' and value == 1.0:
                    fault_indicator = " ❌ (Asymmetry detected)"
                elif name == 'torso_control_flag' and value == 1.0:
                    fault_indicator = " ❌ (Control issue detected)"
                elif name == 'knee_valgus_flag' and value == 1.0:
                    fault_indicator = " ❌ (Knee instability detected)"
                elif name == 'posture_score' and value < 70:
                    fault_indicator = " ❌ (Poor posture score)"
                elif name == 'posture_score' and value > 90:
                    fault_indicator = " ✅ (Good posture score)"
                elif name == 'max_torso_lean_angle' and value > 25:
                    fault_indicator = " ❌ (Excessive lean angle)"
                elif name == 'overall_score' and value < 70:
                    fault_indicator = " ❌ (Low overall score)"
                
                print(f"      {name}: {value:.3f}{fault_indicator}")
            else:
                print(f"      {name}: NOT EXTRACTED ❌")
        
        # Count fault indicators
        fault_count = 0
        if features.get('torso_stability_std', 0) > 5.0:
            fault_count += 1
        if features.get('asymmetry_flag', 0) == 1.0:
            fault_count += 1
        if features.get('torso_control_flag', 0) == 1.0:
            fault_count += 1
        if features.get('knee_valgus_flag', 0) == 1.0:
            fault_count += 1
        if features.get('posture_score', 100) < 70:
            fault_count += 1
        
        print(f"\n📊 **FAULT INDICATOR SUMMARY**")
        print(f"   Total stability fault indicators: {fault_count}/5")
        print(f"   Expected for stability fault video: ≥2 indicators")
        
        # Step 3: ML Model Prediction
        print(f"\n🧠 **STEP 3: ML MODEL PREDICTION**")
        ml_service = MLModelService(settings)
        squat_model = ml_service.get_squat_model()
        
        if not squat_model.is_model_available():
            print(f"   ❌ ML model not available")
            return False
        
        # Filter features to only those the model expects (remove duplicates)
        unique_model_features = list(dict.fromkeys(model_features))  # Remove duplicates
        model_input_features = {name: features.get(name, 0.0) for name in unique_model_features}
        
        print(f"   📊 Using {len(model_input_features)} features for prediction")
        
        is_good_form, confidence, details = squat_model.predict_form_quality(model_input_features)
        
        print(f"   📊 ML Model Results:")
        print(f"      Classification: {'GOOD FORM' if is_good_form else 'BAD FORM'}")
        print(f"      Confidence: {confidence:.3f} ({confidence*100:.1f}%)")
        print(f"      Raw probabilities: {details.get('raw_probabilities', {})}")
        print(f"      Decision threshold: {details.get('optimal_threshold', 0.5)}")
        
        # Step 4: Validation Analysis
        print(f"\n🎯 **STEP 4: VALIDATION ANALYSIS**")
        
        expected_bad_form = True  # Should be bad form (stability fault)
        actual_bad_form = not is_good_form
        prediction_correct = expected_bad_form == actual_bad_form
        
        print(f"   Expected: BAD FORM (stability_fault_1)")
        print(f"   Predicted: {'BAD FORM' if actual_bad_form else 'GOOD FORM'}")
        print(f"   Accuracy: {'✅ CORRECT' if prediction_correct else '❌ INCORRECT'}")
        print(f"   Confidence level: {'🎯 High' if confidence > 0.7 else '🤔 Medium' if confidence > 0.5 else '⚠️ Low'}")
        
        # Step 5: Feature-Prediction Correlation Analysis
        print(f"\n🔬 **STEP 5: FEATURE-PREDICTION CORRELATION**")
        
        if prediction_correct:
            print(f"   ✅ SUCCESS: Model correctly identified stability fault")
            print(f"   📊 Key contributing factors:")
            
            contributing_factors = []
            if features.get('torso_stability_std', 0) > 5.0:
                contributing_factors.append(f"High torso instability: {features.get('torso_stability_std', 0):.2f}")
            if features.get('asymmetry_flag', 0) == 1.0:
                contributing_factors.append("Asymmetry detected")
            if features.get('torso_control_flag', 0) == 1.0:
                contributing_factors.append("Torso control issues")
            if features.get('overall_score', 100) < 70:
                contributing_factors.append(f"Low overall score: {features.get('overall_score', 100):.1f}")
            
            for factor in contributing_factors:
                print(f"      • {factor}")
            
            if not contributing_factors:
                print(f"      • Model detected subtle patterns not obvious in individual features")
        
        else:
            print(f"   ❌ FAILURE: Model missed stability fault")
            print(f"   🔍 Possible reasons:")
            
            if fault_count < 2:
                print(f"      • Too few fault indicators detected ({fault_count}/5)")
            if features.get('posture_score', 0) > 90:
                print(f"      • Posture score too high: {features.get('posture_score', 0):.1f}")
            if features.get('torso_stability_std', 0) <= 5.0:
                print(f"      • Torso stability seems good: {features.get('torso_stability_std', 0):.2f}")
            if confidence > 0.8:
                print(f"      • Model very confident in wrong prediction ({confidence:.1%})")
        
        # Individual ML Scores for FormCheck persistence
        print(f"\n💾 **STEP 6: INDIVIDUAL SCORES FOR DATABASE**")
        individual_scores = {
            'posture_score': features.get('posture_score', 0.0),
            'stability_score': max(0, min(100, 100 - features.get('torso_stability_std', 0.0) * 10)),
            'depth_score': features.get('overall_score', 0.0) * 0.9  # Fallback since no depth features
        }
        
        print(f"   📊 Individual fault scores for FormCheck:")
        print(f"      Posture Score: {individual_scores['posture_score']:.1f}/100")
        print(f"      Stability Score: {individual_scores['stability_score']:.1f}/100")
        print(f"      Depth Score: {individual_scores['depth_score']:.1f}/100")
        
        # Final assessment
        print(f"\n🏁 **FINAL ASSESSMENT**")
        print(f"   Pipeline accuracy: {'✅ WORKING' if prediction_correct else '❌ NEEDS FIXING'}")
        print(f"   Feature extraction: {'✅ DETECTED FAULTS' if fault_count >= 2 else '⚠️ WEAK DETECTION'}")
        print(f"   ML model performance: {'✅ RELIABLE' if abs(confidence - 0.5) > 0.2 else '⚠️ UNCERTAIN'}")
        
        return prediction_correct
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run stability fault detection test."""
    print("🧪 **TESTING STABILITY FAULT DETECTION**")
    print("=" * 80)
    
    success = await test_stability_fault_detection()
    
    print("=" * 80)
    if success:
        print("🎉 **STABILITY FAULT DETECTION WORKING CORRECTLY**")
        print("✅ The ML model can detect stability faults it was trained on!")
    else:
        print("⚠️ **STABILITY FAULT DETECTION HAS ISSUES**")
        print("🔧 The model may need retraining or feature extraction improvements")
    
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)