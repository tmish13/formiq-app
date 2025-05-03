"""Storage module initialization."""
import os
import uuid
import logging
import aiofiles
import tempfile
import shutil
from typing import Optional
from fastapi import UploadFile
from app.core.storage.base import StorageProvider, StorageError
from app.core.storage.s3 import S3StorageProvider, verify_s3_connection
from app.core.logging import get_logger
from app.core.config import settings

logger = get_logger(__name__)

# Create a simple instance for import purposes
# This is a stub that will be replaced during initialization
class LocalStorageProvider(StorageProvider):
    """Local file system storage provider."""
    
    def __init__(self, base_dir=None, base_url=None):
        """Initialize the local storage provider."""
        self.base_dir = base_dir or settings.UPLOAD_DIR
        self.base_url = base_url or settings.UPLOAD_URL

storage_provider = LocalStorageProvider()

async def init_storage():
    """Initialize storage system at application startup.
    
    This function sets up the appropriate storage backend based on configuration
    and ensures all required resources are available.
    """
    logger.info("Initializing storage system")
    
    try:
        # Determine storage type
        if settings.ENVIRONMENT == "production" and settings.USE_S3_STORAGE:
            # In production, we use S3
            # Verify S3 credentials and bucket access
            s3_available = await verify_s3_connection()
            if s3_available:
                logger.info(f"S3 storage initialized using bucket: {settings.AWS_BUCKET_NAME}")
            else:
                logger.error("Failed to connect to S3 - check credentials and bucket configuration")
                raise Exception("S3 storage initialization failed")
        else:
            # In development/test, we use local storage
            # Ensure upload directories exist
            upload_dir = settings.UPLOAD_DIR
            if not os.path.exists(upload_dir):
                os.makedirs(upload_dir, exist_ok=True)
                logger.info(f"Created local storage directory: {upload_dir}")
            
            logger.info(f"Local file storage initialized at: {upload_dir}")
            
    except Exception as e:
        logger.error(f"Failed to initialize storage system: {str(e)}")
        # In production, storage initialization failure is critical
        if settings.ENVIRONMENT == "production":
            raise
        # In development/test, we can continue with warnings
        logger.warning("Storage initialization failed, uploads may not work correctly")


async def upload_video(file: UploadFile) -> str:
    """Upload a video file to storage."""
    try:
        # Reset file cursor to beginning
        await file.seek(0)
        
        # Generate a unique filename
        filename = f"{uuid.uuid4()}{os.path.splitext(file.filename)[1]}"
        
        # Set the full file path
        video_dir = os.path.join(settings.UPLOAD_DIR, "videos")
        os.makedirs(video_dir, exist_ok=True)
        file_path = os.path.join(video_dir, filename)
        
        # Write the file
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        # Return the URL path
        return f"/uploads/videos/{filename}"
    except Exception as e:
        logger.error(f"Error uploading video: {str(e)}")
        raise StorageError(f"Failed to upload video: {str(e)}")


async def delete_video(video_url: str) -> bool:
    """Delete a video file from storage."""
    try:
        # Get the filename from URL
        filename = os.path.basename(video_url)
        video_dir = os.path.join(settings.UPLOAD_DIR, "videos")
        file_path = os.path.join(video_dir, filename)
        
        # Delete the file if it exists
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False
    except Exception as e:
        logger.error(f"Error deleting video: {str(e)}")
        raise StorageError(f"Failed to delete video: {str(e)}")


def get_video_url(video_key: str) -> str:
    """Get the URL for a video."""
    if video_key.startswith(("http://", "https://", "s3://")):
        return video_key
    
    # Normalize path
    video_key = video_key.lstrip("/")
    
    # Assume local storage
    base_url = settings.UPLOAD_URL
    return f"{base_url}/{video_key}"


async def create_temp_copy(file: UploadFile) -> str:
    """Create a temporary copy of a file."""
    try:
        # Reset file cursor to beginning
        await file.seek(0)
        
        # Create temporary file
        temp_dir = tempfile.mkdtemp()
        temp_file_path = os.path.join(temp_dir, file.filename)
        
        # Write the file
        async with aiofiles.open(temp_file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        return temp_file_path
    except Exception as e:
        logger.error(f"Error creating temporary file: {str(e)}")
        raise StorageError(f"Failed to create temporary file: {str(e)}")


def create_temp_file(file_data, suffix=None) -> str:
    """Create a temporary file from file data."""
    try:
        # Create a temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        temp_file.close()
        
        # Write the file data
        with open(temp_file.name, 'wb') as f:
            f.write(file_data.read())
        
        return temp_file.name
    except Exception as e:
        logger.error(f"Error creating temporary file: {str(e)}")
        raise StorageError(f"Failed to create temporary file: {str(e)}")


__all__ = [
    "StorageProvider",
    "StorageError",
    "S3StorageProvider", 
    "verify_s3_connection",
    "init_storage",
    "upload_video",
    "delete_video",
    "get_video_url",
    "create_temp_copy",
    "create_temp_file",
    "storage_provider",
    "LocalStorageProvider"
] 