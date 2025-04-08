import pytest
from unittest.mock import Mock, patch, ANY, AsyncMock, MagicMock
from app.services.storage import StorageService, StorageError
from app.core.config import settings
import boto3
import os
from datetime import datetime, timedelta
import tempfile

@pytest.fixture
def mock_s3():
    """Mock S3 client"""
    with patch('boto3.client') as mock_client:
        s3 = mock_client.return_value
        s3.generate_presigned_url = Mock(return_value="https://test-bucket.s3.amazonaws.com/test.mp4")
        s3.upload_fileobj = Mock()
        s3.download_fileobj = Mock()
        s3.delete_object = Mock()
        s3.head_object = Mock(return_value={
            "ContentLength": 1024,
            "LastModified": datetime.now(),
            "ContentType": "video/mp4"
        })
        yield s3

@pytest.fixture
def mock_local_provider():
    """Create a mock local storage provider"""
    with patch('app.core.storage.storage_provider') as mock_provider:
        # Configure the mock
        mock_provider.upload_file = AsyncMock(return_value="http://localhost:8000/uploads/test/file.mp4")
        mock_provider.delete_file = AsyncMock(return_value=True)
        mock_provider.get_file = AsyncMock(return_value=(b"test content", {"content_type": "video/mp4"}))
        mock_provider.get_key_from_url = MagicMock(return_value="test/file.mp4")
        mock_provider.__class__.__name__ = "MockLocalStorageProvider"
        yield mock_provider

@pytest.fixture
def storage_service(mock_local_provider):
    """Create a storage service with mocked provider"""
    service = StorageService(provider=mock_local_provider)
    return service

@pytest.fixture
def test_file():
    """Create a test file"""
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b"test content")
        return f.name

@pytest.mark.asyncio
async def test_upload_file(storage_service, test_file, mock_local_provider):
    """Test file upload"""
    # Create a mock UploadFile with file-like properties
    class MockUploadFile:
        def __init__(self, filename, content_type):
            self.filename = filename
            self.content_type = content_type
            self.file = open(test_file, 'rb')
            
        async def read(self):
            return self.file.read()
            
        async def seek(self, pos):
            self.file.seek(pos)
            
    mock_file = MockUploadFile("test.mp4", "video/mp4")
    
    url = await storage_service.upload_file(
        file=mock_file,
        folder="test"
    )
    
    # Verify the result
    assert url == "http://localhost:8000/uploads/test/file.mp4"
    
    # Verify correct interactions
    mock_local_provider.upload_file.assert_called_once()
    
    # Check that we passed a file object, key pattern, content type and metadata
    args, kwargs = mock_local_provider.upload_file.call_args
    assert kwargs["content_type"] == "video/mp4"
    assert "metadata" in kwargs
    assert kwargs["public"] == True

@pytest.mark.asyncio
async def test_download_file(storage_service, test_file, mock_local_provider):
    """Test file download"""
    file_url = "http://localhost:8000/uploads/test/file.mp4"
    
    data = await storage_service.download_file(
        file_url=file_url
    )
    
    # Verify the result
    assert data == b"test content"
    
    # Verify correct interactions
    mock_local_provider.get_key_from_url.assert_called_once_with(file_url)
    mock_local_provider.get_file.assert_called_once_with("test/file.mp4")

@pytest.mark.asyncio
async def test_delete_file(storage_service, mock_local_provider):
    """Test file deletion"""
    file_url = "http://localhost:8000/uploads/test/file.mp4"
    await storage_service.delete_file(file_url)
    
    mock_local_provider.get_key_from_url.assert_called_once_with(file_url)
    mock_local_provider.delete_file.assert_called_once_with("test/file.mp4")

def test_get_file_url(storage_service, mock_s3):
    """Test getting file URL"""
    key = "test/test.mp4"
    url = storage_service.get_file_url(
        key=key,
        expires_in=3600
    )
    
    assert url == "https://test-bucket.s3.amazonaws.com/test.mp4"
    mock_s3.generate_presigned_url.assert_called_once()

@pytest.mark.asyncio
async def test_get_file_info(storage_service, mock_local_provider):
    """Test getting file metadata"""
    file_url = "http://localhost:8000/uploads/test/file.mp4"
    
    # Set up mock response for get_file
    mock_local_provider.get_file.return_value = (
        b"test content", 
        {
            "content_type": "video/mp4",
            "content_length": 1024,
            "last_modified": "2023-01-01T00:00:00Z",
            "metadata": {"original_filename": "test.mp4"}
        }
    )
    
    metadata = await storage_service.get_file_info(file_url)
    
    # Verify the result
    assert isinstance(metadata, dict)
    assert "ContentLength" in metadata
    assert "LastModified" in metadata
    assert "ContentType" in metadata
    assert metadata["ContentType"] == "video/mp4"
    
    # Verify correct interactions
    mock_local_provider.get_key_from_url.assert_called_once_with(file_url)
    mock_local_provider.get_file.assert_called_once_with("test/file.mp4")

@pytest.mark.asyncio
async def test_list_files(storage_service, mock_s3):
    """Test listing files - this would be provider specific"""
    pass  # Implementation would depend on the provider

