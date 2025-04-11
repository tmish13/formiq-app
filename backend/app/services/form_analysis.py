import os
import uuid
from typing import List, Optional, Dict, Any
import numpy as np
import cv2
from fastapi import UploadFile
from ..models.form_analysis import FormAnalysisRequest, FormAnalysisResult
from ..core.database import get_db
from ..core.cache import redis_cache
from ..core.storage import save_video, get_video_url
from ..services.pose_analysis import PoseAnalysisService
from ..services.ml_model_service import MLModelService

class FormAnalysisService:
    def __init__(self):
        self.pose_service = PoseAnalysisService()
        self.ml_service = MLModelService()
        self.db = next(get_db())
        self.cache = redis_cache

    async def analyze_form(self, request: FormAnalysisRequest) -> FormAnalysisResult:
        try:
            # Save video to storage
            video_id = str(uuid.uuid4())
            video_path = await save_video(request.video, video_id)
            video_url = get_video_url(video_id)

            # Check cache first
            cache_key = f"form_analysis:{video_id}"
            cached_result = await self.cache.get(cache_key)
            if cached_result:
                return FormAnalysisResult(**cached_result)

            # Extract video frames
            frames = self._extract_frames(video_path)
            if not frames:
                raise ValueError("No frames could be extracted from video")

            # Get ML analysis
            ml_analysis = await self.ml_service.analyze_form(
                frames,
                request.exercise_type or "general"
            )

            # Get pose analysis
            pose_analysis = await self.pose_service.analyze_pose(
                video_path=video_path,
                keypoints=request.keypoints
            )

            # Combine analyses and calculate metrics
            metrics = self._calculate_metrics(
                pose_analysis.keypoints,
                ml_analysis.get("joint_angles", []),
                ml_analysis.get("velocity", [])
            )
            
            # Generate comprehensive feedback
            feedback, suggestions = self._generate_feedback(
                metrics,
                ml_analysis.get("feedback", []),
                ml_analysis.get("risk_level", "medium")
            )

            # Create result
            result = FormAnalysisResult(
                id=video_id,
                exercise_type=request.exercise_type,
                confidence=float(ml_analysis.get("score", 0.0)),
                keypoints=pose_analysis.keypoints,
                metrics=metrics,
                feedback=feedback,
                suggestions=suggestions,
                risk_level=ml_analysis.get("risk_level", "medium"),
                comparison_score=ml_analysis.get("comparison"),
                joint_analysis=ml_analysis.get("joint_angles"),
                movement_analysis=ml_analysis.get("velocity")
            )

            # Cache the result
            await self.cache.set(cache_key, result.dict(), expire=3600)

            # Save to database
            await self.save_analysis(result, request.user_id)

            return result

        except Exception as e:
            # Clean up video file if error occurs
            if video_path and os.path.exists(video_path):
                os.remove(video_path)
            raise e

    def _extract_frames(self, video_path: str, max_frames: int = 300) -> List[np.ndarray]:
        """Extract frames from video for analysis."""
        frames = []
        try:
            cap = cv2.VideoCapture(video_path)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            frame_interval = max(1, total_frames // max_frames)
            
            frame_count = 0
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                    
                if frame_count % frame_interval == 0:
                    # Convert BGR to RGB
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    frames.append(frame)
                    
                frame_count += 1
                
            cap.release()
        except Exception as e:
            print(f"Error extracting frames: {str(e)}")
            
        return frames

    def _calculate_metrics(
        self,
        keypoints: List[Dict[str, Any]],
        joint_angles: List[float],
        velocity: List[float]
    ) -> Dict[str, float]:
        """Calculate comprehensive form metrics."""
        try:
            # Basic metrics from keypoints
            alignment_scores = []
            stability_scores = []
            symmetry_scores = []
            consistency_scores = []

            for frame in keypoints:
                if 'left_shoulder' in frame and 'left_hip' in frame and 'left_ankle' in frame:
                    # Calculate vertical alignment
                    left_points = [frame['left_shoulder'], frame['left_hip'], frame['left_ankle']]
                    left_x_coords = [p['x'] for p in left_points]
                    left_alignment = 1 - np.std(left_x_coords) / 100
                    alignment_scores.append(left_alignment)

                # Calculate stability
                if all(joint in frame for joint in ['left_shoulder', 'right_shoulder', 'left_hip', 'right_hip']):
                    positions = [(frame[joint]['x'], frame[joint]['y']) 
                               for joint in ['left_shoulder', 'right_shoulder', 'left_hip', 'right_hip']]
                    stability = 1 - np.std([x for x, y in positions]) / 100
                    stability_scores.append(stability)

                # Calculate symmetry
                if all(joint in frame for joint in ['left_shoulder', 'right_shoulder', 'left_hip', 'right_hip']):
                    left_side = [frame['left_shoulder'], frame['left_hip']]
                    right_side = [frame['right_shoulder'], frame['right_hip']]
                    left_coords = [(p['x'], p['y']) for p in left_side]
                    right_coords = [(p['x'], p['y']) for p in right_side]
                    symmetry = 1 - abs(np.mean([x for x, y in left_coords]) - np.mean([x for x, y in right_coords])) / 100
                    symmetry_scores.append(symmetry)

            # Calculate consistency from joint angles and velocity
            if joint_angles and velocity:
                angle_consistency = 1 - np.std(joint_angles) / 90  # Normalize by typical range
                velocity_consistency = 1 - np.std(velocity) / 2  # Normalize by typical range
                consistency_scores = [angle_consistency, velocity_consistency]

            return {
                'alignment': float(np.mean(alignment_scores)) if alignment_scores else 0.0,
                'stability': float(np.mean(stability_scores)) if stability_scores else 0.0,
                'symmetry': float(np.mean(symmetry_scores)) if symmetry_scores else 0.0,
                'consistency': float(np.mean(consistency_scores)) if consistency_scores else 0.0,
                'joint_accuracy': float(np.mean(joint_angles)) if joint_angles else 0.0,
                'movement_quality': float(np.mean(velocity)) if velocity else 0.0
            }

        except Exception as e:
            print(f"Error calculating metrics: {str(e)}")
            return {
                'alignment': 0.0,
                'stability': 0.0,
                'symmetry': 0.0,
                'consistency': 0.0,
                'joint_accuracy': 0.0,
                'movement_quality': 0.0
            }

    def _generate_feedback(
        self,
        metrics: Dict[str, float],
        ml_feedback: List[str],
        risk_level: str
    ) -> tuple[List[str], List[str]]:
        """Generate comprehensive feedback and suggestions."""
        feedback = []
        suggestions = []

        # Add ML model feedback
        feedback.extend(ml_feedback)

        # Alignment feedback
        if metrics['alignment'] < 0.7:
            feedback.append("Your form shows misalignment in key positions")
            suggestions.append("Focus on maintaining a straight line from shoulders through hips to ankles")

        # Stability feedback
        if metrics['stability'] < 0.7:
            feedback.append("There's some instability in your movement")
            suggestions.append("Try to maintain more control throughout the exercise")

        # Symmetry feedback
        if metrics['symmetry'] < 0.7:
            feedback.append("Your movement shows some asymmetry between left and right sides")
            suggestions.append("Pay attention to equal engagement of both sides of your body")

        # Consistency feedback
        if metrics['consistency'] < 0.7:
            feedback.append("Your movement speed and control could be more consistent")
            suggestions.append("Try to maintain a steady, controlled pace throughout the exercise")

        # Joint accuracy feedback
        if metrics['joint_accuracy'] < 0.7:
            feedback.append("Some joint angles need adjustment")
            suggestions.append("Focus on proper joint positioning and range of motion")

        # Movement quality feedback
        if metrics['movement_quality'] < 0.7:
            feedback.append("Movement quality could be improved")
            suggestions.append("Practice the movement pattern with lighter weight or no weight")

        # Risk-based suggestions
        if risk_level == "high":
            suggestions.append("Consider working with a trainer to improve form")
            suggestions.append("Reduce weight until proper form can be maintained")
        elif risk_level == "medium":
            suggestions.append("Focus on technique before increasing intensity")

        # Add general feedback if performance is good
        if all(v >= 0.7 for v in metrics.values()):
            feedback.append("Overall form looks good!")
            suggestions.append("Keep maintaining this level of control and form")

        return feedback, suggestions

    async def get_user_history(self, user_id: str) -> List[FormAnalysisResult]:
        """Get analysis history for a user."""
        cache_key = f"user_history:{user_id}"
        history = await self.cache.get(cache_key)
        return [FormAnalysisResult(**item) for item in history] if history else []

    async def get_analysis(self, analysis_id: str, user_id: str) -> Optional[FormAnalysisResult]:
        """Get a specific analysis result."""
        cache_key = f"form_analysis:{analysis_id}"
        result = await self.cache.get(cache_key)
        return FormAnalysisResult(**result) if result else None

    async def save_analysis(self, result: FormAnalysisResult, user_id: str) -> FormAnalysisResult:
        """Save analysis result to cache and database."""
        # Save to cache
        cache_key = f"form_analysis:{result.id}"
        await self.cache.set(cache_key, result.dict(), expire=3600)

        # Update user history in cache
        history_key = f"user_history:{user_id}"
        history = await self.cache.get(history_key) or []
        history.append(result.dict())
        await self.cache.set(history_key, history, expire=86400)  # Cache for 24 hours

        return result 