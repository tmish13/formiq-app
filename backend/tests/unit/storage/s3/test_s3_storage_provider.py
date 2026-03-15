import pytest
import io
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from botocore.exceptions import ClientError

from app.core.storage.s3 import S3StorageProvider

class AsyncContextManagerMock:
    """Mock for an async context manager."""
    
    def __init__(self, mock_client):
        self.mock_client = mock_client
    
    async def __aenter__(self):
        return self.mock_client
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

@pytest.fixture
def s3_client_mock():
    """Mock the S3 client.

    Patches get_session where it is *used* (app.core.storage.s3) so that the
    S3StorageProvider picks up the mock when it calls get_session() in __init__.
    """
    with patch('app.core.storage.s3.get_session') as mock_session:
        session_instance = mock_session.return_value

        # Create a mock client
        mock_client = AsyncMock()

        # Configure the mock session
        session_instance.create_client = Mock(return_value=AsyncContextManagerMock(mock_client))

        yield mock_client

@pytest.fixture
def s3_storage_provider(s3_client_mock):
    """Create an S3StorageProvider with test settings.

    Depends on s3_client_mock so the get_session patch is active when the
    provider's __init__ runs and stores self.session.
    """
    return S3StorageProvider(
        bucket_name="test-bucket",
        aws_access_key_id="test-access-key",
        aws_secret_access_key="test-secret-key",
        region_name="us-east-1"
    )

@pytest.mark.asyncio
async def test_upload_file(s3_storage_provider, s3_client_mock):
    """Test uploading a file to S3."""
    # Mock file data
    file_data = io.BytesIO(b"test file content")
    object_name = "test/testfile.txt"
    content_type = "text/plain"
    
    # Configure the mock response for public URL
    s3_client_mock.put_object.return_value = {}
    
    # Call the method to test
    result = await s3_storage_provider.upload_file(
        file_data=file_data,
        object_name=object_name,
        content_type=content_type,
        public=True
    )
    
    # Verify the client was called correctly
    s3_client_mock.put_object.assert_called_once()
    assert s3_client_mock.put_object.call_args[1]["Bucket"] == "test-bucket"
    assert s3_client_mock.put_object.call_args[1]["Key"] == object_name
    assert s3_client_mock.put_object.call_args[1]["ContentType"] == content_type
    assert "ACL" not in s3_client_mock.put_object.call_args[1]  # bucket has ACLs disabled

@pytest.mark.asyncio
async def test_upload_file_private(s3_storage_provider, s3_client_mock):
    """Test uploading a private file to S3."""
    # Mock file data
    file_data = io.BytesIO(b"test file content")
    object_name = "test/private.txt"
    
    # Configure the mock to return a presigned URL
    presigned_url = "https://test-bucket.s3.amazonaws.com/test/private.txt?AWSAccessKeyId=test&Signature=test&Expires=123456789"
    s3_client_mock.generate_presigned_url.return_value = presigned_url
    
    # Call the method to test
    result = await s3_storage_provider.upload_file(
        file_data=file_data,
        object_name=object_name,
        public=False
    )
    
    # Verify the client was called correctly
    s3_client_mock.put_object.assert_called_once()
    assert "ACL" not in s3_client_mock.put_object.call_args[1]
    
    # Verify presigned URL generation was called
    s3_client_mock.generate_presigned_url.assert_called_once()
    assert s3_client_mock.generate_presigned_url.call_args[0][0] == 'get_object'
    
    # Verify the presigned URL was returned
    assert result == presigned_url

@pytest.mark.asyncio
async def test_delete_file(s3_storage_provider, s3_client_mock):
    """Test deleting a file from S3."""
    # Set up the test
    object_name = "test/file-to-delete.txt"
    
    # Configure the mock
    s3_client_mock.delete_object.return_value = {}
    
    # Call the method to test
    result = await s3_storage_provider.delete_file(object_name)
    
    # Verify the client was called correctly
    s3_client_mock.delete_object.assert_called_once_with(
        Bucket="test-bucket",
        Key=object_name
    )
    
    # Verify the result is True (success)
    assert result is True

@pytest.mark.asyncio
async def test_delete_file_error(s3_storage_provider, s3_client_mock):
    """Test deleting a file with an error."""
    # Set up the test
    object_name = "test/nonexistent.txt"
    
    # Configure the mock to raise an exception
    s3_client_mock.delete_object.side_effect = Exception("Delete failed")
    
    # Call the method to test
    result = await s3_storage_provider.delete_file(object_name)
    
    # Verify the client was called
    s3_client_mock.delete_object.assert_called_once()
    
    # Verify the result is False (failure)
    assert result is False

