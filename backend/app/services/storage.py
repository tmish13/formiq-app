"""Service for handling file storage operations using S3."""
from typing import Optional, BinaryIO, Dict, Any, List, Tuple
import os
import boto3
import aiofiles
import asyncio
import time
import hashlib
import mimetypes
from botocore.exceptions import ClientError
from fastapi import UploadFile
from app.core.config import settings
from app.core.logging import get_logger
from app.core.cache import cache_service

logger = get_logger(__name__)

class StorageError(Exception):
    """Custom exception for storage service errors."""
    pass

class StorageService:
    """Service for handling file storage operations using S3."""
    
    def __init__(self):
        """Initialize storage service with S3 client."""
        self.aws_access_key_id = os.environ.get('AWS_ACCESS_KEY_ID', settings.AWS_ACCESS_KEY_ID)
        self.aws_secret_access_key = os.environ.get('AWS_SECRET_ACCESS_KEY', settings.AWS_SECRET_ACCESS_KEY)
        self.aws_region = os.environ.get('AWS_REGION', settings.AWS_REGION)
        self.s3_bucket = os.environ.get('S3_BUCKET', settings.S3_BUCKET)
        self.cdn_base_url = os.environ.get('CDN_BASE_URL', f"https://{self.s3_bucket}.s3.amazonaws.com")
        self.max_upload_size = int(os.environ.get('MAX_CONTENT_LENGTH', settings.MAX_CONTENT_LENGTH))
        
        # Initialize S3 client with session for better connection handling
        session = boto3.session.Session()
        self.s3_client = session.client(
            's3',
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
            region_name=self.aws_region,
            # Add better connection management for 1,000 users
            config=boto3.session.Config(
                max_pool_connections=50,  # Increased for 1,000 users
                connect_timeout=5,        # Shorter timeout (5s)
                read_timeout=60,          # Longer read timeout for uploads (60s)
                retries={'max_attempts': 3}  # Auto-retry 3 times
            )
        )
        logger.info(f"Initialized storage service with bucket: {self.s3_bucket}")

    async def upload_file(self, file: UploadFile, folder: str = "", user_id: str = None) -> str:
        """Upload a file to S3 and return its URL."""
        start_time = time.time()
        try:
            # Generate a unique file key with timestamp and hash
            timestamp = int(time.time())
            file_hash = hashlib.md5(f"{file.filename}_{timestamp}".encode()).hexdigest()[:10]
            safe_filename = self._sanitize_filename(file.filename)
            
            # Create file path with folder structure for better organization
            folder_path = f"{folder}/{user_id}" if user_id else folder
            file_key = f"{folder_path}/{timestamp}_{file_hash}_{safe_filename}" if folder_path else f"{timestamp}_{file_hash}_{safe_filename}"
            
            # Create temporary file
            temp_path = f"/tmp/{safe_filename}"
            try:
                async with aiofiles.open(temp_path, 'wb') as out_file:
                    # Read in chunks for memory efficiency with large files
                    chunk_size = 1024 * 1024  # 1MB chunks
                    while True:
                        chunk = await file.read(chunk_size)
                        if not chunk:
                            break
                        await out_file.write(chunk)
                
                # Set appropriate content type
                content_type = file.content_type
                if not content_type or content_type == "application/octet-stream":
                    # Try to guess from filename
                    guessed_type, _ = mimetypes.guess_type(file.filename)
                    if guessed_type:
                        content_type = guessed_type
                
                # Upload file with metadata
                extra_args = {
                    "ContentType": content_type,
                    "Metadata": {
                        "original_filename": file.filename,
                        "upload_timestamp": str(timestamp),
                        "user_id": str(user_id) if user_id else "anonymous"
                    }
                }
                
                # Add caching headers for static content
                if content_type and (content_type.startswith('video/') or content_type.startswith('image/')):
                    extra_args["CacheControl"] = "max-age=31536000"  # Cache for 1 year
                
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.s3_client.upload_file(
                        temp_path,
                        self.s3_bucket,
                        file_key,
                        ExtraArgs=extra_args
                    )
                )
                
                # Generate URL using CDN if available
                url = f"{self.cdn_base_url}/{file_key}"
                
                duration = time.time() - start_time
                logger.info(f"Successfully uploaded file to {url} in {duration:.2f}s")
                return url
                
            finally:
                # Clean up temporary file
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                    
        except ClientError as e:
            logger.error(f"S3 client error uploading file: {str(e)}")
            raise StorageError(f"S3 storage error: {str(e)}")
        except Exception as e:
            logger.error(f"Failed to upload file: {str(e)}")
            raise StorageError(f"Failed to upload file: {str(e)}")

    async def delete_file(self, file_url: str) -> None:
        """Delete a file from S3 using its URL."""
        try:
            # Extract key from URL
            file_key = self._extract_key_from_url(file_url)
            
            # Delete file
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.s3_client.delete_object(Bucket=self.s3_bucket, Key=file_key)
            )
            logger.info(f"Successfully deleted file {file_key}")
        except ClientError as e:
            logger.error(f"S3 client error deleting file: {str(e)}")
            raise StorageError(f"S3 storage error: {str(e)}")
        except Exception as e:
            logger.error(f"Failed to delete file: {str(e)}")
            raise StorageError(f"Failed to delete file: {str(e)}")

    async def get_file_info(self, file_url: str) -> Dict[str, Any]:
        """Get file metadata from S3."""
        # First check the cache
        cache_key = f"file_info:{file_url}"
        if cache_service.available:
            cached_info = await cache_service.get(cache_key)
            if cached_info:
                return cached_info
        
        try:
            # Extract key from URL
            file_key = self._extract_key_from_url(file_url)
            
            # Get object metadata
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.s3_client.head_object(Bucket=self.s3_bucket, Key=file_key)
            )
            
            info = {
                "ContentLength": response.get("ContentLength", 0),
                "LastModified": response.get("LastModified").isoformat() if response.get("LastModified") else None,
                "ContentType": response.get("ContentType", "application/octet-stream"),
                "Metadata": response.get("Metadata", {})
            }
            
            # Cache the result
            if cache_service.available:
                await cache_service.set(cache_key, info, expire=3600)  # Cache for 1 hour
                
            return info
            
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                logger.warning(f"File not found: {file_url}")
                raise StorageError(f"File not found: {file_url}")
            logger.error(f"S3 client error getting file info: {str(e)}")
            raise StorageError(f"S3 storage error: {str(e)}")
        except Exception as e:
            logger.error(f"Failed to get file info: {str(e)}")
            raise StorageError(f"Failed to get file info: {str(e)}")

    async def generate_presigned_url(self, 
                                    filename: str, 
                                    folder: str = "", 
                                    user_id: str = None, 
                                    content_type: str = None,
                                    expiration: int = 3600) -> Dict[str, Any]:
        """
        Generate a presigned URL for direct browser upload.
        
        Returns dict with url for upload and the final file url after upload.
        """
        try:
            # Generate a unique file key
            timestamp = int(time.time())
            file_hash = hashlib.md5(f"{filename}_{timestamp}_{user_id}".encode()).hexdigest()[:10]
            safe_filename = self._sanitize_filename(filename)
            
            # Create file path
            folder_path = f"{folder}/{user_id}" if user_id else folder
            file_key = f"{folder_path}/{timestamp}_{file_hash}_{safe_filename}" if folder_path else f"{timestamp}_{file_hash}_{safe_filename}"
            
            # Set content type if provided
            fields = None
            conditions = None
            
            if content_type:
                fields = {"Content-Type": content_type}
                conditions = [{"Content-Type": content_type}]
            
            # Generate POST policy for direct browser upload
            post_data = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.s3_client.generate_presigned_post(
                    Bucket=self.s3_bucket,
                    Key=file_key,
                    Fields=fields,
                    Conditions=conditions,
                    ExpiresIn=expiration
                )
            )
            
            # Return both the presigned URL data and the final URL
            final_url = f"{self.cdn_base_url}/{file_key}"
            
            logger.info(f"Generated presigned URL for {file_key}")
            return {
                "post_data": post_data,
                "file_url": final_url,
                "file_key": file_key,
            }
        except ClientError as e:
            logger.error(f"S3 client error generating presigned URL: {str(e)}")
            raise StorageError(f"S3 storage error: {str(e)}")
        except Exception as e:
            logger.error(f"Failed to generate presigned URL: {str(e)}")
            raise StorageError(f"Failed to generate presigned URL: {str(e)}")

    async def download_file(self, file_url: str) -> bytes:
        """Download a file from S3 and return its contents as bytes."""
        try:
            # Extract key from URL
            file_key = self._extract_key_from_url(file_url)
            
            # Create temporary file
            temp_path = f"/tmp/{os.path.basename(file_key)}"
            
            # Download file
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.s3_client.download_file(
                    self.s3_bucket,
                    file_key,
                    temp_path
                )
            )
            
            # Read file contents
            async with aiofiles.open(temp_path, 'rb') as file:
                content = await file.read()
            
            # Clean up temporary file
            os.remove(temp_path)
            
            logger.info(f"Successfully downloaded file {file_key} ({len(content)} bytes)")
            return content
        except ClientError as e:
            logger.error(f"S3 client error downloading file: {str(e)}")
            raise StorageError(f"S3 storage error: {str(e)}")
        except Exception as e:
            logger.error(f"Failed to download file: {str(e)}")
            raise StorageError(f"Failed to download file: {str(e)}")

    async def get_file_size(self, file_url: str) -> int:
        """Get file size in bytes."""
        try:
            # Check cache first
            cache_key = f"file_size:{file_url}"
            if cache_service.available:
                cached_size = await cache_service.get(cache_key)
                if cached_size is not None:
                    return int(cached_size)
            
            # Get from S3 if not cached
            info = await self.get_file_info(file_url)
            size = info["ContentLength"]
            
            # Cache the result
            if cache_service.available:
                await cache_service.set(cache_key, size, expire=3600)  # 1 hour
                
            return size
        except Exception as e:
            logger.error(f"Failed to get file size: {str(e)}")
            raise StorageError(f"Failed to get file size: {str(e)}")

    async def validate_video_file(self, file: UploadFile) -> Tuple[bool, str]:
        """
        Validate video file type, size and basic integrity.
        Returns (is_valid, error_message) tuple.
        """
        try:
            # Check content type
            allowed_types = settings.ALLOWED_VIDEO_TYPES
            if not file.content_type or file.content_type not in allowed_types:
                return False, f"Invalid video format. Allowed formats: {', '.join(allowed_types)}"
            
            # Read beginning of file to validate it's actually a video
            header = await file.read(2048)  # Read first 2KB
            await file.seek(0)  # Reset file position
            
            # Check for common video file signatures
            video_signatures = {
                b"\x00\x00\x00\x18ftypmp42": "mp4",
                b"\x00\x00\x00\x1cftypisom": "mp4",
                b"\x00\x00\x00\x20ftyp": "mp4",
                b"\x1aE\xdf\xa3": "webm"
            }
            
            is_valid_video = any(sig in header for sig in video_signatures)
            if not is_valid_video:
                return False, "File does not appear to be a valid video"
            
            # Check file size - use stream size or content length header
            if hasattr(file, "size") and file.size:
                file_size = file.size
            else:
                # Try to get size from headers or read the file
                try:
                    file_size = len(await file.read())
                    await file.seek(0)  # Reset file position
                except:
                    file_size = 0
            
            max_size = settings.MAX_CONTENT_LENGTH
            if file_size > max_size:
                return False, f"File size ({file_size} bytes) exceeds maximum limit of {max_size} bytes"
            
            # Check minimum file size to ensure it's not empty
            if file_size < 1024:  # Less than 1KB
                return False, "File is too small to be a valid video"
                
            return True, ""
        except Exception as e:
            logger.error(f"Video validation failed with error: {str(e)}")
            return False, f"Video validation failed: {str(e)}"
            
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to prevent path traversal and invalid characters."""
        # Remove path components
        filename = os.path.basename(filename)
        
        # Replace problematic characters
        for char in ['/', '\\', ':', '*', '?', '"', '<', '>', '|', ' ']:
            filename = filename.replace(char, '_')
            
        return filename
        
    def _extract_key_from_url(self, file_url: str) -> str:
        """Extract S3 key from file URL."""
        # Handle both S3 and CloudFront URLs
        if self.cdn_base_url in file_url:
            return file_url.split(self.cdn_base_url + "/")[1]
        elif f"{self.s3_bucket}.s3.amazonaws.com" in file_url:
            return file_url.split(f"{self.s3_bucket}.s3.amazonaws.com/")[1]
        elif ".amazonaws.com" in file_url:
            # Generic case for other S3 URL formats
            return '/'.join(file_url.split(".amazonaws.com/")[1:])
        else:
            # Assume the URL is already a key
            return file_url 