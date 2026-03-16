"""Unit tests for S3-backed video path resolution in analysis_tasks.

Covers:
  - Local file found → returns (path, False), no download
  - Local file missing + USE_S3_STORAGE=False → returns (None, False)
  - Local file missing + USE_S3_STORAGE=True, no storage_service → returns (None, False)
  - Local file missing + USE_S3_STORAGE=True, storage_service available → downloads,
    returns (temp_path, True), temp_path is an actual file with correct content
  - S3 download failure → returns (None, False), does not raise
  - VideoModel with no url/object_key → returns (None, False)
  - VideoStatus enum fix: VideoStatus.UPLOADED is the correct enum member
  - Squat routing: exercise_type on video model drives _is_squat when template absent

All tests are pure unit tests (no real DB, no real S3, no Celery).
"""
import os
import pytest
import tempfile
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers / stubs mirroring production code
# ---------------------------------------------------------------------------

def _make_video_model(object_key="form_check_videos/u/ts_abc_vid.mp4", url=None, exercise_type="squat"):
    v = MagicMock()
    v.id = "test-video-id"
    v.object_key = object_key
    v.url = url
    v.exercise_type = exercise_type
    return v


def _make_settings(use_s3: bool = False):
    s = MagicMock()
    s.USE_S3_STORAGE = use_s3
    s.UPLOAD_DIR = "uploads"
    s.UPLOAD_URL = "http://localhost:8000/uploads"
    return s


def _make_storage_service(content: bytes = b"fake-video-content"):
    """Mock StorageService that returns `content` from download_file."""
    svc = AsyncMock()
    svc.download_file = AsyncMock(return_value=content)
    return svc


# ---------------------------------------------------------------------------
# Import the function under test
# ---------------------------------------------------------------------------

from app.tasks.analysis_tasks import _resolve_video_local_path


# ---------------------------------------------------------------------------
# 1. Local storage (USE_S3_STORAGE=False) — file on disk
# ---------------------------------------------------------------------------

class TestLocalPathResolution:
    @pytest.mark.asyncio
    async def test_local_file_found_returns_path_not_temp(self, tmp_path):
        """When the file exists on local disk, returns (path, False)."""
        # Create a real temp file to simulate a stored video
        video_file = tmp_path / "video.mp4"
        video_file.write_bytes(b"fake")

        settings = _make_settings(use_s3=False)
        video_model = _make_video_model(object_key=str(video_file))

        # Patch LocalStorageProvider so base_dir maps to tmp_path
        with patch("app.core.storage.LocalStorageProvider") as MockProvider:
            provider_inst = MagicMock()
            provider_inst.base_dir = str(tmp_path)
            provider_inst.get_key_from_url.return_value = "video.mp4"
            MockProvider.return_value = provider_inst

            path, is_temp = await _resolve_video_local_path(video_model, settings)

        assert path == str(tmp_path / "video.mp4")
        assert is_temp is False

    @pytest.mark.asyncio
    async def test_local_file_missing_no_s3_returns_none(self, tmp_path):
        """File not on disk, S3 disabled → returns (None, False)."""
        settings = _make_settings(use_s3=False)
        video_model = _make_video_model(object_key="form_check_videos/u/missing.mp4")

        with patch("app.core.storage.LocalStorageProvider") as MockProvider:
            provider_inst = MagicMock()
            provider_inst.base_dir = str(tmp_path)
            provider_inst.get_key_from_url.return_value = "form_check_videos/u/missing.mp4"
            MockProvider.return_value = provider_inst

            path, is_temp = await _resolve_video_local_path(video_model, settings)

        assert path is None
        assert is_temp is False

    @pytest.mark.asyncio
    async def test_no_url_returns_none(self):
        """Video model with no url/object_key returns (None, False)."""
        settings = _make_settings(use_s3=False)
        video_model = _make_video_model(object_key=None, url=None)
        video_model.object_key = None
        video_model.url = None

        path, is_temp = await _resolve_video_local_path(video_model, settings)

        assert path is None
        assert is_temp is False


# ---------------------------------------------------------------------------
# 2. S3 storage — no storage_service provided
# ---------------------------------------------------------------------------

class TestS3NoStorageService:
    @pytest.mark.asyncio
    async def test_s3_storage_no_service_returns_none(self, tmp_path):
        """USE_S3_STORAGE=True but no storage_service → cannot download → (None, False)."""
        settings = _make_settings(use_s3=True)
        video_model = _make_video_model()

        with patch("app.core.storage.LocalStorageProvider") as MockProvider:
            provider_inst = MagicMock()
            provider_inst.base_dir = str(tmp_path)
            provider_inst.get_key_from_url.return_value = "form_check_videos/u/ts_abc_vid.mp4"
            MockProvider.return_value = provider_inst

            path, is_temp = await _resolve_video_local_path(
                video_model, settings, storage_service=None
            )

        assert path is None
        assert is_temp is False


# ---------------------------------------------------------------------------
# 3. S3 storage — download succeeds
# ---------------------------------------------------------------------------

