"""Amazon S3 storage provider for media files."""
import asyncio
from typing import Dict, Any, Optional, BinaryIO, Tuple, List
import base64
import mimetypes
import aiobotocore.session
from aiobotocore.config import AioConfig
from botocore.exceptions import ClientError, ConnectionError, EndpointConnectionError, NoCredentialsError

from app.core.config import settings
from app.core.logging import get_logger
from app.core.storage import StorageProvider

logger = get_logger(__name__)

# Define S3 specific exceptions for better error handling
class S3ConnectionError(Exception):
    """Error connecting to S3 service."""
    pass

class S3AuthenticationError(Exception):
    """Error authenticating with S3 service."""
    pass

class S3OperationError(Exception):
    """Error performing S3 operation."""
    pass

class S3StorageProvider(StorageProvider):
    """AWS S3 storage provider for media files."""
    
    def __init__(
        self,
        bucket_name: Optional[str] = None,
        aws_access_key: Optional[str] = None,
        aws_secret_key: Optional[str] = None,
        region: Optional[str] = None,
        endpoint_url: Optional[str] = None,
        max_retries: int = 3,
        retry_delay: float = 0.5,
    ):
        """Initialize S3 storage provider.
        
        Args:
            bucket_name: S3 bucket name
            aws_access_key: AWS access key ID
            aws_secret_key: AWS secret access key
            region: AWS region
            endpoint_url: S3 endpoint URL (for non-AWS S3 services)
            max_retries: Maximum number of retry attempts for transient errors
            retry_delay: Base delay between retries in seconds (uses exponential backoff)
        """
        self.bucket_name = bucket_name or settings.AWS_BUCKET_NAME
        self.aws_access_key = aws_access_key or settings.AWS_ACCESS_KEY_ID
        self.aws_secret_key = aws_secret_key or settings.AWS_SECRET_ACCESS_KEY
        self.region = region or settings.AWS_REGION
        self.endpoint_url = endpoint_url or settings.AWS_S3_ENDPOINT
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        logger.info(f"Initialized S3 storage provider for bucket: {self.bucket_name}")
    
    async def get_client(self):
        """Get S3 client session.
        
        Returns:
            S3 client session
        """
        session = aiobotocore.session.get_session()
        
        client_kwargs = {
            'region_name': self.region,
            'aws_access_key_id': self.aws_access_key,
            'aws_secret_access_key': self.aws_secret_key,
            'config': AioConfig(
                signature_version='s3v4',
                connect_timeout=10,  # 10 seconds connection timeout
                read_timeout=30,     # 30 seconds read timeout
                retries={'max_attempts': 3}  # Default boto retries
            ),
        }
        
        # Use endpoint_url if specified (for non-AWS S3 services)
        if self.endpoint_url:
            client_kwargs['endpoint_url'] = self.endpoint_url
        
        return session.create_client('s3', **client_kwargs)
    
    async def _execute_with_retry(self, operation_func, *args, **kwargs):
        """Execute an S3 operation with retry logic for transient errors.
        
        Args:
            operation_func: Async function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            Any: Result of the operation function
            
        Raises:
            S3ConnectionError: If connection to S3 fails after retries
            S3AuthenticationError: If authentication with S3 fails
            S3OperationError: If the S3 operation fails after retries
        """
        retries = 0
        last_exception = None
        
        while retries <= self.max_retries:
            try:
                return await operation_func(*args, **kwargs)
            except (ConnectionError, EndpointConnectionError) as e:
                last_exception = e
                logger.warning(f"S3 connection error (attempt {retries+1}/{self.max_retries+1}): {str(e)}")
            except NoCredentialsError as e:
                # Don't retry auth errors
                raise S3AuthenticationError(f"S3 authentication error: {str(e)}")
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', '')
                
                # Don't retry client errors that won't be resolved with retries
                if error_code in ['AccessDenied', 'InvalidAccessKeyId', 'SignatureDoesNotMatch']:
                    raise S3AuthenticationError(f"S3 authentication error ({error_code}): {str(e)}")
                elif error_code in ['NoSuchBucket', 'NoSuchKey']:
                    # Resource not found errors shouldn't be retried
                    if error_code == 'NoSuchKey':
                        raise FileNotFoundError(f"File not found in S3: {kwargs.get('Key', 'unknown')}")
                    raise S3OperationError(f"S3 resource error ({error_code}): {str(e)}")
                
                # For throttling and other transient errors, retry
                if error_code in ['SlowDown', 'RequestTimeout', 'RequestTimeTooSkewed', 'ServiceUnavailable', 'ThrottlingException']:
                    last_exception = e
                    logger.warning(f"S3 throttling error (attempt {retries+1}/{self.max_retries+1}): {error_code}")
                else:
                    # Other client errors - log and retry
                    last_exception = e
                    logger.warning(f"S3 client error (attempt {retries+1}/{self.max_retries+1}): {error_code} - {str(e)}")
            except Exception as e:
                # Unexpected error - log and retry
                last_exception = e
                logger.warning(f"Unexpected S3 error (attempt {retries+1}/{self.max_retries+1}): {str(e)}")
            
            # Exponential backoff with jitter
            if retries < self.max_retries:
                delay = self.retry_delay * (2 ** retries) * (0.9 + 0.2 * asyncio.get_event_loop().time() % 1)
                await asyncio.sleep(delay)
            
            retries += 1
        
        # If we got here, we exhausted retries
        if isinstance(last_exception, (ConnectionError, EndpointConnectionError)):
            raise S3ConnectionError(f"Failed to connect to S3 after {self.max_retries+1} attempts: {str(last_exception)}")
        
        raise S3OperationError(f"S3 operation failed after {self.max_retries+1} attempts: {str(last_exception)}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Check connectivity and permissions with the S3 service.
        
        Returns:
            Dict[str, Any]: Health check results
        """
        health_result = {
            "healthy": False,
            "bucket_exists": False,
            "can_list_objects": False,
            "can_write": False,
            "can_read": False,
            "can_delete": False,
            "error": None
        }
        
        try:
            async with await self.get_client() as client:
                # Check if bucket exists
                try:
                    await client.head_bucket(Bucket=self.bucket_name)
                    health_result["bucket_exists"] = True
                except ClientError as e:
                    error_code = e.response.get('Error', {}).get('Code', '')
                    error_msg = e.response.get('Error', {}).get('Message', str(e))
                    if error_code == '404':
                        health_result["error"] = f"Bucket {self.bucket_name} does not exist"
                    elif error_code == '403':
                        health_result["error"] = f"Access denied to bucket {self.bucket_name}"
                    else:
                        health_result["error"] = f"Error checking bucket: {error_code} - {error_msg}"
                    return health_result
                
                # Check list permission
                try:
                    await client.list_objects_v2(Bucket=self.bucket_name, MaxKeys=1)
                    health_result["can_list_objects"] = True
                except ClientError as e:
                    health_result["error"] = f"Cannot list objects: {e.response.get('Error', {}).get('Message', str(e))}"
                    return health_result
                
                # Check write permission with a test object
                test_key = f"_health_check/{asyncio.get_event_loop().time()}.txt"
                test_content = b"S3 health check"
                try:
                    await client.put_object(
                        Bucket=self.bucket_name,
                        Key=test_key,
                        Body=test_content,
                        ContentType="text/plain"
                    )
                    health_result["can_write"] = True
                    
                    # Check read permission
                    try:
                        response = await client.get_object(Bucket=self.bucket_name, Key=test_key)
                        data = await response['Body'].read()
                        if data == test_content:
                            health_result["can_read"] = True
                        else:
                            health_result["error"] = "Read verification failed: content mismatch"
                    except ClientError as e:
                        health_result["error"] = f"Cannot read objects: {e.response.get('Error', {}).get('Message', str(e))}"
                    
                    # Check delete permission
                    try:
                        await client.delete_object(Bucket=self.bucket_name, Key=test_key)
                        health_result["can_delete"] = True
                    except ClientError as e:
                        health_result["error"] = f"Cannot delete objects: {e.response.get('Error', {}).get('Message', str(e))}"
                        
                except ClientError as e:
                    health_result["error"] = f"Cannot write objects: {e.response.get('Error', {}).get('Message', str(e))}"
                    return health_result
                
                # Overall health is good only if all checks passed
                health_result["healthy"] = (
                    health_result["bucket_exists"] and
                    health_result["can_list_objects"] and
                    health_result["can_write"] and
                    health_result["can_read"] and
                    health_result["can_delete"]
                )
                
                return health_result
                
        except NoCredentialsError:
            health_result["error"] = "No credentials found for S3 access"
        except ConnectionError as e:
            health_result["error"] = f"Connection error: {str(e)}"
        except Exception as e:
            health_result["error"] = f"Unexpected error: {str(e)}"
            
        return health_result
    
    async def upload_file(
        self,
        file_data: BinaryIO,
        object_name: str,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        public: bool = False,
    ) -> str:
        """Upload a file to S3 storage.
        
        Args:
            file_data: Binary file data
            object_name: S3 object key
            content_type: Content type of the file
            metadata: Additional metadata for the file
            public: Whether the file should be publicly accessible
            
        Returns:
            str: URL of the uploaded file
            
        Raises:
            S3ConnectionError: If connection to S3 fails
            S3AuthenticationError: If authentication with S3 fails
            S3OperationError: If the S3 operation fails
        """
        # Determine content type if not provided
        if not content_type:
            content_type, _ = mimetypes.guess_type(object_name)
            content_type = content_type or 'application/octet-stream'
        
        # Prepare extra args
        extra_args = {
            'ContentType': content_type,
        }
        
        # Set appropriate ACL based on public flag or default setting
        public_access = public or settings.S3_PUBLIC_ACCESS
        if public_access:
            extra_args['ACL'] = 'public-read'
        
        # Add metadata if provided
        if metadata:
            extra_args['Metadata'] = metadata
        
        # Get the client and upload file
        async with await self.get_client() as client:
            file_content = file_data.read()
            
            async def _do_upload():
                await client.put_object(
                    Bucket=self.bucket_name,
                    Key=object_name,
                    Body=file_content,
                    **extra_args
                )
                
                # Return URL - public if accessible, or presigned URL if private
                if public_access:
                    if self.endpoint_url:
                        url = f"{self.endpoint_url}/{self.bucket_name}/{object_name}"
                    else:
                        url = f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{object_name}"
                else:
                    # Generate a pre-signed URL for private files
                    url = await client.generate_presigned_url(
                        'get_object',
                        Params={'Bucket': self.bucket_name, 'Key': object_name},
                        ExpiresIn=3600  # 1 hour
                    )
                
                logger.info(f"Uploaded file to S3: {object_name}")
                return url
            
            return await self._execute_with_retry(_do_upload)
    
    async def delete_file(self, object_name: str) -> bool:
        """Delete a file from S3 storage.
        
        Args:
            object_name: S3 object key
            
        Returns:
            bool: True if deletion was successful
            
        Raises:
            S3ConnectionError: If connection to S3 fails
            S3AuthenticationError: If authentication with S3 fails
        """
        async with await self.get_client() as client:
            try:
                async def _do_delete():
                    await client.delete_object(
                        Bucket=self.bucket_name,
                        Key=object_name
                    )
                    logger.info(f"Deleted file from S3: {object_name}")
                    return True
                
                return await self._execute_with_retry(_do_delete)
            except FileNotFoundError:
                # Object not found is not an error for delete operation
                logger.warning(f"File not found for deletion: {object_name}")
                return False
            except (S3ConnectionError, S3AuthenticationError):
                # Re-raise connection and auth errors
                raise
            except Exception as e:
                logger.error(f"Error deleting file from S3: {str(e)}")
                return False
    
    async def list_files(self, prefix: str = "") -> List[Dict[str, Any]]:
        """List files in S3 storage.
        
        Args:
            prefix: Path prefix to filter by
            
        Returns:
            List[Dict[str, Any]]: List of file information
            
        Raises:
            S3ConnectionError: If connection to S3 fails
            S3AuthenticationError: If authentication with S3 fails
            S3OperationError: If the S3 operation fails
        """
        async with await self.get_client() as client:
            async def _do_list():
                paginator = client.get_paginator('list_objects_v2')
                files = []
                
                async for page in paginator.paginate(Bucket=self.bucket_name, Prefix=prefix):
                    for obj in page.get('Contents', []):
                        public_access = settings.S3_PUBLIC_ACCESS
                        
                        # Create URL
                        if public_access:
                            if self.endpoint_url:
                                url = f"{self.endpoint_url}/{self.bucket_name}/{obj['Key']}"
                            else:
                                url = f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{obj['Key']}"
                        else:
                            # For non-public files, generate a pre-signed URL
                            url = await client.generate_presigned_url(
                                'get_object',
                                Params={'Bucket': self.bucket_name, 'Key': obj['Key']},
                                ExpiresIn=3600  # 1 hour
                            )
                        
                        files.append({
                            'key': obj['Key'],
                            'size': obj['Size'],
                            'last_modified': obj['LastModified'],
                            'url': url
                        })
                
                return files
            
            try:
                return await self._execute_with_retry(_do_list)
            except Exception as e:
                logger.error(f"Error listing files in S3: {str(e)}")
                return []
    
    async def get_file(self, object_name: str) -> Tuple[bytes, Dict[str, Any]]:
        """Get a file from S3 storage.
        
        Args:
            object_name: S3 object key
            
        Returns:
            Tuple[bytes, Dict[str, Any]]: File data and metadata
            
        Raises:
            FileNotFoundError: If the file does not exist
            S3ConnectionError: If connection to S3 fails
            S3AuthenticationError: If authentication with S3 fails
            S3OperationError: If the S3 operation fails
        """
        async with await self.get_client() as client:
            async def _do_get():
                response = await client.get_object(
                    Bucket=self.bucket_name,
                    Key=object_name
                )
                
                # Read the data
                data = await response['Body'].read()
                
                # Extract metadata
                metadata = {
                    'content_type': response.get('ContentType'),
                    'content_length': response.get('ContentLength'),
                    'last_modified': response.get('LastModified'),
                    'metadata': response.get('Metadata', {})
                }
                
                return data, metadata
            
            try:
                return await self._execute_with_retry(_do_get)
            except FileNotFoundError:
                # Re-raise file not found errors
                raise
            except Exception as e:
                logger.error(f"Error getting file from S3: {str(e)}")
                raise S3OperationError(f"Failed to get file from S3: {str(e)}")
    
    @staticmethod
    def get_key_from_url(url: str) -> str:
        """Extract the key from a URL.
        
        Args:
            url: S3 URL
            
        Returns:
            str: S3 object key
        """
        # Remove query parameters if they exist
        if '?' in url:
            url = url.split('?')[0]
            
        # Try parsing AWS S3 URL format
        if 's3.amazonaws.com' in url:
            # Parse standard S3 URL: https://bucket-name.s3.region.amazonaws.com/key
            parts = url.split('.s3.')
            if len(parts) > 1:
                # Extract everything after the bucket name and region
                path_parts = parts[1].split('/', 1)
                if len(path_parts) > 1:
                    return path_parts[1]
        
        # Try custom endpoint format
        if settings.AWS_S3_ENDPOINT and settings.AWS_S3_ENDPOINT in url:
            # Parse custom endpoint URL: {endpoint}/{bucket}/{key}
            parts = url.replace(settings.AWS_S3_ENDPOINT, '').strip('/')
            bucket_parts = parts.split('/', 1)
            if len(bucket_parts) > 1 and bucket_parts[0] == settings.AWS_BUCKET_NAME:
                return bucket_parts[1]
        
        # Try direct bucket URL format
        bucket_prefix = f"/{settings.AWS_BUCKET_NAME}/"
        if bucket_prefix in url:
            # Find the bucket prefix and extract everything after it
            bucket_start = url.find(bucket_prefix)
            if bucket_start >= 0:
                key_part = url[bucket_start + len(bucket_prefix):]
                if key_part:
                    return key_part
        
        # Fallback - just return the last path component
        path_parts = url.split('/')
        return path_parts[-1] if path_parts[-1] else path_parts[-2]


# Create a singleton instance
s3_storage = S3StorageProvider() 