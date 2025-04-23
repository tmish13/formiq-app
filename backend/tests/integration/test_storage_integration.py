"""Integration tests for storage module."""
import os
import pytest
import shutil
from pathlib import Path
from fastapi import UploadFile
from uuid import uuid4

from app.core.config import settings
from app.core.storage import (
    LocalStorageProvider,
    get_storage_provider,
    upload_video,
    delete_video
)
from app.exceptions import VideoProcessingError

@pytest.fixture(scope="module")
def test_storage_dir():
    """Create and clean up a test storage directory."""
    test_dir = Path("/tmp/test_storage_integration")
    if test_dir.exists():
        shutil.rmtree(test_dir)
    test_dir.mkdir(parents=True)
    yield test_dir
    shutil.rmtree(test_dir)

@pytest.fixture(scope="module")
def test_storage_provider(test_storage_dir):
    """Create a test storage provider."""
    return LocalStorageProvider(
        base_dir=str(test_storage_dir),
        base_url="http://test.local/uploads"
    )

@pytest.fixture
async def test_video_file(tmp_path):
    """Create a test video file."""
    video_path = tmp_path / "test_video.mp4"
    # Create a small valid MP4 file (20 bytes of mock data)
    with open(video_path, "wb") as f:
        f.write(b"x" * 20)
    
    file = UploadFile(
        filename="test_video.mp4",
        file=video_path.open("rb"),
        content_type="video/mp4"
    )
    yield file
    await file.close()

class TestStorageIntegration:
    """Integration tests for storage operations."""

    async def test_large_file_upload(self, test_storage_provider, tmp_path):
        """Test uploading a large file (10MB)."""
        large_file_path = tmp_path / "large_video.mp4"
        file_size = 10 * 1024 * 1024  # 10MB
        
        # Create a large test file
        with open(large_file_path, "wb") as f:
            f.write(b"0" * file_size)
        
        file = UploadFile(
            filename="large_video.mp4",
            file=large_file_path.open("rb"),
            content_type="video/mp4"
        )
        
        try:
            object_name = f"videos/test/{uuid4()}.mp4"
            url = await test_storage_provider.upload_file(
                file.file,
                object_name,
                content_type="video/mp4"
            )
            
            # Verify file was uploaded correctly
            uploaded_path = Path(test_storage_provider.base_dir) / object_name
            assert uploaded_path.exists()
            assert uploaded_path.stat().st_size == file_size
            
        finally:
            await file.close()

    async def test_concurrent_uploads(self, test_storage_provider, test_video_file):
        """Test uploading multiple files concurrently."""
        import asyncio
        
        async def upload_file(index: int):
            object_name = f"videos/concurrent/video_{index}.mp4"
            return await test_storage_provider.upload_file(
                test_video_file.file,
                object_name,
                content_type="video/mp4"
            )
        
        # Upload 5 files concurrently
        tasks = [upload_file(i) for i in range(5)]
        urls = await asyncio.gather(*tasks)
        
        # Verify all files were uploaded
        for i, url in enumerate(urls):
            path = Path(test_storage_provider.base_dir) / f"videos/concurrent/video_{i}.mp4"
            assert path.exists()

    async def test_upload_with_nested_directories(self, test_storage_provider, test_video_file):
        """Test uploading files to nested directories."""
        nested_path = "videos/user123/workout456/exercise789/video.mp4"
        url = await test_storage_provider.upload_file(
            test_video_file.file,
            nested_path,
            content_type="video/mp4"
        )
        
        # Verify directory structure was created
        full_path = Path(test_storage_provider.base_dir) / nested_path
        assert full_path.exists()
        assert full_path.parent.is_dir()

    async def test_delete_with_cleanup(self, test_storage_provider, test_video_file):
        """Test deleting files and cleaning up empty directories."""
        # Upload file to nested directory
        nested_path = "videos/to_delete/nested/video.mp4"
        url = await test_storage_provider.upload_file(
            test_video_file.file,
            nested_path,
            content_type="video/mp4"
        )
        
        # Delete file
        await test_storage_provider.delete_file(nested_path)
        
        # Verify file is deleted
        full_path = Path(test_storage_provider.base_dir) / nested_path
        assert not full_path.exists()
        
        # Verify empty parent directories are cleaned up
        assert not full_path.parent.exists()
        assert not full_path.parent.parent.exists()

    async def test_storage_quota(self, test_storage_provider, tmp_path):
        """Test storage quota limits."""
        quota_size = 5 * 1024 * 1024  # 5MB quota
        test_storage_provider.quota_size = quota_size
        
        # Create a file that exceeds quota
        large_file_path = tmp_path / "over_quota.mp4"
        with open(large_file_path, "wb") as f:
            f.write(b"0" * (quota_size + 1024))  # Exceed quota by 1KB
        
        file = UploadFile(
            filename="over_quota.mp4",
            file=large_file_path.open("rb"),
            content_type="video/mp4"
        )
        
        try:
            with pytest.raises(VideoProcessingError) as exc_info:
                await test_storage_provider.upload_file(
                    file.file,
                    "videos/over_quota.mp4",
                    content_type="video/mp4"
                )
            assert "Storage quota exceeded" in str(exc_info.value)
        finally:
            await file.close()

    async def test_file_type_validation(self, test_storage_provider, tmp_path):
        """Test file type validation during upload."""
        # Create an invalid file type
        invalid_file_path = tmp_path / "document.pdf"
        with open(invalid_file_path, "wb") as f:
            f.write(b"PDF content")
        
        file = UploadFile(
            filename="document.pdf",
            file=invalid_file_path.open("rb"),
            content_type="application/pdf"
        )
        
        try:
            with pytest.raises(VideoProcessingError) as exc_info:
                await test_storage_provider.upload_file(
                    file.file,
                    "videos/document.pdf",
                    content_type="application/pdf"
                )
            assert "Invalid file type" in str(exc_info.value)
        finally:
            await file.close() 