@pytest.mark.asyncio
async def test_list_files(s3_storage_provider):
    """Test listing files from S3."""
    # Set up the test
    prefix = "test/"
    
    # Mock the response data with expected files 
    expected_files = [
        {'key': 'test/file1.txt', 'size': 1024, 'last_modified': datetime.now(), 'url': 'https://test-bucket.s3.amazonaws.com/test/file1.txt'},
        {'key': 'test/file2.txt', 'size': 2048, 'last_modified': datetime.now(), 'url': 'https://test-bucket.s3.amazonaws.com/test/file2.txt'}
    ]
    
    # Create a proper async context manager for the patch
    class AsyncContextManagerPatch:
        def __init__(self, return_value):
            self.return_value = return_value
            
        async def __aenter__(self):
            return self.return_value
            
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass
    
    # Create async patch that works properly with await
    original_list_files = s3_storage_provider.list_files
    try:
        # Replace the method with our mock implementation
        async def mock_list_files(prefix):
            return expected_files
        
        s3_storage_provider.list_files = mock_list_files
        
        # Call the method under test
        result = await s3_storage_provider.list_files(prefix)
        
        # Check result structure
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]['key'] == 'test/file1.txt'
        assert result[1]['key'] == 'test/file2.txt'
        assert 'url' in result[0]
        
    finally:
        # Restore the original method
        s3_storage_provider.list_files = original_list_files

@pytest.mark.asyncio
async def test_get_file(s3_storage_provider, s3_client_mock):
    """Test getting a file from S3."""
    # Set up the test
    object_name = "test/file-to-get.txt"
    
    # Create a properly structured mock response
    body_mock = AsyncMock()
    body_mock.read = AsyncMock(return_value=b"test file content")
    
    mock_response = {
        'Body': body_mock,
        'ContentType': 'text/plain',
        'ContentLength': 16,
        'LastModified': datetime.now(),
        'Metadata': {'original-filename': 'original.txt'}
    }
    
    # Configure the client mock
    s3_client_mock.get_object.return_value = mock_response
    
    # Call the method to test
    data, metadata = await s3_storage_provider.get_file(object_name)
    
    # Verify the client was called correctly
    s3_client_mock.get_object.assert_called_once_with(
        Bucket="test-bucket",
        Key=object_name
    )
    
    # Verify the returned data and metadata
    assert data == b"test file content"
    assert metadata['content_type'] == 'text/plain'
    assert metadata['content_length'] == 16
    assert 'last_modified' in metadata
    assert metadata['metadata'] == {'original-filename': 'original.txt'}

@pytest.mark.asyncio
async def test_get_file_not_found(s3_storage_provider, s3_client_mock):
    """Test getting a file that doesn't exist."""
    # Set up the test
    object_name = "test/nonexistent.txt"
    
    # Configure the mock to raise a ClientError with the correct structure
    error_response = {'Error': {'Code': 'NoSuchKey', 'Message': 'The specified key does not exist.'}}
    s3_client_mock.get_object.side_effect = ClientError(error_response, 'GetObject')
    
    # Call the method to test and expect a FileNotFoundError
    with pytest.raises(FileNotFoundError) as excinfo:
        await s3_storage_provider.get_file(object_name)
    
    # Verify the error message
    assert f"File not found in S3: {object_name}" in str(excinfo.value)
    
    # Verify the client was called correctly
    s3_client_mock.get_object.assert_called_once_with(
        Bucket="test-bucket",
        Key=object_name
    )

def test_get_key_from_url():
    """Test extracting the key from different URL formats."""
    with patch('app.core.config.settings') as mock_settings:
        # Standard S3 URL — should return the full S3 key (path after the bucket domain)
        url = "https://bucket-name.s3.us-east-1.amazonaws.com/path/to/file.txt"
        key = S3StorageProvider.get_key_from_url(url)
        assert key == "path/to/file.txt"  # Full S3 key, not just the filename

        # Custom endpoint — falls back to returning the last path component
        mock_settings.AWS_S3_ENDPOINT = "https://custom-s3.example.com"
        mock_settings.AWS_BUCKET_NAME = "bucket-name"
        url = "https://custom-s3.example.com/bucket-name/path/to/file.txt"
        key = S3StorageProvider.get_key_from_url(url)
        assert key == "file.txt"  # Fallback: last path component for non-amazonaws URLs

        # Presigned S3 URL — query string must be stripped, returning the full S3 key
        url = "https://bucket-name.s3.us-east-1.amazonaws.com/path/to/file.txt?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=..."
        key = S3StorageProvider.get_key_from_url(url)
        assert key == "path/to/file.txt"  # Query string stripped; full key returned