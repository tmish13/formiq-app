"""Storage module."""
from typing import BinaryIO, Dict, Any, Optional, List
import os
import uuid
import tempfile
from fastapi import UploadFile
import aiofiles
import shutil

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

class StorageError(Exception):
    """Base exception for storage errors."""
    
    def __init__(self, message: str, code: str = "STORAGE_ERROR"):
        """Initialize StorageError.
        
        Args:
            message: Error message
            code: Error code
        """
        self.message = message
        self.code = code
        super().__init__(message)

async def upload_video(file: UploadFile) -> str:
    """
    Upload video file asynchronously.
    
    Args:
        file: Upload file object
        
    Returns:
        URL to the uploaded video
        
    Raises:
        StorageError: If upload fails
    """
    try:
        # Create upload directory if it doesn't exist
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

        # Generate unique filename
        filename = f"{uuid.uuid4()}{os.path.splitext(file.filename)[1]}"
        filepath = os.path.join(settings.UPLOAD_DIR, filename)

        # Reset file position
        await file.seek(0)
        
        # Save file
        try:
            # Try async file writing
            async with aiofiles.open(filepath, "wb") as buffer:
                content = await file.read()
                await buffer.write(content)
        except ImportError:
            # Fall back to sync file writing for test environments
            with open(filepath, "wb") as buffer:
                content = file.file.read()
                buffer.write(content)

        # Return video URL
        return f"{settings.UPLOAD_URL}/{filename}"
    except Exception as e:
        raise StorageError(f"Failed to upload video: {str(e)}")


async def delete_video(video_url: str) -> None:
    """
    Delete video file.
    
    Args:
        video_url: URL to the video file
        
    Raises:
        StorageError: If deletion fails
    """
    try:
        # Extract filename from URL
        filename = os.path.basename(video_url)
        filepath = os.path.join(settings.UPLOAD_DIR, filename)

        # Delete file if it exists
        if os.path.exists(filepath):
            os.remove(filepath)
    except Exception as e:
        raise StorageError(f"Failed to delete video: {str(e)}")


def create_temp_file(file_data: BinaryIO, suffix: Optional[str] = None) -> str:
    """Create a temporary file from file data.
    
    Args:
        file_data: File data
        suffix: File suffix
        
    Returns:
        str: Path to temporary file
    """
    try:
        # Create a temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        temp_file.close()
        
        # Write the file data
        with open(temp_file.name, 'wb') as f:
            f.write(file_data.read())
        
        return temp_file.name
    except Exception as e:
        raise StorageError(f"Failed to create temporary file: {str(e)}")


def create_temp_copy(file: UploadFile) -> str:
    """
    Create a temporary copy of the uploaded file for testing.
    
    Args:
        file: Upload file object
        
    Returns:
        Path to the temporary file
    """
    try:
        temp_file = os.path.join("/tmp", f"{uuid.uuid4()}{os.path.splitext(file.filename)[1]}")
        with open(temp_file, "wb") as f:
            file.file.seek(0)
            shutil.copyfileobj(file.file, f)
        return temp_file
    except Exception as e:
        raise StorageError(f"Failed to create temporary file: {str(e)}")


def get_video_url(video_key: str) -> str:
    """Get the URL for a video.
    
    Args:
        video_key: Video key
        
    Returns:
        str: Video URL
    """
    if video_key.startswith(("http://", "https://", "s3://")):
        return video_key
    
    # Assume local storage
    if settings.ENVIRONMENT == "development":
        base_url = f"http://localhost:{settings.API_PORT}/uploads"
    else:
        base_url = settings.UPLOAD_URL
        
    # Normalize path
    video_key = video_key.lstrip("/")
    
    return f"{base_url}/{video_key}" 