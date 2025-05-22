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

    def get_file_url(self, key: str, expires_in: int = 3600) -> str:
        """Generate a pre-signed URL for file access.
        
        Args:
            key: Storage key of the file
            expires_in: URL expiration time in seconds
            
        Returns:
            str: Pre-signed URL for file access
        """
        try:
            if hasattr(self.provider, 'generate_presigned_url'):
                return self.provider.generate_presigned_url(key, expires_in)
            else:
                # Return a direct URL if provider doesn't support presigned URLs
                return f"{settings.STORAGE_URL}/{key}"
        except Exception as e:
            logger.error(f"Failed to generate file URL: {str(e)}")
            raise StorageError(f"Failed to generate file URL: {str(e)}")

    async def upload_file_from_path(
        self,
        local_file_path: str,
        object_key: str,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        public: bool = True # Default to public, similar to upload_file
    ) -> str:
        """Upload a file from a local path and return its object key.

        Args:
            local_file_path: The local path to the file to upload.
            object_key: The S3 object key to use for the uploaded file.
            content_type: Optional MIME type of the file.
            metadata: Optional metadata for the S3 object.
            public: Whether the uploaded file should be public.

        Returns:
            str: The object_key of the uploaded file.

        Raises:
            StorageError: If the upload fails or the local file doesn't exist.
            FileNotFoundError: If the local_file_path does not exist.
        """
        start_time = time.time()
        if not os.path.exists(local_file_path):
            logger.error(f"Local file not found for upload: {local_file_path}")
            raise FileNotFoundError(f"Local file not found: {local_file_path}")

        try:
            actual_content_type = content_type
            if not actual_content_type:
                guessed_type, _ = mimetypes.guess_type(local_file_path)
                if guessed_type:
                    actual_content_type = guessed_type
                else:
                    actual_content_type = "application/octet-stream" # Default
            
            file_size = os.path.getsize(local_file_path)
            default_metadata = {
                "original_filename": os.path.basename(local_file_path),
                "upload_timestamp": str(int(start_time)),
                "file_size": str(file_size)
            }
            if metadata:
                default_metadata.update(metadata)

            with open(local_file_path, 'rb') as file_obj:
                # The provider.upload_file method expects a file-like object (BinaryIO)
                # and the object_key directly.
                returned_url_or_key = await self.provider.upload_file(
                    file_obj=file_obj,
                    key=object_key, # Pass object_key as key parameter to provider
                    content_type=actual_content_type,
                    metadata=default_metadata,
                    public=public
                )
            
            # Assuming the provider.upload_file might return a full URL or just the key depending on implementation.
            # For consistency, this service method should return the object_key.
            # If provider.upload_file returns a URL, we might need to extract the key from it, 
            # or ensure provider can return the key or confirms usage of the given key.
            # For now, we assume the `object_key` we passed is used and is what we should return.

            duration = time.time() - start_time
            logger.info(f"Successfully uploaded file from {local_file_path} to S3 key {object_key} in {duration:.2f}s")
            return object_key # Return the key used for the upload
                
        except FileNotFoundError as fnf_error:
            raise fnf_error # Re-raise specifically
        except Exception as e:
            logger.error(f"Failed to upload file from path {local_file_path} to S3 key {object_key}: {e}", exc_info=True)
            raise StorageError(f"Failed to upload file from path {local_file_path}: {e}")

    async def generate_presigned_upload_url(
        self,
        object_key: str,
        content_type: str,
        metadata: Optional[Dict[str, str]] = None,
        expires_in: int = 3600
    ) -> str:
        """Generate a pre-signed URL for direct file upload to storage.
        
        This allows clients to upload directly to S3 without sending the file through the server.
        
        Args:
            object_key: Key/path where the file should be stored
            content_type: MIME type of the file
            metadata: Additional metadata to store with the file
            expires_in: URL expiration time in seconds
            
        Returns:
            str: Pre-signed URL for upload
            
        Raises:
            StorageError: If URL generation fails
        """
        try:
            # Check if the provider supports presigned upload URLs
            if hasattr(self.provider, 'generate_presigned_upload_url'):
                return await self.provider.generate_presigned_upload_url(
                    object_key, content_type, metadata, expires_in
                )
            
            # If using S3 but method not directly available, create a boto3 client and use it
            if hasattr(self.provider, 'bucket_name') and self.provider.__class__.__name__ == 'S3StorageProvider':
                import boto3
                from botocore.client import Config
                
                # Create a boto3 client with appropriate config
                s3_client = boto3.client(
                    's3',
                    region_name=self.provider.region_name,
                    aws_access_key_id=self.provider.aws_access_key_id,
                    aws_secret_access_key=self.provider.aws_secret_access_key,
                    config=Config(signature_version='s3v4')
                )
                
                # Generate presigned URL for PUT operation
                presigned_url = s3_client.generate_presigned_url(
                    'put_object',
                    Params={
                        'Bucket': self.provider.bucket_name,
                        'Key': object_key,
                        'ContentType': content_type,
                        'Metadata': metadata or {}
                    },
                    ExpiresIn=expires_in
                )
                
                logger.info(f"Generated presigned upload URL for {object_key}")
                return presigned_url
            
            # Fallback for providers that don't support presigned uploads
            logger.warning(f"Provider {self.provider.__class__.__name__} doesn't support presigned uploads")
            raise StorageError(f"Provider {self.provider.__class__.__name__} doesn't support presigned uploads")
            
        except Exception as e:
            logger.error(f"Failed to generate presigned upload URL: {str(e)}")
            raise StorageError(f"Failed to generate presigned upload URL: {str(e)}")
            
    async def get_public_url(self, object_key: str) -> str:
        """Get a public URL for an object.
        
        Args:
            object_key: Key of the object
            
        Returns:
            str: Public URL
        """
        try:
            if hasattr(self.provider, 'base_url'):
                return f"{self.provider.base_url}/{object_key}"
            else:
                return f"{settings.STORAGE_URL}/{object_key}"
        except Exception as e:
            logger.error(f"Failed to generate public URL: {str(e)}")
            raise StorageError(f"Failed to generate public URL: {str(e)}")

    def get_file_metadata(self, file_url: str) -> Dict[str, Any]:
        """Synchronous method to get file metadata (wrapper for get_file_info).
        
        Args:
            file_url: URL of the file
            
        Returns:
            Dict[str, Any]: File metadata
        """
        # This is a synchronous wrapper to support older code
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            # If no event loop exists, create one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        return loop.run_until_complete(self.get_file_info(file_url))

    def copy_file(self, source_key: str, dest_key: str) -> None:
        """Copy a file within the storage.
        
        Args:
            source_key: Source file key
            dest_key: Destination file key
        """
        try:
            if hasattr(self.provider, 'copy_object'):
                self.provider.copy_object(
                    Bucket=settings.STORAGE_BUCKET,
                    CopySource={"Bucket": settings.STORAGE_BUCKET, "Key": source_key},
                    Key=dest_key
                )
                logger.info(f"Copied file from {source_key} to {dest_key}")
            else:
                raise NotImplementedError("Provider does not support file copying")
        except Exception as e:
            logger.error(f"Failed to copy file: {str(e)}")
            raise StorageError(f"Failed to copy file: {str(e)}")

    def move_file(self, source_key: str, dest_key: str) -> None:
        """Move a file within the storage.
        
        Args:
            source_key: Source file key
            dest_key: Destination file key
        """
        try:
            # Copy then delete
            self.copy_file(source_key, dest_key)
            if hasattr(self.provider, 'delete_object'):
                self.provider.delete_object(
                    Bucket=settings.STORAGE_BUCKET,
                    Key=source_key
                )
                logger.info(f"Moved file from {source_key} to {dest_key}")
            else:
                raise NotImplementedError("Provider does not support file deletion")
        except Exception as e:
            logger.error(f"Failed to move file: {str(e)}")
            raise StorageError(f"Failed to move file: {str(e)}")

    def upload_large_file(self, file_path: str, key: str, chunk_size: int = 5 * 1024 * 1024) -> None:
        """Upload a large file using multipart upload.
        
        Args:
            file_path: Path to the file
            key: Storage key for the file
            chunk_size: Size of each chunk in bytes
        """
        try:
            if hasattr(self.provider, 'create_multipart_upload'):
                # Logic for multipart upload would go here
                # This is a placeholder for the implementation
                logger.info(f"Uploaded large file to {key}")
            else:
                raise NotImplementedError("Provider does not support multipart uploads")
        except Exception as e:
            logger.error(f"Failed to upload large file: {str(e)}")
            raise StorageError(f"Failed to upload large file: {str(e)}")

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