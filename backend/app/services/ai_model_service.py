"""AI model service for pose detection and form analysis."""
import mediapipe as mp
import numpy as np
import cv2
from typing import Dict, List, Any, Tuple
import torch
from pathlib import Path

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

class AIModelService:
    def __init__(self):
        """Initialize the AI model service."""
        self.pose = mp.solutions.pose.Pose(
            static_image_mode=False,
            model_complexity=2,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = self._load_form_analysis_model()
        
    def _load_form_analysis_model(self) -> Any:
        """Load the form analysis model."""
        try:
            model_path = Path(settings.AI_MODEL_PATH) / "form_analysis_model.pt"
            if model_path.exists():
                return torch.load(model_path, map_location=self.device)
            logger.warning("Form analysis model not found, using default rules")
            return None
        except Exception as e:
            logger.error(f"Error loading form analysis model: {str(e)}")
            return None
            
    def detect_pose(self, frame: np.ndarray) -> Tuple[List[Dict[str, float]], float]:
        """Detect pose landmarks in a frame."""
        try:
            # Convert BGR to RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Process the frame
            results = self.pose.process(frame_rgb)
            
            if not results.pose_landmarks:
                return [], 0.0
                
            # Extract landmarks
            landmarks = []
            for landmark in results.pose_landmarks.landmark:
                landmarks.append({
                    "x": landmark.x,
                    "y": landmark.y,
                    "z": landmark.z,
                    "visibility": landmark.visibility
                })
                
            # Calculate confidence score
            confidence = np.mean([l["visibility"] for l in landmarks])
            
            return landmarks, confidence
            
        except Exception as e:
            logger.error(f"Error detecting pose: {str(e)}")
            return [], 0.0
            
    def analyze_form(self, landmarks: List[Dict[str, float]], exercise_type: str) -> Dict[str, Any]:
        """Analyze exercise form based on pose landmarks."""
        try:
            if not landmarks:
                return {
                    "score": 0.0,
                    "feedback": ["No pose detected in the video"],
                    "risk_level": "high"
                }
                
            # Convert landmarks to tensor if model is available
            if self.model:
                landmarks_tensor = torch.tensor([
                    [l["x"], l["y"], l["z"]] for l in landmarks
                ], dtype=torch.float32).to(self.device)
                
                with torch.no_grad():
                    score, feedback = self.model(landmarks_tensor)
                    
                return {
                    "score": float(score),
                    "feedback": feedback,
                    "risk_level": "low" if float(score) > 0.7 else "medium"
                }
                
            # Fallback to rule-based analysis
            return self._analyze_form_rules(landmarks, exercise_type)
            
        except Exception as e:
            logger.error(f"Error analyzing form: {str(e)}")
            return {
                "score": 0.0,
                "feedback": ["Error analyzing form"],
                "risk_level": "high"
            }
            
    def _analyze_form_rules(self, landmarks: List[Dict[str, float]], exercise_type: str) -> Dict[str, Any]:
        """Rule-based form analysis when model is not available."""
        feedback = []
        score = 1.0
        
        # Basic posture analysis
        if landmarks:
            # Check spine alignment
            spine_angle = self._calculate_spine_angle(landmarks)
            if spine_angle > 20:
                feedback.append("Keep your spine straight")
                score *= 0.8
                
            # Check knee alignment
            knee_angle = self._calculate_knee_angle(landmarks)
            if knee_angle < 90:
                feedback.append("Don't let your knees go past your toes")
                score *= 0.9
                
        return {
            "score": score,
            "feedback": feedback,
            "risk_level": "low" if score > 0.7 else "medium"
        }
        
    def _calculate_spine_angle(self, landmarks: List[Dict[str, float]]) -> float:
        """Calculate the angle of the spine relative to vertical."""
        try:
            # Get relevant landmarks
            hip = np.array([landmarks[23]["x"], landmarks[23]["y"]])
            shoulder = np.array([landmarks[11]["x"], landmarks[11]["y"]])
            
            # Calculate angle
            vector = shoulder - hip
            angle = np.degrees(np.arctan2(vector[0], vector[1]))
            
            return abs(angle)
        except Exception:
            return 0.0
            
    def _calculate_knee_angle(self, landmarks: List[Dict[str, float]]) -> float:
        """Calculate the angle of the knee."""
        try:
            # Get relevant landmarks
            hip = np.array([landmarks[23]["x"], landmarks[23]["y"]])
            knee = np.array([landmarks[25]["x"], landmarks[25]["y"]])
            ankle = np.array([landmarks[27]["x"], landmarks[27]["y"]])
            
            # Calculate vectors
            vector1 = hip - knee
            vector2 = ankle - knee
            
            # Calculate angle
            angle = np.degrees(
                np.arccos(
                    np.dot(vector1, vector2) / 
                    (np.linalg.norm(vector1) * np.linalg.norm(vector2))
                )
            )
            
            return angle
        except Exception:
            return 0.0 