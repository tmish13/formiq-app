"""Pose detection Celery tasks."""
import os
import tempfile
import logging
import json
from typing import Dict, Any, List, Optional
from uuid import UUID

import numpy as np
import cv2
import mediapipe as mp
from sqlalchemy.orm import Session

from app.core.celery_app import celery_app
from app.db.session import get_db_session
from app.models.video import Video, VideoStatus
from app.services.storage import StorageService
from app.core.logging import get_logger
from app.core.config import settings

logger = get_logger(__name__)

class PoseDetector:
    """Wrapper for pose detection model."""
    
    def __init__(self, model_complexity: int = 2):
        """
        Initialize pose detector.
        
        Args:
            model_complexity: Complexity of the pose detection model (0, 1, or 2)
        """
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=model_complexity,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
    def detect(self, frame: np.ndarray) -> Dict[str, Any]:
        """
        Detect poses in a frame.
        
        Args:
            frame: The frame to detect poses in
            
        Returns:
            Dict containing pose landmarks and scores
        """
        # Convert BGR to RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Process frame
        results = self.pose.process(frame_rgb)
        
        if not results.pose_landmarks:
            return {"keypoints": [], "score": 0.0}
            
        # Extract landmarks
        keypoints = []
        for idx, landmark in enumerate(results.pose_landmarks.landmark):
            # Get the name of the landmark if available
            landmark_name = self.mp_pose.PoseLandmark(idx).name.lower() if idx < 33 else f"landmark_{idx}"
            
            keypoints.append({
                "name": landmark_name,
                "x": landmark.x,
                "y": landmark.y,
                "z": landmark.z,
                "visibility": landmark.visibility
            })
            
        # Calculate confidence score
        scores = [kp["visibility"] for kp in keypoints]
        score = sum(scores) / len(scores) if scores else 0.0
        
        return {
            "keypoints": keypoints,
            "score": score
        }
        
    def draw_pose(self, frame: np.ndarray, pose_data: Dict[str, Any]) -> np.ndarray:
        """
        Draw detected pose on a frame.
        
        Args:
            frame: The frame to draw the pose on
            pose_data: Pose data from detect()
            
        Returns:
            Frame with pose drawn on it
        """
        # Create a copy of the frame
        annotated_frame = frame.copy()
        
        # Check if there are keypoints
        if not pose_data["keypoints"]:
            return annotated_frame
            
        # Draw connections
        mp_drawing = mp.solutions.drawing_utils
        mp_drawing_styles = mp.solutions.drawing_styles
        
        # Convert keypoints to mp format
        landmarks_proto = self._keypoints_to_proto(pose_data["keypoints"])
        
        mp_drawing.draw_landmarks(
            annotated_frame,
            landmarks_proto,
            self.mp_pose.POSE_CONNECTIONS,
            landmark_drawing_spec=mp_drawing_styles.get_default_pose_landmarks_style()
        )
        
        return annotated_frame
        
    def _keypoints_to_proto(self, keypoints: List[Dict[str, Any]]) -> Any:
        """
        Convert keypoints to MediaPipe proto format.
        
        Args:
            keypoints: List of keypoints
            
        Returns:
            MediaPipe landmarks proto
        """
        landmarks_proto = self.mp_pose.PoseLandmarkList()
        for kp in keypoints:
            landmark = landmarks_proto.landmark.add()
            landmark.x = kp["x"]
            landmark.y = kp["y"]
            landmark.z = kp["z"]
            landmark.visibility = kp["visibility"]
            
        return landmarks_proto

