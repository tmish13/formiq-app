"""Video processing Celery tasks."""
import os
import tempfile
import logging
from typing import Dict, Any, List, Optional
from uuid import UUID

import cv2
import numpy as np
from sqlalchemy.orm import Session

from app.core.celery_app import celery_app
from app.db.session import get_db_session
from app.models.video import Video, VideoStatus
from app.services.storage_service import StorageService
from app.core.logging import get_logger
from app.core.config import settings

logger = get_logger(__name__)

@celery_app.task(name="app.tasks.video_processing.process_uploaded_video")
def process_uploaded_video(video_id: str) -> Dict[str, Any]:
    """
    Process an uploaded video and prepare it for pose analysis.
    
    This task:
    1. Downloads the video from S3
    2. Processes the video (resizing, frame rate adjustment)
    3. Uploads the processed video back to S3
    4. Updates the video metadata
    5. Triggers the pose detection task
    
    Args:
        video_id: The ID of the video to process
        
    Returns:
        Dict containing processing results and metadata
    """
    logger.info(f"Processing video {video_id}")
    result = {
        "video_id": video_id,
        "status": "failed",
        "error": None,
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
            
            # Initialize storage service
            storage_service = StorageService()
            
            # Download video to temporary file
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_file:
                temp_path = temp_file.name
                
            logger.info(f"Downloading video {video.url} to {temp_path}")
            try:
                # Download file from S3
                video_data = storage_service.download_file(video.url)
                with open(temp_path, "wb") as file:
                    file.write(video_data)
                
                # Process video
                processed_path = process_video(
                    temp_path, 
                    target_fps=settings.VIDEO_FRAME_RATE,
                    max_duration=settings.MAX_VIDEO_DURATION
                )
                
                # Upload processed video back to S3
                processed_url = storage_service.upload_file(
                    processed_path,
                    content_type="video/mp4",
                    object_key=f"processed/{video_id}_processed.mp4"
                )
                
                # Update video record
                video.processed_url = processed_url
                video.status = VideoStatus.READY
                db.commit()
                
                # Trigger pose detection task
                from app.tasks.pose_detection import detect_pose
                detect_pose.delay(video_id=video_id)
                
                # Set result
                result["status"] = "success"
                result["processed_url"] = processed_url
                
            finally:
                # Clean up temporary files
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                if "processed_path" in locals() and os.path.exists(processed_path):
                    os.unlink(processed_path)
                    
        except Exception as e:
            logger.error(f"Error processing video {video_id}: {str(e)}")
            # Update video status to error
            if 'video' in locals():
                video.status = VideoStatus.FAILED
                video.error_message = str(e)
                db.commit()
                
            result["error"] = str(e)
            
    return result

def process_video(
    input_path: str, 
    target_fps: int = 30, 
    target_resolution: tuple = (640, 480),
    max_duration: int = 60
) -> str:
    """
    Process video file for optimal analysis.
    
    Args:
        input_path: Path to the input video file
        target_fps: Target frames per second
        target_resolution: Target resolution (width, height)
        max_duration: Maximum duration in seconds
        
    Returns:
        Path to the processed video file
        
    Raises:
        ValueError: If video processing fails
    """
    try:
        # Get video info
        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            raise ValueError("Failed to open video file")
            
        # Get video properties
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 0
        
        logger.info(f"Video properties: fps={fps}, resolution={width}x{height}, duration={duration:.2f}s")
        
        # Check if processing is needed
        needs_processing = (
            abs(fps - target_fps) > 1 or 
            width != target_resolution[0] or 
            height != target_resolution[1] or
            duration > max_duration
        )
        
        if not needs_processing:
            logger.info("Video already meets requirements, skipping processing")
            return input_path
            
        # Create output path
        output_path = input_path.replace(".mp4", "_processed.mp4")
        
        # Calculate frame interval if duration exceeds maximum
        frame_interval = 1
        if duration > max_duration:
            # Only keep enough frames to meet the max duration at target FPS
            max_frames = max_duration * target_fps
            frame_interval = max(1, total_frames // max_frames)
            logger.info(f"Limiting duration: keeping 1 in {frame_interval} frames")
            
        # Initialize video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(
            output_path,
            fourcc,
            target_fps,
            target_resolution
        )
        
        # Process frames
        frame_count = 0
        processed_count = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
                
            # Apply frame interval for long videos
            if frame_count % frame_interval == 0:
                # Resize if needed
                if width != target_resolution[0] or height != target_resolution[1]:
                    frame = cv2.resize(frame, target_resolution)
                    
                out.write(frame)
                processed_count += 1
                
            frame_count += 1
            
        # Release resources
        cap.release()
        out.release()
        
        logger.info(f"Video processed: {processed_count} frames at {target_fps} fps")
        return output_path
        
    except Exception as e:
        logger.error(f"Video processing error: {str(e)}")
        raise ValueError(f"Failed to process video: {str(e)}")

@celery_app.task(name="app.tasks.video_processing.extract_frames")
def extract_frames(video_id: str, interval: float = 1.0) -> Dict[str, Any]:
    """
    Extract frames from a video at a specified interval.
    
    Args:
        video_id: The ID of the video to extract frames from
        interval: Time interval between frames in seconds
        
    Returns:
        Dict containing extraction results and frame info
    """
    logger.info(f"Extracting frames from video {video_id} at {interval}s intervals")
    result = {
        "video_id": video_id,
        "status": "failed",
        "error": None,
        "frames": []
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
                
            # Use processed URL if available, otherwise use original URL
            video_url = video.processed_url or video.url
            
            # Initialize storage service
            storage_service = StorageService()
            
            # Download video to temporary file
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_file:
                temp_path = temp_file.name
                
            try:
                # Download file from S3
                video_data = storage_service.download_file(video_url)
                with open(temp_path, "wb") as file:
                    file.write(video_data)
                
                # Extract frames
                frames = []
                output_dir = tempfile.mkdtemp()
                
                # Open video
                cap = cv2.VideoCapture(temp_path)
                fps = cap.get(cv2.CAP_PROP_FPS)
                frame_interval = int(fps * interval)
                frame_count = 0
                
                while True:
                    ret, frame = cap.read()
                    if not ret:
                        break
                        
                    if frame_count % frame_interval == 0:
                        # Save frame to temporary file
                        frame_path = os.path.join(output_dir, f"frame_{frame_count}.jpg")
                        cv2.imwrite(frame_path, frame)
                        
                        # Upload frame to S3
                        frame_url = storage_service.upload_file(
                            frame_path,
                            content_type="image/jpeg",
                            object_key=f"frames/{video_id}/frame_{frame_count}.jpg"
                        )
                        
                        frames.append({
                            "frame_number": frame_count,
                            "timestamp": frame_count / fps,
                            "url": frame_url
                        })
                        
                    frame_count += 1
                    
                cap.release()
                
                # Update result
                result["status"] = "success"
                result["frames"] = frames
                result["frame_count"] = len(frames)
                
            finally:
                # Clean up temporary files
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                for frame in result["frames"]:
                    frame_path = os.path.join(output_dir, f"frame_{frame['frame_number']}.jpg")
                    if os.path.exists(frame_path):
                        os.unlink(frame_path)
                if os.path.exists(output_dir):
                    os.rmdir(output_dir)
                
        except Exception as e:
            logger.error(f"Error extracting frames from video {video_id}: {str(e)}")
            result["error"] = str(e)
            
    return result 