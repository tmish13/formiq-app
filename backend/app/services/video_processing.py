"""Video processing service for exercise form analysis."""
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import cv2
from datetime import datetime
import tempfile
import os

from app.core.monitoring import track_model_inference
from app.models.enums import ExerciseType
from app.core.config import settings

class VideoProcessingService:
    """Service for processing exercise videos."""
    
    def __init__(self):
        """Initialize video processing service."""
        self.frame_rate = settings.VIDEO_FRAME_RATE
        self.max_frames = settings.MAX_VIDEO_FRAMES
        self.target_size = (256, 256)  # Target size for processed frames
        
        # Exercise-specific frame selection configs
        self.frame_selection_configs = {
            ExerciseType.SQUAT: {
                "key_frames": ["start", "descent", "bottom", "ascent", "end"],
                "frame_count": 5
            },
            ExerciseType.PUSHUP: {
                "key_frames": ["start", "descent", "bottom", "ascent", "end"],
                "frame_count": 5
            },
            ExerciseType.PLANK: {
                "key_frames": ["setup", "hold", "end"],
                "frame_count": 3
            }
        }
    
    async def process_video(
        self,
        video_data: bytes,
        exercise_type: ExerciseType
    ) -> Dict[str, Any]:
        """
        Process video data for exercise analysis.
        
        Args:
            video_data: Raw video bytes
            exercise_type: Type of exercise being performed
            
        Returns:
            Dictionary containing processed frames and metadata
        """
        start_time = datetime.now().timestamp()
        
        try:
            # Save video to temporary file
            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_file:
                temp_file.write(video_data)
                temp_path = temp_file.name
            
            try:
                # Extract and process frames
                frames = await self._extract_frames(temp_path, exercise_type)
                
                # Select key frames
                key_frames = self._select_key_frames(frames, exercise_type)
                
                # Preprocess frames
                processed_frames = self._preprocess_frames(key_frames)
                
                # Track processing metrics
                duration = datetime.now().timestamp() - start_time
                track_model_inference(
                    exercise_type=exercise_type.value,
                    frame_count=len(processed_frames),
                    has_errors=False,
                    model_type="video_processing",
                    duration=duration,
                    confidence=1.0,
                    error_type=None
                )
                
                return {
                    "frames": processed_frames,
                    "frame_count": len(processed_frames),
                    "duration": duration,
                    "frame_rate": self.frame_rate,
                    "resolution": self.target_size,
                    "exercise_type": exercise_type.value
                }
                
            finally:
                # Clean up temporary file
                os.unlink(temp_path)
                
        except Exception as e:
            # Track error metrics
            track_model_inference(
                exercise_type=exercise_type.value,
                frame_count=0,
                has_errors=True,
                model_type="video_processing",
                duration=datetime.now().timestamp() - start_time,
                confidence=0.0,
                error_type=str(type(e).__name__)
            )
            raise
    
    async def _extract_frames(
        self,
        video_path: str,
        exercise_type: ExerciseType
    ) -> List[np.ndarray]:
        """Extract frames from video file."""
        frames = []
        cap = cv2.VideoCapture(video_path)
        
        try:
            # Get video properties
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = int(cap.get(cv2.CAP_PROP_FPS))
            
            # Calculate frame interval
            interval = max(1, total_frames // self.max_frames)
            
            frame_count = 0
            while cap.isOpened() and frame_count < self.max_frames:
                ret, frame = cap.read()
                if not ret:
                    break
                
                if frame_count % interval == 0:
                    frames.append(frame)
                
                frame_count += 1
                
        finally:
            cap.release()
        
        return frames
    
    def _select_key_frames(
        self,
        frames: List[np.ndarray],
        exercise_type: ExerciseType
    ) -> List[np.ndarray]:
        """Select key frames for exercise analysis."""
        if not frames:
            return []
            
        config = self.frame_selection_configs.get(exercise_type)
        if not config:
            return frames
            
        frame_count = config["frame_count"]
        if len(frames) <= frame_count:
            return frames
            
        # Calculate indices for key frames
        indices = [
            int(i * (len(frames) - 1) / (frame_count - 1))
            for i in range(frame_count)
        ]
        
        return [frames[i] for i in indices]
    
    def _preprocess_frames(self, frames: List[np.ndarray]) -> List[np.ndarray]:
        """Preprocess frames for ML model input."""
        processed_frames = []
        
        for frame in frames:
            # Resize frame
            resized = cv2.resize(frame, self.target_size)
            
            # Convert to RGB
            rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
            
            # Normalize pixel values
            normalized = rgb.astype(np.float32) / 255.0
            
            processed_frames.append(normalized)
        
        return processed_frames
    
    def _validate_video(self, video_path: str) -> Tuple[bool, Optional[str]]:
        """Validate video file format and properties."""
        try:
            cap = cv2.VideoCapture(video_path)
            
            if not cap.isOpened():
                return False, "Could not open video file"
            
            # Check video properties
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = int(cap.get(cv2.CAP_PROP_FPS))
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            # Validate dimensions
            if width < 320 or height < 240:
                return False, "Video resolution too low"
            
            # Validate frame rate
            if fps < 15:
                return False, "Frame rate too low"
            
            # Validate duration
            duration = frame_count / fps
            if duration > settings.MAX_VIDEO_DURATION:
                return False, f"Video duration exceeds {settings.MAX_VIDEO_DURATION} seconds"
            
            return True, None
            
        except Exception as e:
            return False, str(e)
            
        finally:
            if 'cap' in locals():
                cap.release() 