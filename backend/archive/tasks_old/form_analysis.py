"""Form analysis Celery tasks."""
import os
import tempfile
import logging
import json
from typing import Dict, Any, List, Optional, Tuple
from uuid import UUID
import asyncio

import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy.future import select

from app.core.celery_app import celery_app
from app.db.session import get_db_session
from app.models.video import Video, VideoStatus
from app.models.user import User
from app.services.storage import StorageService
from app.services.email_service import EmailService
from app.core.logging import get_logger
from app.core.config import settings
from app.core.utils.keypoint_utils import calculate_joint_angles
from app.core.analysis.form_analyzer import FormAnalyzer

logger = get_logger(__name__)

class FormAnalyzer:
    """Exercise form analysis class."""
    
    def __init__(self, exercise_type: str = "generic"):
        """
        Initialize form analyzer.
        
        Args:
            exercise_type: Type of exercise (e.g., squat, pushup)
        """
        self.exercise_type = exercise_type
        self.exercise_config = self._get_exercise_config()
        
    def _get_exercise_config(self) -> Dict[str, Any]:
        """
        Get exercise-specific configuration.
        
        Returns:
            Dict containing exercise configuration
        """
        # Get from settings or use defaults
        if self.exercise_type in settings.EXERCISE_CONFIGS:
            return settings.EXERCISE_CONFIGS[self.exercise_type]
            
        # Default config for generic exercise
        return {
            "key_points": ["hip", "knee", "ankle", "shoulder", "elbow", "wrist"],
            "target_angles": {},
            "angle_tolerances": {},
            "phases": ["preparation", "execution", "recovery"]
        }
        
    def analyze_form(self, pose_sequence: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze exercise form from a sequence of poses.
        
        Args:
            pose_sequence: List of pose data dictionaries
            
        Returns:
            Dict containing analysis results
        """
        if not pose_sequence:
            return {
                "score": 0.0,
                "feedback": [],
                "issues": [],
                "rep_count": 0
            }
            
        # Calculate joint angles for each frame
        frames_with_angles = []
        for pose in pose_sequence:
            # Get keypoints
            keypoints = pose["keypoints"]
            
            # Calculate joint angles
            angles = self._calculate_angles(keypoints)
            
            frames_with_angles.append({
                "frame_number": pose["frame_number"],
                "timestamp": pose["timestamp"],
                "keypoints": keypoints,
                "angles": angles,
                "score": pose["score"]
            })
            
        # Detect exercise phases
        phases = self._detect_phases(frames_with_angles)
        
        # Count repetitions
        rep_count = self._count_repetitions(phases)
        
        # Check form against target angles
        issues = self._check_form(frames_with_angles, phases)
        
        # Generate feedback
        feedback = self._generate_feedback(issues, rep_count)
        
        # Calculate overall score
        score = self._calculate_score(issues, rep_count)
        
        return {
            "score": score,
            "feedback": feedback,
            "issues": issues,
            "rep_count": rep_count,
            "phases": phases
        }
        
    def _calculate_angles(self, keypoints: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Calculate joint angles from keypoints.
        
        Args:
            keypoints: List of pose keypoints
            
        Returns:
            Dict of joint name to angle value
        """
        # Extract keypoints as dictionary by name
        keypoints_dict = {kp["name"]: (kp["x"], kp["y"]) for kp in keypoints if kp["visibility"] > 0.5}
        
        # Calculate joint angles
        angles = {}
        
        # Calculate hip angle (between shoulder, hip, and knee)
        if all(k in keypoints_dict for k in ["left_shoulder", "left_hip", "left_knee"]):
            angles["left_hip"] = self._angle_between_points(
                keypoints_dict["left_shoulder"],
                keypoints_dict["left_hip"],
                keypoints_dict["left_knee"]
            )
            
        if all(k in keypoints_dict for k in ["right_shoulder", "right_hip", "right_knee"]):
            angles["right_hip"] = self._angle_between_points(
                keypoints_dict["right_shoulder"],
                keypoints_dict["right_hip"],
                keypoints_dict["right_knee"]
            )
            
        # Calculate knee angle (between hip, knee, and ankle)
        if all(k in keypoints_dict for k in ["left_hip", "left_knee", "left_ankle"]):
            angles["left_knee"] = self._angle_between_points(
                keypoints_dict["left_hip"],
                keypoints_dict["left_knee"],
                keypoints_dict["left_ankle"]
            )
            
        if all(k in keypoints_dict for k in ["right_hip", "right_knee", "right_ankle"]):
            angles["right_knee"] = self._angle_between_points(
                keypoints_dict["right_hip"],
                keypoints_dict["right_knee"],
                keypoints_dict["right_ankle"]
            )
            
        # Calculate elbow angle (between shoulder, elbow, and wrist)
        if all(k in keypoints_dict for k in ["left_shoulder", "left_elbow", "left_wrist"]):
            angles["left_elbow"] = self._angle_between_points(
                keypoints_dict["left_shoulder"],
                keypoints_dict["left_elbow"],
                keypoints_dict["left_wrist"]
            )
            
        if all(k in keypoints_dict for k in ["right_shoulder", "right_elbow", "right_wrist"]):
            angles["right_elbow"] = self._angle_between_points(
                keypoints_dict["right_shoulder"],
                keypoints_dict["right_elbow"],
                keypoints_dict["right_wrist"]
            )
            
        # Calculate average angles (left and right)
        if "left_hip" in angles and "right_hip" in angles:
            angles["hip"] = (angles["left_hip"] + angles["right_hip"]) / 2
            
        if "left_knee" in angles and "right_knee" in angles:
            angles["knee"] = (angles["left_knee"] + angles["right_knee"]) / 2
            
        if "left_elbow" in angles and "right_elbow" in angles:
            angles["elbow"] = (angles["left_elbow"] + angles["right_elbow"]) / 2
            
        return angles
        
    def _angle_between_points(self, p1: Tuple[float, float], p2: Tuple[float, float], p3: Tuple[float, float]) -> float:
        """
        Calculate angle between three points in degrees.
        
        Args:
            p1: First point (x, y)
            p2: Second point (x, y) - the vertex
            p3: Third point (x, y)
            
        Returns:
            Angle in degrees
        """
        # Convert to numpy arrays
        p1 = np.array(p1)
        p2 = np.array(p2)
        p3 = np.array(p3)
        
        # Calculate vectors
        v1 = p1 - p2
        v2 = p3 - p2
        
        # Calculate angle
        cosine_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
        cosine_angle = np.clip(cosine_angle, -1.0, 1.0)
        angle = np.degrees(np.arccos(cosine_angle))
        
        return angle
        
    def _detect_phases(self, frames: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Detect exercise phases in a sequence of frames.
        
        Args:
            frames: List of frames with angles
            
        Returns:
            List of detected phases with start/end timestamps
        """
        if not frames:
            return []
            
        # For now, use a simple approach based on joint angles
        # This would need to be customized for each exercise type
        phases = []
        current_phase = None
        phase_start_idx = 0
        
        # Example for squat detection using knee angle
        # Assumes frames are sorted by timestamp
        if self.exercise_type == "squat":
            for i, frame in enumerate(frames):
                if "knee" in frame["angles"]:
                    knee_angle = frame["angles"]["knee"]
                    
                    # Start of squat (going down)
                    if knee_angle < 150 and current_phase is None:
                        current_phase = "descending"
                        phase_start_idx = i
                        
                    # Bottom of squat
                    elif knee_angle < 110 and current_phase == "descending":
                        phases.append({
                            "phase": "descending",
                            "start_frame": phase_start_idx,
                            "end_frame": i,
                            "start_time": frames[phase_start_idx]["timestamp"],
                            "end_time": frame["timestamp"]
                        })
                        current_phase = "bottom"
                        phase_start_idx = i
                        
                    # Ascending from squat
                    elif knee_angle > 130 and current_phase == "bottom":
                        phases.append({
                            "phase": "bottom",
                            "start_frame": phase_start_idx,
                            "end_frame": i,
                            "start_time": frames[phase_start_idx]["timestamp"],
                            "end_time": frame["timestamp"]
                        })
                        current_phase = "ascending"
                        phase_start_idx = i
                        
                    # Completed squat
                    elif knee_angle > 160 and current_phase == "ascending":
                        phases.append({
                            "phase": "ascending",
                            "start_frame": phase_start_idx,
                            "end_frame": i,
                            "start_time": frames[phase_start_idx]["timestamp"],
                            "end_time": frame["timestamp"]
                        })
                        current_phase = None
                
        # Add last incomplete phase if needed
        if current_phase and phase_start_idx < len(frames) - 1:
            last_idx = len(frames) - 1
            phases.append({
                "phase": current_phase,
                "start_frame": phase_start_idx,
                "end_frame": last_idx,
                "start_time": frames[phase_start_idx]["timestamp"],
                "end_time": frames[last_idx]["timestamp"]
            })
            
        return phases
        
    def _count_repetitions(self, phases: List[Dict[str, Any]]) -> int:
        """
        Count exercise repetitions from phases.
        
        Args:
            phases: List of detected phases
            
        Returns:
            Number of complete repetitions
        """
        rep_count = 0
        required_phases = []
        
        # Define required phases for a complete rep based on exercise type
        if self.exercise_type == "squat":
            required_phases = ["descending", "bottom", "ascending"]
        elif self.exercise_type == "pushup":
            required_phases = ["descending", "bottom", "ascending"]
        else:
            # Generic approach for unknown exercises
            return len(phases) // 3  # Assuming 3 phases per rep
            
        # Count complete reps
        phase_index = 0
        while phase_index <= len(phases) - len(required_phases):
            is_complete_rep = True
            
            for i, required_phase in enumerate(required_phases):
                if phase_index + i >= len(phases) or phases[phase_index + i]["phase"] != required_phase:
                    is_complete_rep = False
                    break
                    
            if is_complete_rep:
                rep_count += 1
                phase_index += len(required_phases)
            else:
                phase_index += 1
                
        return rep_count
        
    def _check_form(self, frames: List[Dict[str, Any]], phases: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Check form against target angles and identify issues.
        
        Args:
            frames: List of frames with angles
            phases: List of detected phases
            
        Returns:
            List of identified form issues
        """
        issues = []
        
        # Get target angles from exercise config
        target_angles = self.exercise_config.get("target_angles", {})
        tolerances = self.exercise_config.get("angle_tolerances", {})
        
        # Check each phase
        for phase in phases:
            phase_name = phase["phase"]
            phase_frames = frames[phase["start_frame"]:phase["end_frame"] + 1]
            
            # Check key angles during this phase
            for joint, target in target_angles.items():
                # Skip if target is not defined for this phase
                if isinstance(target, dict) and phase_name not in target:
                    continue
                    
                # Get target value for this phase
                target_value = target[phase_name] if isinstance(target, dict) else target
                
                # Get tolerance for this joint
                tolerance = tolerances.get(joint, 15)
                
                # Check angles in all frames of this phase
                for frame in phase_frames:
                    if joint in frame["angles"]:
                        angle = frame["angles"][joint]
                        deviation = abs(angle - target_value)
                        
                        if deviation > tolerance:
                            # Add issue
                            issues.append({
                                "joint": joint,
                                "phase": phase_name,
                                "frame": frame["frame_number"],
                                "timestamp": frame["timestamp"],
                                "actual": angle,
                                "target": target_value,
                                "deviation": deviation,
                                "severity": self._calculate_severity(deviation, tolerance)
                            })
                            
        return issues
        
    def _calculate_severity(self, deviation: float, tolerance: float) -> str:
        """
        Calculate severity level based on deviation from target angle.
        
        Args:
            deviation: Deviation from target angle
            tolerance: Allowed tolerance
            
        Returns:
            Severity level ("low", "medium", or "high")
        """
        if deviation <= tolerance * 1.2:
            return "low"
        elif deviation <= tolerance * 2:
            return "medium"
        else:
            return "high"
            
    def _generate_feedback(self, issues: List[Dict[str, Any]], rep_count: int) -> List[Dict[str, Any]]:
        """
        Generate actionable feedback based on identified issues.
        
        Args:
            issues: List of identified form issues
            rep_count: Number of completed repetitions
            
        Returns:
            List of feedback items
        """
        feedback = []
        
        # Group issues by joint and phase
        joint_phase_issues = {}
        for issue in issues:
            key = f"{issue['joint']}_{issue['phase']}"
            if key not in joint_phase_issues:
                joint_phase_issues[key] = []
            joint_phase_issues[key].append(issue)
            
        # Generate feedback for each issue group
        for key, group_issues in joint_phase_issues.items():
            joint, phase = key.split("_")
            
            # Skip if not enough issues
            if len(group_issues) < 2:
                continue
                
            # Get average deviation
            avg_deviation = sum(issue["deviation"] for issue in group_issues) / len(group_issues)
            
            # Determine if angle is too high or too low
            direction = "high" if group_issues[0]["actual"] > group_issues[0]["target"] else "low"
            
            # Get worst severity
            severity = max(issue["severity"] for issue in group_issues)
            
            # Generate feedback based on joint, phase, and direction
            message = self._get_feedback_message(joint, phase, direction, severity)
            
            feedback.append({
                "joint": joint,
                "phase": phase,
                "message": message,
                "severity": severity,
                "frame_examples": [issue["frame"] for issue in group_issues[:3]]
            })
            
        # Add overall feedback
        if rep_count == 0:
            feedback.append({
                "joint": "overall",
                "phase": "overall",
                "message": "No complete repetitions detected. Try to perform the full range of motion for the exercise.",
                "severity": "high",
                "frame_examples": []
            })
        elif len(feedback) == 0:
            feedback.append({
                "joint": "overall",
                "phase": "overall",
                "message": f"Great job! {rep_count} repetitions with good form.",
                "severity": "low",
                "frame_examples": []
            })
            
        return feedback
        
    def _get_feedback_message(self, joint: str, phase: str, direction: str, severity: str) -> str:
        """
        Get exercise-specific feedback message.
        
        Args:
            joint: Joint name
            phase: Exercise phase
            direction: Direction of issue ("high" or "low")
            severity: Issue severity
            
        Returns:
            Feedback message
        """
        # Squat-specific feedback
        if self.exercise_type == "squat":
            if joint == "knee" and phase == "bottom":
                if direction == "high":
                    return "Your squat depth is not sufficient. Try going deeper by bending your knees more."
                else:
                    return "You're going too deep in your squat, which may strain your knees. Try to maintain a 90-degree knee angle at the bottom."
                    
            elif joint == "hip" and phase == "descending":
                if direction == "high":
                    return "Keep your chest up and back straight when descending into the squat."
                    
            elif joint == "knee" and phase == "ascending":
                if direction == "low":
                    return "Drive through your heels when coming up from the squat."
                    
        # Pushup-specific feedback
        elif self.exercise_type == "pushup":
            if joint == "elbow" and phase == "bottom":
                if direction == "high":
                    return "You're not going deep enough in your pushup. Try to lower your chest closer to the ground."
                else:
                    return "You're going too deep in your pushup, which may strain your shoulders. Aim for a 90-degree bend in your elbows at the bottom."
                    
        # Generic feedback as fallback
        if severity == "high":
            return f"Significant issue with {joint} angle during the {phase} phase. Focus on maintaining proper form."
        elif severity == "medium":
            return f"Minor issue with {joint} angle during the {phase} phase. Pay attention to your form."
        else:
            return f"Slight deviation in {joint} angle during the {phase} phase. Overall good form."
            
    def _calculate_score(self, issues: List[Dict[str, Any]], rep_count: int) -> float:
        """
        Calculate overall form score.
        
        Args:
            issues: List of identified form issues
            rep_count: Number of completed repetitions
            
        Returns:
            Score from 0 to 10
        """
        # Base score
        base_score = 10.0
        
        # Deduct points for issues
        severity_points = {
            "low": 0.2,
            "medium": 0.5,
            "high": 1.0
        }
        
        # Count issues by severity
        severity_counts = {"low": 0, "medium": 0, "high": 0}
        for issue in issues:
            severity_counts[issue["severity"]] += 1
            
        # Calculate deductions
        total_deduction = (
            severity_counts["low"] * severity_points["low"] +
            severity_counts["medium"] * severity_points["medium"] +
            severity_counts["high"] * severity_points["high"]
        )
        
        # Cap deductions
        total_deduction = min(total_deduction, 8.0)
        
        # Calculate final score
        final_score = base_score - total_deduction
        
        # Adjust for rep count
        if rep_count == 0:
            final_score = min(final_score, 3.0)
        elif rep_count == 1:
            final_score = min(final_score, 7.0)
            
        return round(max(final_score, 1.0), 1)  # Ensure minimum score of 1.0

@celery_app.task(name="app.tasks.form_analysis.analyze_form")
def analyze_form(video_id: str, exercise_type: Optional[str] = None) -> Dict[str, Any]:
    """
    Analyze exercise form in a video.
    
    This task:
    1. Retrieves pose data from the video
    2. Analyzes the form for the specified exercise type
    3. Generates feedback and scores
    4. Stores results in the database
    5. Sends notification email to the user
    
    Args:
        video_id: The ID of the video to analyze
        exercise_type: Type of exercise (e.g., "squat", "pushup")
        
    Returns:
        Dict containing analysis results and metadata
    """
    logger.info(f"Analyzing form in video {video_id}")
    result = {
        "video_id": video_id,
        "status": "failed",
        "error": None,
        "analysis": None
    }
    
    # Get database session
    with get_db_session() as db:
        try:
            # Get video record
            video = db.query(Video).filter(Video.id == UUID(video_id)).first()
            if not video:
                message = f"Video {video_id} not found"
                logger.error(message)
                result["error"] = message
                return result
                
            # Check if pose data exists
            if not video.pose_data:
                message = "No pose data available for analysis"
                logger.error(message)
                result["error"] = message
                
                # Update video status
                video.status = VideoStatus.FAILED
                video.error_message = message
                db.commit()
                
                return result
                
            # Use provided exercise type or default
            exercise_type = exercise_type or video.exercise_type or "generic"
            
            # Update video status
            video.status = VideoStatus.PROCESSING
            db.commit()
            
            # Initialize form analyzer
            analyzer = FormAnalyzer(exercise_type=exercise_type)
            
            # Analyze form
            analysis = analyzer.analyze_form(video.pose_data)
            
            # Store analysis results
            video.analysis_results = analysis
            video.score = analysis["score"]
            video.rep_count = analysis["rep_count"]
            video.feedback = analysis["feedback"]
            video.status = VideoStatus.READY
            db.commit()
            
            # Send notification email to the user
            try:
                # Get user
                user = db.query(User).filter(User.id == video.user_id).first()
                
                if user and user.email and user.is_active:
                    # Run async code in sync context
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    send_result = loop.run_until_complete(
                        EmailService.send_analysis_complete_notification(user, video)
                    )
                    
                    if send_result:
                        logger.info(f"Analysis completion email sent to {user.email} for video {video_id}")
                    else:
                        logger.warning(f"Failed to send analysis completion email to {user.email} for video {video_id}")
                        
                    loop.close()
            except Exception as email_error:
                # Log error but don't fail the task
                logger.error(f"Error sending analysis completion email: {str(email_error)}")
            
            # Update result
            result["status"] = "success"
            result["analysis"] = analysis
            
        except Exception as e:
            logger.error(f"Error analyzing form in video {video_id}: {str(e)}")
            
            # Update video status
            if 'video' in locals():
                video.status = VideoStatus.FAILED
                video.error_message = str(e)
                db.commit()
                
            result["error"] = str(e)
            
    return result 