"""Tests for S3 storage provider using moto mock."""
import os
import pytest
from moto import mock_aws
import boto3
from pathlib import Path
from fastapi import UploadFile
from uuid import uuid4

from app.core.storage import S3StorageProvider
from app.exceptions import VideoProcessingError

# Constants for testing
TEST_BUCKET = "test-video-bucket"
TEST_REGION = "us-east-1"
TEST_ACCESS_KEY = "test-access-key"
TEST_SECRET_KEY = "test-secret-key"

@pytest.fixture
def aws_credentials():
    """Mock AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = TEST_ACCESS_KEY
    os.environ["AWS_SECRET_ACCESS_KEY"] = TEST_SECRET_KEY
    os.environ["AWS_DEFAULT_REGION"] = TEST_REGION

@pytest.fixture
def s3_client(aws_credentials):
    """Create mocked S3 client."""
    with mock_aws():
        s3 = boto3.client("s3", region_name=TEST_REGION)
        # Create test bucket
        s3.create_bucket(Bucket=TEST_BUCKET)
        yield s3

@pytest.fixture
def s3_storage(s3_client):
    """Create S3StorageProvider instance."""
    return S3StorageProvider(
        bucket_name=TEST_BUCKET,
        aws_access_key_id=TEST_ACCESS_KEY,
        aws_secret_access_key=TEST_SECRET_KEY,
        region_name=TEST_REGION,
        base_url=f"https://{TEST_BUCKET}.s3.{TEST_REGION}.amazonaws.com"
    )

@pytest.fixture
async def test_video_file(tmp_path):
    """Create a test video file."""
    video_path = tmp_path / "test_video.mp4"
    with open(video_path, "wb") as f:
        f.write(b"test video content")
    
    # Create file object
    file = video_path.open("rb")
    
    # Create UploadFile instance with content type
    upload_file = UploadFile(
        filename="test_video.mp4",
        file=file,
        content_type="video/mp4"
    )
    
    yield upload_file
    await upload_file.close()
    file.close()

class TestS3StorageProvider:
    """Test cases for S3StorageProvider."""

    async def test_upload_file(self, s3_storage, s3_client, test_video_file):
        """Test uploading a file to S3."""
        object_key = f"videos/test/{uuid4()}.mp4"
        url = await s3_storage.upload_file(
            test_video_file.file,
            object_key,
            content_type="video/mp4"
        )
        
        # Verify URL format
        assert url == f"https://{TEST_BUCKET}.s3.{TEST_REGION}.amazonaws.com/{object_key}"
        
        # Verify file exists in S3
        response = s3_client.head_object(Bucket=TEST_BUCKET, Key=object_key)
        assert response["ContentType"] == "video/mp4"

    async def test_upload_with_metadata(self, s3_storage, s3_client, test_video_file):
        """Test uploading a file with metadata."""
        object_key = f"videos/test/{uuid4()}.mp4"
        metadata = {
            "user_id": "test-user",
            "exercise_type": "squat"
        }
        
        url = await s3_storage.upload_file(
            test_video_file.file,
            object_key,
            content_type="video/mp4",
            metadata=metadata
        )
        
        # Verify metadata in S3
        response = s3_client.head_object(Bucket=TEST_BUCKET, Key=object_key)
        assert response["Metadata"]["user_id"] == "test-user"
        assert response["Metadata"]["exercise_type"] == "squat"

    async def test_delete_file(self, s3_storage, s3_client, test_video_file):
        """Test deleting a file from S3."""
        # Upload file first
        object_key = f"videos/test/{uuid4()}.mp4"
        await s3_storage.upload_file(
            test_video_file.file,
            object_key,
            content_type="video/mp4"
        )
        
        # Delete file
        result = await s3_storage.delete_file(object_key)
        assert result is True
        
        # Verify file is deleted
        with pytest.raises(s3_client.exceptions.NoSuchKey):
            s3_client.head_object(Bucket=TEST_BUCKET, Key=object_key)

    async def test_list_files(self, s3_storage, s3_client, test_video_file):
        """Test listing files in S3."""
        # Upload multiple files
        object_keys = []
        for i in range(3):
            key = f"videos/test/file_{i}_{uuid4()}.mp4"
            object_keys.append(key)
            await s3_storage.upload_file(
                test_video_file.file,
                key,
                content_type="video/mp4"
            )
        
        # List files
        files = await s3_storage.list_files()
        assert len(files) == 3
        assert all(f["key"] in object_keys for f in files)

    async def test_get_file(self, s3_storage, s3_client, test_video_file):
        """Test getting a file from S3."""
        object_key = f"videos/test/{uuid4()}.mp4"
        await s3_storage.upload_file(
            test_video_file.file,
            object_key,
            content_type="video/mp4"
        )
        
        # Get file
        file_data = await s3_storage.get_file(object_key)
        assert file_data is not None
        assert len(file_data) > 0

    async def test_invalid_bucket(self):
        """Test initialization with invalid bucket."""
        with pytest.raises(Exception):
            S3StorageProvider(
                bucket_name="nonexistent-bucket",
                aws_access_key_id=TEST_ACCESS_KEY,
                aws_secret_access_key=TEST_SECRET_KEY,
                region_name=TEST_REGION
            )

    async def test_upload_invalid_file(self, s3_storage):
        """Test uploading an invalid file."""
        with pytest.raises(VideoProcessingError):
            await s3_storage.upload_file(
                None,
                "test.mp4",
                content_type="video/mp4"
            )

    async def test_delete_nonexistent_file(self, s3_storage):
        """Test deleting a nonexistent file."""
        result = await s3_storage.delete_file("nonexistent.mp4")
        assert result is False

    async def test_presigned_url(self, s3_storage, s3_client, test_video_file):
        """Test generating presigned URLs."""
        object_key = f"videos/test/{uuid4()}.mp4"
        await s3_storage.upload_file(
            test_video_file.file,
            object_key,
            content_type="video/mp4"
        )
        
        # Generate presigned URL
        url = await s3_storage.get_presigned_url(object_key, expires_in=3600)
        assert url is not None
        assert TEST_BUCKET in url
        assert object_key in url
        assert "Signature=" in url 