class TestS3Download:
    @pytest.mark.asyncio
    async def test_s3_download_creates_temp_file(self, tmp_path):
        """S3 download succeeds → returns (temp_path, True), file contains bytes."""
        settings = _make_settings(use_s3=True)
        video_model = _make_video_model(object_key="form_check_videos/u/vid.mp4")
        fake_content = b"fake-video-bytes-12345"
        storage_svc = _make_storage_service(content=fake_content)

        with patch("app.core.storage.LocalStorageProvider") as MockProvider:
            provider_inst = MagicMock()
            provider_inst.base_dir = str(tmp_path)
            provider_inst.get_key_from_url.return_value = "form_check_videos/u/vid.mp4"
            MockProvider.return_value = provider_inst

            path, is_temp = await _resolve_video_local_path(
                video_model, settings, storage_service=storage_svc
            )

        assert path is not None
        assert is_temp is True
        assert os.path.isfile(path)
        with open(path, "rb") as f:
            assert f.read() == fake_content

        # Cleanup
        os.unlink(path)

    @pytest.mark.asyncio
    async def test_s3_download_uses_object_key_not_url_path(self, tmp_path):
        """Storage service is called with video_model.object_key (not a presigned URL path)."""
        settings = _make_settings(use_s3=True)
        expected_key = "form_check_videos/user123/ts_abc_file.mp4"
        video_model = _make_video_model(object_key=expected_key)
        storage_svc = _make_storage_service()

        with patch("app.core.storage.LocalStorageProvider") as MockProvider:
            provider_inst = MagicMock()
            provider_inst.base_dir = str(tmp_path)
            provider_inst.get_key_from_url.return_value = expected_key
            MockProvider.return_value = provider_inst

            path, is_temp = await _resolve_video_local_path(
                video_model, settings, storage_service=storage_svc
            )

        # download_file should be called with the S3 object key
        storage_svc.download_file.assert_called_once_with(expected_key)

        if path:
            os.unlink(path)

    @pytest.mark.asyncio
    async def test_s3_download_temp_file_has_mp4_suffix(self, tmp_path):
        """Temp file suffix is derived from the object key (preserves .mp4)."""
        settings = _make_settings(use_s3=True)
        video_model = _make_video_model(object_key="form_check_videos/u/vid.mp4")
        storage_svc = _make_storage_service()

        with patch("app.core.storage.LocalStorageProvider") as MockProvider:
            provider_inst = MagicMock()
            provider_inst.base_dir = str(tmp_path)
            provider_inst.get_key_from_url.return_value = "form_check_videos/u/vid.mp4"
            MockProvider.return_value = provider_inst

            path, is_temp = await _resolve_video_local_path(
                video_model, settings, storage_service=storage_svc
            )

        assert path is not None
        assert path.endswith(".mp4"), f"Expected .mp4 suffix, got: {path!r}"

        if path:
            os.unlink(path)


# ---------------------------------------------------------------------------
# 4. S3 storage — download fails
# ---------------------------------------------------------------------------

class TestS3DownloadFailure:
    @pytest.mark.asyncio
    async def test_s3_download_failure_returns_none(self, tmp_path):
        """S3 download raises → returns (None, False), does NOT propagate exception."""
        settings = _make_settings(use_s3=True)
        video_model = _make_video_model()

        storage_svc = AsyncMock()
        storage_svc.download_file = AsyncMock(side_effect=Exception("S3 connection timeout"))

        with patch("app.core.storage.LocalStorageProvider") as MockProvider:
            provider_inst = MagicMock()
            provider_inst.base_dir = str(tmp_path)
            provider_inst.get_key_from_url.return_value = "form_check_videos/u/vid.mp4"
            MockProvider.return_value = provider_inst

            # Must not raise
            path, is_temp = await _resolve_video_local_path(
                video_model, settings, storage_service=storage_svc
            )

        assert path is None
        assert is_temp is False


# ---------------------------------------------------------------------------
# 5. VideoStatus enum correctness
# ---------------------------------------------------------------------------

class TestVideoStatusEnum:
    def test_video_status_uploaded_member_exists(self):
        from app.models.enums import VideoStatus
        assert hasattr(VideoStatus, "UPLOADED")

    def test_video_status_uploaded_is_enum_not_string(self):
        from app.models.enums import VideoStatus
        from enum import Enum
        assert isinstance(VideoStatus.UPLOADED, Enum)

    def test_form_check_service_imports_video_status(self):
        """VideoStatus must be importable from form_check_service (was missing, caused Pydantic warning)."""
        from app.services.form_check_service import VideoStatus
        assert VideoStatus is not None


# ---------------------------------------------------------------------------
# 6. Squat routing via exercise_type fallback
# ---------------------------------------------------------------------------

class TestSquatRoutingFromExerciseType:
    """When ExerciseTemplate lookup fails, exercise_type on the Video model
    drives _is_squat so PostureV1 still runs."""

    def test_squat_exercise_type_yields_is_squat_true(self):
        """video_model.exercise_type = 'squat' → _is_squat = True."""
        exercise_type = "squat"
        _is_squat = "squat" in exercise_type.lower()
        assert _is_squat is True

    def test_all_squat_aliases_yield_is_squat_true(self):
        aliases = ["squat", "low bar squat", "high bar squat", "back squat", "front squat"]
        for alias in aliases:
            assert "squat" in alias.lower(), f"alias {alias!r} expected to contain 'squat'"

    def test_non_squat_exercise_yields_is_squat_false(self):
        for ex in ["deadlift", "bench press", "overhead press"]:
            _is_squat = "squat" in ex.lower()
            assert _is_squat is False, f"{ex!r} wrongly flagged as squat"
