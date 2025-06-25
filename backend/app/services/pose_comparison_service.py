"""
Pose Comparison and Alignment Service

This service provides functionality to compare user poses with reference poses,
calculate alignment scores, identify deviations, and generate data for visual overlays.
"""

import logging
import numpy as np
from typing import Dict, List, Tuple, Optional, Any, Union
from scipy.spatial.distance import euclidean
from scipy.optimize import minimize
import math

from app.core.logging import get_logger
from app.core.config import Settings

logger = get_logger(__name__)


class PoseAlignmentService:
    """
    Service for aligning and comparing user poses with reference poses.
    
    Provides methods to:
    - Calculate pose similarity scores
    - Identify specific pose deviations
    - Generate alignment data for visual overlays
    - Match video frames to reference movement phases
    """
    
    def __init__(self, settings: Optional[Settings] = None):
        """Initialize the pose alignment service."""
        self.settings = settings
        
        # Joint importance weights for scoring (based on biomechanical significance)
        self.joint_weights = {
            # Core joints (highest importance)
            'left_hip': 1.0,
            'right_hip': 1.0,
            'left_knee': 1.0,
            'right_knee': 1.0,
            'left_ankle': 0.9,
            'right_ankle': 0.9,
            'left_shoulder': 0.8,
            'right_shoulder': 0.8,
            
            # Secondary joints
            'left_elbow': 0.6,
            'right_elbow': 0.6,
            'left_wrist': 0.4,
            'right_wrist': 0.4,
            
            # Head and facial landmarks (lower importance for form analysis)
            'nose': 0.3,
            'left_eye': 0.2,
            'right_eye': 0.2,
            'left_ear': 0.2,
            'right_ear': 0.2,
            
            # Hand landmarks (lowest importance)
            'left_thumb': 0.1,
            'right_thumb': 0.1,
            'left_index': 0.1,
            'right_index': 0.1,
            'left_pinky': 0.1,
            'right_pinky': 0.1,
            
            # Foot landmarks
            'left_heel': 0.3,
            'right_heel': 0.3,
            'left_foot_index': 0.3,
            'right_foot_index': 0.3
        }
        
        # Confidence thresholds
        self.min_confidence = 0.5
        self.good_confidence = 0.7
        
    def calculate_pose_similarity(
        self,
        user_pose: Dict[str, List[float]],
        reference_pose: Dict[str, List[float]],
        normalize_positions: bool = True
    ) -> Dict[str, Any]:
        """
        Calculate similarity between user pose and reference pose.
        
        Args:
            user_pose: User's pose landmarks
            reference_pose: Reference pose landmarks
            normalize_positions: Whether to normalize pose positions
            
        Returns:
            Dictionary with similarity score and detailed comparison
        """
        try:
            result = {
                'overall_similarity': 0.0,
                'joint_similarities': {},
                'deviations': {},
                'alignment_quality': 'poor',
                'total_joints_compared': 0,
                'high_confidence_joints': 0
            }
            
            # Normalize poses if requested
            if normalize_positions:
                user_pose = self._normalize_pose(user_pose)
                reference_pose = self._normalize_pose(reference_pose)
            
            # Find common joints
            common_joints = set(user_pose.keys()) & set(reference_pose.keys())
            if not common_joints:
                logger.warning("No common joints found between user and reference pose")
                return result
            
            joint_scores = []
            weighted_scores = []
            
            for joint_name in common_joints:
                user_point = user_pose[joint_name]
                ref_point = reference_pose[joint_name]
                
                # Check confidence (if available)
                user_confidence = user_point[2] if len(user_point) > 2 else 1.0
                ref_confidence = ref_point[2] if len(ref_point) > 2 else 1.0
                
                # Skip low confidence points
                if user_confidence < self.min_confidence:
                    continue
                
                # Calculate 2D distance (x, y coordinates)
                user_xy = np.array(user_point[:2])
                ref_xy = np.array(ref_point[:2])
                
                distance = euclidean(user_xy, ref_xy)
                
                # Convert distance to similarity score (0-1, where 1 is perfect match)
                # Assume poses are normalized to 0-1 coordinate space
                max_distance = math.sqrt(2)  # Maximum possible distance in normalized space
                similarity = max(0, 1 - (distance / max_distance))
                
                # Apply joint importance weight
                weight = self.joint_weights.get(joint_name, 0.5)
                weighted_score = similarity * weight
                
                joint_scores.append(similarity)
                weighted_scores.append(weighted_score)
                
                # Store individual joint results
                result['joint_similarities'][joint_name] = {
                    'similarity': similarity,
                    'distance': distance,
                    'user_confidence': user_confidence,
                    'weight': weight,
                    'weighted_score': weighted_score
                }
                
                # Identify significant deviations
                if similarity < 0.7:  # Threshold for deviation
                    result['deviations'][joint_name] = {
                        'distance': distance,
                        'similarity': similarity,
                        'severity': 'high' if similarity < 0.5 else 'medium'
                    }
                
                # Count high confidence joints
                if user_confidence >= self.good_confidence:
                    result['high_confidence_joints'] += 1
            
            # Calculate overall similarity
            if weighted_scores:
                result['overall_similarity'] = np.mean(weighted_scores)
                result['total_joints_compared'] = len(weighted_scores)
                
                # Determine alignment quality
                if result['overall_similarity'] >= 0.8:
                    result['alignment_quality'] = 'excellent'
                elif result['overall_similarity'] >= 0.7:
                    result['alignment_quality'] = 'good'
                elif result['overall_similarity'] >= 0.5:
                    result['alignment_quality'] = 'fair'
                else:
                    result['alignment_quality'] = 'poor'
            
            logger.debug(f"Pose similarity calculated: {result['overall_similarity']:.3f}")
            return result
            
        except Exception as e:
            logger.error(f"Error calculating pose similarity: {e}", exc_info=True)
            return {
                'overall_similarity': 0.0,
                'joint_similarities': {},
                'deviations': {},
                'alignment_quality': 'error',
                'total_joints_compared': 0,
                'high_confidence_joints': 0,
                'error': str(e)
            }
    
    def match_video_to_reference_phases(
        self,
        user_video_poses: List[Dict[str, List[float]]],
        reference_pose_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Match user video frames to reference movement phases.
        
        Args:
            user_video_poses: List of user poses from video frames
            reference_pose_data: Reference pose data with phases
            
        Returns:
            Dictionary with frame-to-phase mappings and alignment scores
        """
        try:
            result = {
                'frame_mappings': [],
                'phase_alignments': {},
                'best_matches': {},
                'overall_alignment': 0.0,
                'temporal_analysis': {}
            }
            
            # Extract reference phases
            if 'key_poses' not in reference_pose_data:
                logger.error("Reference pose data missing key_poses")
                return result
            
            key_poses = reference_pose_data['key_poses']
            reference_phases = ['setup', 'mid_descent', 'bottom', 'mid_ascent']
            
            # Ensure all required phases exist
            available_phases = [phase for phase in reference_phases if phase in key_poses]
            if not available_phases:
                logger.error("No valid reference phases found")
                return result
            
            # Match each video frame to best reference phase
            frame_mappings = []
            phase_scores = {phase: [] for phase in available_phases}
            
            for frame_idx, user_pose in enumerate(user_video_poses):
                if not user_pose:
                    continue
                
                frame_result = {
                    'frame_index': frame_idx,
                    'best_phase': None,
                    'best_score': 0.0,
                    'phase_scores': {}
                }
                
                # Compare with each reference phase
                for phase_name in available_phases:
                    ref_pose = key_poses[phase_name]
                    
                    similarity_result = self.calculate_pose_similarity(
                        user_pose=user_pose,
                        reference_pose=ref_pose,
                        normalize_positions=True
                    )
                    
                    score = similarity_result['overall_similarity']
                    frame_result['phase_scores'][phase_name] = score
                    
                    # Track best match
                    if score > frame_result['best_score']:
                        frame_result['best_score'] = score
                        frame_result['best_phase'] = phase_name
                    
                    # Collect scores for phase analysis
                    phase_scores[phase_name].append(score)
                
                frame_mappings.append(frame_result)
            
            result['frame_mappings'] = frame_mappings
            
            # Analyze phase alignments
            for phase_name, scores in phase_scores.items():
                if scores:
                    result['phase_alignments'][phase_name] = {
                        'average_score': np.mean(scores),
                        'best_score': np.max(scores),
                        'frame_count': len(scores),
                        'quality': 'good' if np.mean(scores) > 0.7 else 'fair' if np.mean(scores) > 0.5 else 'poor'
                    }
            
            # Calculate overall alignment
            all_scores = [frame['best_score'] for frame in frame_mappings if frame['best_score'] > 0]
            if all_scores:
                result['overall_alignment'] = np.mean(all_scores)
            
            # Temporal analysis
            result['temporal_analysis'] = self._analyze_movement_tempo(frame_mappings, available_phases)
            
            logger.info(f"Video-to-reference matching complete. Overall alignment: {result['overall_alignment']:.3f}")
            return result
            
        except Exception as e:
            logger.error(f"Error matching video to reference phases: {e}", exc_info=True)
            return {
                'frame_mappings': [],
                'phase_alignments': {},
                'best_matches': {},
                'overall_alignment': 0.0,
                'temporal_analysis': {},
                'error': str(e)
            }
    
    def generate_overlay_alignment_data(
        self,
        user_pose: Dict[str, List[float]],
        reference_pose: Dict[str, List[float]],
        highlight_deviations: bool = True
    ) -> Dict[str, Any]:
        """
        Generate data for visual overlay alignment between user and reference poses.
        
        Args:
            user_pose: User's current pose
            reference_pose: Reference pose to compare against
            highlight_deviations: Whether to highlight significant deviations
            
        Returns:
            Dictionary with overlay data for frontend visualization
        """
        try:
            # Calculate similarity
            similarity_result = self.calculate_pose_similarity(
                user_pose=user_pose,
                reference_pose=reference_pose,
                normalize_positions=True
            )
            
            overlay_data = {
                'user_keypoints': user_pose,
                'reference_keypoints': reference_pose,
                'similarity_score': similarity_result['overall_similarity'],
                'alignment_quality': similarity_result['alignment_quality'],
                'joint_colors': {},
                'deviation_highlights': [],
                'connection_lines': [],
                'feedback_annotations': []
            }
            
            # Generate color coding for joints based on alignment quality
            for joint_name, joint_data in similarity_result['joint_similarities'].items():
                similarity = joint_data['similarity']
                
                if similarity >= 0.8:
                    color = '#4CAF50'  # Green - good alignment
                elif similarity >= 0.6:
                    color = '#FFC107'  # Amber - fair alignment
                else:
                    color = '#F44336'  # Red - poor alignment
                
                overlay_data['joint_colors'][joint_name] = {
                    'color': color,
                    'similarity': similarity,
                    'alpha': min(1.0, joint_data['user_confidence'])
                }
            
            # Generate deviation highlights if requested
            if highlight_deviations:
                for joint_name, deviation in similarity_result['deviations'].items():
                    if joint_name in user_pose and joint_name in reference_pose:
                        user_point = user_pose[joint_name][:2]
                        ref_point = reference_pose[joint_name][:2]
                        
                        overlay_data['deviation_highlights'].append({
                            'joint': joint_name,
                            'user_position': user_point,
                            'reference_position': ref_point,
                            'distance': deviation['distance'],
                            'severity': deviation['severity'],
                            'arrow_data': {
                                'start': user_point,
                                'end': ref_point,
                                'color': '#F44336' if deviation['severity'] == 'high' else '#FF9800'
                            }
                        })
            
            # Generate connection lines for pose skeleton
            overlay_data['connection_lines'] = self._generate_pose_connections(
                user_pose, reference_pose, similarity_result['joint_similarities']
            )
            
            # Generate feedback annotations
            overlay_data['feedback_annotations'] = self._generate_pose_feedback_annotations(
                similarity_result['deviations'], similarity_result['overall_similarity']
            )
            
            return overlay_data
            
        except Exception as e:
            logger.error(f"Error generating overlay alignment data: {e}", exc_info=True)
            return {
                'user_keypoints': user_pose,
                'reference_keypoints': reference_pose,
                'similarity_score': 0.0,
                'alignment_quality': 'error',
                'joint_colors': {},
                'deviation_highlights': [],
                'connection_lines': [],
                'feedback_annotations': [],
                'error': str(e)
            }
    
    def _normalize_pose(self, pose: Dict[str, List[float]]) -> Dict[str, List[float]]:
        """
        Normalize pose coordinates to a standard reference frame.
        
        Args:
            pose: Pose landmarks dictionary
            
        Returns:
            Normalized pose dictionary
        """
        try:
            if not pose:
                return pose
            
            # Extract x, y coordinates (ignore confidence for normalization)
            points = []
            for joint_name, coords in pose.items():
                if len(coords) >= 2:
                    points.append([coords[0], coords[1]])
            
            if len(points) < 2:
                return pose  # Can't normalize with too few points
            
            points = np.array(points)
            
            # Calculate bounding box
            min_x, min_y = np.min(points, axis=0)
            max_x, max_y = np.max(points, axis=0)
            
            # Calculate scale and center
            width = max_x - min_x
            height = max_y - min_y
            scale = max(width, height)
            
            if scale == 0:
                return pose  # All points are the same
            
            center_x = (min_x + max_x) / 2
            center_y = (min_y + max_y) / 2
            
            # Normalize each point
            normalized_pose = {}
            for joint_name, coords in pose.items():
                if len(coords) >= 2:
                    # Normalize x, y coordinates
                    norm_x = (coords[0] - center_x) / scale + 0.5
                    norm_y = (coords[1] - center_y) / scale + 0.5
                    
                    # Keep original confidence if available
                    if len(coords) > 2:
                        normalized_pose[joint_name] = [norm_x, norm_y, coords[2]]
                    else:
                        normalized_pose[joint_name] = [norm_x, norm_y]
                else:
                    normalized_pose[joint_name] = coords
            
            return normalized_pose
            
        except Exception as e:
            logger.error(f"Error normalizing pose: {e}")
            return pose
    
    def _analyze_movement_tempo(
        self,
        frame_mappings: List[Dict[str, Any]],
        phases: List[str]
    ) -> Dict[str, Any]:
        """Analyze the tempo and timing of movement phases."""
        try:
            tempo_analysis = {
                'phase_durations': {},
                'phase_transitions': [],
                'tempo_quality': 'unknown',
                'recommendations': []
            }
            
            if not frame_mappings:
                return tempo_analysis
            
            # Track phase transitions
            current_phase = None
            phase_start_frame = 0
            
            for frame_data in frame_mappings:
                best_phase = frame_data['best_phase']
                frame_idx = frame_data['frame_index']
                
                if best_phase != current_phase:
                    if current_phase is not None:
                        # Record phase duration
                        duration = frame_idx - phase_start_frame
                        if current_phase not in tempo_analysis['phase_durations']:
                            tempo_analysis['phase_durations'][current_phase] = []
                        tempo_analysis['phase_durations'][current_phase].append(duration)
                        
                        # Record transition
                        tempo_analysis['phase_transitions'].append({
                            'from_phase': current_phase,
                            'to_phase': best_phase,
                            'frame': frame_idx,
                            'duration': duration
                        })
                    
                    current_phase = best_phase
                    phase_start_frame = frame_idx
            
            # Analyze tempo quality (assuming 30fps)
            fps = 30
            for phase, durations in tempo_analysis['phase_durations'].items():
                avg_duration_frames = np.mean(durations)
                avg_duration_seconds = avg_duration_frames / fps
                
                # Expected durations for squat phases (can be made exercise-specific)
                expected_durations = {
                    'setup': 1.0,
                    'mid_descent': 1.5,
                    'bottom': 0.5,
                    'mid_ascent': 1.0
                }
                
                expected = expected_durations.get(phase, 1.0)
                if abs(avg_duration_seconds - expected) <= 0.5:
                    tempo_analysis['tempo_quality'] = 'good'
                elif abs(avg_duration_seconds - expected) <= 1.0:
                    tempo_analysis['tempo_quality'] = 'fair'
                else:
                    tempo_analysis['tempo_quality'] = 'needs_improvement'
                    
                    if avg_duration_seconds < expected * 0.7:
                        tempo_analysis['recommendations'].append(f"Slow down {phase} phase")
                    elif avg_duration_seconds > expected * 1.5:
                        tempo_analysis['recommendations'].append(f"Speed up {phase} phase")
            
            return tempo_analysis
            
        except Exception as e:
            logger.error(f"Error analyzing movement tempo: {e}")
            return {
                'phase_durations': {},
                'phase_transitions': [],
                'tempo_quality': 'error',
                'recommendations': []
            }
    
    def _generate_pose_connections(
        self,
        user_pose: Dict[str, List[float]],
        reference_pose: Dict[str, List[float]],
        joint_similarities: Dict[str, Dict[str, float]]
    ) -> List[Dict[str, Any]]:
        """Generate connection lines for pose skeleton visualization."""
        
        # Define pose skeleton connections (MediaPipe format)
        connections = [
            # Face
            ('left_eye', 'right_eye'),
            ('left_eye', 'nose'),
            ('right_eye', 'nose'),
            ('left_ear', 'left_eye'),
            ('right_ear', 'right_eye'),
            
            # Torso
            ('left_shoulder', 'right_shoulder'),
            ('left_shoulder', 'left_hip'),
            ('right_shoulder', 'right_hip'),
            ('left_hip', 'right_hip'),
            
            # Arms
            ('left_shoulder', 'left_elbow'),
            ('left_elbow', 'left_wrist'),
            ('right_shoulder', 'right_elbow'),
            ('right_elbow', 'right_wrist'),
            
            # Legs
            ('left_hip', 'left_knee'),
            ('left_knee', 'left_ankle'),
            ('right_hip', 'right_knee'),
            ('right_knee', 'right_ankle'),
            
            # Feet
            ('left_ankle', 'left_heel'),
            ('left_ankle', 'left_foot_index'),
            ('right_ankle', 'right_heel'),
            ('right_ankle', 'right_foot_index'),
        ]
        
        connection_lines = []
        
        for joint1, joint2 in connections:
            if joint1 in user_pose and joint2 in user_pose:
                # Calculate connection quality based on joint similarities
                sim1 = joint_similarities.get(joint1, {}).get('similarity', 0.5)
                sim2 = joint_similarities.get(joint2, {}).get('similarity', 0.5)
                avg_similarity = (sim1 + sim2) / 2
                
                # Color based on average similarity
                if avg_similarity >= 0.8:
                    color = '#4CAF50'  # Green
                elif avg_similarity >= 0.6:
                    color = '#FFC107'  # Amber
                else:
                    color = '#F44336'  # Red
                
                connection_lines.append({
                    'joint1': joint1,
                    'joint2': joint2,
                    'user_start': user_pose[joint1][:2],
                    'user_end': user_pose[joint2][:2],
                    'reference_start': reference_pose.get(joint1, [0, 0])[:2],
                    'reference_end': reference_pose.get(joint2, [0, 0])[:2],
                    'color': color,
                    'similarity': avg_similarity,
                    'thickness': max(1, int(3 * avg_similarity))
                })
        
        return connection_lines
    
    def _generate_pose_feedback_annotations(
        self,
        deviations: Dict[str, Dict[str, float]],
        overall_similarity: float
    ) -> List[Dict[str, Any]]:
        """Generate feedback annotations for pose overlay."""
        
        annotations = []
        
        # Overall feedback
        if overall_similarity >= 0.8:
            annotations.append({
                'type': 'overall',
                'message': 'Excellent form!',
                'color': '#4CAF50',
                'position': 'top_center'
            })
        elif overall_similarity >= 0.6:
            annotations.append({
                'type': 'overall',
                'message': 'Good form with minor adjustments needed',
                'color': '#FFC107',
                'position': 'top_center'
            })
        else:
            annotations.append({
                'type': 'overall',
                'message': 'Form needs improvement',
                'color': '#F44336',
                'position': 'top_center'
            })
        
        # Specific joint feedback
        critical_joints = ['left_knee', 'right_knee', 'left_hip', 'right_hip']
        
        for joint_name, deviation in deviations.items():
            if joint_name in critical_joints and deviation['severity'] == 'high':
                joint_display_name = joint_name.replace('_', ' ').title()
                annotations.append({
                    'type': 'joint_specific',
                    'joint': joint_name,
                    'message': f'Adjust {joint_display_name} position',
                    'color': '#F44336',
                    'severity': deviation['severity'],
                    'distance': deviation['distance']
                })
        
        return annotations


class PoseComparisonService:
    """
    Main service for pose comparison and alignment operations.
    Integrates with the FormIQ AI pipeline.
    """
    
    def __init__(self, settings: Optional[Settings] = None):
        """Initialize the pose comparison service."""
        self.settings = settings
        self.alignment_service = PoseAlignmentService(settings)
        
    def compare_form_check_poses(
        self,
        form_check_data: Dict[str, Any],
        reference_pose_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Compare poses from a form check with reference poses.
        
        Args:
            form_check_data: Form check data including user poses
            reference_pose_data: Reference pose data
            
        Returns:
            Comprehensive comparison results
        """
        try:
            logger.info("Starting form check pose comparison")
            
            comparison_results = {
                'frame_comparisons': [],
                'phase_analysis': {},
                'overall_assessment': {},
                'visualization_data': {},
                'recommendations': []
            }
            
            # Extract user poses (this would come from video analysis)
            user_poses = form_check_data.get('pose_sequence', [])
            if not user_poses:
                logger.warning("No user poses found in form check data")
                return comparison_results
            
            # Match video to reference phases
            phase_matching = self.alignment_service.match_video_to_reference_phases(
                user_video_poses=user_poses,
                reference_pose_data=reference_pose_data
            )
            
            comparison_results['phase_analysis'] = phase_matching
            
            # Generate frame-by-frame comparisons for key frames
            key_frame_indices = self._select_key_frames(user_poses, phase_matching)
            
            for frame_idx in key_frame_indices:
                if frame_idx < len(user_poses):
                    user_pose = user_poses[frame_idx]
                    frame_mapping = phase_matching['frame_mappings'][frame_idx]
                    best_phase = frame_mapping['best_phase']
                    
                    if best_phase and best_phase in reference_pose_data.get('key_poses', {}):
                        reference_pose = reference_pose_data['key_poses'][best_phase]
                        
                        # Generate detailed comparison
                        similarity_result = self.alignment_service.calculate_pose_similarity(
                            user_pose=user_pose,
                            reference_pose=reference_pose
                        )
                        
                        # Generate overlay data
                        overlay_data = self.alignment_service.generate_overlay_alignment_data(
                            user_pose=user_pose,
                            reference_pose=reference_pose
                        )
                        
                        comparison_results['frame_comparisons'].append({
                            'frame_index': frame_idx,
                            'phase': best_phase,
                            'similarity_result': similarity_result,
                            'overlay_data': overlay_data
                        })
            
            # Overall assessment
            comparison_results['overall_assessment'] = self._generate_overall_assessment(
                phase_matching, comparison_results['frame_comparisons']
            )
            
            # Generate recommendations
            comparison_results['recommendations'] = self._generate_recommendations(
                comparison_results['overall_assessment'],
                phase_matching.get('temporal_analysis', {})
            )
            
            logger.info("Form check pose comparison completed successfully")
            return comparison_results
            
        except Exception as e:
            logger.error(f"Error in form check pose comparison: {e}", exc_info=True)
            return {
                'frame_comparisons': [],
                'phase_analysis': {},
                'overall_assessment': {'error': str(e)},
                'visualization_data': {},
                'recommendations': []
            }
    
    def _select_key_frames(
        self,
        user_poses: List[Dict[str, List[float]]],
        phase_matching: Dict[str, Any]
    ) -> List[int]:
        """Select key frames for detailed comparison."""
        
        key_frames = []
        frame_mappings = phase_matching.get('frame_mappings', [])
        
        if not frame_mappings:
            # Fallback: select evenly distributed frames
            num_frames = len(user_poses)
            return [0, num_frames//3, num_frames//2, 2*num_frames//3, num_frames-1]
        
        # Find the best frame for each phase
        phase_best_frames = {}
        for frame_data in frame_mappings:
            phase = frame_data['best_phase']
            score = frame_data['best_score']
            frame_idx = frame_data['frame_index']
            
            if phase not in phase_best_frames or score > phase_best_frames[phase]['score']:
                phase_best_frames[phase] = {'frame_index': frame_idx, 'score': score}
        
        # Collect best frame indices
        key_frames = [data['frame_index'] for data in phase_best_frames.values()]
        
        # Ensure we have at least a few frames
        if len(key_frames) < 3:
            num_frames = len(user_poses)
            key_frames.extend([0, num_frames//2, num_frames-1])
        
        return sorted(list(set(key_frames)))  # Remove duplicates and sort
    
    def _generate_overall_assessment(
        self,
        phase_matching: Dict[str, Any],
        frame_comparisons: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate overall assessment of pose comparison."""
        
        assessment = {
            'overall_score': 0.0,
            'phase_scores': {},
            'strengths': [],
            'weaknesses': [],
            'improvement_areas': []
        }
        
        # Calculate overall score from phase alignment
        overall_alignment = phase_matching.get('overall_alignment', 0.0)
        assessment['overall_score'] = overall_alignment
        
        # Analyze phase-specific performance
        phase_alignments = phase_matching.get('phase_alignments', {})
        for phase, data in phase_alignments.items():
            score = data.get('average_score', 0.0)
            assessment['phase_scores'][phase] = score
            
            if score >= 0.8:
                assessment['strengths'].append(f"Excellent {phase} form")
            elif score < 0.6:
                assessment['weaknesses'].append(f"Needs improvement in {phase}")
                assessment['improvement_areas'].append(phase)
        
        # Analyze common deviations from frame comparisons
        all_deviations = {}
        for frame_comp in frame_comparisons:
            deviations = frame_comp['similarity_result'].get('deviations', {})
            for joint, deviation in deviations.items():
                if joint not in all_deviations:
                    all_deviations[joint] = []
                all_deviations[joint].append(deviation['severity'])
        
        # Identify persistent issues
        for joint, severities in all_deviations.items():
            if len(severities) >= 2 and 'high' in severities:
                joint_name = joint.replace('_', ' ').title()
                assessment['improvement_areas'].append(f"{joint_name} alignment")
        
        return assessment
    
    def _generate_recommendations(
        self,
        overall_assessment: Dict[str, Any],
        temporal_analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate actionable recommendations based on assessment."""
        
        recommendations = []
        
        # Overall score recommendations
        overall_score = overall_assessment.get('overall_score', 0.0)
        if overall_score >= 0.8:
            recommendations.append({
                'type': 'positive',
                'category': 'overall',
                'message': 'Excellent form! Keep up the great work.',
                'priority': 'low'
            })
        elif overall_score >= 0.6:
            recommendations.append({
                'type': 'improvement',
                'category': 'overall',
                'message': 'Good form with room for minor improvements.',
                'priority': 'medium'
            })
        else:
            recommendations.append({
                'type': 'correction',
                'category': 'overall',
                'message': 'Focus on fundamental form improvements.',
                'priority': 'high'
            })
        
        # Phase-specific recommendations
        phase_scores = overall_assessment.get('phase_scores', {})
        for phase, score in phase_scores.items():
            if score < 0.6:
                recommendations.append({
                    'type': 'correction',
                    'category': 'phase',
                    'phase': phase,
                    'message': f'Focus on improving {phase} technique.',
                    'priority': 'high' if score < 0.4 else 'medium'
                })
        
        # Tempo recommendations
        tempo_recs = temporal_analysis.get('recommendations', [])
        for rec in tempo_recs:
            recommendations.append({
                'type': 'tempo',
                'category': 'timing',
                'message': rec,
                'priority': 'medium'
            })
        
        # Joint-specific recommendations
        improvement_areas = overall_assessment.get('improvement_areas', [])
        for area in improvement_areas:
            if 'knee' in area.lower():
                recommendations.append({
                    'type': 'technique',
                    'category': 'joint_alignment',
                    'message': 'Focus on knee tracking and stability.',
                    'priority': 'high'
                })
            elif 'hip' in area.lower():
                recommendations.append({
                    'type': 'technique',
                    'category': 'joint_alignment',
                    'message': 'Work on hip hinge and depth.',
                    'priority': 'high'
                })
        
        return recommendations