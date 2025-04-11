"""Machine learning model service for advanced form analysis."""
import torch
import numpy as np
from typing import Dict, List, Tuple, Optional
from pathlib import Path
import mediapipe as mp
from app.core.config import settings
from app.core.logging import get_logger
from app.models.enums import ExerciseType, FeedbackSeverity

logger = get_logger(__name__)

class MLModelService:
    def __init__(self):
        """Initialize ML model service."""
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.pose_model = self._load_pose_model()
        self.form_comparison_model = self._load_form_comparison_model()
        self.template_poses = self._load_template_poses()
        
        # Initialize MediaPipe for pose detection
        self.mp_pose = mp.solutions.pose.Pose(
            static_image_mode=False,
            model_complexity=2,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
    def _load_pose_model(self) -> Optional[torch.nn.Module]:
        """Load pose estimation model."""
        try:
            model_path = Path(settings.ML_MODEL_PATH) / "pose_model.pt"
            if model_path.exists():
                model = torch.load(model_path, map_location=self.device)
                model.eval()
                return model
            logger.warning("Pose model not found")
            return None
        except Exception as e:
            logger.error(f"Error loading pose model: {str(e)}")
            return None
            
    def _load_form_comparison_model(self) -> Optional[torch.nn.Module]:
        """Load form comparison model."""
        try:
            model_path = Path(settings.ML_MODEL_PATH) / "form_comparison_model.pt"
            if model_path.exists():
                model = torch.load(model_path, map_location=self.device)
                model.eval()
                return model
            logger.warning("Form comparison model not found")
            return None
        except Exception as e:
            logger.error(f"Error loading form comparison model: {str(e)}")
            return None
            
    def _load_template_poses(self) -> Dict[str, np.ndarray]:
        """Load template poses for each exercise type."""
        templates = {}
        template_dir = Path(settings.ML_MODEL_PATH) / "templates"
        if template_dir.exists():
            for exercise_type in ExerciseType:
                template_path = template_dir / f"{exercise_type.value}_template.npy"
                if template_path.exists():
                    templates[exercise_type.value] = np.load(template_path)
        return templates
        
    async def analyze_form(
        self,
        video_frames: List[np.ndarray],
        exercise_type: str
    ) -> Dict[str, any]:
        """Analyze exercise form using ML models.
        
        Args:
            video_frames: List of video frames as numpy arrays
            exercise_type: Type of exercise being performed
            
        Returns:
            Dictionary containing analysis results
        """
        try:
            # Extract pose landmarks from frames
            landmarks = []
            for frame in video_frames:
                results = self.mp_pose.process(frame)
                if results.pose_landmarks:
                    landmarks.append(self._convert_landmarks_to_array(results.pose_landmarks))
                    
            if not landmarks:
                return {
                    "score": 0.0,
                    "feedback": ["No pose detected in video"],
                    "risk_level": "high",
                    "comparison": None
                }
                
            # Convert landmarks to tensor
            landmarks_tensor = torch.tensor(landmarks, dtype=torch.float32).to(self.device)
            
            # Compare with template if available
            comparison_score = None
            if exercise_type in self.template_poses and self.form_comparison_model:
                template = torch.tensor(
                    self.template_poses[exercise_type],
                    dtype=torch.float32
                ).to(self.device)
                
                with torch.no_grad():
                    comparison_score = self.form_comparison_model(landmarks_tensor, template)
                    
            # Analyze form using pose model
            if self.pose_model:
                with torch.no_grad():
                    form_score, joint_angles, velocity = self.pose_model(landmarks_tensor)
                    
                feedback = self._generate_feedback(
                    joint_angles.cpu().numpy(),
                    velocity.cpu().numpy(),
                    exercise_type
                )
                
                return {
                    "score": float(form_score),
                    "feedback": feedback,
                    "risk_level": self._calculate_risk_level(form_score),
                    "comparison": float(comparison_score) if comparison_score is not None else None,
                    "joint_angles": joint_angles.cpu().numpy().tolist(),
                    "velocity": velocity.cpu().numpy().tolist()
                }
                
            # Fallback to basic analysis if no model
            return self._basic_form_analysis(landmarks, exercise_type)
            
        except Exception as e:
            logger.error(f"Error in form analysis: {str(e)}")
            return {
                "score": 0.0,
                "feedback": ["Error analyzing form"],
                "risk_level": "high",
                "comparison": None
            }
            
    def _convert_landmarks_to_array(self, landmarks) -> np.ndarray:
        """Convert MediaPipe landmarks to numpy array."""
        return np.array([[lm.x, lm.y, lm.z] for lm in landmarks.landmark])
        
    def _generate_feedback(
        self,
        joint_angles: np.ndarray,
        velocity: np.ndarray,
        exercise_type: str
    ) -> List[str]:
        """Generate feedback based on joint angles and movement velocity."""
        feedback = []
        
        # Get exercise-specific angle thresholds
        thresholds = self._get_angle_thresholds(exercise_type)
        
        # Check joint angles
        for joint, (min_angle, max_angle) in thresholds.items():
            angle = joint_angles[joint]
            if angle < min_angle:
                feedback.append(f"Increase {joint} angle")
            elif angle > max_angle:
                feedback.append(f"Decrease {joint} angle")
                
        # Check movement velocity
        avg_velocity = np.mean(velocity)
        if avg_velocity > 2.0:
            feedback.append("Slow down the movement for better control")
        elif avg_velocity < 0.5:
            feedback.append("Speed up the movement slightly")
            
        return feedback
        
    def _calculate_risk_level(self, score: float) -> str:
        """Calculate risk level based on form score."""
        if score >= 0.8:
            return "low"
        elif score >= 0.6:
            return "medium"
        return "high"
        
    def _get_angle_thresholds(self, exercise_type: str) -> Dict[str, Tuple[float, float]]:
        """Get joint angle thresholds for specific exercise type."""
        # Example thresholds, should be customized per exercise
        return {
            "knee": (0, 90),
            "hip": (0, 100),
            "spine": (-20, 20)
        }
        
    def _basic_form_analysis(
        self,
        landmarks: List[np.ndarray],
        exercise_type: str
    ) -> Dict[str, any]:
        """Basic form analysis when ML models are not available."""
        try:
            # Calculate basic metrics
            stability = self._calculate_stability(landmarks)
            symmetry = self._calculate_symmetry(landmarks)
            smoothness = self._calculate_smoothness(landmarks)
            
            # Generate score
            score = np.mean([stability, symmetry, smoothness])
            
            # Generate feedback
            feedback = []
            if stability < 0.7:
                feedback.append("Maintain more stable posture")
            if symmetry < 0.7:
                feedback.append("Keep movements more symmetrical")
            if smoothness < 0.7:
                feedback.append("Make movements smoother and more controlled")
                
            return {
                "score": float(score),
                "feedback": feedback,
                "risk_level": self._calculate_risk_level(score),
                "comparison": None
            }
            
        except Exception as e:
            logger.error(f"Error in basic form analysis: {str(e)}")
            return {
                "score": 0.0,
                "feedback": ["Error in form analysis"],
                "risk_level": "high",
                "comparison": None
            }
            
    def _calculate_stability(self, landmarks: List[np.ndarray]) -> float:
        """Calculate stability score from landmarks."""
        try:
            # Calculate variance of key joint positions
            joint_variance = np.var(landmarks, axis=0)
            return float(1.0 - np.mean(joint_variance))
        except:
            return 0.0
            
    def _calculate_symmetry(self, landmarks: List[np.ndarray]) -> float:
        """Calculate symmetry score from landmarks."""
        try:
            # Compare left and right side movements
            left_side = landmarks[:, :len(landmarks)//2]
            right_side = landmarks[:, len(landmarks)//2:]
            symmetry = 1.0 - np.mean(np.abs(left_side - np.fliplr(right_side)))
            return float(symmetry)
        except:
            return 0.0
            
    def _calculate_smoothness(self, landmarks: List[np.ndarray]) -> float:
        """Calculate movement smoothness from landmarks."""
        try:
            # Calculate jerk (rate of change of acceleration)
            velocity = np.diff(landmarks, axis=0)
            acceleration = np.diff(velocity, axis=0)
            jerk = np.diff(acceleration, axis=0)
            smoothness = 1.0 - np.mean(np.abs(jerk))
            return float(smoothness)
        except:
            return 0.0 