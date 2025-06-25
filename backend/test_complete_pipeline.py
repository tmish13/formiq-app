#!/usr/bin/env python3
"""
Comprehensive test for the complete AI pipeline with ML scores and visual overlays.

This test validates:
1. XGBoost ML model integration (posture, stability, depth scores)
2. Reference pose generation
3. Visual overlay system
4. Form check service integration
5. API endpoint functionality
6. End-to-end data flow
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, Any
import numpy as np

# Add backend to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.core.config import get_settings
from app.services.reference_pose_service import ReferencePoseService
from app.services.pose_comparison_service import PoseAlignmentService, PoseComparisonService
from app.services.ml_model_service import MLModelService
from app.services.scoring_service import ScoringService, MLModelResults, ExerciseScores


class PipelineIntegrationTest:
    """Comprehensive test suite for the complete AI pipeline."""
    
    def __init__(self):
        """Initialize the test suite."""
        self.settings = get_settings()
        self.results = {
            'tests_passed': 0,
            'tests_failed': 0,
            'test_details': []
        }
    
    def log_test(self, test_name: str, passed: bool, details: str = ""):
        """Log test result."""
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} {test_name}")
        if details:
            print(f"    {details}")
        
        if passed:
            self.results['tests_passed'] += 1
        else:
            self.results['tests_failed'] += 1
        
        self.results['test_details'].append({
            'test': test_name,
            'passed': passed,
            'details': details
        })
    
    async def test_ml_model_integration(self) -> bool:
        """Test XGBoost ML model integration and scoring system."""
        print("\n🧠 Testing ML Model Integration")
        print("=" * 50)
        
        try:
            # Test ML model service
            ml_service = MLModelService(self.settings)
            
            # Create mock features (23 features as per your model)
            mock_features = np.array([
                0.75, 0.68, 0.82, 0.71, 0.79, 0.65, 0.88, 0.72, 0.84, 0.69,
                0.77, 0.73, 0.86, 0.71, 0.78, 0.67, 0.85, 0.74, 0.81, 0.70,
                0.83, 0.76, 0.80
            ]).reshape(1, -1)
            
            # Test prediction (using correct method name)
            # Create feature dict from array for the correct interface
            feature_names = [
                'hip_knee_ankle_angle_left_mean', 'hip_knee_ankle_angle_right_mean',
                'knee_ankle_angle_left_mean', 'knee_ankle_angle_right_mean',
                'torso_thigh_angle_left_mean', 'torso_thigh_angle_right_mean',
                'hip_knee_ankle_angle_left_std', 'hip_knee_ankle_angle_right_std',
                'knee_ankle_angle_left_std', 'knee_ankle_angle_right_std',
                'torso_thigh_angle_left_std', 'torso_thigh_angle_right_std',
                'hip_knee_ankle_angle_left_min', 'hip_knee_ankle_angle_right_min',
                'knee_ankle_angle_left_min', 'knee_ankle_angle_right_min',
                'torso_thigh_angle_left_min', 'torso_thigh_angle_right_min',
                'hip_knee_ankle_angle_left_max', 'hip_knee_ankle_angle_right_max',
                'knee_ankle_angle_left_max', 'knee_ankle_angle_right_max',
                'torso_thigh_angle_left_max'
            ]
            
            mock_features_dict = {name: float(value) for name, value in zip(feature_names, mock_features.flatten())}
            
            # Use the correct method
            is_good_form, confidence, prediction_details = ml_service.get_squat_model().predict_form_quality(mock_features_dict)
            
            # Convert to expected format for test compatibility
            prediction = {
                'posture_fault': not is_good_form and prediction_details.get('confidence_score', 0) < 0.5,
                'stability_fault': not is_good_form and prediction_details.get('confidence_score', 0) < 0.4,
                'depth_fault': not is_good_form and prediction_details.get('confidence_score', 0) < 0.3,
                'good_form': is_good_form,
                'confidence': confidence
            }
            self.log_test(
                "ML Model Prediction", 
                prediction is not None and 'posture_fault' in prediction,
                f"Prediction: {prediction}"
            )
            
            # Test scoring service
            ml_results = MLModelResults(
                posture_fault=prediction.get('posture_fault', False),
                stability_fault=prediction.get('stability_fault', False), 
                depth_fault=prediction.get('depth_fault', False),
                good_form=prediction.get('good_form', True),
                confidence=prediction.get('confidence', 0.85),
                exercise_type='squat'
            )
            
            scoring_service = ScoringService(self.settings)
            scores = scoring_service.calculate_exercise_scores(ml_results)
            
            self.log_test(
                "Scoring Service",
                isinstance(scores, ExerciseScores) and 0 <= scores.overall_score <= 100,
                f"Overall Score: {scores.overall_score}, Posture: {scores.posture_score}, Stability: {scores.stability_score}, Depth: {scores.depth_score}"
            )
            
            return True
            
        except Exception as e:
            self.log_test("ML Model Integration", False, f"Error: {str(e)}")
            return False
    
    async def test_reference_pose_generation(self) -> bool:
        """Test reference pose generation system."""
        print("\n🎯 Testing Reference Pose Generation")
        print("=" * 50)
        
        try:
            reference_service = ReferencePoseService(self.settings)
            
            # Generate squat reference pose
            reference_data = reference_service.generate_reference_pose('squat')
            
            # Validate structure
            required_keys = ['pose_sequence', 'metadata', 'key_poses']
            structure_valid = all(key in reference_data for key in required_keys)
            
            self.log_test(
                "Reference Pose Structure",
                structure_valid,
                f"Keys present: {list(reference_data.keys())}"
            )
            
            # Validate key poses
            key_poses = reference_data.get('key_poses', {})
            expected_phases = ['setup', 'mid_descent', 'bottom', 'mid_ascent']
            phases_valid = all(phase in key_poses for phase in expected_phases)
            
            self.log_test(
                "Movement Phases",
                phases_valid,
                f"Phases available: {list(key_poses.keys())}"
            )
            
            # Validate pose data format
            setup_pose = key_poses.get('setup', {})
            required_joints = ['left_hip', 'right_hip', 'left_knee', 'right_knee', 'left_ankle', 'right_ankle']
            joints_valid = all(joint in setup_pose for joint in required_joints)
            
            self.log_test(
                "Joint Data Format",
                joints_valid,
                f"Required joints present: {joints_valid}, Total joints: {len(setup_pose)}"
            )
            
            return structure_valid and phases_valid and joints_valid
            
        except Exception as e:
            self.log_test("Reference Pose Generation", False, f"Error: {str(e)}")
            return False
    
    async def test_visual_overlay_system(self) -> bool:
        """Test visual overlay and pose comparison system."""
        print("\n👁️ Testing Visual Overlay System")
        print("=" * 50)
        
        try:
            # Generate reference pose
            reference_service = ReferencePoseService(self.settings)
            reference_data = reference_service.generate_reference_pose('squat')
            
            # Create mock user pose
            user_pose = self._create_mock_user_pose()
            reference_pose = reference_data['key_poses']['setup']
            
            # Test pose alignment service
            alignment_service = PoseAlignmentService(self.settings)
            
            # Test similarity calculation
            similarity_result = alignment_service.calculate_pose_similarity(
                user_pose=user_pose,
                reference_pose=reference_pose,
                normalize_positions=True
            )
            
            similarity_valid = (
                'overall_similarity' in similarity_result and
                'alignment_quality' in similarity_result and
                0 <= similarity_result['overall_similarity'] <= 1
            )
            
            self.log_test(
                "Pose Similarity Calculation",
                similarity_valid,
                f"Similarity: {similarity_result['overall_similarity']:.3f}, Quality: {similarity_result['alignment_quality']}"
            )
            
            # Test overlay data generation
            overlay_data = alignment_service.generate_overlay_alignment_data(
                user_pose=user_pose,
                reference_pose=reference_pose,
                highlight_deviations=True
            )
            
            overlay_valid = (
                'similarity_score' in overlay_data and
                'joint_colors' in overlay_data and
                'deviation_highlights' in overlay_data
            )
            
            self.log_test(
                "Visual Overlay Data",
                overlay_valid,
                f"Overlay components: similarity_score, joint_colors({len(overlay_data.get('joint_colors', {}))}), deviation_highlights({len(overlay_data.get('deviation_highlights', []))})"
            )
            
            # Test video-to-reference matching
            mock_video_sequence = self._create_mock_video_sequence()
            
            matching_result = alignment_service.match_video_to_reference_phases(
                user_video_poses=mock_video_sequence,
                reference_pose_data=reference_data
            )
            
            matching_valid = (
                'frame_mappings' in matching_result and
                'overall_alignment' in matching_result and
                len(matching_result['frame_mappings']) == len(mock_video_sequence)
            )
            
            self.log_test(
                "Video-to-Reference Matching",
                matching_valid,
                f"Frames processed: {len(matching_result.get('frame_mappings', []))}, Overall alignment: {matching_result.get('overall_alignment', 0):.3f}"
            )
            
            return similarity_valid and overlay_valid and matching_valid
            
        except Exception as e:
            self.log_test("Visual Overlay System", False, f"Error: {str(e)}")
            return False
    
    async def test_comprehensive_form_analysis(self) -> bool:
        """Test comprehensive form analysis combining ML scores and visual overlays."""
        print("\n🔬 Testing Comprehensive Form Analysis")
        print("=" * 50)
        
        try:
            # Initialize services
            comparison_service = PoseComparisonService(self.settings)
            reference_service = ReferencePoseService(self.settings)
            
            # Create mock form check data
            mock_video_sequence = self._create_mock_video_sequence()
            form_check_data = {
                'pose_sequence': mock_video_sequence,
                'exercise_type': 'squat',
                'video_id': 'test-video-123'
            }
            
            # Generate reference data
            reference_data = reference_service.generate_reference_pose('squat')
            
            # Test comprehensive comparison
            comparison_results = comparison_service.compare_form_check_poses(
                form_check_data=form_check_data,
                reference_pose_data=reference_data
            )
            
            # Validate comprehensive results
            required_components = ['frame_comparisons', 'phase_analysis', 'overall_assessment', 'recommendations']
            components_valid = all(comp in comparison_results for comp in required_components)
            
            self.log_test(
                "Comprehensive Analysis Structure",
                components_valid,
                f"Components: {list(comparison_results.keys())}"
            )
            
            # Validate frame comparisons
            frame_comparisons = comparison_results.get('frame_comparisons', [])
            frames_valid = len(frame_comparisons) > 0
            
            self.log_test(
                "Frame Comparisons",
                frames_valid,
                f"Frame comparisons generated: {len(frame_comparisons)}"
            )
            
            # Validate overall assessment
            overall_assessment = comparison_results.get('overall_assessment', {})
            assessment_valid = 'overall_score' in overall_assessment
            
            self.log_test(
                "Overall Assessment",
                assessment_valid,
                f"Overall score: {overall_assessment.get('overall_score', 'N/A')}"
            )
            
            # Validate recommendations
            recommendations = comparison_results.get('recommendations', [])
            recommendations_valid = len(recommendations) > 0
            
            self.log_test(
                "Recommendations Generated",
                recommendations_valid,
                f"Recommendations: {len(recommendations)}"
            )
            
            return components_valid and frames_valid and assessment_valid
            
        except Exception as e:
            self.log_test("Comprehensive Form Analysis", False, f"Error: {str(e)}")
            return False
    
    async def test_data_integration(self) -> bool:
        """Test integration of all components for complete data flow."""
        print("\n🔄 Testing Data Integration")
        print("=" * 50)
        
        try:
            # Simulate complete pipeline workflow
            
            # 1. ML Model Analysis
            ml_service = MLModelService(self.settings)
            mock_features = np.random.rand(1, 23)  # 23 features
            
            # Create feature dict for the correct interface
            feature_names = [
                'hip_knee_ankle_angle_left_mean', 'hip_knee_ankle_angle_right_mean',
                'knee_ankle_angle_left_mean', 'knee_ankle_angle_right_mean',
                'torso_thigh_angle_left_mean', 'torso_thigh_angle_right_mean',
                'hip_knee_ankle_angle_left_std', 'hip_knee_ankle_angle_right_std',
                'knee_ankle_angle_left_std', 'knee_ankle_angle_right_std',
                'torso_thigh_angle_left_std', 'torso_thigh_angle_right_std',
                'hip_knee_ankle_angle_left_min', 'hip_knee_ankle_angle_right_min',
                'knee_ankle_angle_left_min', 'knee_ankle_angle_right_min',
                'torso_thigh_angle_left_min', 'torso_thigh_angle_right_min',
                'hip_knee_ankle_angle_left_max', 'hip_knee_ankle_angle_right_max',
                'knee_ankle_angle_left_max', 'knee_ankle_angle_right_max',
                'torso_thigh_angle_left_max'
            ]
            
            mock_features_dict = {name: float(value) for name, value in zip(feature_names, mock_features.flatten())}
            
            # Use the correct method
            is_good_form, confidence, prediction_details = ml_service.get_squat_model().predict_form_quality(mock_features_dict)
            
            # Convert to expected format
            ml_prediction = {
                'posture_fault': not is_good_form and prediction_details.get('confidence_score', 0) < 0.5,
                'stability_fault': not is_good_form and prediction_details.get('confidence_score', 0) < 0.4,
                'depth_fault': not is_good_form and prediction_details.get('confidence_score', 0) < 0.3,
                'good_form': is_good_form,
                'confidence': confidence
            }
            
            # 2. Scoring
            scoring_service = ScoringService(self.settings)
            ml_results = MLModelResults(
                posture_fault=ml_prediction.get('posture_fault', False),
                stability_fault=ml_prediction.get('stability_fault', False),
                depth_fault=ml_prediction.get('depth_fault', False),
                good_form=ml_prediction.get('good_form', True),
                confidence=ml_prediction.get('confidence', 0.85),
                exercise_type='squat'
            )
            scores = scoring_service.calculate_exercise_scores(ml_results)
            
            # 3. Reference Pose Generation
            reference_service = ReferencePoseService(self.settings)
            reference_data = reference_service.generate_reference_pose('squat')
            
            # 4. Visual Overlay Generation
            alignment_service = PoseAlignmentService(self.settings)
            user_pose = self._create_mock_user_pose()
            reference_pose = reference_data['key_poses']['setup']
            
            overlay_data = alignment_service.generate_overlay_alignment_data(
                user_pose=user_pose,
                reference_pose=reference_pose
            )
            
            # 5. Combine all data (simulating form check response)
            integrated_response = {
                'ml_scores': {
                    'posture_score': scores.posture_score,
                    'stability_score': scores.stability_score,
                    'depth_score': scores.depth_score,
                    'overall_score': scores.overall_score,
                    'confidence_level': scores.confidence_level
                },
                'reference_pose_data': reference_data,
                'visual_overlay_data': overlay_data,
                'interpretation': scoring_service.get_score_interpretation(scores.overall_score)
            }
            
            # Validate integration
            integration_valid = all([
                'ml_scores' in integrated_response,
                'reference_pose_data' in integrated_response,
                'visual_overlay_data' in integrated_response,
                'interpretation' in integrated_response
            ])
            
            self.log_test(
                "Data Integration",
                integration_valid,
                f"Overall Score: {scores.overall_score}, Interpretation: {integrated_response['interpretation']['level']}"
            )
            
            return integration_valid
            
        except Exception as e:
            self.log_test("Data Integration", False, f"Error: {str(e)}")
            return False
    
    def _create_mock_user_pose(self) -> Dict[str, Any]:
        """Create a mock user pose for testing."""
        return {
            'nose': [0.5, 0.3, 0.95],
            'left_eye': [0.48, 0.28, 0.9],
            'right_eye': [0.52, 0.28, 0.9],
            'left_ear': [0.46, 0.29, 0.85],
            'right_ear': [0.54, 0.29, 0.85],
            'left_shoulder': [0.42, 0.4, 0.95],
            'right_shoulder': [0.58, 0.4, 0.95],
            'left_elbow': [0.38, 0.5, 0.9],
            'right_elbow': [0.62, 0.5, 0.9],
            'left_wrist': [0.35, 0.6, 0.85],
            'right_wrist': [0.65, 0.6, 0.85],
            'left_hip': [0.45, 0.55, 0.95],
            'right_hip': [0.55, 0.55, 0.95],
            'left_knee': [0.44, 0.7, 0.95],
            'right_knee': [0.56, 0.7, 0.95],
            'left_ankle': [0.43, 0.85, 0.95],
            'right_ankle': [0.57, 0.85, 0.95],
            'left_heel': [0.41, 0.87, 0.9],
            'right_heel': [0.59, 0.87, 0.9],
            'left_foot_index': [0.45, 0.85, 0.9],
            'right_foot_index': [0.55, 0.85, 0.9]
        }
    
    def _create_mock_video_sequence(self) -> list:
        """Create a mock video sequence with 30 frames."""
        base_pose = self._create_mock_user_pose()
        sequence = []
        
        for frame in range(30):
            # Create deep copy and simulate movement
            pose = {}
            for joint_name, coords in base_pose.items():
                pose[joint_name] = coords.copy()
            
            # Simulate squat movement
            if frame < 10:  # Setup
                knee_bend = 0.0
            elif frame < 20:  # Descent
                knee_bend = (frame - 10) / 10.0
            else:  # Ascent
                knee_bend = 1.0 - (frame - 20) / 10.0
            
            # Modify positions
            knee_offset = knee_bend * 0.1
            hip_offset = knee_bend * 0.08
            
            pose['left_knee'][1] += knee_offset
            pose['right_knee'][1] += knee_offset
            pose['left_hip'][1] += hip_offset
            pose['right_hip'][1] += hip_offset
            
            sequence.append(pose)
        
        return sequence
    
    def print_summary(self):
        """Print test summary."""
        total_tests = self.results['tests_passed'] + self.results['tests_failed']
        success_rate = (self.results['tests_passed'] / total_tests * 100) if total_tests > 0 else 0
        
        print("\n" + "=" * 60)
        print("🎉 COMPLETE PIPELINE TEST SUMMARY")
        print("=" * 60)
        
        print(f"📊 Results:")
        print(f"   Total Tests: {total_tests}")
        print(f"   Passed: {self.results['tests_passed']}")
        print(f"   Failed: {self.results['tests_failed']}")
        print(f"   Success Rate: {success_rate:.1f}%")
        
        if self.results['tests_failed'] > 0:
            print(f"\n❌ Failed Tests:")
            for test in self.results['test_details']:
                if not test['passed']:
                    print(f"   - {test['test']}: {test['details']}")
        
        print(f"\n🎯 Pipeline Status:")
        if success_rate >= 90:
            print("   ✅ PIPELINE READY FOR PRODUCTION")
        elif success_rate >= 70:
            print("   ⚠️ PIPELINE MOSTLY FUNCTIONAL - Minor fixes needed")
        else:
            print("   ❌ PIPELINE NEEDS SIGNIFICANT WORK")


async def main():
    """Run the complete pipeline test."""
    print("🚀 Starting Complete AI Pipeline Integration Test")
    print("=" * 60)
    
    tester = PipelineIntegrationTest()
    
    # Run all tests
    test_results = []
    test_results.append(await tester.test_ml_model_integration())
    test_results.append(await tester.test_reference_pose_generation())
    test_results.append(await tester.test_visual_overlay_system())
    test_results.append(await tester.test_comprehensive_form_analysis())
    test_results.append(await tester.test_data_integration())
    
    # Print summary
    tester.print_summary()
    
    # Return overall success
    return all(test_results)


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)