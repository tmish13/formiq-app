"""G-36 (audit/upload-streaming): an upload is streamed to storage, never copied into memory.

Before this change the service did `await file.read()` and wrapped the bytes in a BytesIO, so
every in-flight upload held a whole video in the API process (20 concurrent uploads OOM-killed
gunicorn workers). Starlette already spools the multipart body to a temp file past 1 MiB; the
service now hands that spooled file to the provider, and the local provider copies it in
HASH_CHUNK_BYTES pieces.
"""
import io
from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.datastructures import UploadFile

from app.core.hashing import HASH_CHUNK_BYTES

pytestmark = pytest.mark.unit


def _service(provider):
    from app.services.storage_service import StorageService

    async def breaker_call(coro_factory, fallback=None):
        return await coro_factory()

    svc = StorageService.__new__(StorageService)
    svc.provider = provider
    svc.max_upload_size = 100 * 1024 * 1024
    svc.storage_breaker = MagicMock(call=breaker_call)
    svc.app_settings = MagicMock()
    return svc


class _Recorder(io.BytesIO):
    """A stream that remembers the size of every read() it is asked for."""

    def __init__(self, data):
        super().__init__(data)
        self.sizes = []

    def read(self, size=-1):
        self.sizes.append(size)
        return super().read(size)


class TestServiceStreams:
    async def test_the_provider_receives_the_upload_file_itself_rewound_not_a_copy(self):
        data = b"\x00" * (3 * HASH_CHUNK_BYTES + 17)
        upload = UploadFile(filename="clip.mp4", file=io.BytesIO(data))
        await upload.read(HASH_CHUNK_BYTES)  # something upstream (the hasher) already read from it
        seen = {}

        async def capture(file_obj, key, **kw):
            seen["obj"], seen["pos"] = file_obj, file_obj.tell()
            return "url"

        provider = MagicMock(upload_file=AsyncMock(side_effect=capture))
        key = await _service(provider).upload_file_and_get_key(upload, folder="v", user_id="u1")
        assert key.endswith("clip.mp4")
        assert seen["obj"] is upload.file, "a BytesIO copy would double the per-request memory"
        assert seen["pos"] == 0

    async def test_upload_file_takes_the_same_path(self):
        upload = UploadFile(filename="clip.mp4", file=io.BytesIO(b"x" * 2048))
        seen = {}

        async def capture(file_obj, key, **kw):
            seen["obj"] = file_obj
            return "https://files/clip.mp4"

        provider = MagicMock(upload_file=AsyncMock(side_effect=capture))
        await _service(provider).upload_file(upload, folder="v", user_id="u1")
        assert seen["obj"] is upload.file


class TestLocalProviderCopiesInChunks:
    async def test_bounded_reads_and_identical_bytes(self, tmp_path):
        from app.core.storage import LocalStorageProvider

        provider = LocalStorageProvider(base_dir=str(tmp_path), base_url="http://files")
        data = bytes(range(256)) * (3 * HASH_CHUNK_BYTES // 256) + b"tail"
        stream = _Recorder(data)
        url = await provider.upload_file(stream, "u1/clip.bin", content_type="video/mp4")
        assert url == "http://files/u1/clip.bin"
        assert (tmp_path / "u1" / "clip.bin").read_bytes() == data
        assert stream.sizes, "the provider never read the stream"
        assert max(stream.sizes) <= HASH_CHUNK_BYTES, f"an unbounded read: {stream.sizes}"
        assert -1 not in stream.sizes and None not in stream.sizes
        # 3 full chunks + the 4-byte tail + the empty read that ends the loop
        assert len(stream.sizes) == 5
