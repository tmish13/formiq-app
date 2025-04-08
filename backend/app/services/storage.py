"""Service for handling file storage operations."""
from typing import Optional, BinaryIO, Dict, Any, List, Tuple
import os
import hashlib
import mimetypes
import time
from fastapi import UploadFile
from app.core.config import settings
from app.core.logging import get_logger
from app.core.cache import cache_service
from app.core.storage import storage_provider, StorageProvider
from app.core.exceptions import StorageError

logger = get_logger(__name__)

class StorageService:
    """Service for handling file storage operations."""
    
    def __init__(self, provider: Optional[StorageProvider] = None):
        """Initialize storage service with the storage provider.
        
        Args:
            provider: Storage provider to use (defaults to the global provider)
        """
        self.provider = provider or storage_provider
        self.max_upload_size = settings.MAX_CONTENT_LENGTH
        logger.info(f"Initialized storage service with provider: {self.provider.__class__.__name__}")

    async def upload_file(self, file: UploadFile, folder: str = "", user_id: str = None) -> str:
        """Upload a file and return its URL.
        
        Args:
            file: File to upload
            folder: Folder to store the file in
            user_id: Optional user ID for organization
            
        Returns:
            str: URL of the uploaded file
            
        Raises:
            StorageError: If upload fails
        """
        start_time = time.time()
        try:
            # Generate a unique file key with timestamp and hash
            timestamp = int(time.time())
            file_hash = hashlib.md5(f"{file.filename}_{timestamp}".encode()).hexdigest()[:10]
            safe_filename = self._sanitize_filename(file.filename)
            
            # Create file path with folder structure for better organization
            folder_path = f"{folder}/{user_id}" if user_id else folder
            file_key = f"{folder_path}/{timestamp}_{file_hash}_{safe_filename}" if folder_path else f"{timestamp}_{file_hash}_{safe_filename}"
            
            # Set appropriate content type
            content_type = file.content_type
            if not content_type or content_type == "application/octet-stream":
                # Try to guess from filename
                guessed_type, _ = mimetypes.guess_type(file.filename)
                if guessed_type:
                    content_type = guessed_type
            
            # Create metadata
            metadata = {
                "original_filename": file.filename,
                "upload_timestamp": str(timestamp),
                "user_id": str(user_id) if user_id else "anonymous"
            }
            
            # Read the file into memory
            file_content = await file.read()
            # Rewind the file for future read operations
            await file.seek(0)
            
            # Convert to a file-like object
            from io import BytesIO
            file_obj = BytesIO(file_content)
            
            # Upload the file using storage provider
            url = await self.provider.upload_file(
                file_obj,
                file_key,
                content_type=content_type,
                metadata=metadata,
                public=True
            )
            
            duration = time.time() - start_time
            logger.info(f"Successfully uploaded file to {url} in {duration:.2f}s")
            return url
                
        except Exception as e:
            logger.error(f"Failed to upload file: {str(e)}")
            raise StorageError(f"Failed to upload file: {str(e)}")

    async def delete_file(self, file_url: str) -> None:
        """Delete a file using its URL.
        
        Args:
            file_url: URL of the file to delete
            
        Raises:
            StorageError: If deletion fails
        """
        try:
            # Extract key from URL
            file_key = self.provider.get_key_from_url(file_url)
            
            # Delete the file
            success = await self.provider.delete_file(file_key)
            
            if success:
                logger.info(f"Successfully deleted file {file_key}")
            else:
                logger.warning(f"File not found or failed to delete: {file_key}")
                
        except Exception as e:
            logger.error(f"Failed to delete file: {str(e)}")
            raise StorageError(f"Failed to delete file: {str(e)}")

    async def get_file_info(self, file_url: str) -> Dict[str, Any]:
        """Get file metadata.
        
        Args:
            file_url: URL of the file
            
        Returns:
            Dict[str, Any]: File metadata
            
        Raises:
            StorageError: If retrieval fails
        """
        # First check the cache
        cache_key = f"file_info:{file_url}"
        if cache_service.available:
            cached_info = await cache_service.get(cache_key)
            if cached_info:
                return cached_info
        
        try:
            # Extract key from URL
            file_key = self.provider.get_key_from_url(file_url)
            
            # Get file data and metadata
            _, metadata = await self.provider.get_file(file_key)
            
            # Standardize metadata format
            info = {
                "ContentLength": metadata.get("content_length", 0),
                "LastModified": metadata.get("last_modified"),
                "ContentType": metadata.get("content_type", "application/octet-stream"),
                "Metadata": metadata.get("metadata", {})
            }
            
            # Cache the result
            if cache_service.available:
                await cache_service.set(cache_key, info, expire=3600)  # Cache for 1 hour
                
            return info
            
        except FileNotFoundError:
            logger.warning(f"File not found: {file_url}")
            raise StorageError(f"File not found: {file_url}")
        except Exception as e:
            logger.error(f"Failed to get file info: {str(e)}")
            raise StorageError(f"Failed to get file info: {str(e)}")

    async def download_file(self, file_url: str) -> bytes:
        """Download a file and return its contents as bytes.
        
        Args:
            file_url: URL of the file
            
        Returns:
            bytes: File contents
            
        Raises:
            StorageError: If download fails
        """
        try:
            # Extract key from URL
            file_key = self.provider.get_key_from_url(file_url)
            
            # Get file data
            data, _ = await self.provider.get_file(file_key)
            
            logger.info(f"Successfully downloaded file {file_key}")
            return data
            
        except FileNotFoundError:
            logger.warning(f"File not found: {file_url}")
            raise StorageError(f"File not found: {file_url}")
        except Exception as e:
            logger.error(f"Failed to download file: {str(e)}")
            raise StorageError(f"Failed to download file: {str(e)}")

    async def get_file_size(self, file_url: str) -> int:
        """Get file size in bytes.
        
        Args:
            file_url: URL of the file
            
        Returns:
            int: File size in bytes
            
        Raises:
            StorageError: If retrieval fails
        """
        try:
            # Use file info which is cached
            info = await self.get_file_info(file_url)
            return info.get("ContentLength", 0)
            
        except Exception as e:
            logger.error(f"Failed to get file size: {str(e)}")
            raise StorageError(f"Failed to get file size: {str(e)}")

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to be safe for storage.
        
        Args:
            filename: Original filename
            
        Returns:
            str: Sanitized filename
        """
        # Remove potentially unsafe characters
        import re
        safe_name = re.sub(r'[^\w\-\.]', '_', filename)
        
        # Ensure it doesn't start with a dot (hidden file)
        if safe_name.startswith('.'):
            safe_name = 'f' + safe_name
            
        return safe_name 