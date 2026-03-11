"""
S3StorageProvider — regression tests for production fixes.

Each test documents a specific bug that was found in production and the exact
behaviour that the fix must preserve.  These complement the fuller
test_s3_storage_provider.py suite and are intentionally narrow.
"""
import io
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from botocore.exceptions import ClientError

from app.core.storage.s3 import S3StorageProvider


# ---------------------------------------------------------------------------
# Helper: shared async context-manager mock wiring
# ---------------------------------------------------------------------------

class _AsyncCM:
    def __init__(self, client):
        self._client = client

    async def __aenter__(self):
        return self._client

    async def __aexit__(self, *args):
        pass


@pytest.fixture()
def s3_client_mock():
    with patch("app.core.storage.s3.get_session") as mock_session:
        mock_client = AsyncMock()
        mock_session.return_value.create_client = MagicMock(
            return_value=_AsyncCM(mock_client)
        )
        yield mock_client


@pytest.fixture()
def provider(s3_client_mock):
    return S3StorageProvider(
        bucket_name="reg-bucket",
        aws_access_key_id="test-key",
        aws_secret_access_key="test-secret",
        region_name="us-east-1",
    )


# ---------------------------------------------------------------------------
# Regression 1: get_key_from_url — off-by-one + query-string stripping
#
# Bug: url[aws_index + 13:] strips ".amazonaws.com" (14 chars) incorrectly,
#      leaving a leading "/" on the key.  Query strings were also not stripped.
# Fix: url[aws_index + 15:].split('?')[0]  (14 chars + 1 for the "/" = 15)
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestGetKeyFromUrl:
    def test_standard_s3_url_returns_full_key(self):
        url = "https://bucket.s3.us-east-1.amazonaws.com/path/to/file.txt"
        key = S3StorageProvider.get_key_from_url(url)
        assert key == "path/to/file.txt", f"Got: {key!r}"

    def test_presigned_url_strips_query_string(self):
        url = (
            "https://bucket.s3.us-east-1.amazonaws.com/path/to/file.txt"
            "?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=..."
        )
        key = S3StorageProvider.get_key_from_url(url)
        assert "?" not in key
        assert key == "path/to/file.txt", f"Got: {key!r}"

    def test_non_aws_url_falls_back_to_last_component(self):
        url = "https://custom-s3.example.com/my-bucket/path/to/file.txt"
        key = S3StorageProvider.get_key_from_url(url)
        # fallback: last path component
        assert key == "file.txt", f"Got: {key!r}"


# ---------------------------------------------------------------------------
# Regression 2: upload_file (private) — presigned URL must be generated
#
# Bug: private uploads returned the presigned URL string from a call that was
#      made AFTER the `async with` block had already closed the client, so the
#      call failed and the URL was never returned.
# Fix: generate_presigned_url is called INSIDE the `async with` block.
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.asyncio
async def test_private_upload_generates_presigned_url(provider, s3_client_mock):
    """Private upload must return a presigned URL, not the static bucket URL."""
    presigned = "https://reg-bucket.s3.amazonaws.com/obj?AWSAccessKeyId=k&Signature=s&Expires=99"
    s3_client_mock.put_object = AsyncMock(return_value={})
    s3_client_mock.generate_presigned_url = AsyncMock(return_value=presigned)

    result = await provider.upload_file(
        file_data=io.BytesIO(b"data"),
        object_name="folder/obj.mp4",
        public=False,
    )

    # The presigned URL must be returned (not the static URL)
    assert result == presigned
    s3_client_mock.generate_presigned_url.assert_called_once()
    call_args = s3_client_mock.generate_presigned_url.call_args
    assert call_args[0][0] == "get_object"
    assert call_args[1]["Params"]["Key"] == "folder/obj.mp4"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_public_upload_does_not_generate_presigned_url(provider, s3_client_mock):
    """Public upload must return the static URL and skip presigned generation."""
    s3_client_mock.put_object = AsyncMock(return_value={})

    result = await provider.upload_file(
        file_data=io.BytesIO(b"data"),
        object_name="public/asset.jpg",
        public=True,
    )

    assert "https://reg-bucket.s3.us-east-1.amazonaws.com/public/asset.jpg" == result
    s3_client_mock.generate_presigned_url.assert_not_called()


# ---------------------------------------------------------------------------
# Regression 3: get_file — metadata must be included in returned dict
#
# Bug: metadata key was absent from the returned dict so callers that accessed
#      result["metadata"] got KeyError.
# Fix: add `"metadata": response.get("Metadata", {})` to the returned dict.
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_file_includes_metadata(provider, s3_client_mock):
    """get_file must include the S3 object metadata in its returned dict."""
    body_mock = AsyncMock()
    body_mock.read = AsyncMock(return_value=b"content")
    s3_client_mock.get_object = AsyncMock(return_value={
        "Body": body_mock,
        "ContentType": "video/mp4",
        "ContentLength": 7,
        "LastModified": datetime.utcnow(),
        "Metadata": {"original-filename": "squat.mp4"},
    })

    data, meta = await provider.get_file("videos/squat.mp4")

    assert data == b"content"
    assert "metadata" in meta, "Returned dict must have a 'metadata' key"
    assert meta["metadata"] == {"original-filename": "squat.mp4"}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_file_missing_s3_metadata_returns_empty_dict(provider, s3_client_mock):
    """When S3 returns no Metadata, get_file must return an empty dict, not raise."""
    body_mock = AsyncMock()
    body_mock.read = AsyncMock(return_value=b"x")
    s3_client_mock.get_object = AsyncMock(return_value={
        "Body": body_mock,
        "ContentType": "application/octet-stream",
        "ContentLength": 1,
        "LastModified": datetime.utcnow(),
        # No "Metadata" key
    })

    _, meta = await provider.get_file("obj.bin")
    assert meta["metadata"] == {}


# ---------------------------------------------------------------------------
# Regression 4: get_file — NoSuchKey ClientError must become FileNotFoundError
#
# Bug: ClientError with Code=NoSuchKey propagated as a generic ClientError,
#      forcing callers to parse the AWS error structure.
# Fix: explicitly convert NoSuchKey to FileNotFoundError with a readable message.
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_file_no_such_key_raises_file_not_found(provider, s3_client_mock):
    """S3 NoSuchKey must be re-raised as FileNotFoundError."""
    err = {"Error": {"Code": "NoSuchKey", "Message": "does not exist"}}
    s3_client_mock.get_object = AsyncMock(
        side_effect=ClientError(err, "GetObject")
    )

    with pytest.raises(FileNotFoundError) as exc_info:
        await provider.get_file("gone/video.mp4")

    assert "gone/video.mp4" in str(exc_info.value)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_file_other_client_error_propagates(provider, s3_client_mock):
    """Non-NoSuchKey ClientErrors must propagate unchanged (not swallowed)."""
    err = {"Error": {"Code": "AccessDenied", "Message": "Forbidden"}}
    s3_client_mock.get_object = AsyncMock(
        side_effect=ClientError(err, "GetObject")
    )

    with pytest.raises(ClientError):
        await provider.get_file("secret.mp4")