@celery_app.task(name="app.tasks.pose_detection.detect_pose")
def detect_pose(video_id: str, frame_interval: float = 0.5) -> Dict[str, Any]:
    """
    Detect poses in a video.
    
    This task:
    1. Extracts frames from the video at specified intervals
    2. Detects poses in each frame
    3. Stores pose data in the database
    4. Triggers form analysis if enough valid poses are detected
    
    Args:
        video_id: The ID of the video to analyze
        frame_interval: Time interval between frames in seconds
        
    Returns:
        Dict containing detection results and metadata
    """
    logger.info(f"Detecting poses in video {video_id}")
    result = {
        "video_id": video_id,
        "status": "failed",
        "error": None,
        "poses": []
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
                
            # Update video status
            video.status = VideoStatus.PROCESSING
            db.commit()
            
            # Initialize storage service and pose detector
            storage_service = StorageService()
            pose_detector = PoseDetector(model_complexity=2)
            
            # Use processed URL if available, otherwise use original URL
            video_url = video.processed_url or video.url
            
            # Download video to temporary file
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_file:
                temp_path = temp_file.name
                
            try:
                # Download file from S3
                video_data = storage_service.download_file(video_url)
                with open(temp_path, "wb") as file:
                    file.write(video_data)
                
                # Extract frames and detect poses
                poses = []
                visualizations = []
                output_dir = tempfile.mkdtemp()
                
                # Open video
                cap = cv2.VideoCapture(temp_path)
                fps = cap.get(cv2.CAP_PROP_FPS)
                frame_interval_frames = int(fps * frame_interval)
                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                frame_count = 0
                
                while True:
                    ret, frame = cap.read()
                    if not ret:
                        break
                        
                    if frame_count % frame_interval_frames == 0:
                        # Detect pose in frame
                        pose_data = pose_detector.detect(frame)
                        
                        # Only include frames with good poses
                        if pose_data["score"] >= settings.MIN_CONFIDENCE_THRESHOLD:
                            # Draw pose on frame for visualization
                            annotated_frame = pose_detector.draw_pose(frame, pose_data)
                            
                            # Save annotated frame
                            frame_path = os.path.join(output_dir, f"pose_{frame_count}.jpg")
                            cv2.imwrite(frame_path, annotated_frame)
                            
                            # Upload frame to S3
                            frame_url = storage_service.upload_file(
                                frame_path,
                                content_type="image/jpeg",
                                object_key=f"poses/{video_id}/frame_{frame_count}.jpg"
                            )
                            
                            # Add frame timestamp
                            timestamp = frame_count / fps
                            
                            poses.append({
                                "frame_number": frame_count,
                                "timestamp": timestamp,
                                "keypoints": pose_data["keypoints"],
                                "score": pose_data["score"]
                            })
                            
                            visualizations.append({
                                "frame_number": frame_count,
                                "timestamp": timestamp,
                                "url": frame_url
                            })
                        
                    frame_count += 1
                    
                    # Log progress periodically
                    if frame_count % 100 == 0:
                        logger.info(f"Processed {frame_count}/{total_frames} frames")
                    
                cap.release()
                
                # Store pose data in video record
                video.pose_data = poses
                video.pose_visualizations = visualizations
                
                # Calculate stats
                valid_poses = len(poses)
                average_score = sum(p["score"] for p in poses) / valid_poses if valid_poses > 0 else 0
                
                video.stats = {
                    "total_frames": frame_count,
                    "valid_poses": valid_poses,
                    "average_score": average_score,
                    "frame_interval": frame_interval
                }
                
                # Update status
                if valid_poses >= 10:  # Minimum number of good poses
                    video.status = VideoStatus.READY
                    # Trigger form analysis task
                    from app.tasks.form_analysis import analyze_form
                    analyze_form.delay(video_id=video_id)
                else:
                    video.status = VideoStatus.FAILED
                    video.error_message = "Insufficient valid poses detected"
                
                db.commit()
                
                # Update result
                result["status"] = "success"
                result["poses"] = poses
                result["visualizations"] = visualizations
                result["stats"] = video.stats
                
            finally:
                # Clean up temporary files
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                for vis in visualizations:
                    frame_path = os.path.join(output_dir, f"pose_{vis['frame_number']}.jpg")
                    if os.path.exists(frame_path):
                        os.unlink(frame_path)
                if os.path.exists(output_dir):
                    os.rmdir(output_dir)
                
        except Exception as e:
            logger.error(f"Error detecting poses in video {video_id}: {str(e)}")
            
            # Update video status
            if 'video' in locals():
                video.status = VideoStatus.FAILED
                video.error_message = str(e)
                db.commit()
                
            result["error"] = str(e)
            
    return result 