def test_copy_file(storage_service, mock_s3):
    """Test file copying"""
    source_key = "test/source.mp4"
    dest_key = "test/dest.mp4"
    
    storage_service.copy_file(source_key, dest_key)
    
    mock_s3.copy_object.assert_called_once()
    mock_s3.copy_object.assert_called_with(
        Bucket="test-bucket",
        CopySource={"Bucket": "test-bucket", "Key": source_key},
        Key=dest_key
    )

def test_move_file(storage_service, mock_s3):
    """Test file moving"""
    source_key = "test/source.mp4"
    dest_key = "test/dest.mp4"
    
    storage_service.move_file(source_key, dest_key)
    
    mock_s3.copy_object.assert_called_once()
    mock_s3.delete_object.assert_called_once()

def test_upload_large_file(storage_service, test_file, mock_s3):
    """Test uploading large file with multipart upload"""
    key = "test/large.mp4"
    mock_s3.create_multipart_upload.return_value = {"UploadId": "test-upload-id"}
    
    storage_service.upload_large_file(
        file_path=test_file,
        key=key,
        chunk_size=5 * 1024 * 1024  # 5MB chunks
    )
    
    mock_s3.create_multipart_upload.assert_called_once()
    mock_s3.upload_part.assert_called()
    mock_s3.complete_multipart_upload.assert_called_once()

@pytest.mark.asyncio
async def test_handle_upload_error(storage_service, mock_local_provider):
    """Test handling upload errors"""
    mock_local_provider.upload_file.side_effect = Exception("Upload failed")
    
    # Create a mock UploadFile
    class MockUploadFile:
        def __init__(self):
            self.filename = "test.mp4"
            self.content_type = "video/mp4"
            
        async def read(self):
            return b"test content"
            
        async def seek(self, pos):
            pass
    
    with pytest.raises(StorageError):
        await storage_service.upload_file(
            file=MockUploadFile(),
            folder="test"
        )

@pytest.mark.asyncio
async def test_handle_download_error(storage_service, mock_local_provider):
    """Test handling download errors"""
    mock_local_provider.get_file.side_effect = Exception("Download failed")
    
    with pytest.raises(StorageError):
        await storage_service.download_file(
            file_url="http://localhost:8000/uploads/test/file.mp4"
        )

@pytest.mark.asyncio
async def test_handle_delete_error(storage_service, mock_local_provider):
    """Test handling delete errors"""
    mock_local_provider.delete_file.side_effect = Exception("Delete failed")
    
    with pytest.raises(StorageError):
        await storage_service.delete_file("http://localhost:8000/uploads/test/file.mp4")

def test_cleanup_expired_files(storage_service, mock_s3):
    """Test cleaning up expired files"""
    mock_s3.list_objects_v2.return_value = {
        "Contents": [
            {
                "Key": "temp/file1.mp4",
                "LastModified": datetime.now() - timedelta(days=2)
            },
            {
                "Key": "temp/file2.mp4",
                "LastModified": datetime.now() - timedelta(hours=1)
            }
        ]
    }
    
    storage_service.cleanup_expired_files(
        prefix="temp/",
        max_age_hours=24
    )
    
    assert mock_s3.delete_object.call_count == 1
    mock_s3.delete_object.assert_called_with(
        Bucket="test-bucket",
        Key="temp/file1.mp4"
    )

@pytest.mark.asyncio
async def test_get_file_size(storage_service, mock_local_provider):
    """Test getting file size"""
    file_url = "http://localhost:8000/uploads/test/file.mp4"
    
    # Set up mock response for get_file_info
    mock_info = {
        "ContentLength": 1024,
        "LastModified": "2023-01-01T00:00:00Z",
        "ContentType": "video/mp4",
        "Metadata": {"original_filename": "test.mp4"}
    }
    
    # Mock the get_file_info method of the storage_service
    with patch.object(storage_service, 'get_file_info', new_callable=AsyncMock) as mock_get_info:
        mock_get_info.return_value = mock_info
        
        size = await storage_service.get_file_size(file_url)
        assert size == 1024
        mock_get_info.assert_called_once_with(file_url)

def test_check_file_exists(storage_service, mock_s3):
    """Test checking file existence"""
    key = "test/test.mp4"
    exists = storage_service.check_file_exists(key)
    
    assert exists is True

def test_check_file_not_exists(storage_service, mock_s3):
    """Test checking non-existent file"""
    mock_s3.head_object.side_effect = Exception("Not found")
    
    exists = storage_service.check_file_exists("test/nonexistent.mp4")
    assert exists is False

def test_get_file_acl(storage_service, mock_s3):
    """Test getting file ACL"""
    mock_s3.get_object_acl.return_value = {
        "Grants": [
            {
                "Grantee": {"Type": "CanonicalUser"},
                "Permission": "READ"
            }
        ]
    }
    
    acl = storage_service.get_file_acl("test/test.mp4")
    assert isinstance(acl, dict)
    assert "Grants" in acl

def test_set_file_acl(storage_service, mock_s3):
    """Test setting file ACL"""
    acl = {
        "Grants": [
            {
                "Grantee": {"Type": "CanonicalUser"},
                "Permission": "READ"
            }
        ]
    }
    
    storage_service.set_file_acl("test/test.mp4", acl)
    mock_s3.put_object_acl.assert_called_once() 