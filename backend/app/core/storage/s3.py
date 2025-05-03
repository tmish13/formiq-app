"""S3 storage provider implementation."""
import os
from typing import Optional, Dict, Any, BinaryIO, Tuple, List
import aiobotocore
from aiobotocore.session import get_session
from fastapi import UploadFile
import boto3
from botocore.exceptions import ClientError

from app.core.config import settings
from app.core.logging import get_logger
from .base import StorageProvider

logger = get_logger(__name__)

class S3StorageProvider(StorageProvider):
    """S3 storage provider implementation."""
    
    def __init__(
        self,
        bucket_name: Optional[str] = None,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        region_name: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        """Initialize the S3 storage provider.
        
        Args:
            bucket_name: S3 bucket name
            aws_access_key_id: AWS access key ID
            aws_secret_access_key: AWS secret access key
            region_name: AWS region name
            base_url: Base URL for accessing files
        """
        self.bucket_name = bucket_name or settings.AWS_BUCKET_NAME
        self.aws_access_key_id = aws_access_key_id or settings.AWS_ACCESS_KEY_ID
        self.aws_secret_access_key = aws_secret_access_key or settings.AWS_SECRET_ACCESS_KEY
        self.region_name = region_name or settings.AWS_REGION
        self.base_url = base_url or f"https://{self.bucket_name}.s3.{self.region_name}.amazonaws.com"
        self.session = get_session()
    
    async def get_client(self):
        """Get an S3 client using async context manager."""
        return self.session.create_client(
            's3',
            region_name=self.region_name,
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
        )
    
    async def upload_file(
        self,
        file_data: BinaryIO,
        object_name: str,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        public: bool = False,
    ) -> str:
        """Upload a file to S3.
        
        Args:
            file_data: Binary file data
            object_name: Name to give the file
            content_type: Content type
            metadata: Metadata
            public: Whether the file is public
            
        Returns:
            str: URL to access the file
        """
        try:
            # Prepare upload parameters
            upload_args = {
                'Bucket': self.bucket_name,
                'Key': object_name,
                'Body': file_data,
            }
            
            if content_type:
                upload_args['ContentType'] = content_type
            
            if metadata:
                upload_args['Metadata'] = metadata
            
            if public:
                upload_args['ACL'] = 'public-read'
            
            # Upload file using context manager
            async with await self.get_client() as s3_client:
                await s3_client.put_object(**upload_args)
            
            # Create URL
            url = f"{self.base_url}/{object_name}"
            logger.info(f"Uploaded file to S3: {url}")
            
            return url
            
        except Exception as e:
            logger.error(f"Failed to upload file to S3: {str(e)}")
            raise
    
    async def delete_file(self, object_name: str) -> bool:
        """Delete a file from S3.
        
        Args:
            object_name: Name of the file
            
        Returns:
            bool: True if deletion was successful
        """
        try:
            async with await self.get_client() as s3_client:
                await s3_client.delete_object(
                    Bucket=self.bucket_name,
                    Key=object_name,
                )
            logger.info(f"Deleted file from S3: {object_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete file from S3: {str(e)}")
            return False
    
    async def list_files(self, prefix: str = "") -> List[Dict[str, Any]]:
        """List files in S3.
        
        Args:
            prefix: Path prefix to filter by
            
        Returns:
            List[Dict[str, Any]]: List of file information
        """
        try:
            async with await self.get_client() as s3_client:
                response = await s3_client.list_objects_v2(
                    Bucket=self.bucket_name,
                    Prefix=prefix,
                )
            
            files = []
            for obj in response.get('Contents', []):
                files.append({
                    'key': obj['Key'],
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'],
                    'url': f"{self.base_url}/{obj['Key']}"
                })
            
            return files
            
        except Exception as e:
            logger.error(f"Failed to list files in S3: {str(e)}")
            return []
    
    async def get_file(self, object_name: str) -> Tuple[bytes, Dict[str, Any]]:
        """Get a file from S3.
        
        Args:
            object_name: Name of the file
            
        Returns:
            Tuple[bytes, Dict[str, Any]]: File data and metadata
        """
        try:
            async with await self.get_client() as s3_client:
                response = await s3_client.get_object(
                    Bucket=self.bucket_name,
                    Key=object_name,
                )
                data = await response['Body'].read()
            
            metadata = {
                'content_length': response['ContentLength'],
                'last_modified': response['LastModified'],
                'content_type': response.get('ContentType'),
            }
            
            return data, metadata
            
        except Exception as e:
            logger.error(f"Failed to get file from S3: {str(e)}")
            raise
    
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
        
        # Find the index of the bucket name
        if '.amazonaws.com' in url:
            aws_index = url.index('.amazonaws.com')
            path = url[aws_index + 13:]  # Skip '.amazonaws.com/'
            return path
        
        # Fallback - just return the last part
        return parts[-1]

    async def verify_s3_connection(self) -> bool:
        """Verify S3 credentials and bucket access.
        
        This function attempts to connect to S3 and verify access to the 
        configured bucket.
        
        Returns:
            bool: True if credentials are valid and bucket is accessible
        """
        try:
            # Create S3 client
            s3_client = boto3.client(
                's3',
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key,
                region_name=self.region_name,
                endpoint_url=settings.AWS_S3_ENDPOINT
            )
            
            # Verify bucket exists by listing objects (limits to 1)
            s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                MaxKeys=1
            )
            
            logger.info(f"Successfully verified S3 access to bucket {self.bucket_name}")
            return True
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            logger.error(f"S3 verification failed: {error_code} - {str(e)}")
            return False
        except Exception as e:
            logger.error(f"S3 verification error: {str(e)}")
            return False

async def verify_s3_connection() -> bool:
    """Verify S3 credentials and bucket access.
    
    This function attempts to connect to S3 and verify access to the 
    configured bucket.
    
    Returns:
        bool: True if credentials are valid and bucket is accessible
    """
    # Skip verification if S3 is not configured
    if not settings.AWS_ACCESS_KEY_ID or not settings.AWS_SECRET_ACCESS_KEY:
        logger.warning("S3 credentials not configured")
        return False
        
    try:
        # Create S3 client
        s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
            endpoint_url=settings.AWS_S3_ENDPOINT
        )
        
        # Verify bucket exists by listing objects (limits to 1)
        s3_client.list_objects_v2(
            Bucket=settings.AWS_BUCKET_NAME,
            MaxKeys=1
        )
        
        logger.info(f"Successfully verified S3 access to bucket {settings.AWS_BUCKET_NAME}")
        return True
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        logger.error(f"S3 verification failed: {error_code} - {str(e)}")
        return False
    except Exception as e:
        logger.error(f"S3 verification error: {str(e)}")
        return False

# Create S3 storage provider instance
s3_storage = S3StorageProvider() 