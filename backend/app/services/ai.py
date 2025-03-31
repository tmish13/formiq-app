"""AI service for exercise form analysis."""
from enum import Enum
import numpy as np
import torch
import cv2
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import json
import mediapipe as mp
import asyncio
from concurrent.futures import ThreadPoolExecutor
from app.core.exceptions import ServiceError
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

class AIServiceError(ServiceError):
    """Exception raised for AI service related errors."""
    pass

class ExerciseType(str, Enum):
    """Supported exercise types."""
    SQUAT = "squat"
    DEADLIFT = "deadlift"
    BENCH_PRESS = "bench_press"

class AIService:
    """Service for AI-powered exercise form analysis."""
    
    def __init__(self):
        """Initialize AI models and pose estimator."""
        try:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self.models = self._load_models()
            self.pose_estimator = mp.solutions.pose.Pose(
                static_image_mode=False,
                model_complexity=2,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5
            )
            self.executor = ThreadPoolExecutor(max_workers=4)
            logger.info("AI Service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize AI Service: {str(e)}")
            raise AIServiceError(f"AI Service initialization failed: {str(e)}")

    def _load_models(self) -> Dict[ExerciseType, torch.nn.Module]:
        """Load exercise-specific models."""
        try:
            models = {}
            model_dir = Path(settings.MODEL_DIR)
            for exercise in ExerciseType:
                model_path = model_dir / f"{exercise.value}_model.pt"
                if model_path.exists():
                    model = torch.load(model_path, map_location=self.device)
                    model.eval()
                    models[exercise] = model
                else:
                    logger.warning(f"Model not found for {exercise.value}")
            return models
        except Exception as e:
            logger.error(f"Failed to load models: {str(e)}")
            raise AIServiceError(f"Model loading failed: {str(e)}")

    async def analyze_form(self, video: List[np.ndarray], exercise_type: ExerciseType) -> Dict[str, Any]:
        """
        Analyze exercise form in a video asynchronously.
        
        Args:
            video: List of video frames as numpy arrays
            exercise_type: Type of exercise being performed
            
        Returns:
            Dict containing analysis results including score and feedback
        """
        try:
            # Validate inputs
            if not isinstance(exercise_type, ExerciseType):
                raise AIServiceError(f"Invalid exercise type: {exercise_type}")
            await self._validate_video_duration(video)
            
            # Process video in thread pool
            frames = await asyncio.get_event_loop().run_in_executor(
                self.executor, self._extract_frames, video
            )
            
            # Extract landmarks in parallel
            landmarks_tasks = [
                asyncio.get_event_loop().run_in_executor(
                    self.executor, self._extract_pose_landmarks, frame
                )
                for frame in frames
            ]
            landmarks_sequence = await asyncio.gather(*landmarks_tasks)
            
            # Validate landmarks
            for landmarks in landmarks_sequence:
                if not self._validate_landmarks_confidence(landmarks):
                    raise AIServiceError("Low confidence in pose detection")
            
            # Analyze pose sequence
            analysis = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self._analyze_pose_sequence,
                landmarks_sequence,
                exercise_type
            )
            
            # Generate feedback
            feedback = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self._generate_feedback,
                analysis,
                exercise_type
            )
            
            # Detect exercise phases
            phases = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self._detect_exercise_phases,
                landmarks_sequence,
                exercise_type
            )
            
            return {
                "score": analysis["score"],
                "feedback": feedback,
                "keypoints": analysis["issues"],
                "suggestions": self._generate_suggestions(analysis["issues"], exercise_type),
                "phases": phases
            }
            
        except Exception as e:
            logger.error(f"Form analysis failed: {str(e)}")
            raise AIServiceError(f"Form analysis failed: {str(e)}")

    def _extract_frames(self, video: List[np.ndarray]) -> List[np.ndarray]:
        """Extract frames from video at regular intervals."""
        try:
            return [frame for frame in video]
        except Exception as e:
            logger.error(f"Frame extraction failed: {str(e)}")
            raise AIServiceError(f"Frame extraction failed: {str(e)}")

    def _preprocess_video(self, video: List[np.ndarray]) -> torch.Tensor:
        """Preprocess video frames for model input."""
        try:
            processed_frames = []
            for frame in video:
                # Resize and normalize
                frame = cv2.resize(frame, (224, 224))
                frame = frame / 255.0
                frame = np.transpose(frame, (2, 0, 1))
                processed_frames.append(frame)
            
            return torch.tensor(processed_frames, dtype=torch.float32, device=self.device)
        except Exception as e:
            logger.error(f"Video preprocessing failed: {str(e)}")
            raise AIServiceError(f"Video preprocessing failed: {str(e)}")

    def _extract_pose_landmarks(self, frame: np.ndarray) -> List[Dict[str, float]]:
        """Extract pose landmarks from a single frame."""
        try:
            results = self.pose_estimator.process(frame)
            if not results.pose_landmarks:
                raise AIServiceError("No pose detected in frame")
            
            landmarks = []
            for landmark in results.pose_landmarks.landmark:
                landmarks.append({
                    "x": landmark.x,
                    "y": landmark.y,
                    "z": landmark.z,
                    "visibility": landmark.visibility
                })
            return landmarks
        except Exception as e:
            logger.error(f"Pose landmark extraction failed: {str(e)}")
            raise AIServiceError(f"Pose landmark extraction failed: {str(e)}")

    def _analyze_pose_sequence(
        self,
        landmarks_sequence: List[List[Dict[str, float]]],
        exercise_type: ExerciseType
    ) -> Dict[str, Any]:
        """Analyze sequence of pose landmarks."""
        try:
            model = self.models.get(exercise_type)
            if not model:
                raise AIServiceError(f"No model available for {exercise_type}")
            
            # Convert landmarks to model input format
            input_tensor = self._landmarks_to_tensor(landmarks_sequence)
            
            # Get model predictions
            with torch.no_grad():
                predictions = model(input_tensor)
            
            # Process predictions
            score = float(torch.mean(predictions).item()) * 10  # Scale to 0-10
            issues = self._detect_form_issues(predictions, landmarks_sequence, exercise_type)
            
            return {
                "score": score,
                "issues": issues
            }
        except Exception as e:
            logger.error(f"Pose sequence analysis failed: {str(e)}")
            raise AIServiceError(f"Pose sequence analysis failed: {str(e)}")

    def _generate_feedback(self, analysis: Dict[str, Any], exercise_type: ExerciseType) -> str:
        """Generate human-readable feedback from analysis results."""
        try:
            feedback_parts = []
            
            # Overall score feedback
            score = analysis["score"]
            if score >= 8:
                feedback_parts.append("Your form is excellent!")
            elif score >= 6:
                feedback_parts.append("Your form is good, but there's room for improvement.")
            else:
                feedback_parts.append("Your form needs significant improvement.")
            
            # Issue-specific feedback
            for issue in analysis["issues"]:
                feedback = self._get_issue_feedback(issue, exercise_type)
                if feedback:
                    feedback_parts.append(feedback)
            
            return " ".join(feedback_parts)
        except Exception as e:
            logger.error(f"Feedback generation failed: {str(e)}")
            raise AIServiceError(f"Feedback generation failed: {str(e)}")

    def _detect_exercise_phases(
        self,
        landmarks_sequence: List[List[Dict[str, float]]],
        exercise_type: ExerciseType
    ) -> List[Dict[str, int]]:
        """Detect different phases of the exercise."""
        try:
            phases = []
            # Implementation depends on exercise type
            if exercise_type == ExerciseType.SQUAT:
                phases = self._detect_squat_phases(landmarks_sequence)
            elif exercise_type == ExerciseType.DEADLIFT:
                phases = self._detect_deadlift_phases(landmarks_sequence)
            return phases
        except Exception as e:
            logger.error(f"Phase detection failed: {str(e)}")
            raise AIServiceError(f"Phase detection failed: {str(e)}")

    def _calculate_joint_angles(
        self,
        landmarks: List[Dict[str, float]],
        joint1: int,
        joint2: int,
        joint3: int
    ) -> float:
        """Calculate angle between three joints."""
        try:
            # Convert landmarks to vectors
            v1 = np.array([
                landmarks[joint1]["x"] - landmarks[joint2]["x"],
                landmarks[joint1]["y"] - landmarks[joint2]["y"]
            ])
            v2 = np.array([
                landmarks[joint3]["x"] - landmarks[joint2]["x"],
                landmarks[joint3]["y"] - landmarks[joint2]["y"]
            ])
            
            # Calculate angle
            cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
            angle = np.arccos(np.clip(cos_angle, -1.0, 1.0))
            return float(np.degrees(angle))
        except Exception as e:
            logger.error(f"Joint angle calculation failed: {str(e)}")
            raise AIServiceError(f"Joint angle calculation failed: {str(e)}")

    async def _validate_video_duration(self, video: List[np.ndarray]) -> None:
        """Validate video duration."""
        try:
            duration = len(video) / settings.FPS
            if duration > settings.MAX_VIDEO_DURATION:
                raise AIServiceError(f"Video duration exceeds maximum limit of {settings.MAX_VIDEO_DURATION} seconds")
        except Exception as e:
            logger.error(f"Video duration validation failed: {str(e)}")
            raise AIServiceError(f"Video duration validation failed: {str(e)}")

    def _validate_landmarks_confidence(self, landmarks: List[Dict[str, float]]) -> bool:
        """Check if pose landmarks have sufficient confidence."""
        return all(landmark["visibility"] > 0.5 for landmark in landmarks)

    def _landmarks_to_tensor(self, landmarks_sequence: List[List[Dict[str, float]]]) -> torch.Tensor:
        """Convert landmarks sequence to model input tensor."""
        try:
            # Flatten landmarks into feature vectors
            features = []
            for landmarks in landmarks_sequence:
                frame_features = []
                for landmark in landmarks:
                    frame_features.extend([landmark["x"], landmark["y"], landmark["z"]])
                features.append(frame_features)
            
            return torch.tensor(features, dtype=torch.float32, device=self.device)
        except Exception as e:
            logger.error(f"Landmark conversion failed: {str(e)}")
            raise AIServiceError(f"Landmark conversion failed: {str(e)}")

    def _detect_form_issues(
        self,
        predictions: torch.Tensor,
        landmarks_sequence: List[List[Dict[str, float]]],
        exercise_type: ExerciseType
    ) -> List[Dict[str, Any]]:
        """Detect specific form issues based on model predictions and landmarks."""
        try:
            issues = []
            thresholds = self._get_exercise_specific_thresholds(exercise_type)
            
            # Analyze each frame
            for frame_idx, (pred, landmarks) in enumerate(zip(predictions, landmarks_sequence)):
                frame_issues = self._check_frame_issues(
                    frame_idx,
                    pred,
                    landmarks,
                    exercise_type,
                    thresholds
                )
                issues.extend(frame_issues)
            
            return issues
        except Exception as e:
            logger.error(f"Form issue detection failed: {str(e)}")
            raise AIServiceError(f"Form issue detection failed: {str(e)}")

    def _get_exercise_specific_thresholds(self, exercise_type: ExerciseType) -> Dict[str, float]:
        """Get threshold values for form checks based on exercise type."""
        if exercise_type == ExerciseType.SQUAT:
            return {
                "knee_valgus": 0.7,
                "back_rounding": 0.8,
                "depth": 0.6
            }
        elif exercise_type == ExerciseType.DEADLIFT:
            return {
                "back_rounding": 0.8,
                "bar_path": 0.7,
                "hip_height": 0.6
            }
        return {}

    def _generate_suggestions(self, issues: List[Dict[str, Any]], exercise_type: ExerciseType) -> List[str]:
        """Generate improvement suggestions based on detected issues."""
        suggestions = []
        for issue in issues:
            if issue["severity"] == "high":
                suggestions.append(f"Focus on {issue['description']} to improve your form.")
            elif issue["severity"] == "medium":
                suggestions.append(f"Consider adjusting {issue['description']} for better form.")
        return suggestions

    def _get_issue_feedback(self, issue: Dict[str, Any], exercise_type: ExerciseType) -> str:
        """Generate human-readable feedback for a specific issue."""
        # Implementation of this method depends on the specific issue
        # This is a placeholder and should be implemented based on your requirements
        return "" 