"""Storage module."""
import os
import uuid
from fastapi import UploadFile
import aiofiles
import shutil

from app.core.config import settings
from app.core.exceptions import StorageError


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