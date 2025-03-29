"""Service for handling video processing and analysis."""
from typing import Dict, Any, List, Optional, Tuple
import cv2
import numpy as np
import tempfile
import os
from PIL import Image
from fastapi import UploadFile
from app.core.config import settings
from app.core.logging import get_logger
from app.services.storage import StorageService

logger = get_logger(__name__)

class VideoError(Exception):
    """Custom exception for video service errors."""
    pass

class VideoService:
    """Service for handling video processing and analysis."""
    
    def __init__(self):
        """Initialize video service."""
        self.storage = StorageService()
        self.supported_formats = [".mp4", ".avi", ".mov", ".mkv"]
        self.max_duration = 300  # 5 minutes
        self.target_fps = 30
        self.target_resolution = (640, 480)

    async def process_video(self, video_file: UploadFile) -> Dict[str, Any]:
        """Process uploaded video file."""
        try:
            # Validate video file
            if not self._is_valid_video(video_file):
                raise VideoError("Invalid video format")

            # Save video temporarily
            temp_path = self._save_temp_file(video_file)
            try:
                # Get video info
                info = self._get_video_info(temp_path)
                
                # Validate video duration
                if info["duration"] > self.max_duration:
                    raise VideoError(f"Video duration exceeds {self.max_duration} seconds")
                
                # Process video if needed
                if self._needs_processing(info):
                    processed_path = self._process_video(temp_path, info)
                else:
                    processed_path = temp_path
                
                # Upload to storage
                video_url = await self.storage.upload_file(
                    processed_path,
                    content_type="video/mp4"
                )
                
                return {
                    "url": video_url,
                    "duration": info["duration"],
                    "fps": info["fps"],
                    "resolution": info["resolution"],
                    "format": info["format"]
                }
            finally:
                # Clean up temporary files
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                if "processed_path" in locals() and os.path.exists(processed_path):
                    os.remove(processed_path)
        except Exception as e:
            logger.error(f"Failed to process video: {str(e)}")
            raise VideoError(f"Failed to process video: {str(e)}")

    def extract_frames(self, video_path: str, interval: float = 1.0) -> List[np.ndarray]:
        """Extract frames from video at specified interval."""
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise VideoError("Failed to open video file")
            
            frames = []
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_interval = int(fps * interval)
            frame_count = 0
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                    
                if frame_count % frame_interval == 0:
                    frames.append(frame)
                frame_count += 1
            
            cap.release()
            return frames
        except Exception as e:
            logger.error(f"Failed to extract frames: {str(e)}")
            raise VideoError(f"Failed to extract frames: {str(e)}")

    def save_frame(self, frame: np.ndarray, output_path: str) -> None:
        """Save a video frame as image."""
        try:
            # Convert BGR to RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image = Image.fromarray(rgb_frame)
            image.save(output_path)
        except Exception as e:
            logger.error(f"Failed to save frame: {str(e)}")
            raise VideoError(f"Failed to save frame: {str(e)}")

    def _is_valid_video(self, video_file: UploadFile) -> bool:
        """Check if video file format is supported."""
        file_ext = os.path.splitext(video_file.filename)[1].lower()
        return file_ext in self.supported_formats

    def _save_temp_file(self, video_file: UploadFile) -> str:
        """Save uploaded file to temporary location."""
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_file:
                temp_file.write(video_file.file.read())
                return temp_file.name
        except Exception as e:
            logger.error(f"Failed to save temporary file: {str(e)}")
            raise VideoError(f"Failed to save temporary file: {str(e)}")

    def _get_video_info(self, video_path: str) -> Dict[str, Any]:
        """Get video file information."""
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise VideoError("Failed to open video file")
            
            info = {
                "fps": cap.get(cv2.CAP_PROP_FPS),
                "frame_count": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
                "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                "format": os.path.splitext(video_path)[1].lower()
            }
            info["duration"] = info["frame_count"] / info["fps"]
            info["resolution"] = (info["width"], info["height"])
            
            cap.release()
            return info
        except Exception as e:
            logger.error(f"Failed to get video info: {str(e)}")
            raise VideoError(f"Failed to get video info: {str(e)}")

    def _needs_processing(self, video_info: Dict[str, Any]) -> bool:
        """Check if video needs processing."""
        return (
            abs(video_info["fps"] - self.target_fps) > 1 or
            video_info["resolution"] != self.target_resolution or
            video_info["format"] != ".mp4"
        )

    def _process_video(self, input_path: str, video_info: Dict[str, Any]) -> str:
        """Process video to match target specifications."""
        try:
            output_path = input_path.replace(video_info["format"], "_processed.mp4")
            
            # Set up video writer
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(
                output_path,
                fourcc,
                self.target_fps,
                self.target_resolution
            )
            
            # Process frames
            cap = cv2.VideoCapture(input_path)
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Resize frame if needed
                if video_info["resolution"] != self.target_resolution:
                    frame = cv2.resize(frame, self.target_resolution)
                
                out.write(frame)
            
            cap.release()
            out.release()
            
            return output_path
        except Exception as e:
            logger.error(f"Failed to process video: {str(e)}")
            raise VideoError(f"Failed to process video: {str(e)}")

    def delete_video(self, video_url: str) -> None:
        """Delete video from storage."""
        try:
            self.storage.delete_file(video_url)
            logger.info(f"Deleted video: {video_url}")
        except Exception as e:
            logger.error(f"Failed to delete video: {str(e)}")
            raise VideoError(f"Failed to delete video: {str(e)}") 