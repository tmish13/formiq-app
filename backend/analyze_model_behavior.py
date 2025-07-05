#!/usr/bin/env python3
"""
Analyze ML model behavior to understand why it's misclassifying.
"""
import sys
import json
import numpy as np
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.ml_model_service import MLModelService
from app.core.config import Settings

def analyze_model_decision_boundary():
    """Analyze how the model makes decisions."""
    
    print("🔬 **ANALYZING ML MODEL DECISION BEHAVIOR**")
    print("=" * 70)
    
    try:
        settings = Settings()
        ml_service = MLModelService(settings)
        squat_model = ml_service.get_squat_model()
        
        if not squat_model.is_model_available():
            print("❌ ML model not available")
            return False
        
        # Load feature names (with duplicates removed)
        with open('app/ml_models/squat/feature_names.json', 'r') as f:
            feature_names = json.load(f)
        
        unique_features = list(dict.fromkeys(feature_names))  # Remove duplicates
        print(f"📊 Model uses {len(unique_features)} unique features:")
        for i, feat in enumerate(unique_features, 1):
            print(f"   {i:2d}. {feat}")
        
        # Test 1: Perfect features (should be GOOD)
        print(f"\n🧪 **TEST 1: PERFECT FORM FEATURES**")
        perfect_features = {
            'posture_score': 100.0,
            'max_torso_lean_angle': 5.0,
            'torso_control_flag': 0.0,
            'excessive_forward_lean': 0.0,
            'asymmetry_flag': 0.0,
            'torso_stability_std': 2.0,
            'knee_valgus_flag': 0.0,
            'ascent_duration': 1.5,
            'tempo_ratio': 0.8,
            'overall_score': 95.0
        }
        
        is_good, confidence, details = squat_model.predict_form_quality(perfect_features)
        print(f"   Result: {'GOOD' if is_good else 'BAD'} (confidence: {confidence:.3f})")
        print(f"   Raw probs: {details.get('raw_probabilities', {})}")
        
        # Test 2: Terrible features (should be BAD)
        print(f"\n🧪 **TEST 2: TERRIBLE FORM FEATURES**")
        terrible_features = {
            'posture_score': 30.0,
            'max_torso_lean_angle': 45.0,
            'torso_control_flag': 1.0,
            'excessive_forward_lean': 1.0,
            'asymmetry_flag': 1.0,
            'torso_stability_std': 15.0,
            'knee_valgus_flag': 1.0,
            'ascent_duration': 3.0,
            'tempo_ratio': 0.3,
            'overall_score': 25.0
        }
        
        is_good, confidence, details = squat_model.predict_form_quality(terrible_features)
        print(f"   Result: {'GOOD' if is_good else 'BAD'} (confidence: {confidence:.3f})")
        print(f"   Raw probs: {details.get('raw_probabilities', {})}")
        
        # Test 3: Mixed features - Good posture, bad everything else
        print(f"\n🧪 **TEST 3: GOOD POSTURE + BAD STABILITY**")
        mixed_features = {
            'posture_score': 100.0,  # Perfect posture
            'max_torso_lean_angle': 5.0,  # Good lean
            'torso_control_flag': 1.0,  # BAD: Control issue
            'excessive_forward_lean': 0.0,  # Good
            'asymmetry_flag': 1.0,  # BAD: Asymmetry
            'torso_stability_std': 12.0,  # BAD: Very unstable
            'knee_valgus_flag': 1.0,  # BAD: Knee issue
            'ascent_duration': 2.5,  # BAD: Slow
            'tempo_ratio': 0.4,  # BAD: Poor tempo
            'overall_score': 50.0  # BAD: Low overall
        }
        
        is_good, confidence, details = squat_model.predict_form_quality(mixed_features)
        print(f"   Result: {'GOOD' if is_good else 'BAD'} (confidence: {confidence:.3f})")
        print(f"   Raw probs: {details.get('raw_probabilities', {})}")
        print(f"   💡 This test shows if posture score dominates decision")
        
        # Test 4: Bad posture, good everything else
        print(f"\n🧪 **TEST 4: BAD POSTURE + GOOD STABILITY**")
        mixed_features2 = {
            'posture_score': 30.0,  # BAD: Poor posture
            'max_torso_lean_angle': 35.0,  # BAD: Excessive lean
            'torso_control_flag': 0.0,  # Good control
            'excessive_forward_lean': 0.0,  # Good
            'asymmetry_flag': 0.0,  # Good symmetry
            'torso_stability_std': 2.0,  # Good stability
            'knee_valgus_flag': 0.0,  # Good knees
            'ascent_duration': 1.2,  # Good speed
            'tempo_ratio': 0.9,  # Good tempo
            'overall_score': 85.0  # Good overall
        }
        
        is_good, confidence, details = squat_model.predict_form_quality(mixed_features2)
        print(f"   Result: {'GOOD' if is_good else 'BAD'} (confidence: {confidence:.3f})")
        print(f"   Raw probs: {details.get('raw_probabilities', {})}")
        
        # Test 5: Gradual posture score reduction
        print(f"\n🧪 **TEST 5: POSTURE SCORE THRESHOLD ANALYSIS**")
        base_features = {
            'max_torso_lean_angle': 8.0,
            'torso_control_flag': 1.0,  # Some issues present
            'excessive_forward_lean': 0.0,
            'asymmetry_flag': 1.0,  # Some issues present
            'torso_stability_std': 8.0,  # Some instability
            'knee_valgus_flag': 1.0,  # Some issues present
            'ascent_duration': 2.0,
            'tempo_ratio': 0.6,
            'overall_score': 65.0
        }
        
        print(f"   Testing posture score thresholds:")
        for posture_score in [100, 90, 80, 70, 60, 50, 40, 30]:
            test_features = base_features.copy()
            test_features['posture_score'] = posture_score
            
            is_good, confidence, details = squat_model.predict_form_quality(test_features)
            result_symbol = "✅" if is_good else "❌"
            print(f"      Posture {posture_score:3d}: {'GOOD' if is_good else 'BAD'} {result_symbol} (conf: {confidence:.3f})")
        
        # Test 6: Real video feature analysis
        print(f"\n🧪 **TEST 6: REAL VIDEO FEATURE REPLICATION**")
        
        # Features from the stability fault video we just tested
        real_stability_fault = {
            'posture_score': 100.0,
            'max_torso_lean_angle': 6.327,
            'torso_control_flag': 1.0,
            'excessive_forward_lean': 0.0,
            'asymmetry_flag': 0.0,
            'torso_stability_std': 2.189,
            'knee_valgus_flag': 1.0,
            'ascent_duration': 1.0,  # Estimated
            'tempo_ratio': 0.8,  # Estimated
            'overall_score': 73.333
        }
        
        is_good, confidence, details = squat_model.predict_form_quality(real_stability_fault)
        print(f"   Real stability fault features:")
        print(f"   Result: {'GOOD' if is_good else 'BAD'} (confidence: {confidence:.3f})")
        print(f"   Raw probs: {details.get('raw_probabilities', {})}")
        
        # Manual override test - force low posture score
        print(f"\n🧪 **TEST 7: MANUAL OVERRIDE - FORCE LOW POSTURE**")
        override_features = real_stability_fault.copy()
        override_features['posture_score'] = 40.0  # Force low posture
        
        is_good, confidence, details = squat_model.predict_form_quality(override_features)
        print(f"   Same features but posture_score = 40:")
        print(f"   Result: {'GOOD' if is_good else 'BAD'} (confidence: {confidence:.3f})")
        print(f"   Raw probs: {details.get('raw_probabilities', {})}")
        
        # Analysis summary
        print(f"\n📊 **ANALYSIS SUMMARY**")
        print(f"   🔍 The model behavior suggests:")
        print(f"   1. Perfect features → Correctly predicts GOOD")
        print(f"   2. Terrible features → Should predict BAD")
        print(f"   3. High posture + faults → May still predict GOOD (problem!)")
        print(f"   4. Low posture + good stability → Should predict BAD")
        print(f"   5. Posture threshold test → Shows at what point model flips")
        print(f"   6. Real video replication → Confirms the misclassification")
        print(f"   7. Manual override → Tests if reducing posture fixes prediction")
        
        return True
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run model behavior analysis."""
    print("🔬 **ML MODEL DECISION BOUNDARY ANALYSIS**")
    print("=" * 70)
    
    success = analyze_model_decision_boundary()
    
    print("=" * 70)
    if success:
        print("✅ **MODEL ANALYSIS COMPLETED**")
        print("📊 Review the test results above to understand model behavior")
    else:
        print("❌ **MODEL ANALYSIS FAILED**")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)