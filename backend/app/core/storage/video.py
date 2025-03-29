"""Video storage management module."""
import os
from typing import Optional
from uuid import UUID
from fastapi import UploadFile
from app.core.config import settings
from app.core.logging import get_logger

# Initialize logger
logger = get_logger(__name__)

async def upload_video(video: UploadFile, user_id: UUID) -> str:
    """
    Upload a video file to storage.
    
    Args:
        video: Video file to upload
        user_id: User ID for path construction
        
    Returns:
        str: URL of the uploaded video
        
    Raises:
        ProcessingError: If upload fails
    """
    try:
        # Create user directory if it doesn't exist
        user_dir = os.path.join(settings.UPLOAD_DIR, str(user_id))
        os.makedirs(user_dir, exist_ok=True)
        
        # Generate unique filename
        filename = f"{UUID()}{os.path.splitext(video.filename)[1]}"
        file_path = os.path.join(user_dir, filename)
        
        # Save file
        with open(file_path, "wb+") as file_object:
            content = await video.read()
            file_object.write(content)
            
        # Return URL
        return f"{settings.MEDIA_URL}/videos/{user_id}/{filename}"
    except Exception as e:
        logger.error(f"Failed to upload video: {str(e)}")
        raise

async def delete_video(video_url: str) -> None:
    """
    Delete a video file from storage.
    
    Args:
        video_url: URL of the video to delete
        
    Raises:
        ProcessingError: If deletion fails
    """
    try:
        # Extract path from URL
        path = video_url.replace(f"{settings.MEDIA_URL}/videos/", "")
        file_path = os.path.join(settings.UPLOAD_DIR, path)
        
        # Delete file if it exists
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Deleted video: {file_path}")
    except Exception as e:
        logger.error(f"Failed to delete video: {str(e)}")
        raise 