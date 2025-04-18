"""Storage provider factory module."""
from typing import Optional, Dict, Any, BinaryIO, Tuple, List
import importlib.util
import os
from fastapi import UploadFile
import uuid
import asyncio

from app.core.config import settings
from app.core.logging import get_logger
from .video import save_video, upload_video, delete_video, get_video_url
from .s3 import S3StorageProvider
from .base import StorageProvider

logger = get_logger(__name__)

__all__ = [
    'StorageProvider',
    'LocalStorageProvider',
    'S3StorageProvider',
    'get_storage_provider',
    'save_video',
    'upload_video',
    'delete_video',
    'get_video_url'
]

# Local file system storage provider
class LocalStorageProvider(StorageProvider):
    """Local file system storage provider."""
    
    def __init__(self, base_dir: Optional[str] = None, base_url: Optional[str] = None):
        """Initialize the local storage provider.
        
        Args:
            base_dir: Base directory for storing files
            base_url: Base URL for accessing files
        """
        self.base_dir = base_dir or settings.UPLOAD_DIR
        self.base_url = base_url or settings.UPLOAD_URL
        
        # Ensure the directory exists
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir, exist_ok=True)
            logger.info(f"Created storage directory: {self.base_dir}")
    
    async def upload_file(
        self,
        file_data: BinaryIO,
        object_name: str,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        public: bool = False,
    ) -> str:
        """Upload a file to local storage.
        
        Args:
            file_data: Binary file data
            object_name: Name to give the file
            content_type: Content type (unused for local storage)
            metadata: Metadata (unused for local storage)
            public: Whether the file is public (unused for local storage)
            
        Returns:
            str: URL to access the file
        """
        # Create the full path
        full_path = os.path.join(self.base_dir, object_name)
        
        # Ensure the directory exists
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        # Write the file
        with open(full_path, 'wb') as f:
            f.write(file_data.read())
        
        # Create the URL
        url = f"{self.base_url}/{object_name}"
        logger.info(f"Uploaded file to local storage: {full_path}")
        
        return url
    
    async def delete_file(self, object_name: str) -> bool:
        """Delete a file from local storage.
        
        Args:
            object_name: Name of the file
            
        Returns:
            bool: True if deletion was successful
        """
        full_path = os.path.join(self.base_dir, object_name)
        
        if os.path.exists(full_path):
            os.remove(full_path)
            logger.info(f"Deleted file from local storage: {full_path}")
            return True
        else:
            logger.warning(f"File not found for deletion: {full_path}")
            return False
    
    async def list_files(self, prefix: str = "") -> List[Dict[str, Any]]:
        """List files in local storage.
        
        Args:
            prefix: Path prefix to filter by
            
        Returns:
            List[Dict[str, Any]]: List of file information
        """
        path = os.path.join(self.base_dir, prefix)
        files = []
        
        if os.path.exists(path) and os.path.isdir(path):
            for root, _, filenames in os.walk(path):
                for filename in filenames:
                    # Get relative path from base_dir
                    rel_dir = os.path.relpath(root, self.base_dir)
                    rel_path = os.path.join(rel_dir, filename)
                    
                    # Normalize path for URL
                    rel_path = rel_path.replace("\\", "/")
                    
                    # Get file information
                    full_path = os.path.join(root, filename)
                    stat = os.stat(full_path)
                    
                    files.append({
                        'key': rel_path,
                        'size': stat.st_size,
                        'last_modified': stat.st_mtime,
                        'url': f"{self.base_url}/{rel_path}"
                    })
        
        return files
    
    async def get_file(self, object_name: str) -> Tuple[bytes, Dict[str, Any]]:
        """Get a file from local storage.
        
        Args:
            object_name: Name of the file
            
        Returns:
            Tuple[bytes, Dict[str, Any]]: File data and metadata
        """
        full_path = os.path.join(self.base_dir, object_name)
        
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"File not found: {full_path}")
        
        # Read the file
        with open(full_path, 'rb') as f:
            data = f.read()
        
        # Get file information
        stat = os.stat(full_path)
        metadata = {
            'content_length': stat.st_size,
            'last_modified': stat.st_mtime,
        }
        
        return data, metadata
    
    @staticmethod
    def get_key_from_url(url: str) -> str:
        """Extract the key from a URL.
        
        Args:
            url: File URL
            
        Returns:
            str: File key
        """
        # Extract the path from the URL
        parts = url.split('/')
        
        # Find the index of the uploads part
        if 'uploads' in parts:
            uploads_index = parts.index('uploads')
            # Return everything after "uploads/videos"
            return '/'.join(parts[uploads_index + 2:])
        
        # Fallback - just return the last part
        return parts[-1]


