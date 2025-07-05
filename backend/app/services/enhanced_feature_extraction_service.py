"""
Enhanced feature extraction service for squat form analysis.

Fixes critical issues in the original feature extraction:
1. Proper depth fault detection
2. More sensitive posture scoring
3. Better stability analysis
4. Enhanced fault detection thresholds
"""

import logging
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from scipy.signal import find_peaks, savgol_filter

logger = logging.getLogger(__name__)


class EnhancedSquatFeatureExtractor:
    """
    Enhanced version of SquatFeatureExtractor with improved fault detection.
    
    Key improvements:
    - More sensitive depth detection
    - Better posture scoring that detects subtle faults
    - Enhanced stability analysis
    - Proper fault thresholds based on biomechanical research
    """
    
    # MediaPipe pose landmark indices
    MEDIAPIPE_LANDMARK_MAP = {
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
    
    def __init__(self, confidence_threshold: float = 0.5):
        """
        Initialize the enhanced feature extractor.
        
        Args:
            confidence_threshold: Minimum confidence for using a landmark
        """
        self.confidence_threshold = confidence_threshold
    
    def _convert_mediapipe_to_joint_format(self, 
                                         pose_sequence: List[Optional[List[Optional[Dict[str, Any]]]]]) -> List[Dict[str, Any]]:
        """
        Convert MediaPipe pose sequence to the joint format expected by feature extraction.
        
        MediaPipe format: List of frames, each frame is List of 33 landmarks with {x, y, z, visibility}
        Target format: List of frames, each frame is Dict with joint names and coordinates
        
        Args:
            pose_sequence: MediaPipe pose sequence
            
        Returns:
            Converted sequence in joint format
        """
        converted_sequence = []
        
        for frame_landmarks in pose_sequence:
            if frame_landmarks is None:
                # Skip frames with no pose detected
                continue
                
            frame_joints = {}
            
            # Extract key joints for squat analysis
            try:
                # Hip (center of left and right hip)
                left_hip = frame_landmarks[self.MEDIAPIPE_LANDMARK_MAP['left_hip']]
                right_hip = frame_landmarks[self.MEDIAPIPE_LANDMARK_MAP['right_hip']]
                
                if (left_hip and right_hip and 
                    left_hip.get('visibility', 0) > self.confidence_threshold and
                    right_hip.get('visibility', 0) > self.confidence_threshold):
                    
                    hip_x = (left_hip['x'] + right_hip['x']) / 2
                    hip_y = (left_hip['y'] + right_hip['y']) / 2
                    hip_z = (left_hip.get('z', 0) + right_hip.get('z', 0)) / 2
                    hip_confidence = (left_hip.get('visibility', 0) + right_hip.get('visibility', 0)) / 2
                    
                    frame_joints['hip'] = [hip_x, hip_y, hip_z, hip_confidence]
                
                # Left and right hip separately
                if left_hip and left_hip.get('visibility', 0) > self.confidence_threshold:
                    frame_joints['left_hip'] = [left_hip['x'], left_hip['y'], 
                                              left_hip.get('z', 0), left_hip.get('visibility', 0)]
                
                if right_hip and right_hip.get('visibility', 0) > self.confidence_threshold:
                    frame_joints['right_hip'] = [right_hip['x'], right_hip['y'], 
                                               right_hip.get('z', 0), right_hip.get('visibility', 0)]
                
                # Knees
                left_knee = frame_landmarks[self.MEDIAPIPE_LANDMARK_MAP['left_knee']]
                right_knee = frame_landmarks[self.MEDIAPIPE_LANDMARK_MAP['right_knee']]
                
                if left_knee and left_knee.get('visibility', 0) > self.confidence_threshold:
                    frame_joints['left_knee'] = [left_knee['x'], left_knee['y'], 
                                               left_knee.get('z', 0), left_knee.get('visibility', 0)]
                
                if right_knee and right_knee.get('visibility', 0) > self.confidence_threshold:
                    frame_joints['right_knee'] = [right_knee['x'], right_knee['y'], 
                                                right_knee.get('z', 0), right_knee.get('visibility', 0)]
                
                # Ankles
                left_ankle = frame_landmarks[self.MEDIAPIPE_LANDMARK_MAP['left_ankle']]
                right_ankle = frame_landmarks[self.MEDIAPIPE_LANDMARK_MAP['right_ankle']]
                
                if left_ankle and left_ankle.get('visibility', 0) > self.confidence_threshold:
                    frame_joints['left_ankle'] = [left_ankle['x'], left_ankle['y'], 
                                                left_ankle.get('z', 0), left_ankle.get('visibility', 0)]
                
                if right_ankle and right_ankle.get('visibility', 0) > self.confidence_threshold:
                    frame_joints['right_ankle'] = [right_ankle['x'], right_ankle['y'], 
                                                 right_ankle.get('z', 0), right_ankle.get('visibility', 0)]
                
                # Shoulders (for torso angle calculation)
                left_shoulder = frame_landmarks[self.MEDIAPIPE_LANDMARK_MAP['left_shoulder']]
                right_shoulder = frame_landmarks[self.MEDIAPIPE_LANDMARK_MAP['right_shoulder']]
                
                if (left_shoulder and right_shoulder and 
                    left_shoulder.get('visibility', 0) > self.confidence_threshold and
                    right_shoulder.get('visibility', 0) > self.confidence_threshold):
                    
                    shoulder_x = (left_shoulder['x'] + right_shoulder['x']) / 2
                    shoulder_y = (left_shoulder['y'] + right_shoulder['y']) / 2
                    shoulder_z = (left_shoulder.get('z', 0) + right_shoulder.get('z', 0)) / 2
                    shoulder_confidence = (left_shoulder.get('visibility', 0) + right_shoulder.get('visibility', 0)) / 2
                    
                    frame_joints['shoulder'] = [shoulder_x, shoulder_y, shoulder_z, shoulder_confidence]
                
                # Individual shoulders
                if left_shoulder and left_shoulder.get('visibility', 0) > self.confidence_threshold:
                    frame_joints['left_shoulder'] = [left_shoulder['x'], left_shoulder['y'], 
                                                   left_shoulder.get('z', 0), left_shoulder.get('visibility', 0)]
                
                if right_shoulder and right_shoulder.get('visibility', 0) > self.confidence_threshold:
                    frame_joints['right_shoulder'] = [right_shoulder['x'], right_shoulder['y'], 
                                                    right_shoulder.get('z', 0), right_shoulder.get('visibility', 0)]
                
                # Feet (for foot stability analysis)
                left_heel = frame_landmarks[self.MEDIAPIPE_LANDMARK_MAP['left_heel']]
                right_heel = frame_landmarks[self.MEDIAPIPE_LANDMARK_MAP['right_heel']]
                left_foot_index = frame_landmarks[self.MEDIAPIPE_LANDMARK_MAP['left_foot_index']]
                right_foot_index = frame_landmarks[self.MEDIAPIPE_LANDMARK_MAP['right_foot_index']]
                
                if left_heel and left_heel.get('visibility', 0) > self.confidence_threshold:
                    frame_joints['left_heel'] = [left_heel['x'], left_heel['y'], 
                                               left_heel.get('z', 0), left_heel.get('visibility', 0)]
                
                if right_heel and right_heel.get('visibility', 0) > self.confidence_threshold:
                    frame_joints['right_heel'] = [right_heel['x'], right_heel['y'], 
                                                right_heel.get('z', 0), right_heel.get('visibility', 0)]
                
                if left_foot_index and left_foot_index.get('visibility', 0) > self.confidence_threshold:
                    frame_joints['left_foot_index'] = [left_foot_index['x'], left_foot_index['y'], 
                                                     left_foot_index.get('z', 0), left_foot_index.get('visibility', 0)]
                
                if right_foot_index and right_foot_index.get('visibility', 0) > self.confidence_threshold:
                    frame_joints['right_foot_index'] = [right_foot_index['x'], right_foot_index['y'], 
                                                      right_foot_index.get('z', 0), right_foot_index.get('visibility', 0)]
                
            except (KeyError, IndexError, TypeError) as e:
                logger.warning(f"Error processing frame landmarks: {e}")
                continue
            
            if frame_joints:  # Only add frames with valid joints
                converted_sequence.append(frame_joints)
        
        return converted_sequence
    
    def _calculate_angle(self, p1: List[float], p2: List[float], p3: List[float]) -> float:
        """Calculate angle at point p2 formed by points p1-p2-p3 in 2D"""
        try:
            v1 = np.array([p1[0] - p2[0], p1[1] - p2[1]])
            v2 = np.array([p3[0] - p2[0], p3[1] - p2[1]])
            
            # Handle zero vectors
            norm_v1 = np.linalg.norm(v1)
            norm_v2 = np.linalg.norm(v2)
            
            if norm_v1 < 1e-6 or norm_v2 < 1e-6:
                return np.nan
            
            cos_angle = np.dot(v1, v2) / (norm_v1 * norm_v2)
            angle = np.arccos(np.clip(cos_angle, -1.0, 1.0))
            return np.degrees(angle)
        except Exception:
            return np.nan
    
    def _extract_joint_angles_per_frame(self, frame: Dict[str, Any]) -> Dict[str, float]:
        """Extract joint angles for a single frame"""
        angles = {}
        
        try:
            # Left knee angle (left_hip -> left_knee -> left_ankle)
            if all(joint in frame for joint in ['left_hip', 'left_knee', 'left_ankle']):
                left_knee_angle = self._calculate_angle(
                    frame['left_hip'][:2], 
                    frame['left_knee'][:2], 
                    frame['left_ankle'][:2]
                )
                angles['left_knee_angle'] = left_knee_angle
            
            # Right knee angle
            if all(joint in frame for joint in ['right_hip', 'right_knee', 'right_ankle']):
                right_knee_angle = self._calculate_angle(
                    frame['right_hip'][:2], 
                    frame['right_knee'][:2], 
                    frame['right_ankle'][:2]
                )
                angles['right_knee_angle'] = right_knee_angle
            
            # Hip angles (shoulder -> hip -> knee)
            if all(joint in frame for joint in ['shoulder', 'left_hip', 'left_knee']):
                left_hip_angle = self._calculate_angle(
                    frame['shoulder'][:2], 
                    frame['left_hip'][:2], 
                    frame['left_knee'][:2]
                )
                angles['left_hip_angle'] = left_hip_angle
            
            if all(joint in frame for joint in ['shoulder', 'right_hip', 'right_knee']):
                right_hip_angle = self._calculate_angle(
                    frame['shoulder'][:2], 
                    frame['right_hip'][:2], 
                    frame['right_knee'][:2]
                )
                angles['right_hip_angle'] = right_hip_angle
            
            # Torso lean angle (relative to vertical)
            if all(joint in frame for joint in ['shoulder', 'hip']):
                hip = frame['hip'][:2]
                shoulder = frame['shoulder'][:2]
                
                # Create vertical reference point
                vertical_point = [hip[0], hip[1] - 0.1]  # Point above hip (normalized coords)
                
                torso_angle = self._calculate_angle(
                    vertical_point, hip, shoulder
                )
                angles['torso_lean_angle'] = torso_angle
            
            # Ankle angles (knee -> ankle -> foot)
            if all(joint in frame for joint in ['left_knee', 'left_ankle', 'left_foot_index']):
                left_ankle_angle = self._calculate_angle(
                    frame['left_knee'][:2], 
                    frame['left_ankle'][:2], 
                    frame['left_foot_index'][:2]
                )
                angles['left_ankle_angle'] = left_ankle_angle
            
            if all(joint in frame for joint in ['right_knee', 'right_ankle', 'right_foot_index']):
                right_ankle_angle = self._calculate_angle(
                    frame['right_knee'][:2], 
                    frame['right_ankle'][:2], 
                    frame['right_foot_index'][:2]
                )
                angles['right_ankle_angle'] = right_ankle_angle
            
            # Enhanced knee valgus detection (using 3D projection if available)
            if all(joint in frame for joint in ['left_hip', 'left_knee', 'left_ankle']):
                # Calculate lateral deviation of knee from hip-ankle line
                hip_pos = np.array(frame['left_hip'][:2])
                knee_pos = np.array(frame['left_knee'][:2])
                ankle_pos = np.array(frame['left_ankle'][:2])
                
                # Calculate distance from knee to hip-ankle line
                line_vec = ankle_pos - hip_pos
                point_vec = knee_pos - hip_pos
                
                if np.linalg.norm(line_vec) > 1e-6:
                    proj_length = np.dot(point_vec, line_vec) / np.linalg.norm(line_vec)
                    proj_point = hip_pos + (proj_length / np.linalg.norm(line_vec)) * line_vec
                    lateral_deviation = np.linalg.norm(knee_pos - proj_point)
                    
                    # Convert to approximate angle (enhanced calculation)
                    angles['left_knee_valgus_deg'] = lateral_deviation * 150  # Enhanced scale factor
                
            # Similar for right knee valgus
            if all(joint in frame for joint in ['right_hip', 'right_knee', 'right_ankle']):
                hip_pos = np.array(frame['right_hip'][:2])
                knee_pos = np.array(frame['right_knee'][:2])
                ankle_pos = np.array(frame['right_ankle'][:2])
                
                line_vec = ankle_pos - hip_pos
                point_vec = knee_pos - hip_pos
                
                if np.linalg.norm(line_vec) > 1e-6:
                    proj_length = np.dot(point_vec, line_vec) / np.linalg.norm(line_vec)
                    proj_point = hip_pos + (proj_length / np.linalg.norm(line_vec)) * line_vec
                    lateral_deviation = np.linalg.norm(knee_pos - proj_point)
                    
                    angles['right_knee_valgus_deg'] = lateral_deviation * 150
            
            # Enhanced foot stability indicators
            if all(joint in frame for joint in ['left_heel', 'left_foot_index']):
                heel_y = frame['left_heel'][1]
                toe_y = frame['left_foot_index'][1]
                # More sensitive foot flat detection
                angles['left_foot_flat'] = 1.0 if abs(heel_y - toe_y) < 0.015 else 0.0
            
            if all(joint in frame for joint in ['right_heel', 'right_foot_index']):
                heel_y = frame['right_heel'][1]
                toe_y = frame['right_foot_index'][1]
                angles['right_foot_flat'] = 1.0 if abs(heel_y - toe_y) < 0.015 else 0.0
            
        except Exception as e:
            logger.warning(f"Error calculating joint angles: {e}")
        
        return angles
    
    def _detect_squat_phases(self, knee_angles: List[float]) -> Dict[str, List[int]]:
        """
        Detect squat phases (descent, bottom, ascent) from knee angle trajectory.
        
        Args:
            knee_angles: List of minimum knee angles across frames
            
        Returns:
            Dictionary with phase indices: {'descent': [...], 'bottom': [...], 'ascent': [...]}
        """
        phases = {'descent': [], 'bottom': [], 'ascent': []}
        
        if len(knee_angles) < 3:
            return phases
        
        try:
            # Smooth the signal to reduce noise
            if len(knee_angles) >= 5:
                smoothed = savgol_filter(knee_angles, window_length=5, polyorder=2)
            else:
                smoothed = knee_angles
            
            # Find the minimum point (bottom of squat)
            min_idx = np.argmin(smoothed)
            
            # Simple phase detection
            # Descent: start to minimum
            phases['descent'] = list(range(0, min_idx))
            
            # Bottom: around minimum (±2 frames)
            bottom_start = max(0, min_idx - 2)
            bottom_end = min(len(smoothed), min_idx + 3)
            phases['bottom'] = list(range(bottom_start, bottom_end))
            
            # Ascent: minimum to end
            phases['ascent'] = list(range(min_idx, len(smoothed)))
            
        except Exception as e:
            logger.warning(f"Error detecting squat phases: {e}")
        
        return phases
    
    def extract_features(self, pose_sequence: List[Optional[List[Optional[Dict[str, Any]]]]]) -> Dict[str, float]:
        """
        Extract enhanced biomechanical features with improved fault detection.
        
        Args:
            pose_sequence: MediaPipe pose sequence from video processing
            
        Returns:
            Dictionary containing enhanced features with better fault detection
        """
        try:
            # Convert MediaPipe format to joint format
            joint_sequence = self._convert_mediapipe_to_joint_format(pose_sequence)
            
            if len(joint_sequence) < 3:
                logger.warning("Insufficient frames for feature extraction")
                return self._get_default_features()
            
            # Extract angles for each frame
            all_frame_angles = []
            all_knee_angles = []
            all_hip_positions = []
            all_torso_angles = []
            all_hip_angles = []
            all_knee_valgus_left = []
            all_knee_valgus_right = []
            all_ankle_angles = []
            all_foot_flat_left = []
            all_foot_flat_right = []
            
            for frame in joint_sequence:
                frame_angles = self._extract_joint_angles_per_frame(frame)
                all_frame_angles.append(frame_angles)
                
                # Collect knee angles (use minimum of left/right)
                left_knee = frame_angles.get('left_knee_angle', np.nan)
                right_knee = frame_angles.get('right_knee_angle', np.nan)
                
                if not np.isnan(left_knee) and not np.isnan(right_knee):
                    min_knee_angle = min(left_knee, right_knee)
                elif not np.isnan(left_knee):
                    min_knee_angle = left_knee
                elif not np.isnan(right_knee):
                    min_knee_angle = right_knee
                else:
                    min_knee_angle = np.nan
                
                all_knee_angles.append(min_knee_angle)
                
                # Collect hip positions (Y coordinate)
                if 'hip' in frame and frame['hip'] is not None:
                    all_hip_positions.append(frame['hip'][1])
                else:
                    all_hip_positions.append(np.nan)
                
                # Collect other angles
                all_torso_angles.append(frame_angles.get('torso_lean_angle', np.nan))
                
                # Average hip angles
                left_hip_angle = frame_angles.get('left_hip_angle', np.nan)
                right_hip_angle = frame_angles.get('right_hip_angle', np.nan)
                
                if not np.isnan(left_hip_angle) and not np.isnan(right_hip_angle):
                    avg_hip_angle = (left_hip_angle + right_hip_angle) / 2
                elif not np.isnan(left_hip_angle):
                    avg_hip_angle = left_hip_angle
                elif not np.isnan(right_hip_angle):
                    avg_hip_angle = right_hip_angle
                else:
                    avg_hip_angle = np.nan
                
                all_hip_angles.append(avg_hip_angle)
                
                # Collect knee valgus and other measurements
                all_knee_valgus_left.append(frame_angles.get('left_knee_valgus_deg', np.nan))
                all_knee_valgus_right.append(frame_angles.get('right_knee_valgus_deg', np.nan))
                
                # Average ankle angles
                left_ankle = frame_angles.get('left_ankle_angle', np.nan)
                right_ankle = frame_angles.get('right_ankle_angle', np.nan)
                
                if not np.isnan(left_ankle) and not np.isnan(right_ankle):
                    avg_ankle_angle = (left_ankle + right_ankle) / 2
                elif not np.isnan(left_ankle):
                    avg_ankle_angle = left_ankle
                elif not np.isnan(right_ankle):
                    avg_ankle_angle = right_ankle
                else:
                    avg_ankle_angle = np.nan
                
                all_ankle_angles.append(avg_ankle_angle)
                
                # Foot stability
                all_foot_flat_left.append(frame_angles.get('left_foot_flat', np.nan))
                all_foot_flat_right.append(frame_angles.get('right_foot_flat', np.nan))
            
            # Detect squat phases
            phases = self._detect_squat_phases(all_knee_angles)
            
            # Calculate enhanced features
            features = self._calculate_enhanced_features(
                all_knee_angles, all_hip_positions, all_torso_angles, all_hip_angles,
                all_knee_valgus_left, all_knee_valgus_right, all_ankle_angles,
                all_foot_flat_left, all_foot_flat_right, phases
            )
            
            return features
            
        except Exception as e:
            logger.error(f"Enhanced feature extraction failed: {e}", exc_info=True)
            return self._get_default_features()
    
    def _calculate_enhanced_features(self, knee_angles, hip_positions, torso_angles, hip_angles,
                                   knee_valgus_left, knee_valgus_right, ankle_angles,
                                   foot_flat_left, foot_flat_right, phases) -> Dict[str, float]:
        """Calculate enhanced features with improved fault detection"""
        
        # Filter valid values
        valid_knee_angles = [a for a in knee_angles if not np.isnan(a)]
        valid_hip_positions = [p for p in hip_positions if not np.isnan(p)]
        valid_torso_angles = [a for a in torso_angles if not np.isnan(a)]
        valid_hip_angles = [a for a in hip_angles if not np.isnan(a)]
        valid_knee_valgus_left = [v for v in knee_valgus_left if not np.isnan(v)]
        valid_knee_valgus_right = [v for v in knee_valgus_right if not np.isnan(v)]
        valid_ankle_angles = [a for a in ankle_angles if not np.isnan(a)]
        valid_foot_flat_left = [f for f in foot_flat_left if not np.isnan(f)]
        valid_foot_flat_right = [f for f in foot_flat_right if not np.isnan(f)]
        
        features = {}
        
        # 1. relative_hip_depth (enhanced)
        if valid_hip_positions:
            max_hip_y = max(valid_hip_positions)
            min_hip_y = min(valid_hip_positions)
            features['relative_hip_depth'] = (max_hip_y - min_hip_y) if max_hip_y != min_hip_y else 0.0
        else:
            features['relative_hip_depth'] = 0.0
        
        # 2. hip_rom_sufficient (enhanced threshold)
        if valid_hip_angles:
            hip_rom = max(valid_hip_angles) - min(valid_hip_angles)
            features['hip_rom_sufficient'] = 1.0 if hip_rom > 25 else 0.0  # Lowered threshold
        else:
            features['hip_rom_sufficient'] = 0.0
        
        # 3. depth_flag (ENHANCED - more sensitive)
        if valid_knee_angles:
            min_knee_angle = min(valid_knee_angles)
            # Enhanced depth detection - multiple criteria
            depth_criteria = [
                min_knee_angle < 100,  # More lenient threshold for detection
                features['relative_hip_depth'] > 0.06,  # Lower threshold for hip movement
                features['hip_rom_sufficient'] == 1.0  # Adequate hip flexion
            ]
            # If knee angle is severely limited (>120°), it's definitely a depth fault
            if min_knee_angle > 120:
                features['depth_flag'] = 0.0  # Definitely insufficient depth
            elif min_knee_angle < 80:
                features['depth_flag'] = 1.0  # Definitely good depth
            else:
                # Use multiple criteria for borderline cases
                features['depth_flag'] = 1.0 if sum(depth_criteria) >= 2 else 0.0
        else:
            features['depth_flag'] = 0.0
        
        # 4. min_knee_angle
        features['min_knee_angle'] = min(valid_knee_angles) if valid_knee_angles else 180.0
        
        # 5. posture_score (ENHANCED - more sensitive fault detection)
        posture_score = 100.0
        if valid_torso_angles:
            max_torso_lean = max(valid_torso_angles)
            torso_std = np.std(valid_torso_angles)
            
            # More granular posture scoring
            if max_torso_lean > 35:
                posture_score -= 50  # Severe lean
            elif max_torso_lean > 25:
                posture_score -= 35  # Moderate lean
            elif max_torso_lean > 15:
                posture_score -= 20  # Mild lean
            elif max_torso_lean > 10:
                posture_score -= 10  # Slight lean
            
            # Penalty for inconsistent posture
            if torso_std > 8:
                posture_score -= 15
            elif torso_std > 5:
                posture_score -= 10
        
        # Additional posture penalties
        if valid_knee_valgus_left or valid_knee_valgus_right:
            max_valgus = max(
                max(valid_knee_valgus_left) if valid_knee_valgus_left else 0,
                max(valid_knee_valgus_right) if valid_knee_valgus_right else 0
            )
            if max_valgus > 8:
                posture_score -= 25
            elif max_valgus > 4:
                posture_score -= 15
        
        features['posture_score'] = max(0.0, posture_score)
        
        # 6. max_torso_lean_angle
        features['max_torso_lean_angle'] = max(valid_torso_angles) if valid_torso_angles else 0.0
        
        # 7. torso_control_flag (enhanced sensitivity)
        if valid_torso_angles and len(valid_torso_angles) > 2:
            torso_std = np.std(valid_torso_angles)
            features['torso_control_flag'] = 1.0 if torso_std > 7 else 0.0  # More sensitive
        else:
            features['torso_control_flag'] = 0.0
        
        # 8. excessive_forward_lean (enhanced threshold)
        features['excessive_forward_lean'] = 1.0 if features['max_torso_lean_angle'] > 25 else 0.0
        
        # 9. asymmetry_flag (enhanced detection)
        if valid_knee_valgus_left and valid_knee_valgus_right:
            avg_left = np.mean(valid_knee_valgus_left)
            avg_right = np.mean(valid_knee_valgus_right)
            if max(avg_left, avg_right) > 0:
                asymmetry_ratio = abs(avg_left - avg_right) / max(avg_left, avg_right)
                features['asymmetry_flag'] = 1.0 if asymmetry_ratio > 0.15 else 0.0  # More sensitive
            else:
                features['asymmetry_flag'] = 0.0
        else:
            features['asymmetry_flag'] = 0.0
        
        # 10. torso_stability_std
        features['torso_stability_std'] = np.std(valid_torso_angles) if valid_torso_angles else 0.0
        
        # 11. knee_valgus_flag (enhanced threshold)
        max_left_valgus = max(valid_knee_valgus_left) if valid_knee_valgus_left else 0.0
        max_right_valgus = max(valid_knee_valgus_right) if valid_knee_valgus_right else 0.0
        features['knee_valgus_flag'] = 1.0 if max(max_left_valgus, max_right_valgus) > 3.0 else 0.0  # More sensitive
        
        # 12. stability_score (enhanced calculation)
        stability_score = 100.0
        if features['knee_valgus_flag'] == 1.0:
            stability_score -= 40  # Increased penalty
        if features['asymmetry_flag'] == 1.0:
            stability_score -= 35  # Increased penalty
        if features['torso_control_flag'] == 1.0:
            stability_score -= 25  # New penalty for control issues
        features['stability_score'] = max(0.0, stability_score)
        
        # 13. ascent_duration (assuming 30fps)
        fps = 30
        ascent_frames = len(phases.get('ascent', []))
        features['ascent_duration'] = ascent_frames / fps
        
        # 14. tempo_ratio
        descent_frames = len(phases.get('descent', []))
        features['descent_duration'] = descent_frames / fps
        if features['ascent_duration'] > 0:
            features['tempo_ratio'] = features['descent_duration'] / features['ascent_duration']
        else:
            features['tempo_ratio'] = 0.0
        
        # 15. controlled_descent_flag
        features['controlled_descent_flag'] = 1.0 if features['descent_duration'] >= 1.5 else 0.0
        
        # 16. overall_score (enhanced calculation)
        # Weight depth more heavily for depth faults
        depth_score = 80.0 if features['depth_flag'] == 1.0 else 20.0
        posture_weight = 0.4
        stability_weight = 0.3
        depth_weight = 0.3
        
        features['overall_score'] = (
            depth_score * depth_weight + 
            features['posture_score'] * posture_weight + 
            features['stability_score'] * stability_weight
        )
        
        # Additional features (17-23)
        # 17. knee_asymmetry
        if valid_knee_valgus_left and valid_knee_valgus_right:
            avg_left = np.mean(valid_knee_valgus_left)
            avg_right = np.mean(valid_knee_valgus_right)
            if max(avg_left, avg_right) > 0:
                features['knee_asymmetry'] = abs(avg_left - avg_right) / max(avg_left, avg_right)
            else:
                features['knee_asymmetry'] = 0.0
        else:
            features['knee_asymmetry'] = 0.0
        
        # 18. right_knee_valgus_flag
        features['right_knee_valgus_flag'] = 1.0 if max_right_valgus > 3.0 else 0.0
        
        # 19. descent_duration (already calculated above)
        
        # 20. smooth_ascent_flag
        if phases['ascent'] and len(knee_angles) > 0:
            ascent_knee_angles = [knee_angles[i] for i in phases['ascent'] 
                                if i < len(knee_angles) and not np.isnan(knee_angles[i])]
            if len(ascent_knee_angles) > 3:
                diffs = np.diff(ascent_knee_angles)
                features['smooth_ascent_flag'] = 1.0 if np.std(diffs) > 8 else 0.0  # Flag if NOT smooth
            else:
                features['smooth_ascent_flag'] = 0.0
        else:
            features['smooth_ascent_flag'] = 0.0
        
        # 21. max_right_knee_valgus_deg
        features['max_right_knee_valgus_deg'] = max_right_valgus
        
        # 22. max_left_knee_valgus_deg
        features['max_left_knee_valgus_deg'] = max_left_valgus
        
        # 23. knee_rom
        if valid_knee_angles:
            features['knee_rom'] = max(valid_knee_angles) - min(valid_knee_angles)
        else:
            features['knee_rom'] = 0.0
        
        return features
    
    def _get_default_features(self) -> Dict[str, float]:
        """Return default feature values when extraction fails"""
        return {
            'relative_hip_depth': 0.0,
            'hip_rom_sufficient': 0.0,
            'depth_flag': 0.0,
            'min_knee_angle': 180.0,
            'posture_score': 50.0,
            'max_torso_lean_angle': 0.0,
            'torso_control_flag': 0.0,
            'excessive_forward_lean': 0.0,
            'asymmetry_flag': 0.0,
            'torso_stability_std': 0.0,
            'knee_valgus_flag': 0.0,
            'stability_score': 50.0,
            'ascent_duration': 1.0,
            'tempo_ratio': 1.0,
            'controlled_descent_flag': 0.0,
            'overall_score': 50.0,
            'knee_asymmetry': 0.0,
            'right_knee_valgus_flag': 0.0,
            'descent_duration': 1.0,
            'smooth_ascent_flag': 0.0,
            'max_right_knee_valgus_deg': 0.0,
            'max_left_knee_valgus_deg': 0.0,
            'knee_rom': 0.0
        }