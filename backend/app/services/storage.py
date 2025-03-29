"""Service for handling file storage operations using S3."""
from typing import Optional, BinaryIO, Dict, Any
import os
import boto3
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

    def upload_file(self, file: UploadFile, folder: str = "") -> str:
        """Upload a file to S3 and return its URL."""
        try:
            file_key = f"{folder}/{file.filename}" if folder else file.filename
            
            # Upload file
            self.s3_client.upload_fileobj(
                file.file,
                self.s3_bucket,
                file_key,
                ExtraArgs={
                    "ContentType": file.content_type
                }
            )
            
            # Generate URL
            url = f"https://{self.s3_bucket}.s3.amazonaws.com/{file_key}"
            logger.info(f"Successfully uploaded file to {url}")
            return url
        except Exception as e:
            logger.error(f"Failed to upload file: {str(e)}")
            raise StorageError(f"Failed to upload file: {str(e)}")

    def delete_file(self, file_url: str) -> None:
        """Delete a file from S3 using its URL."""
        try:
            # Extract key from URL
            file_key = file_url.split(f"{self.s3_bucket}.s3.amazonaws.com/")[1]
            
            # Delete file
            self.s3_client.delete_object(
                Bucket=self.s3_bucket,
                Key=file_key
            )
            logger.info(f"Successfully deleted file {file_key}")
        except Exception as e:
            logger.error(f"Failed to delete file: {str(e)}")
            raise StorageError(f"Failed to delete file: {str(e)}")

    def get_file_info(self, file_url: str) -> Dict[str, Any]:
        """Get file metadata from S3."""
        try:
            # Extract key from URL
            file_key = file_url.split(f"{self.s3_bucket}.s3.amazonaws.com/")[1]
            
            # Get object metadata
            response = self.s3_client.head_object(
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

    def generate_presigned_url(self, file_key: str, expiration: int = 3600) -> str:
        """Generate a presigned URL for file upload."""
        try:
            url = self.s3_client.generate_presigned_url(
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

    def download_file(self, file_url: str, destination: str) -> None:
        """Download a file from S3 to local destination."""
        try:
            # Extract key from URL
            file_key = file_url.split(f"{self.s3_bucket}.s3.amazonaws.com/")[1]
            
            # Download file
            self.s3_client.download_file(
                self.s3_bucket,
                file_key,
                destination
            )
            logger.info(f"Successfully downloaded file to {destination}")
        except Exception as e:
            logger.error(f"Failed to download file: {str(e)}")
            raise StorageError(f"Failed to download file: {str(e)}") 