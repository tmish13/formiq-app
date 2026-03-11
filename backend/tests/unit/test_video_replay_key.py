"""Tests for video replay reliability: upload_file_and_get_key + fresh URL on GET."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from io import BytesIO


class TestUploadFileAndGetKey:
    """upload_file_and_get_key() must return the S3 key, not a presigned URL."""

    @pytest.mark.asyncio
    async def test_returns_key_not_url(self):
        """upload_file_and_get_key returns the file_key (path-like string), not a URL."""
        from app.services.storage_service import StorageService

        mock_provider = MagicMock()
        # The provider.upload_file coroutine returns a presigned URL (as real S3 does)
        mock_provider.upload_file = AsyncMock(return_value="https://s3.amazonaws.com/bucket/folder/123_abc_video.mp4")

        mock_breaker = MagicMock()
        # circuit_breaker.call just delegates to the coroutine
        async def fake_breaker_call(coro_factory, fallback=None):
            return await coro_factory()
        mock_breaker.call = fake_breaker_call

        service = StorageService.__new__(StorageService)
        service.provider = mock_provider
        service.max_upload_size = 100 * 1024 * 1024
        service.storage_breaker = mock_breaker
        service.app_settings = MagicMock()

        mock_file = MagicMock()
        mock_file.filename = "test_video.mp4"
        mock_file.content_type = "video/mp4"
        mock_file.read = AsyncMock(return_value=b"fake video content")
        mock_file.seek = AsyncMock()

        result = await service.upload_file_and_get_key(mock_file, folder="form_check_videos", user_id="user123")

        # Result should be the generated file_key, not a URL
        assert not result.startswith("http")
        assert "test_video.mp4" in result
        assert "user123" in result

    @pytest.mark.asyncio
    async def test_key_differs_from_upload_file_url(self):
        """upload_file() returns a URL; upload_file_and_get_key() returns a key."""
        from app.services.storage_service import StorageService

        returned_url = "https://s3.amazonaws.com/bucket/videos/user1/123_abc_video.mp4"
        mock_provider = MagicMock()
        mock_provider.upload_file = AsyncMock(return_value=returned_url)

        mock_breaker = MagicMock()
        async def fake_breaker_call(coro_factory, fallback=None):
            return await coro_factory()
        mock_breaker.call = fake_breaker_call

        service = StorageService.__new__(StorageService)
        service.provider = mock_provider
        service.max_upload_size = 100 * 1024 * 1024
        service.storage_breaker = mock_breaker
        service.app_settings = MagicMock()

        mock_file = MagicMock()
        mock_file.filename = "video.mp4"
        mock_file.content_type = "video/mp4"
        mock_file.read = AsyncMock(return_value=b"content")
        mock_file.seek = AsyncMock()

        key = await service.upload_file_and_get_key(mock_file, folder="videos", user_id="user1")

        # The key should NOT be the presigned URL returned by the provider
        assert key != returned_url
        # The key should look like an S3 object key (no protocol prefix)
        assert not key.startswith("https://")
        assert not key.startswith("http://")


class TestGetFileUrlGeneratesFreshPresignedUrl:
    """get_file_url(key) generates a fresh presigned URL from the stored key."""

    def test_get_file_url_calls_provider(self):
        from app.services.storage_service import StorageService

        mock_provider = MagicMock()
        mock_provider.generate_presigned_url = MagicMock(
            return_value="https://s3.amazonaws.com/bucket/key/file.mp4?X-Amz-Expires=3600"
        )

        service = StorageService.__new__(StorageService)
        service.provider = mock_provider
        service.app_settings = MagicMock()

        url = service.get_file_url("form_check_videos/user1/123_abc_video.mp4", expires_in=3600)

        mock_provider.generate_presigned_url.assert_called_once_with(
            "form_check_videos/user1/123_abc_video.mp4", 3600
        )
        assert url.startswith("https://")

    def test_get_file_url_fallback_when_no_presigned_support(self):
        """When provider has no generate_presigned_url, falls back to STORAGE_URL."""
        from app.services.storage_service import StorageService
        import app.services.storage_service as ss_module

        mock_provider = MagicMock(spec=[])  # no generate_presigned_url attribute
        with patch.object(ss_module, "settings") as mock_settings:
            mock_settings.STORAGE_URL = "http://localhost:9000"

            service = StorageService.__new__(StorageService)
            service.provider = mock_provider
            service.app_settings = MagicMock()

            url = service.get_file_url("my/key.mp4")
            assert url == "http://localhost:9000/my/key.mp4"
