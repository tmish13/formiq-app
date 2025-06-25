"""
Reference Pose Generation Service

This service generates scientifically accurate reference poses for exercises
based on biomechanical research and form rules. It creates ideal keypoint
data for visual overlays that can adapt to different body types.

Based on research from:
- Straub & Powers, 2024: Biomechanical Review of the Squat Exercise
- Stone et al., 2024: The Use of Free Weight Squats in Sports
- McMahon et al., 2013: How deep should you squat to maximise training response
"""

import json
import math
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from app.core.logging import get_logger
from app.core.config import Settings

logger = get_logger(__name__)


class ReferenceSquatGenerator:
    """
    Generates biomechanically accurate reference squat poses for visual overlays.
    
    Creates ideal keypoint sequences that follow research-backed form principles:
    - Torso angle ≤30° from vertical (Straub & Powers, 2024)
    - Knee flexion ≤90° at bottom (McMahon et al., 2013)
    - Knee valgus ≤5° (Stone et al., 2024)
    - Neutral spine ≥160° (form_rules.json)
    """
    
    # MediaPipe pose landmark indices matching feature_extraction_service.py
    LANDMARK_MAP = {
        'nose': 0,
        'left_eye_inner': 1, 'left_eye': 2, 'left_eye_outer': 3,
        'right_eye_inner': 4, 'right_eye': 5, 'right_eye_outer': 6,
        'left_ear': 7, 'right_ear': 8,
        'mouth_left': 9, 'mouth_right': 10,
        'left_shoulder': 11, 'right_shoulder': 12,
        'left_elbow': 13, 'right_elbow': 14,
        'left_wrist': 15, 'right_wrist': 16,
        'left_pinky': 17, 'right_pinky': 18,
        'left_index': 19, 'right_index': 20,
        'left_thumb': 21, 'right_thumb': 22,
        'left_hip': 23, 'right_hip': 24,
        'left_knee': 25, 'right_knee': 26,
        'left_ankle': 27, 'right_ankle': 28,
        'left_heel': 29, 'right_heel': 30,
        'left_foot_index': 31, 'right_foot_index': 32
    }
    
    def __init__(self, settings: Optional[Settings] = None):
        """Initialize the reference pose generator."""
        self.settings = settings
        self.form_rules = self._load_form_rules()
        
    def _load_form_rules(self) -> Dict[str, Any]:
        """Load form rules from JSON or return defaults."""
        try:
            # Try to load from project if available
            rules_path = Path(__file__).parent.parent.parent / "form_rules.json"
            if rules_path.exists():
                with open(rules_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load form_rules.json: {e}")
        
        # Return research-based defaults from form_rules.json
        return {
            "squat": {
                "depth": {
                    "min_knee_angle": {"threshold": 90},
                    "hip_rom": {"threshold": 0.2}
                },
                "posture": {
                    "max_torso_lean_angle": {"threshold": 30},
                    "spine_angle": {"threshold": 160}
                },
                "stability": {
                    "max_right_knee_valgus_deg": {"threshold": 5},
                    "max_left_knee_valgus_deg": {"threshold": 5}
                },
                "tempo": {
                    "descent_duration": {"threshold": 2.0},
                    "ascent_duration": {"threshold": 1.5}
                }
            }
        }
    
    def generate_squat_reference_pose(
        self,
        body_proportions: Optional[Dict[str, float]] = None,
        stance_width: str = "shoulder_width",
        target_frames: int = 90  # 3 seconds at 30fps
    ) -> Dict[str, Any]:
        """
        Generate a complete squat reference pose sequence.
        
        Args:
            body_proportions: Optional body measurements for scaling
            stance_width: "narrow", "shoulder_width", or "wide"
            target_frames: Number of frames for the complete sequence
            
        Returns:
            Dictionary with pose sequence, phases, and metadata
        """
        logger.info("Generating squat reference pose sequence")
        
        # Default body proportions (normalized to shoulder width = 1.0)
        if body_proportions is None:
            body_proportions = {
                'shoulder_width': 1.0,      # Base unit
                'torso_length': 1.2,        # Shoulder to hip
                'thigh_length': 1.0,        # Hip to knee
                'shin_length': 1.0,         # Knee to ankle
                'foot_length': 0.25,        # Heel to toe
                'arm_length': 1.5           # Shoulder to wrist
            }
        
        # Generate key poses for different phases
        phases = self._generate_squat_phases(body_proportions, stance_width, target_frames)
        
        # Create smooth interpolated sequence
        pose_sequence = self._interpolate_pose_sequence(phases, target_frames)
        
        # Add metadata
        metadata = {
            'exercise_type': 'squat',
            'body_proportions': body_proportions,
            'stance_width': stance_width,
            'total_frames': target_frames,
            'phases': {
                'setup': {'start': 0, 'end': int(target_frames * 0.1)},
                'descent': {'start': int(target_frames * 0.1), 'end': int(target_frames * 0.5)},
                'bottom': {'start': int(target_frames * 0.5), 'end': int(target_frames * 0.6)},
                'ascent': {'start': int(target_frames * 0.6), 'end': int(target_frames * 0.9)},
                'completion': {'start': int(target_frames * 0.9), 'end': target_frames}
            },
            'biomechanical_targets': {
                'max_torso_lean': 30,  # degrees
                'min_knee_angle': 90,  # degrees
                'max_knee_valgus': 5,  # degrees
                'min_spine_angle': 160,  # degrees
                'descent_duration': 2.0,  # seconds
                'ascent_duration': 1.5   # seconds
            }
        }
        
        return {
            'pose_sequence': pose_sequence,
            'metadata': metadata,
            'key_poses': phases
        }
    
    def _generate_squat_phases(
        self,
        body_proportions: Dict[str, float],
        stance_width: str,
        total_frames: int
    ) -> Dict[str, Dict[str, List[float]]]:
        """Generate key poses for different squat phases."""
        
        # Base stance configuration
        stance_multipliers = {
            'narrow': 0.8,
            'shoulder_width': 1.0,
            'wide': 1.2
        }
        stance_mult = stance_multipliers.get(stance_width, 1.0)
        
        # Calculate base positions (normalized coordinates 0-1)
        base_width = body_proportions['shoulder_width'] * stance_mult * 0.3
        base_height = body_proportions['torso_length'] + body_proportions['thigh_length'] + body_proportions['shin_length']
        
        phases = {}
        
        # 1. SETUP PHASE - Standing position
        phases['setup'] = self._generate_standing_pose(body_proportions, base_width, base_height)
        
        # 2. BOTTOM PHASE - Deepest squat position
        phases['bottom'] = self._generate_bottom_pose(body_proportions, base_width, base_height)
        
        # 3. MID-DESCENT PHASE - Halfway down
        phases['mid_descent'] = self._interpolate_between_poses(phases['setup'], phases['bottom'], 0.5)
        
        # 4. MID-ASCENT PHASE - Halfway up
        phases['mid_ascent'] = self._interpolate_between_poses(phases['bottom'], phases['setup'], 0.5)
        
        return phases
    
    def _generate_standing_pose(
        self,
        body_proportions: Dict[str, float],
        base_width: float,
        base_height: float
    ) -> Dict[str, List[float]]:
        """Generate the standing/setup pose."""
        
        pose = {}
        
        # Center point of the pose
        center_x, center_y = 0.5, 0.5
        
        # Foot positions (base of the pose)
        foot_y = center_y + (base_height * 0.4)  # Feet at bottom
        
        # Left foot
        pose['left_ankle'] = [center_x - base_width/2, foot_y, 0.95]
        pose['left_heel'] = [center_x - base_width/2 - 0.02, foot_y + 0.01, 0.95]
        pose['left_foot_index'] = [center_x - base_width/2 + 0.03, foot_y, 0.95]
        
        # Right foot
        pose['right_ankle'] = [center_x + base_width/2, foot_y, 0.95]
        pose['right_heel'] = [center_x + base_width/2 + 0.02, foot_y + 0.01, 0.95]
        pose['right_foot_index'] = [center_x + base_width/2 - 0.03, foot_y, 0.95]
        
        # Knee positions (standing straight)
        knee_y = foot_y - body_proportions['shin_length'] * 0.3
        pose['left_knee'] = [center_x - base_width/2, knee_y, 0.95]
        pose['right_knee'] = [center_x + base_width/2, knee_y, 0.95]
        
        # Hip positions
        hip_y = knee_y - body_proportions['thigh_length'] * 0.3
        pose['left_hip'] = [center_x - base_width/3, hip_y, 0.95]
        pose['right_hip'] = [center_x + base_width/3, hip_y, 0.95]
        
        # Shoulder positions (upright posture)
        shoulder_y = hip_y - body_proportions['torso_length'] * 0.3
        pose['left_shoulder'] = [center_x - body_proportions['shoulder_width'] * 0.15, shoulder_y, 0.95]
        pose['right_shoulder'] = [center_x + body_proportions['shoulder_width'] * 0.15, shoulder_y, 0.95]
        
        # Arm positions (arms at sides or holding weight)
        elbow_y = shoulder_y + 0.1
        pose['left_elbow'] = [center_x - body_proportions['shoulder_width'] * 0.2, elbow_y, 0.9]
        pose['right_elbow'] = [center_x + body_proportions['shoulder_width'] * 0.2, elbow_y, 0.9]
        
        wrist_y = elbow_y + 0.1
        pose['left_wrist'] = [center_x - body_proportions['shoulder_width'] * 0.15, wrist_y, 0.9]
        pose['right_wrist'] = [center_x + body_proportions['shoulder_width'] * 0.15, wrist_y, 0.9]
        
        # Head positions
        head_y = shoulder_y - 0.08
        pose['nose'] = [center_x, head_y, 0.95]
        pose['left_ear'] = [center_x - 0.03, head_y, 0.9]
        pose['right_ear'] = [center_x + 0.03, head_y, 0.9]
        
        # Eyes
        pose['left_eye'] = [center_x - 0.02, head_y, 0.95]
        pose['right_eye'] = [center_x + 0.02, head_y, 0.95]
        
        # Add remaining landmarks with lower confidence
        self._add_remaining_landmarks(pose, center_x, center_y)
        
        return pose
    
    def _generate_bottom_pose(
        self,
        body_proportions: Dict[str, float],
        base_width: float,
        base_height: float
    ) -> Dict[str, List[float]]:
        """Generate the bottom/deepest squat pose."""
        
        pose = {}
        
        # Center point
        center_x, center_y = 0.5, 0.5
        
        # Feet stay in same position as standing
        foot_y = center_y + (base_height * 0.4)
        
        # Left foot (same as standing)
        pose['left_ankle'] = [center_x - base_width/2, foot_y, 0.95]
        pose['left_heel'] = [center_x - base_width/2 - 0.02, foot_y + 0.01, 0.95]
        pose['left_foot_index'] = [center_x - base_width/2 + 0.03, foot_y, 0.95]
        
        # Right foot (same as standing)
        pose['right_ankle'] = [center_x + base_width/2, foot_y, 0.95]
        pose['right_heel'] = [center_x + base_width/2 + 0.02, foot_y + 0.01, 0.95]
        pose['right_foot_index'] = [center_x + base_width/2 - 0.03, foot_y, 0.95]
        
        # Knee positions (bent to ~90 degrees, slight forward movement)
        knee_y = foot_y - body_proportions['shin_length'] * 0.15  # Knees come forward
        knee_forward_offset = 0.03  # Small forward movement
        pose['left_knee'] = [center_x - base_width/2 + knee_forward_offset, knee_y, 0.95]
        pose['right_knee'] = [center_x + base_width/2 - knee_forward_offset, knee_y, 0.95]
        
        # Hip positions (dropped down and slightly back for proper squat mechanics)
        hip_y = knee_y + 0.02  # Hips slightly below knees for proper depth
        hip_back_offset = 0.05  # Hips move back
        pose['left_hip'] = [center_x - base_width/3 - hip_back_offset, hip_y, 0.95]
        pose['right_hip'] = [center_x + base_width/3 - hip_back_offset, hip_y, 0.95]
        
        # Shoulder positions (maintain upright posture, ≤30° lean)
        torso_lean = 0.02  # Small forward lean (≤30° from vertical)
        shoulder_y = hip_y - body_proportions['torso_length'] * 0.25  # Shorter torso due to lean
        pose['left_shoulder'] = [center_x - body_proportions['shoulder_width'] * 0.15 + torso_lean, shoulder_y, 0.95]
        pose['right_shoulder'] = [center_x + body_proportions['shoulder_width'] * 0.15 + torso_lean, shoulder_y, 0.95]
        
        # Arm positions (maintain balance)
        elbow_y = shoulder_y + 0.08
        pose['left_elbow'] = [center_x - body_proportions['shoulder_width'] * 0.2 + torso_lean, elbow_y, 0.9]
        pose['right_elbow'] = [center_x + body_proportions['shoulder_width'] * 0.2 + torso_lean, elbow_y, 0.9]
        
        wrist_y = elbow_y + 0.08
        pose['left_wrist'] = [center_x - body_proportions['shoulder_width'] * 0.15 + torso_lean, wrist_y, 0.9]
        pose['right_wrist'] = [center_x + body_proportions['shoulder_width'] * 0.15 + torso_lean, wrist_y, 0.9]
        
        # Head positions (maintain neutral spine)
        head_y = shoulder_y - 0.07
        pose['nose'] = [center_x + torso_lean, head_y, 0.95]
        pose['left_ear'] = [center_x - 0.03 + torso_lean, head_y, 0.9]
        pose['right_ear'] = [center_x + 0.03 + torso_lean, head_y, 0.9]
        
        # Eyes
        pose['left_eye'] = [center_x - 0.02 + torso_lean, head_y, 0.95]
        pose['right_eye'] = [center_x + 0.02 + torso_lean, head_y, 0.95]
        
        # Add remaining landmarks
        self._add_remaining_landmarks(pose, center_x + torso_lean, center_y)
        
        return pose
    
    def _add_remaining_landmarks(self, pose: Dict[str, List[float]], center_x: float, center_y: float):
        """Add remaining MediaPipe landmarks with appropriate confidence."""
        
        # Hand landmarks (lower confidence, approximate positions)
        for side in ['left', 'right']:
            wrist_key = f'{side}_wrist'
            if wrist_key in pose:
                wrist_pos = pose[wrist_key]
                
                # Fingers (lower confidence)
                pose[f'{side}_thumb'] = [wrist_pos[0], wrist_pos[1] + 0.02, 0.7]
                pose[f'{side}_index'] = [wrist_pos[0], wrist_pos[1] + 0.025, 0.7]
                pose[f'{side}_pinky'] = [wrist_pos[0], wrist_pos[1] + 0.02, 0.7]
        
        # Additional eye landmarks
        if 'left_eye' in pose and 'right_eye' in pose:
            left_eye = pose['left_eye']
            right_eye = pose['right_eye']
            
            pose['left_eye_inner'] = [left_eye[0] + 0.005, left_eye[1], 0.85]
            pose['left_eye_outer'] = [left_eye[0] - 0.005, left_eye[1], 0.85]
            pose['right_eye_inner'] = [right_eye[0] - 0.005, right_eye[1], 0.85]
            pose['right_eye_outer'] = [right_eye[0] + 0.005, right_eye[1], 0.85]
        
        # Mouth landmarks
        if 'nose' in pose:
            nose_pos = pose['nose']
            pose['mouth_left'] = [nose_pos[0] - 0.01, nose_pos[1] + 0.02, 0.85]
            pose['mouth_right'] = [nose_pos[0] + 0.01, nose_pos[1] + 0.02, 0.85]
    
    def _interpolate_between_poses(
        self,
        pose1: Dict[str, List[float]],
        pose2: Dict[str, List[float]],
        factor: float
    ) -> Dict[str, List[float]]:
        """Interpolate between two poses."""
        
        interpolated = {}
        
        # Get all common landmarks
        common_landmarks = set(pose1.keys()) & set(pose2.keys())
        
        for landmark in common_landmarks:
            p1 = np.array(pose1[landmark])
            p2 = np.array(pose2[landmark])
            
            # Interpolate position and confidence
            interpolated_pos = p1 + factor * (p2 - p1)
            interpolated[landmark] = interpolated_pos.tolist()
        
        return interpolated
    
    def _interpolate_pose_sequence(
        self,
        phases: Dict[str, Dict[str, List[float]]],
        total_frames: int
    ) -> List[Dict[str, List[float]]]:
        """Create smooth interpolated sequence between key poses."""
        
        sequence = []
        
        # Define the sequence of phases and their frame ranges
        phase_sequence = [
            ('setup', 0, int(total_frames * 0.1)),
            ('mid_descent', int(total_frames * 0.1), int(total_frames * 0.5)),
            ('bottom', int(total_frames * 0.5), int(total_frames * 0.6)),
            ('mid_ascent', int(total_frames * 0.6), int(total_frames * 0.9)),
            ('setup', int(total_frames * 0.9), total_frames)
        ]
        
        for i, (phase_name, start_frame, end_frame) in enumerate(phase_sequence):
            frame_count = end_frame - start_frame
            
            if i == 0:
                # First phase - hold the setup pose
                for frame in range(frame_count):
                    sequence.append(phases['setup'].copy())
            
            elif i == len(phase_sequence) - 1:
                # Last phase - return to setup
                for frame in range(frame_count):
                    factor = frame / max(1, frame_count - 1)
                    interpolated = self._interpolate_between_poses(
                        phases['mid_ascent'], phases['setup'], factor
                    )
                    sequence.append(interpolated)
            
            else:
                # Intermediate phases - interpolate to next phase
                current_phase = phases[phase_name]
                
                if i < len(phase_sequence) - 1:
                    next_phase_name = phase_sequence[i + 1][0]
                    next_phase = phases[next_phase_name]
                    
                    for frame in range(frame_count):
                        factor = frame / max(1, frame_count - 1)
                        interpolated = self._interpolate_between_poses(
                            current_phase, next_phase, factor
                        )
                        sequence.append(interpolated)
        
        # Ensure we have exactly the target number of frames
        while len(sequence) < total_frames:
            sequence.append(sequence[-1].copy())
        
        return sequence[:total_frames]
    
    def validate_pose_biomechanics(self, pose: Dict[str, List[float]]) -> Dict[str, Any]:
        """
        Validate that a generated pose meets biomechanical standards.
        
        Returns:
            Dictionary with validation results and biomechanical measurements
        """
        
        validation_results = {
            'is_valid': True,
            'violations': [],
            'measurements': {}
        }
        
        try:
            # Check torso lean angle
            if all(k in pose for k in ['left_shoulder', 'right_shoulder', 'left_hip', 'right_hip']):
                # Calculate average positions
                avg_shoulder_x = (pose['left_shoulder'][0] + pose['right_shoulder'][0]) / 2
                avg_shoulder_y = (pose['left_shoulder'][1] + pose['right_shoulder'][1]) / 2
                avg_hip_x = (pose['left_hip'][0] + pose['right_hip'][0]) / 2
                avg_hip_y = (pose['left_hip'][1] + pose['right_hip'][1]) / 2
                
                # Calculate torso lean angle
                torso_vector = np.array([avg_shoulder_x - avg_hip_x, avg_shoulder_y - avg_hip_y])
                vertical_vector = np.array([0, -1])  # Pointing up
                
                cos_angle = np.dot(torso_vector, vertical_vector) / (np.linalg.norm(torso_vector) * np.linalg.norm(vertical_vector))
                torso_angle = np.degrees(np.arccos(np.clip(cos_angle, -1.0, 1.0)))
                
                validation_results['measurements']['torso_lean_angle'] = torso_angle
                
                # Check against threshold (30° from research)
                max_lean = self.form_rules.get('squat', {}).get('posture', {}).get('max_torso_lean_angle', {}).get('threshold', 30)
                if torso_angle > max_lean:
                    validation_results['is_valid'] = False
                    validation_results['violations'].append(f"Excessive torso lean: {torso_angle:.1f}° > {max_lean}°")
            
            # Check knee angles
            for side in ['left', 'right']:
                hip_key = f'{side}_hip'
                knee_key = f'{side}_knee'
                ankle_key = f'{side}_ankle'
                
                if all(k in pose for k in [hip_key, knee_key, ankle_key]):
                    hip_pos = np.array(pose[hip_key][:2])
                    knee_pos = np.array(pose[knee_key][:2])
                    ankle_pos = np.array(pose[ankle_key][:2])
                    
                    # Calculate knee angle
                    v1 = hip_pos - knee_pos
                    v2 = ankle_pos - knee_pos
                    
                    cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
                    knee_angle = np.degrees(np.arccos(np.clip(cos_angle, -1.0, 1.0)))
                    
                    validation_results['measurements'][f'{side}_knee_angle'] = knee_angle
            
            # Additional biomechanical checks can be added here
            
        except Exception as e:
            logger.error(f"Error validating pose biomechanics: {e}")
            validation_results['is_valid'] = False
            validation_results['violations'].append(f"Validation error: {str(e)}")
        
        return validation_results


class ReferenceDeadliftGenerator(ReferenceSquatGenerator):
    """Generator for deadlift reference poses (future extension)."""
    
    def generate_deadlift_reference_pose(self, **kwargs) -> Dict[str, Any]:
        """Generate deadlift reference pose (placeholder for future implementation)."""
        logger.info("Deadlift reference pose generation not yet implemented")
        return {
            'pose_sequence': [],
            'metadata': {'exercise_type': 'deadlift', 'status': 'not_implemented'},
            'key_poses': {}
        }


class ReferencePoseService:
    """
    Main service for generating and managing reference poses for all exercises.
    """
    
    def __init__(self, settings: Optional[Settings] = None):
        """Initialize the reference pose service."""
        self.settings = settings
        self.squat_generator = ReferenceSquatGenerator(settings)
        # Future generators can be added here
        
    def generate_reference_pose(
        self,
        exercise_type: str,
        body_proportions: Optional[Dict[str, float]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate reference pose for specified exercise type.
        
        Args:
            exercise_type: Type of exercise ('squat', 'deadlift', etc.)
            body_proportions: Optional body measurements for scaling
            **kwargs: Exercise-specific parameters
            
        Returns:
            Dictionary with pose sequence and metadata
        """
        
        exercise_type = exercise_type.lower()
        
        if exercise_type == 'squat':
            return self.squat_generator.generate_squat_reference_pose(
                body_proportions=body_proportions,
                **kwargs
            )
        elif exercise_type == 'deadlift':
            # Future implementation
            deadlift_generator = ReferenceDeadliftGenerator(self.settings)
            return deadlift_generator.generate_deadlift_reference_pose(**kwargs)
        else:
            logger.warning(f"Unsupported exercise type: {exercise_type}")
            return {
                'pose_sequence': [],
                'metadata': {'exercise_type': exercise_type, 'status': 'unsupported'},
                'key_poses': {}
            }
    
    def get_supported_exercises(self) -> List[str]:
        """Get list of supported exercise types."""
        return ['squat']  # Will be expanded as more generators are added
    
    def validate_reference_pose(
        self,
        exercise_type: str,
        pose_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate generated reference pose against biomechanical standards."""
        
        if exercise_type.lower() == 'squat':
            # Validate key poses from the sequence
            validation_results = []
            key_poses = pose_data.get('key_poses', {})
            
            for phase_name, pose in key_poses.items():
                phase_validation = self.squat_generator.validate_pose_biomechanics(pose)
                validation_results.append({
                    'phase': phase_name,
                    'validation': phase_validation
                })
            
            return {
                'exercise_type': exercise_type,
                'overall_valid': all(result['validation']['is_valid'] for result in validation_results),
                'phase_validations': validation_results
            }
        
        return {
            'exercise_type': exercise_type,
            'overall_valid': False,
            'error': f'Validation not implemented for {exercise_type}'
        }