def get_storage_provider() -> StorageProvider:
    """Get the appropriate storage provider based on settings.
    
    Returns:
        StorageProvider: Storage provider instance
    """
    # Check if we should use S3
    should_use_s3 = getattr(settings, "USE_S3_STORAGE", False)
    environment = settings.ENVIRONMENT
    
    # For production environments, validate S3 configuration
    if should_use_s3:
        # Check if we're in production or explicitly enabled for other environments
        should_proceed = environment == "production" or getattr(settings, "FORCE_S3_STORAGE", False)
        
        if not should_proceed:
            logger.info("S3 storage is only enabled in production environment unless FORCE_S3_STORAGE=True")
            logger.info(f"Using local storage provider at {settings.UPLOAD_DIR}")
            return LocalStorageProvider()
        
        # Validate S3 configuration
        missing_configs = []
        
        # Verify AWS credentials are set
        if not settings.AWS_ACCESS_KEY_ID:
            missing_configs.append("AWS_ACCESS_KEY_ID")
        if not settings.AWS_SECRET_ACCESS_KEY:
            missing_configs.append("AWS_SECRET_ACCESS_KEY")
        if not settings.AWS_REGION:
            missing_configs.append("AWS_REGION")
        if not settings.AWS_BUCKET_NAME:
            missing_configs.append("AWS_BUCKET_NAME")
        
        if missing_configs:
            missing_str = ", ".join(missing_configs)
            logger.warning(f"S3 storage requested but missing required configuration: {missing_str}")
            logger.warning("Falling back to local storage for safety.")
            return LocalStorageProvider()
        
        try:
            # Import the S3 storage provider
            if importlib.util.find_spec("app.core.storage.s3"):
                try:
                    # Check if the required dependency is available
                    import aiobotocore
                    from app.core.storage.s3 import s3_storage
                    logger.info(f"Using S3 storage provider with bucket: {settings.AWS_BUCKET_NAME}")
                    return s3_storage
                except ImportError as e:
                    logger.error(f"S3 dependencies not available: {str(e)}")
                    logger.error("Install required packages with: pip install aiobotocore")
                    logger.warning("Falling back to local storage.")
            else:
                logger.warning("S3 storage module not found. Falling back to local storage.")
        except Exception as e:
            logger.error(f"Failed to initialize S3 storage provider: {str(e)}")
            logger.warning("Falling back to local storage.")
    
    # Use local storage
    logger.info(f"Using local storage provider at {settings.UPLOAD_DIR}")
    return LocalStorageProvider()


# Create a storage provider instance
storage_provider = get_storage_provider()


async def upload_video(file: UploadFile) -> str:
    """Upload a video file to storage.
    
    Args:
        file: Video file to upload
        
    Returns:
        str: URL to access the uploaded video
    """
    # Reset file cursor to beginning
    await file.seek(0)
    
    # Generate a unique filename
    filename = f"{uuid.uuid4()}{os.path.splitext(file.filename)[1]}"
    
    # Store in videos subdirectory
    object_name = f"videos/{filename}"
    
    # Upload using the storage provider
    return await storage_provider.upload_file(
        file_data=file.file,
        object_name=object_name,
        content_type=file.content_type,
        metadata={"original_filename": file.filename},
        public=True,
    )


async def delete_video(video_url: str) -> bool:
    """Delete a video from storage.
    
    Args:
        video_url: URL of the video to delete
        
    Returns:
        bool: True if deletion was successful
    """
    # Get the object key from the URL
    object_name = storage_provider.get_key_from_url(video_url)
    
    # Delete the file
    return await storage_provider.delete_file(object_name) 