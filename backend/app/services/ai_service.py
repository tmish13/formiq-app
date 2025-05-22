"""Consolidated AI service for pose detection and form analysis."""
import mediapipe as mp
import numpy as np
import cv2
from typing import Dict, List, Any, Tuple, Optional, Union
import torch
from pathlib import Path
import asyncio # Added for asyncio.to_thread
import time
import hashlib
import os

from app.core.config import settings
from app.core.logging import get_logger
from app.models.enums import ExerciseType

logger = get_logger(__name__)

# Renamed from AIModelService
class AIService:
    NUM_EXPECTED_LANDMARKS = 33 # MediaPipe Pose model typically has 33 landmarks

    def __init__(self):
        """Initialize the AI model service."""
        logger.info("Initializing AIService...")
        self.pose = mp.solutions.pose.Pose(
            static_image_mode=False,
            model_complexity=settings.AI_MODEL_COMPLEXITY, # Use setting
            min_detection_confidence=settings.AI_MIN_DETECTION_CONFIDENCE,
            min_tracking_confidence=settings.AI_MIN_TRACKING_CONFIDENCE
        )
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"AI Service using device: {self.device}")
        self.model = self._load_form_analysis_model()
        # TODO: Integrate loading of other models (pose, comparison) from ml_model_service.py
        # TODO: Integrate loading of templates from ml_model_service.py
        
    def _load_form_analysis_model(self) -> Any:
        """Load the form analysis model."""
        try:
            # Consistent path from settings
            model_path = Path(settings.AI_MODEL_PATH) / "form_analysis_model.pt" 
            if model_path.exists():
                logger.info(f"Loading form analysis model from: {model_path}")
                model = torch.load(model_path, map_location=self.device)
                model.eval() # Set model to evaluation mode
                logger.info("Form analysis model loaded successfully.")
                return model
            logger.warning(f"Form analysis model not found at {model_path}. Using default rules.")
            return None
        except Exception as e:
            logger.error(f"Error loading form analysis model: {str(e)}", exc_info=True)
            return None
            
    def detect_pose(self, frame: np.ndarray) -> Tuple[List[Dict[str, float]], float]:
        """Detect pose landmarks in a frame."""
        try:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame_rgb.flags.writeable = False # Performance optimization
            results = self.pose.process(frame_rgb)
            frame_rgb.flags.writeable = True # Re-enable writing
            # frame = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR) # Convert back if needed for drawing
            
            if not results.pose_landmarks:
                return [], 0.0
                
            landmarks = []
            visibility_sum = 0.0
            lm_count = 0
            for landmark in results.pose_landmarks.landmark:
                landmarks.append({
                    "x": landmark.x,
                    "y": landmark.y,
                    "z": landmark.z,
                    "visibility": landmark.visibility
                })
                visibility_sum += landmark.visibility
                lm_count += 1
                
            confidence = (visibility_sum / lm_count) if lm_count > 0 else 0.0
            
            return landmarks, confidence
            
        except Exception as e:
            logger.error(f"Error detecting pose: {str(e)}", exc_info=True)
            return [], 0.0
            
    async def analyze_form(self, landmarks: List[Dict[str, float]], exercise_type: str) -> Dict[str, Any]:
        """Analyze exercise form based on pose landmarks. Now asynchronous."""
        
        def _run_model_inference_and_rules():
            # This internal synchronous function will be run in a thread
            if not landmarks:
                logger.warning("analyze_form (sync part) called with no landmarks.")
                return {
                    "score": 0.0,
                    "feedback": ["No pose detected."],
                    "risk_level": "high",
                    "feedback_structured": []
                }
            
            current_score = 1.0 # Default score for rule-based, or initial score from model
            feedback_messages = []
            risk = "low"
            feedback_structured_list = []

            if self.model:
                logger.debug(f"Analyzing form using loaded model for {exercise_type}. (Sync part)")
                landmarks_input = [[l["x"], l["y"], l.get("z", 0)] for l in landmarks] # Use .get for z
                landmarks_tensor = torch.tensor([landmarks_input], dtype=torch.float32).to(self.device)
                
                with torch.no_grad():
                    model_output = self.model(landmarks_tensor)
                    inferred_score = float(model_output.mean().item()) 
                    current_score = inferred_score # Use model score as base
                    feedback_messages.append(f"Model analyzed {exercise_type} - Score: {inferred_score:.2f}")
                    # Example: Add a structured feedback from model if available
                    feedback_structured_list.append({
                        "type": FeedbackType.TECHNIQUE, # Example
                        "message": f"Model raw score: {inferred_score:.2f}",
                        "timestamp": 0.0, # General feedback
                        "severity": FeedbackSeverity.INFO
                    })
            else:
                logger.warning(f"Form analysis model not loaded. Using rule-based analysis for {exercise_type}. (Sync part)")
                feedback_messages.append("Model not loaded, using basic rules.")

            # Rule-based analysis (can augment or replace model feedback)
            try:
                # Example: Spine alignment (indices are examples, adjust to your landmark model)
                # Assuming landmark indices: 11 (L_SHOULDER), 23 (L_HIP), 24 (R_HIP)
                spine_angle = self._calculate_angle(landmarks, 11, 23, 24) 
                if spine_angle is not None and (spine_angle < 160 or spine_angle > 200):
                    msg = "Maintain a neutral spine."
                    feedback_messages.append(msg)
                    feedback_structured_list.append({
                        "type": FeedbackType.ALIGNMENT,
                        "message": msg,
                        "timestamp": 0.0,
                        "severity": FeedbackSeverity.MEDIUM,
                        "suggestions": ["Engage core, keep chest up."]
                    })
                    current_score *= 0.8
                
                if exercise_type.lower() == 'squat':
                    # LHip (23), LKnee (25), LAnkle (27)
                    left_knee_angle = self._calculate_angle(landmarks, 23, 25, 27)
                    # RHip (24), RKnee (26), RAnkle (28)
                    right_knee_angle = self._calculate_angle(landmarks, 24, 26, 28)
                    avg_knee_angles = [a for a in [left_knee_angle, right_knee_angle] if a is not None]
                    avg_knee_angle = np.mean(avg_knee_angles) if avg_knee_angles else None
                    
                    if avg_knee_angle is not None and avg_knee_angle < 80: 
                        msg = "Ensure sufficient squat depth (knees bent more). Current avg angle: {avg_knee_angle:.1f}"
                        feedback_messages.append(msg)
                        feedback_structured_list.append({
                            "type": FeedbackType.RANGE_OF_MOTION,
                            "message": msg,
                            "timestamp": 0.0,
                            "severity": FeedbackSeverity.LOW,
                            "suggestions": ["Try to lower your hips further."]
                        })
                        current_score *= 0.9
                
                if not feedback_messages:
                    feedback_messages.append("Form looks generally good based on available rules.")
            
            except Exception as e_rules:
                logger.error(f"Error during rule-based analysis (sync part): {e_rules}", exc_info=True)
                feedback_messages.append("Error during rule-based analysis.")
                current_score = 0.0 # Penalize heavily if rules crash

            final_score = max(0.0, min(1.0, current_score)) # Clamp score if it's 0-1 scale
            # If score is 0-100, adjust clamping or scaling as needed.
            # Assuming score from model is 0-1, and rules adjust it. If model is 0-100, adapt.
            # Let's assume the output score should be 0-100 for FormCheck.
            final_score_100 = final_score * 100

            risk_level = "low" if final_score > 0.7 else "medium" if final_score > 0.4 else "high"
                
            return {
                "score": final_score_100, 
                "feedback": feedback_messages, # List of strings
                "risk_level": risk_level,
                "feedback_structured": feedback_structured_list # List of dicts for FeedbackItemCreate
            }

        try:
            # Run the synchronous parts (model inference, rules) in a thread
            analysis_output = await asyncio.to_thread(_run_model_inference_and_rules)
            return analysis_output
        except Exception as e_async_wrapper:
            logger.error(f"Async wrapper error in analyze_form: {e_async_wrapper}", exc_info=True)
            return {
                "score": 0.0,
                "feedback": ["Analysis failed due to an internal error."],
                "risk_level": "high",
                "feedback_structured": []
            }
            
    def _get_landmark_coords(self, landmarks: List[Dict[str, float]], index: int) -> Optional[np.ndarray]:
        """Safely get landmark coordinates as a numpy array."""
        if 0 <= index < len(landmarks):
            lm = landmarks[index]
            # Check visibility? For angle calculation, maybe use even if low visibility?
            # if lm['visibility'] > settings.AI_MIN_VISIBILITY_THRESHOLD:
            return np.array([lm["x"], lm["y"], lm.get("z", 0)]) # Use z if available, else 0
        return None

    def _calculate_angle(self, landmarks: List[Dict[str, float]], p1_idx: int, p2_idx: int, p3_idx: int) -> Optional[float]:
        """Calculate the angle formed by three landmarks."""
        p1 = self._get_landmark_coords(landmarks, p1_idx)
        p2 = self._get_landmark_coords(landmarks, p2_idx) # Vertex
        p3 = self._get_landmark_coords(landmarks, p3_idx)

        if p1 is None or p2 is None or p3 is None:
            return None

        try:
            # Calculate vectors
            v1 = p1 - p2
            v2 = p3 - p2

            # Calculate angle using dot product
            dot_product = np.dot(v1, v2)
            norm_v1 = np.linalg.norm(v1)
            norm_v2 = np.linalg.norm(v2)

            if norm_v1 == 0 or norm_v2 == 0:
                return None # Avoid division by zero
            
            cos_angle = dot_product / (norm_v1 * norm_v2)
            # Clamp value to avoid potential floating point issues with arccos
            cos_angle = np.clip(cos_angle, -1.0, 1.0)
            
            angle = np.degrees(np.arccos(cos_angle))
            return angle
        except Exception as e:
            logger.error(f"Error calculating angle for points {p1_idx},{p2_idx},{p3_idx}: {str(e)}")
            return None

    # Placeholder for methods from other services to be potentially merged here
    # def _load_pose_model ... from ml_model_service
    # def _load_form_comparison_model ... from ml_model_service
    # def _load_template_poses ... from ml_model_service
    # def _detect_exercise_phases ... from ai.py
    # def _generate_detailed_feedback ... maybe call BiomechanicsService?

    async def initialize_models(self):
        """Initialize AI models"""
        try:
            # TODO: Initialize actual models
            pass
        except Exception as e:
            raise AIServiceError(f"Failed to initialize AI models: {str(e)}")

    async def analyze_exercise_form(self, video_path: str) -> Dict[str, Any]:
        """Analyze exercise form using AI."""
        try:
            # Implementation for form analysis
            return {
                "score": 0.0,
                "feedback": [],
                "keypoints": [],
                "risk_level": "low"
            }
        except Exception as e:
            raise AIServiceError(f"Failed to analyze exercise form: {str(e)}")

    async def generate_workout_plan(
        self,
        user_level: str,
        goals: List[str],
        equipment: List[str],
        duration: int
    ) -> Dict[str, Any]:
        """Generate a personalized workout plan."""
        try:
            # Implementation for workout plan generation
            return {
                "plan": [],
                "duration": duration,
                "difficulty": user_level,
                "equipment_needed": equipment
            }
        except Exception as e:
            raise AIServiceError(f"Failed to generate workout plan: {str(e)}")

    async def suggest_exercises(
        self,
        exercise_type: ExerciseType,
        user_level: str,
        equipment: List[str]
    ) -> List[Dict[str, Any]]:
        """Suggest exercises based on type and user level."""
        try:
            # Implementation for exercise suggestions
            return []
        except Exception as e:
            raise AIServiceError(f"Failed to suggest exercises: {str(e)}")

    async def analyze_progress(self, workout_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze user's workout progress."""
        try:
            # Implementation for progress analysis
            return {
                "improvements": [],
                "recommendations": [],
                "stats": {}
            }
        except Exception as e:
            raise AIServiceError(f"Failed to analyze progress: {str(e)}")

    async def generate_form_tips(self, exercise_type: ExerciseType) -> List[str]:
        """Generate form tips for a specific exercise type."""
        try:
            # Implementation for form tips generation
            return []
        except Exception as e:
            raise AIServiceError(f"Failed to generate form tips: {str(e)}")

    async def predict_injury_risk(self, exercise_data: Dict[str, Any]) -> Dict[str, Any]:
        """Predict injury risk for an exercise."""
        try:
            # Implementation for injury risk prediction
            return {
                "risk_level": "low",
                "risk_factors": [],
                "recommendations": []
            }
        except Exception as e:
            raise AIServiceError(f"Failed to predict injury risk: {str(e)}")

    async def optimize_workout(
        self,
        current_plan: Dict[str, Any],
        user_feedback: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Optimize a workout plan based on user feedback."""
        try:
            # Implementation for workout optimization
            return current_plan
        except Exception as e:
            raise AIServiceError(f"Failed to optimize workout: {str(e)}")

    def extract_frames(self, video_path: str, frame_rate: int = 30) -> List[np.ndarray]:
        """Extract frames from video at specified rate."""
        try:
            frames = []
            cap = cv2.VideoCapture(video_path)
            frame_count = 0
            
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                    
                if frame_count % frame_rate == 0:
                    frames.append(frame)
                frame_count += 1
                
            cap.release()
            return frames
        except Exception as e:
            logger.error(f"Error extracting frames: {str(e)}")
            raise

    async def preprocess_video(self, video_path: str) -> str:
        """Preprocess video for analysis"""
        try:
            # TODO: Implement video preprocessing
            return video_path
        except Exception as e:
            raise AIServiceError(f"Failed to preprocess video: {str(e)}")

    async def extract_pose_landmarks(self, frame: np.ndarray) -> Dict:
        """Extract pose landmarks from frame"""
        try:
            # TODO: Implement pose landmark extraction
            return {}
        except Exception as e:
            raise AIServiceError(f"Failed to extract pose landmarks: {str(e)}")

    async def analyze_pose_sequence(self, landmarks: List[Dict]) -> Dict:
        """Analyze sequence of pose landmarks"""
        try:
            # TODO: Implement pose sequence analysis
            return {}
        except Exception as e:
            raise AIServiceError(f"Failed to analyze pose sequence: {str(e)}")

    async def generate_feedback(self, analysis: Dict) -> str:
        """Generate feedback based on analysis"""
        try:
            # TODO: Implement feedback generation
            return "Good form!"
        except Exception as e:
            raise AIServiceError(f"Failed to generate feedback: {str(e)}")

    async def detect_exercise_phases(self, landmarks: List[Dict]) -> List[Dict]:
        """Detect different phases of the exercise"""
        try:
            # TODO: Implement phase detection
            return []
        except Exception as e:
            raise AIServiceError(f"Failed to detect exercise phases: {str(e)}")

    async def calculate_joint_angles(self, landmarks: Dict) -> Dict:
        """Calculate joint angles from landmarks"""
        try:
            # TODO: Implement joint angle calculation
            return {}
        except Exception as e:
            raise AIServiceError(f"Failed to calculate joint angles: {str(e)}")

    async def analyze_form_with_low_confidence(self, video_path: str, exercise_type: ExerciseType) -> Dict:
        """Analyze form when confidence is low"""
        try:
            # TODO: Implement low confidence analysis
            return {}
        except Exception as e:
            raise AIServiceError(f"Failed to analyze form with low confidence: {str(e)}")

    async def handle_model_error(self, video_path: str, error: Exception) -> Dict:
        """Handle model errors gracefully"""
        try:
            # TODO: Implement error handling
            return {}
        except Exception as e:
            raise AIServiceError(f"Failed to handle model error: {str(e)}")

    async def validate_video_duration(self, video_path: str) -> bool:
        """Validate video duration"""
        try:
            # TODO: Implement video duration validation
            return True
        except Exception as e:
            raise AIServiceError(f"Failed to validate video duration: {str(e)}")

    async def get_exercise_specific_thresholds(self, exercise_type: ExerciseType) -> Dict:
        """Get exercise-specific thresholds"""
        try:
            # TODO: Implement threshold retrieval
            return {}
        except Exception as e:
            raise AIServiceError(f"Failed to get exercise thresholds: {str(e)}")

    async def save_analysis_debug_info(self, video_path: str, analysis: Dict, output_path: str):
        """Save debug information for analysis"""
        try:
            # TODO: Implement debug information saving
            logger.info(f"Debug info for {video_path} would be saved to {output_path} with data: {analysis}")
            pass # Placeholder
        except Exception as e:
            raise AIServiceError(f"Failed to save debug info: {str(e)}")

    async def process_frames_for_pose(
        self,
        frame_paths: List[str],
        min_pose_confidence_threshold: Optional[float] = None
    ) -> List[Optional[List[Optional[Dict[str, float]]]]]:
        """
        Processes a list of frame image paths to detect pose landmarks.
        Ensures each frame's result is a list of NUM_EXPECTED_LANDMARKS items (Optional[Dict])
        or None if the frame is unusable.

        Args:
            frame_paths: A list of file paths to individual frame images.
            min_pose_confidence_threshold: The minimum confidence for overall pose detection per frame
                                           and for individual landmark visibility.

        Returns:
            A list where each outer list element corresponds to a frame:
            - None: if the overall pose confidence for the frame is below the threshold,
                    if the frame cannot be read, if MediaPipe detects no landmarks, 
                    or if an error occurs during processing for that frame.
            - List[Optional[Dict[str, float]]]: A list of length NUM_EXPECTED_LANDMARKS.
              Each inner list element is either a landmark Dict (if detected and visible)
              or None (if not detected or below visibility threshold).
        """
        logger.info(f"AIService: Starting pose processing for {len(frame_paths)} frames with threshold {min_pose_confidence_threshold}.")
        
        if min_pose_confidence_threshold is None:
            logger.warning("min_pose_confidence_threshold not provided to process_frames_for_pose, using AI_MIN_DETECTION_CONFIDENCE as fallback.")
            min_pose_confidence_threshold = settings.AI_MIN_DETECTION_CONFIDENCE 

        all_frame_results: List[Optional[List[Optional[Dict[str, float]]]]] = []

        for i, frame_path in enumerate(frame_paths):
            try:
                frame = await asyncio.to_thread(cv2.imread, frame_path)
                if frame is None:
                    logger.warning(f"AIService: Could not read frame {i+1}/{len(frame_paths)}: {frame_path}")
                    all_frame_results.append(None)
                    continue

                # raw_landmarks_from_mp is List[Dict[str, float]] (guaranteed 33 if pose detected)
                # overall_frame_confidence is float
                raw_landmarks_from_mp, overall_frame_confidence = await asyncio.to_thread(self.detect_pose, frame)

                if overall_frame_confidence < min_pose_confidence_threshold or not raw_landmarks_from_mp:
                    log_msg = f"AIService: Frame {i+1}/{len(frame_paths)} ({frame_path}) unusable. "
                    if overall_frame_confidence < min_pose_confidence_threshold:
                        log_msg += f"Overall confidence ({overall_frame_confidence:.2f}) < threshold ({min_pose_confidence_threshold:.2f}). "
                    if not raw_landmarks_from_mp:
                        log_msg += "No landmarks detected by MediaPipe."
                    logger.debug(log_msg.strip())
                    all_frame_results.append(None)
                    continue
                
                # Initialize with Nones for all expected landmarks
                output_landmarks_for_frame: List[Optional[Dict[str, float]]] = [None] * self.NUM_EXPECTED_LANDMARKS
                num_detected_raw = len(raw_landmarks_from_mp)
                visible_count = 0

                for lm_idx in range(self.NUM_EXPECTED_LANDMARKS):
                    if lm_idx < num_detected_raw: # Should always be true if raw_landmarks_from_mp is not empty
                        landmark_data = raw_landmarks_from_mp[lm_idx]
                        if landmark_data.get('visibility', 0.0) >= min_pose_confidence_threshold:
                            output_landmarks_for_frame[lm_idx] = landmark_data
                            visible_count += 1
                        # else: it remains None, correctly indicating low visibility or absence
                    # else: lm_idx >= num_detected_raw, means MediaPipe returned fewer than expected, remains None

                logger.debug(
                    f"AIService: Frame {i+1}/{len(frame_paths)} ({frame_path}): Processed. "
                    f"Overall confidence: {overall_frame_confidence:.2f}. "
                    f"MediaPipe detected: {num_detected_raw}. Visible (>= threshold): {visible_count}/{self.NUM_EXPECTED_LANDMARKS}."
                )
                all_frame_results.append(output_landmarks_for_frame)

            except Exception as e:
                logger.error(f"AIService: Error processing frame {i+1}/{len(frame_paths)} ({frame_path}) for pose: {e}", exc_info=True)
                all_frame_results.append(None)
        
        processed_count = sum(1 for lm_list in all_frame_results if lm_list is not None)
        logger.info(f"AIService: Finished pose processing. Successfully processed {processed_count}/{len(frame_paths)} frames outputting structured landmark lists.")
        return all_frame_results

    # Helper function for linear interpolation of landmark data
    def _interpolate_landmark(
        self, 
        lm_prev: Optional[Dict[str, float]], 
        lm_next: Optional[Dict[str, float]], 
        ratio: float
    ) -> Optional[Dict[str, float]]:
        if lm_prev is None or lm_next is None:
            return None # Cannot interpolate if one of the endpoints is missing

        # Ensure all required keys are present; use .get for safety
        x_prev, y_prev, z_prev, vis_prev = lm_prev.get('x'), lm_prev.get('y'), lm_prev.get('z'), lm_prev.get('visibility')
        x_next, y_next, z_next, vis_next = lm_next.get('x'), lm_next.get('y'), lm_next.get('z'), lm_next.get('visibility')

        if any(v is None for v in [x_prev, y_prev, z_prev, vis_prev, x_next, y_next, z_next, vis_next]):
            logger.debug("Interpolation skipped due to missing coordinate/visibility in source landmarks.")
            return None # Not enough data to interpolate

        # Interpolate coordinates
        interp_x = x_prev + (x_next - x_prev) * ratio
        interp_y = y_prev + (y_next - y_prev) * ratio
        interp_z = z_prev + (z_next - z_prev) * ratio
        # Interpolate visibility (or use a fixed value like 0.5 to mark as interpolated)
        interp_vis = vis_prev + (vis_next - vis_prev) * ratio 
        # Alternatively, could set interp_vis = min(vis_prev, vis_next) or a fixed value e.g. 0.5

        return {"x": interp_x, "y": interp_y, "z": interp_z, "visibility": interp_vis}

    async def smooth_and_interpolate_poses(
        self,
        pose_sequence: List[Optional[List[Optional[Dict[str, float]]]]],
        num_expected_landmarks: int = 33,
        smoothing_window_size: int = 5, # Must be odd
        max_interpolation_gap: int = 3 
    ) -> List[Optional[List[Optional[Dict[str, float]]]]]:
        """
        Smooths and interpolates a sequence of pose landmarks.

        Assumes input pose_sequence[frame_idx] is either None or a list of 
        `num_expected_landmarks` items, where each is Optional[Dict[str, float]].
        """
        if not pose_sequence:
            return []

        num_frames = len(pose_sequence)
        if num_frames < 3: # Not enough data for meaningful smoothing/interpolation
            logger.info("Pose sequence too short for smoothing/interpolation, returning as is.")
            return pose_sequence

        # --- Step 1: Restructure data into per-landmark trajectories ---
        # trajectories[landmark_idx][frame_idx] = Optional[Dict[str, float]]
        trajectories: List[List[Optional[Dict[str, float]]]] = [
            [None] * num_frames for _ in range(num_expected_landmarks)
        ]

        for frame_idx, frame_landmarks_list in enumerate(pose_sequence):
            if frame_landmarks_list is not None:
                if len(frame_landmarks_list) != num_expected_landmarks:
                    logger.warning(
                        f"Frame {frame_idx} has {len(frame_landmarks_list)} landmarks, "
                        f"expected {num_expected_landmarks}. Skipping this frame for smoothing/interpolation."
                    )
                    # To handle this, we mark all landmarks for this frame as None in trajectories
                    for lm_idx in range(num_expected_landmarks):
                        trajectories[lm_idx][frame_idx] = None
                    continue 
                for lm_idx in range(num_expected_landmarks):
                    trajectories[lm_idx][frame_idx] = frame_landmarks_list[lm_idx]
        
        processed_trajectories = [[None] * num_frames for _ in range(num_expected_landmarks)]

        # --- Step 2 & 3: Interpolation and Smoothing per landmark trajectory ---
        for lm_idx in range(num_expected_landmarks):
            current_trajectory = trajectories[lm_idx]
            interpolated_trajectory: List[Optional[Dict[str, float]]] = [None] * num_frames
            
            # --- Interpolation Pass ---
            for frame_idx in range(num_frames):
                if current_trajectory[frame_idx] is not None:
                    interpolated_trajectory[frame_idx] = current_trajectory[frame_idx]
                else: # Attempt to interpolate
                    prev_lm_data, next_lm_data = None, None
                    prev_lm_frame_idx, next_lm_frame_idx = -1, -1

                    # Find previous valid landmark
                    for k in range(1, max_interpolation_gap + 1):
                        if frame_idx - k >= 0 and current_trajectory[frame_idx - k] is not None:
                            prev_lm_data = current_trajectory[frame_idx - k]
                            prev_lm_frame_idx = frame_idx - k
                            break
                    
                    # Find next valid landmark
                    for k in range(1, max_interpolation_gap + 1):
                        if frame_idx + k < num_frames and current_trajectory[frame_idx + k] is not None:
                            next_lm_data = current_trajectory[frame_idx + k]
                            next_lm_frame_idx = frame_idx + k
                            break
                    
                    if prev_lm_data and next_lm_data and (next_lm_frame_idx - prev_lm_frame_idx <= max_interpolation_gap +1 ): # Check gap validity
                        # Calculate interpolation ratio
                        ratio = (frame_idx - prev_lm_frame_idx) / (next_lm_frame_idx - prev_lm_frame_idx)
                        interpolated_landmark = self._interpolate_landmark(prev_lm_data, next_lm_data, ratio)
                        if interpolated_landmark:
                            interpolated_trajectory[frame_idx] = interpolated_landmark
                        else: # Fallback if interpolation failed for some reason
                            interpolated_trajectory[frame_idx] = None 
                    else: # Could not interpolate
                        interpolated_trajectory[frame_idx] = None
            
            # --- Smoothing Pass (Moving Average) ---
            # Ensure smoothing_window_size is odd
            if smoothing_window_size % 2 == 0:
                logger.warning("Smoothing window size must be odd. Adjusting to next odd number.")
                smoothing_window_size +=1
            
            half_window = smoothing_window_size // 2
            smoothed_trajectory: List[Optional[Dict[str, float]]] = list(interpolated_trajectory) # Start with interpolated

            for frame_idx in range(num_frames):
                if interpolated_trajectory[frame_idx] is None: # Cannot smooth if no data
                    continue

                window_landmarks = []
                for k_offset in range(-half_window, half_window + 1):
                    win_frame_idx = frame_idx + k_offset
                    if 0 <= win_frame_idx < num_frames and interpolated_trajectory[win_frame_idx] is not None:
                        window_landmarks.append(interpolated_trajectory[win_frame_idx])
                
                if not window_landmarks: # Should not happen if interpolated_trajectory[frame_idx] is not None
                    continue

                # Average coordinates and visibility
                avg_x = sum(lm['x'] for lm in window_landmarks if lm and 'x' in lm) / len(window_landmarks)
                avg_y = sum(lm['y'] for lm in window_landmarks if lm and 'y' in lm) / len(window_landmarks)
                avg_z = sum(lm['z'] for lm in window_landmarks if lm and 'z' in lm) / len(window_landmarks)
                # Keep original visibility or average it too? For now, keep original from interpolated.
                # If averaging visibility: avg_vis = sum(lm['visibility'] for lm in window_landmarks) / len(window_landmarks)
                
                # Create a new dictionary for the smoothed landmark to avoid modifying the original from interpolated_trajectory
                smoothed_trajectory[frame_idx] = {
                    "x": avg_x, "y": avg_y, "z": avg_z,
                    "visibility": interpolated_trajectory[frame_idx]['visibility'] # Keep interpolated visibility
                }
            processed_trajectories[lm_idx] = smoothed_trajectory

        # --- Step 4: Reconstruct the output sequence ---
        final_pose_sequence: List[Optional[List[Optional[Dict[str, float]]]]] = [None] * num_frames
        for frame_idx in range(num_frames):
            # Check if all landmarks for this frame are None after processing
            # This could happen if the original frame was None, or if interpolation/smoothing failed for all landmarks.
            # A frame should be considered "present" if at least one landmark is present.
            
            landmarks_for_this_frame: List[Optional[Dict[str, float]]] = [
                processed_trajectories[lm_idx][frame_idx] for lm_idx in range(num_expected_landmarks)
            ]

            # If the original frame was None (e.g. process_frames_for_pose returned None for it),
            # we should respect that and keep it None, unless interpolation specifically filled it.
            # The current logic populates processed_trajectories even for initially None frames if interpolation occurs.
            # Let's decide: if pose_sequence[frame_idx] was None, the result should also be None,
            # unless we specifically want interpolation to "create" frames.
            # For now, if original pose_sequence[frame_idx] was None, let's ensure final_pose_sequence[frame_idx] is None.
            if pose_sequence[frame_idx] is None:
                 final_pose_sequence[frame_idx] = None
            elif any(lm is not None for lm in landmarks_for_this_frame): # Frame has at least one landmark
                final_pose_sequence[frame_idx] = landmarks_for_this_frame
            else: # Frame had no valid landmarks after processing
                final_pose_sequence[frame_idx] = None # Or an empty list if that's preferred: []
                                                     # Current type hint expects List[Optional[...]] so None for the whole frame is okay.
        
        logger.info(f"AIService: Pose sequence smoothing and interpolation completed for {num_frames} frames.")
        return final_pose_sequence 

    async def analyze_video_file_for_form_check(
        self,
        video_file_path: str,
        exercise_type: ExerciseType # Use the enum type
    ) -> Dict[str, Any]:
        """
        Analyzes a video file for form check, performs frame extraction, 
        pose detection, and form analysis using the best frame.
        This method encapsulates logic previously in FormCheckService.
        """
        logger.info(f"AIService: Analyzing video file {video_file_path} for exercise {exercise_type.value}")

        def _synchronous_frame_processing(path: str, ai_service_instance: 'AIService') -> List[Dict[str, Any]]:
            """Synchronous helper to process video frames using OpenCV and detect poses."""
            cap = cv2.VideoCapture(path)
            if not cap.isOpened():
                logger.error(f"AIService: Could not open video file: {path}")
                raise IOError(f"Could not open video file: {path}")

            frame_results = []
            processed_frames = 0
            # Potentially use a setting for max_frames if different from pose detection default
            max_frames_to_process = settings.AI_MAX_FRAMES_PER_VIDEO_ANALYSIS or 300 

            while cap.isOpened() and processed_frames < max_frames_to_process:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Call the existing synchronous detect_pose method of this AIService instance
                landmarks, confidence = ai_service_instance.detect_pose(frame)
            
                if landmarks:
                    frame_results.append({"landmarks": landmarks, "confidence": confidence, "frame_index": processed_frames})
                processed_frames += 1

            cap.release()
            if processed_frames >= max_frames_to_process:
                logger.warning(f"AIService: Video {path} exceeded max frames ({max_frames_to_process}), processing truncated.")
            elif not frame_results:
                logger.warning(f"AIService: No landmarks detected in any frame for video {path}.")
            return frame_results

        try:
            # Run the synchronous OpenCV frame processing (including pose detection) in a separate thread
            # Pass 'self' (the AIService instance) to the threaded function to call self.detect_pose
            all_frame_landmark_results = await asyncio.to_thread(_synchronous_frame_processing, video_file_path, self)

            if not all_frame_landmark_results:
                logger.warning(f"AIService: No poses detected in video: {video_file_path}. Returning default/error structure.")
                return {
                    "score": 0.0, 
                    "feedback": ["No poses detected in the video. Unable to analyze form."], 
                    "risk_level": "high", 
                    "feedback_structured": [],
                    "model_version": self.model.version if hasattr(self.model, 'version') else "unknown_model_see_rules",
                    "video_hash": hashlib.md5(video_file_path.encode()).hexdigest() # Example hash
                }

            # Find the frame with the highest confidence for detailed analysis
            # (This is a simplification; a real system might analyze a sequence or key phases)
            best_frame_data = max(all_frame_landmark_results, key=lambda x: x["confidence"])
            logger.info(f"AIService: Best frame for analysis from {video_file_path} is index {best_frame_data.get('frame_index')} with confidence {best_frame_data.get('confidence')}")
            
            # Call the existing async form analysis method (model + rules) of this AIService instance
            # analyze_form expects exercise_type as a string value from the enum
            analysis_results = await self.analyze_form(
                landmarks=best_frame_data["landmarks"],
                exercise_type=exercise_type.value 
            )
            
            # Add model version and a video hash (example) to the results
            analysis_results["model_version"] = self.model.version if self.model and hasattr(self.model, 'version') else "rule_based_or_unknown_model"
            
            # Calculate a hash of the video file for potential caching key by the caller
            # This is a basic example; a more robust hash might read file content.
            # However, video_file_path might be a temp path, so content hash is better if video content is available.
            # For simplicity, using path hash. Caller (Celery task) might generate a content hash earlier.
            analysis_results["video_hash"] = hashlib.md5(str(video_file_path).encode() + str(os.path.getmtime(video_file_path)).encode()).hexdigest()

            logger.info(f"AIService: Successfully analyzed video file {video_file_path} for {exercise_type.value}")
            return analysis_results

        except IOError as ioe:
            logger.error(f"AIService: Video IO error during analysis ({video_file_path}): {ioe}", exc_info=True)
            # Return a structured error that the Celery task can use
            return {"score": 0.0, "feedback": [f"Error accessing video file: {ioe}"], "risk_level": "high", "feedback_structured": [], "error_message": f"Video IO Error: {ioe}"}
        except Exception as e:
            logger.error(f"AIService: Unexpected error in analyze_video_file_for_form_check for {video_file_path}: {e}", exc_info=True)
            return {"score": 0.0, "feedback": ["Video analysis failed due to an unexpected internal AI service error."], "risk_level": "high", "feedback_structured": [], "error_message": f"AI Service Error: {e}"} 

    async def process_np_frames_for_pose(
        self, 
        frames: List[np.ndarray], 
        min_pose_confidence_threshold: Optional[float] = None
    ) -> List[Optional[Dict[str, Any]]]:
        """
        Detects poses in a list of NumPy frames.
        This method is designed to be called from async contexts (like Celery tasks)
        and handles running the CPU-bound pose detection in worker threads.

        Args:
            frames: A list of video frames, where each frame is a NumPy array (BGR format).
            min_pose_confidence_threshold: Optional minimum confidence for a pose to be considered valid.
                                           If None, uses default from settings or class.

        Returns:
            A list of pose results. Each element corresponds to a frame:
            - If pose detected above threshold: Dict{"landmarks": List[Dict], "confidence": float}
            - If pose not detected or below threshold: None
        """
        if not frames:
            return []

        # Use the class's configured min_detection_confidence if not overridden
        threshold = min_pose_confidence_threshold if min_pose_confidence_threshold is not None \
                    else settings.AI_MIN_DETECTION_CONFIDENCE # Default to global setting

        all_frame_pose_data: List[Optional[Dict[str, Any]]] = []

        for frame_np in frames:
            if frame_np is None: # Should not happen if Celery task filters, but defensive
                all_frame_pose_data.append(None)
                continue
            
            try:
                # self.detect_pose is synchronous, run it in a thread
                landmarks, confidence = await asyncio.to_thread(self.detect_pose, frame_np)
                
                if landmarks and confidence >= threshold:
                    all_frame_pose_data.append({
                        "landmarks": landmarks,
                        "confidence": confidence
                    })
                else:
                    all_frame_pose_data.append(None) # No pose or below threshold
            except Exception as e:
                logger.error(f"Error processing a frame with self.detect_pose: {e}", exc_info=True)
                all_frame_pose_data.append(None) # Mark as failed for this frame
        
        return all_frame_pose_data 

    STANDARD_ANGLE_DEFINITIONS = {
        "left_knee": (23, 25, 27),    # LHip, LKnee, LAnkle
        "right_knee": (24, 26, 28),   # RHip, RKnee, RAnkle
        "left_hip": (11, 23, 25),     # LShoulder, LHip, LKnee
        "right_hip": (12, 24, 26),    # RShoulder, RHip, RKnee
        "left_elbow": (11, 13, 15),   # LShoulder, LElbow, LWrist
        "right_elbow": (12, 14, 16),  # RShoulder, RElbow, RWrist
        "left_shoulder": (13, 11, 23), # LElbow, LShoulder, LHip
        "right_shoulder": (14, 12, 24) # RElbow, RShoulder, RHip
    }

    async def calculate_angles_for_pose_sequence(
        self,
        pose_sequence: List[Optional[Dict[str, Any]]]
    ) -> List[Optional[Dict[str, float]]]:
        """
        Calculates a standard set of joint angles for each pose in a sequence.

        Args:
            pose_sequence: A list of pose data dictionaries, where each dictionary 
                           is expected to have a "landmarks" key containing a list of 
                           landmark dicts (e.g., output from process_np_frames_for_pose).

        Returns:
            A list of dictionaries, where each dictionary contains the calculated angles 
            for the corresponding frame's pose, or None if no valid pose/landmarks.
        """
        if not pose_sequence:
            return []

        all_frames_angles: List[Optional[Dict[str, float]]] = []

        for frame_pose_data in pose_sequence:
            if frame_pose_data is None or "landmarks" not in frame_pose_data:
                all_frames_angles.append(None)
                continue

            landmarks = frame_pose_data["landmarks"]
            if not isinstance(landmarks, list): # Ensure landmarks is a list
                all_frames_angles.append(None)
                continue
                
            # This part is CPU-bound but likely very fast for a few angle calculations.
            # If performance becomes an issue for many angles/frames, can wrap this inner loop.
            # For now, direct call is fine as _calculate_angle is efficient.
            
            def _calculate_all_angles_for_frame():
                calculated_angles_for_frame: Dict[str, float] = {}
                for angle_name, (p1_idx, p2_idx, p3_idx) in self.STANDARD_ANGLE_DEFINITIONS.items():
                    angle_value = self._calculate_angle(landmarks, p1_idx, p2_idx, p3_idx)
                    if angle_value is not None:
                        calculated_angles_for_frame[angle_name] = angle_value
                return calculated_angles_for_frame if calculated_angles_for_frame else None

            # Running the synchronous helper in a thread
            frame_angles = await asyncio.to_thread(_calculate_all_angles_for_frame)
            all_frames_angles.append(frame_angles)
            
        return all_frames_angles

# END OF AIService class
# Ensure this class definition ends correctly if more methods are outside or this is the true end.
# For example, if there's an AIServiceError class after, make sure it's preserved.
# Based on previous read_file, process_np_frames_for_pose was the last method, this is added after. 