import pytest
from unittest.mock import Mock, patch
from ..services.storage import StorageService, StorageError
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
def storage_service(mock_s3):
    """Create a storage service instance"""
    with patch.dict(os.environ, {
        'AWS_ACCESS_KEY_ID': 'test_key',
        'AWS_SECRET_ACCESS_KEY': 'test_secret',
        'AWS_REGION': 'us-east-1',
        'S3_BUCKET': 'test-bucket'
    }):
        service = StorageService()
        return service

@pytest.fixture
def test_file():
    """Create a test file"""
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b"test content")
        return f.name

def test_upload_file(storage_service, test_file, mock_s3):
    """Test file upload"""
    key = "test/test.mp4"
    storage_service.upload_file(
        file_path=test_file,
        key=key,
        content_type="video/mp4"
    )
    
    mock_s3.upload_fileobj.assert_called_once()
    mock_s3.upload_fileobj.assert_called_with(
        ANY,
        "test-bucket",
        key,
        ExtraArgs={"ContentType": "video/mp4"}
    )

def test_download_file(storage_service, test_file, mock_s3):
    """Test file download"""
    key = "test/test.mp4"
    storage_service.download_file(
        key=key,
        local_path=test_file
    )
    
    mock_s3.download_fileobj.assert_called_once()
    mock_s3.download_fileobj.assert_called_with(
        "test-bucket",
        key,
        ANY
    )

def test_delete_file(storage_service, mock_s3):
    """Test file deletion"""
    key = "test/test.mp4"
    storage_service.delete_file(key)
    
    mock_s3.delete_object.assert_called_once()
    mock_s3.delete_object.assert_called_with(
        Bucket="test-bucket",
        Key=key
    )

def test_get_file_url(storage_service, mock_s3):
    """Test getting file URL"""
    key = "test/test.mp4"
    url = storage_service.get_file_url(
        key=key,
        expires_in=3600
    )
    
    assert url == "https://test-bucket.s3.amazonaws.com/test.mp4"
    mock_s3.generate_presigned_url.assert_called_once()

def test_get_file_metadata(storage_service, mock_s3):
    """Test getting file metadata"""
    key = "test/test.mp4"
    metadata = storage_service.get_file_metadata(key)
    
    assert isinstance(metadata, dict)
    assert "size" in metadata
    assert "last_modified" in metadata
    assert "content_type" in metadata

def test_list_files(storage_service, mock_s3):
    """Test listing files"""
    mock_s3.list_objects_v2.return_value = {
        "Contents": [
            {
                "Key": "test/file1.mp4",
                "LastModified": datetime.now(),
                "Size": 1024
            },
            {
                "Key": "test/file2.mp4",
                "LastModified": datetime.now(),
                "Size": 2048
            }
        ]
    }
    
    files = storage_service.list_files(prefix="test/")
    
    assert len(files) == 2
    assert all("key" in file for file in files)
    assert all("size" in file for file in files)
    assert all("last_modified" in file for file in files)

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

def test_handle_upload_error(storage_service, test_file, mock_s3):
    """Test handling upload errors"""
    mock_s3.upload_fileobj.side_effect = Exception("Upload failed")
    
    with pytest.raises(StorageError):
        storage_service.upload_file(
            file_path=test_file,
            key="test/test.mp4"
        )

def test_handle_download_error(storage_service, mock_s3):
    """Test handling download errors"""
    mock_s3.download_fileobj.side_effect = Exception("Download failed")
    
    with pytest.raises(StorageError):
        storage_service.download_file(
            key="test/test.mp4",
            local_path="local.mp4"
        )

def test_handle_delete_error(storage_service, mock_s3):
    """Test handling delete errors"""
    mock_s3.delete_object.side_effect = Exception("Delete failed")
    
    with pytest.raises(StorageError):
        storage_service.delete_file("test/test.mp4")

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

def test_get_file_size(storage_service, mock_s3):
    """Test getting file size"""
    key = "test/test.mp4"
    size = storage_service.get_file_size(key)
    
    assert size == 1024  # From mock_s3.head_object return value

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