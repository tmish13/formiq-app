"""Service for handling file storage operations using S3."""
from typing import Optional, BinaryIO, Dict, Any, List
import os
import boto3
import aiofiles
import asyncio
from botocore.exceptions import ClientError
from fastapi import UploadFile
from app.core.config import settings
from app.core.logging import get_logger

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
        
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
            region_name=self.aws_region
        )

    async def upload_file(self, file: UploadFile, folder: str = "") -> str:
        """Upload a file to S3 and return its URL."""
        try:
            file_key = f"{folder}/{file.filename}" if folder else file.filename
            
            # Create temporary file
            temp_path = f"/tmp/{file.filename}"
            async with aiofiles.open(temp_path, 'wb') as out_file:
                content = await file.read()
                await out_file.write(content)
            
            # Upload file
            await asyncio.get_event_loop().run_in_executor(
                None,
                self.s3_client.upload_file,
                temp_path,
                self.s3_bucket,
                file_key,
                ExtraArgs={"ContentType": file.content_type}
            )
            
            # Clean up temporary file
            os.remove(temp_path)
            
            # Generate URL
            url = f"https://{self.s3_bucket}.s3.amazonaws.com/{file_key}"
            logger.info(f"Successfully uploaded file to {url}")
            return url
        except Exception as e:
            logger.error(f"Failed to upload file: {str(e)}")
            raise StorageError(f"Failed to upload file: {str(e)}")

    async def delete_file(self, file_url: str) -> None:
        """Delete a file from S3 using its URL."""
        try:
            # Extract key from URL
            file_key = file_url.split(f"{self.s3_bucket}.s3.amazonaws.com/")[1]
            
            # Delete file
            await asyncio.get_event_loop().run_in_executor(
                None,
                self.s3_client.delete_object,
                Bucket=self.s3_bucket,
                Key=file_key
            )
            logger.info(f"Successfully deleted file {file_key}")
        except Exception as e:
            logger.error(f"Failed to delete file: {str(e)}")
            raise StorageError(f"Failed to delete file: {str(e)}")

    async def get_file_info(self, file_url: str) -> Dict[str, Any]:
        """Get file metadata from S3."""
        try:
            # Extract key from URL
            file_key = file_url.split(f"{self.s3_bucket}.s3.amazonaws.com/")[1]
            
            # Get object metadata
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                self.s3_client.head_object,
                Bucket=self.s3_bucket,
                Key=file_key
            )
            
            return {
                "ContentLength": response.get("ContentLength", 0),
                "LastModified": response.get("LastModified"),
                "ContentType": response.get("ContentType", "application/octet-stream")
            }
        except Exception as e:
            logger.error(f"Failed to get file info: {str(e)}")
            raise StorageError(f"Failed to get file info: {str(e)}")

    async def generate_presigned_url(self, file_key: str, expiration: int = 3600) -> str:
        """Generate a presigned URL for file upload."""
        try:
            url = await asyncio.get_event_loop().run_in_executor(
                None,
                self.s3_client.generate_presigned_url,
                'put_object',
                Params={
                    'Bucket': self.s3_bucket,
                    'Key': file_key
                },
                ExpiresIn=expiration
            )
            logger.info(f"Generated presigned URL for {file_key}")
            return url
        except Exception as e:
            logger.error(f"Failed to generate presigned URL: {str(e)}")
            raise StorageError(f"Failed to generate presigned URL: {str(e)}")

    async def download_file(self, file_url: str) -> bytes:
        """Download a file from S3 and return its contents as bytes."""
        try:
            # Extract key from URL
            file_key = file_url.split(f"{self.s3_bucket}.s3.amazonaws.com/")[1]
            
            # Create temporary file
            temp_path = f"/tmp/{file_key.split('/')[-1]}"
            
            # Download file
            await asyncio.get_event_loop().run_in_executor(
                None,
                self.s3_client.download_file,
                self.s3_bucket,
                file_key,
                temp_path
            )
            
            # Read file contents
            async with aiofiles.open(temp_path, 'rb') as file:
                content = await file.read()
            
            # Clean up temporary file
            os.remove(temp_path)
            
            logger.info(f"Successfully downloaded file {file_key}")
            return content
        except Exception as e:
            logger.error(f"Failed to download file: {str(e)}")
            raise StorageError(f"Failed to download file: {str(e)}")

    async def get_file_size(self, file_url: str) -> int:
        """Get file size in bytes."""
        try:
            info = await self.get_file_info(file_url)
            return info["ContentLength"]
        except Exception as e:
            logger.error(f"Failed to get file size: {str(e)}")
            raise StorageError(f"Failed to get file size: {str(e)}")

    async def get_file_metadata(self, file_url: str) -> Dict[str, Any]:
        """Get file metadata including content type and size."""
        try:
            info = await self.get_file_info(file_url)
            return {
                "content_type": info["ContentType"],
                "size": info["ContentLength"],
                "last_modified": info["LastModified"]
            }
        except Exception as e:
            logger.error(f"Failed to get file metadata: {str(e)}")
            raise StorageError(f"Failed to get file metadata: {str(e)}")

    def validate_video_file(self, file: UploadFile) -> bool:
        """Validate video file type and size."""
        try:
            # Check content type
            if file.content_type not in settings.ALLOWED_VIDEO_TYPES:
                raise StorageError(f"Invalid video format. Allowed formats: {settings.ALLOWED_VIDEO_TYPES}")
            
            # Check file size
            if file.size > settings.MAX_CONTENT_LENGTH:
                raise StorageError(f"File size exceeds maximum limit of {settings.MAX_CONTENT_LENGTH} bytes")
            
            return True
        except Exception as e:
            logger.error(f"Video validation failed: {str(e)}")
            raise StorageError(f"Video validation failed: {str(e)}") 