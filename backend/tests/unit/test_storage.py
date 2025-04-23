"""Storage module tests."""
import pytest
import os
from unittest.mock import Mock, patch
from fastapi import UploadFile
from app.core.storage import (
    StorageProvider,
    LocalStorageProvider,
    get_storage_provider,
    upload_video,
    delete_video
)
from app.core.config import settings
from app.exceptions import VideoProcessingError

@pytest.fixture
def mock_upload_file():
    """Create a mock UploadFile for testing."""
    mock_file = Mock(spec=UploadFile)
    mock_file.filename = "test_video.mp4"
    mock_file.content_type = "video/mp4"
    mock_file.file = Mock()
    mock_file.file.read.return_value = b"test content"
    return mock_file

@pytest.fixture
def local_storage():
    """Create a LocalStorageProvider instance for testing."""
    test_dir = "/tmp/test_storage"
    test_url = "http://test.local/uploads"
    provider = LocalStorageProvider(base_dir=test_dir, base_url=test_url)
    return provider

class TestStorageProvider:
    """Test cases for StorageProvider."""

    async def test_storage_provider_interface(self):
        """Test that StorageProvider defines the required interface."""
        provider = StorageProvider()
        with pytest.raises(NotImplementedError):
            await provider.upload_file(None, "test.txt")
        with pytest.raises(NotImplementedError):
            await provider.delete_file("test.txt")
        with pytest.raises(NotImplementedError):
            await provider.list_files()
        with pytest.raises(NotImplementedError):
            await provider.get_file("test.txt")

class TestLocalStorageProvider:
    """Test cases for LocalStorageProvider."""

    async def test_upload_file(self, local_storage, mock_upload_file):
        """Test uploading a file."""
        object_name = "test/video.mp4"
        url = await local_storage.upload_file(
            mock_upload_file.file,
            object_name,
            content_type="video/mp4"
        )
        assert url == f"{local_storage.base_url}/{object_name}"
        assert os.path.exists(os.path.join(local_storage.base_dir, object_name))

    async def test_delete_file(self, local_storage):
        """Test deleting a file."""
        object_name = "test/to_delete.mp4"
        full_path = os.path.join(local_storage.base_dir, object_name)
        
        # Create test file
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'wb') as f:
            f.write(b"test content")
        
        # Test deletion
        result = await local_storage.delete_file(object_name)
        assert result is True
        assert not os.path.exists(full_path)

    async def test_list_files(self, local_storage):
        """Test listing files."""
        # Create test files
        test_files = ["test1.mp4", "test2.mp4"]
        for filename in test_files:
            path = os.path.join(local_storage.base_dir, filename)
            with open(path, 'wb') as f:
                f.write(b"test content")
        
        files = await local_storage.list_files()
        assert len(files) == len(test_files)
        assert all(f["key"] in test_files for f in files)

    def test_get_key_from_url(self, local_storage):
        """Test extracting key from URL."""
        url = "http://test.local/uploads/videos/test.mp4"
        key = local_storage.get_key_from_url(url)
        assert key == "test.mp4"

class TestVideoStorage:
    """Test cases for video storage functions."""

    async def test_upload_video(self, mock_upload_file):
        """Test video upload function."""
        user_id = "123e4567-e89b-12d3-a456-426614174000"
        url = await upload_video(mock_upload_file, user_id)
        assert url.startswith(f"{settings.MEDIA_URL}/videos/{user_id}")
        assert url.endswith(".mp4")

    async def test_upload_video_error(self, mock_upload_file):
        """Test video upload error handling."""
        mock_upload_file.read.side_effect = Exception("Upload failed")
        with pytest.raises(VideoProcessingError):
            await upload_video(mock_upload_file, "test-user")

    async def test_delete_video(self):
        """Test video deletion."""
        video_url = f"{settings.MEDIA_URL}/videos/test-user/test.mp4"
        # Create test file
        file_path = os.path.join(settings.UPLOAD_DIR, "test-user", "test.mp4")
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'wb') as f:
            f.write(b"test content")
        
        await delete_video(video_url)
        assert not os.path.exists(file_path)

    async def test_delete_video_error(self):
        """Test video deletion error handling."""
        with pytest.raises(VideoProcessingError):
            await delete_video("invalid/url") 