#!/usr/bin/env python3
"""
Test the enhanced feature extraction to ensure it properly detects faults.
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
from app.services.enhanced_feature_extraction_service import EnhancedSquatFeatureExtractor
from app.services.feature_extraction_service import SquatFeatureExtractor
from app.models.enums import ExerciseType
from app.core.config import Settings

async def compare_feature_extractors():
    """Compare original vs enhanced feature extraction on known fault videos."""
    
    test_videos = [
        {
            'path': '/Users/tarpanmishra/FORMIQ Form Analysis Model/data/clipped_videos/squat/bad_form/hypertrophy_faults_1/depth_fault_3_hypertrophy_fault_1.mp4',
            'expected_faults': ['depth_fault', 'hypertrophy_fault'],
            'description': 'Depth + Hypertrophy fault video'
        },
        {
            'path': '/Users/tarpanmishra/FORMIQ Form Analysis Model/data/clipped_videos/squat/bad_form/stability_faults/1692_stability_fault_1.mp4',
            'expected_faults': ['stability_fault'],
            'description': 'Stability fault video'
        }
    ]
    
    print("🔬 **COMPARING ORIGINAL VS ENHANCED FEATURE EXTRACTION**")
    print("=" * 80)
    
    settings = Settings()
    video_processor = VideoProcessingService(app_settings=settings)
    ai_service = AIService(app_settings=settings)
    
    # Initialize both extractors
    original_extractor = SquatFeatureExtractor()
    enhanced_extractor = EnhancedSquatFeatureExtractor()
    
    for test_video in test_videos:
        if not os.path.exists(test_video['path']):
            print(f"❌ Video not found: {test_video['path']}")
            continue
            
        print(f"\n🎥 **Testing: {test_video['description']}**")
        print(f"📁 Expected faults: {test_video['expected_faults']}")
        
        # Process video
        with open(test_video['path'], 'rb') as f:
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
        print(f"📊 Valid poses: {len(valid_poses)}")
        
        if len(valid_poses) < 3:
            print(f"❌ Insufficient poses for analysis")
            continue
        
        # Extract features with both extractors
        original_features = original_extractor.extract_features(valid_poses)
        enhanced_features = enhanced_extractor.extract_features(valid_poses)
        
        print(f"\n📊 **FEATURE COMPARISON**")
        
        # Key features to compare
        key_features = [
            'depth_flag', 'posture_score', 'stability_score', 'overall_score',
            'min_knee_angle', 'max_torso_lean_angle', 'knee_valgus_flag',
            'torso_control_flag', 'asymmetry_flag', 'torso_stability_std'
        ]
        
        print(f"{'Feature':<25} {'Original':<12} {'Enhanced':<12} {'Improvement':<15}")
        print("-" * 70)
        
        improvements = []
        
        for feature in key_features:
            orig_val = original_features.get(feature, 0)
            enh_val = enhanced_features.get(feature, 0)
            
            # Determine if enhanced version is better for fault detection
            improvement = ""
            if 'depth_fault' in test_video['expected_faults']:
                if feature == 'depth_flag':
                    improvement = "✅ Better" if enh_val > orig_val else "❌ Worse" if enh_val < orig_val else "Same"
                elif feature == 'min_knee_angle':
                    # Lower angle is better for depth detection
                    improvement = "✅ Better" if enh_val < orig_val else "❌ Worse" if enh_val > orig_val else "Same"
                elif feature in ['posture_score', 'stability_score', 'overall_score']:
                    # Lower scores are better for bad form detection
                    improvement = "✅ Better" if enh_val < orig_val else "❌ Worse" if enh_val > orig_val else "Same"
                elif feature in ['knee_valgus_flag', 'torso_control_flag', 'asymmetry_flag']:
                    # Flags should be triggered (1.0) for faults
                    improvement = "✅ Better" if enh_val > orig_val else "❌ Worse" if enh_val < orig_val else "Same"
            
            if 'stability_fault' in test_video['expected_faults']:
                if feature in ['knee_valgus_flag', 'asymmetry_flag', 'torso_control_flag']:
                    improvement = "✅ Better" if enh_val > orig_val else "❌ Worse" if enh_val < orig_val else "Same"
                elif feature == 'stability_score':
                    improvement = "✅ Better" if enh_val < orig_val else "❌ Worse" if enh_val > orig_val else "Same"
                elif feature == 'torso_stability_std':
                    improvement = "✅ Better" if enh_val > orig_val else "❌ Worse" if enh_val < orig_val else "Same"
            
            if improvement == "✅ Better":
                improvements.append(feature)
            
            print(f"{feature:<25} {orig_val:<12.3f} {enh_val:<12.3f} {improvement:<15}")
        
        # Summary for this video
        print(f"\n📈 **IMPROVEMENTS SUMMARY**")
        print(f"   Features improved: {len(improvements)}/{len(key_features)}")
        print(f"   Improved features: {improvements}")
        
        # Fault detection analysis
        print(f"\n🔍 **FAULT DETECTION ANALYSIS**")
        
        if 'depth_fault' in test_video['expected_faults']:
            orig_depth_detected = original_features.get('depth_flag', 0) == 1
            enh_depth_detected = enhanced_features.get('depth_flag', 0) == 1
            
            print(f"   Depth fault detection:")
            print(f"      Original: {'✅ Detected' if orig_depth_detected else '❌ Missed'}")
            print(f"      Enhanced: {'✅ Detected' if enh_depth_detected else '❌ Missed'}")
            
            if not orig_depth_detected and enh_depth_detected:
                print(f"      🎉 Enhanced extractor fixed depth detection!")
            elif orig_depth_detected and not enh_depth_detected:
                print(f"      ⚠️ Enhanced extractor broke depth detection!")
        
        if 'stability_fault' in test_video['expected_faults']:
            # Count stability indicators
            orig_stability_indicators = sum([
                original_features.get('knee_valgus_flag', 0),
                original_features.get('asymmetry_flag', 0),
                original_features.get('torso_control_flag', 0)
            ])
            
            enh_stability_indicators = sum([
                enhanced_features.get('knee_valgus_flag', 0),
                enhanced_features.get('asymmetry_flag', 0),
                enhanced_features.get('torso_control_flag', 0)
            ])
            
            print(f"   Stability fault indicators:")
            print(f"      Original: {orig_stability_indicators}/3 flags triggered")
            print(f"      Enhanced: {enh_stability_indicators}/3 flags triggered")
            
            if enh_stability_indicators > orig_stability_indicators:
                print(f"      🎉 Enhanced extractor detected more stability issues!")
        
        # Overall form classification
        orig_likely_bad = (
            original_features.get('posture_score', 100) < 70 or
            original_features.get('stability_score', 100) < 70 or
            original_features.get('overall_score', 100) < 60
        )
        
        enh_likely_bad = (
            enhanced_features.get('posture_score', 100) < 70 or
            enhanced_features.get('stability_score', 100) < 70 or
            enhanced_features.get('overall_score', 100) < 60
        )
        
        print(f"\n🎯 **OVERALL ASSESSMENT**")
        print(f"   Original extractor suggests: {'BAD form' if orig_likely_bad else 'GOOD form'}")
        print(f"   Enhanced extractor suggests: {'BAD form' if enh_likely_bad else 'GOOD form'}")
        print(f"   Expected: BAD form (has faults)")
        
        if not orig_likely_bad and enh_likely_bad:
            print(f"   🎉 Enhanced extractor correctly identifies bad form!")
        elif orig_likely_bad and not enh_likely_bad:
            print(f"   ⚠️ Enhanced extractor missed bad form!")
        elif enh_likely_bad:
            print(f"   ✅ Enhanced extractor maintains correct bad form detection")
        else:
            print(f"   ❌ Both extractors failed to detect bad form")

async def main():
    """Run enhanced feature extraction test."""
    print("🧪 **TESTING ENHANCED FEATURE EXTRACTION**")
    print("=" * 80)
    
    await compare_feature_extractors()
    
    print("=" * 80)
    print("🏁 **TESTING COMPLETED**")
    print("📝 Review the improvements above to ensure enhanced extraction is working")

if __name__ == "__main__":
    asyncio.run(main())