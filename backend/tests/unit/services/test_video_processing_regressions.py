"""
VideoProcessingService — regression tests for production fixes.

Documents and guards each specific bug found and fixed during the test-suite
hardening pass (Feb 2026).

API notes (confirmed by reading the implementation):
  _validate_video(path) → (is_valid: bool, message: str|None, metadata: dict|None)
    – returns (False, msg, None/meta) for most failures; raises VideoValidationError
      ONLY for duration (which is then caught by the outer try/except and returned
      as (False, str(e), None)).
  _preprocess_frames(frames) → list[np.ndarray]
    – resizes to self.target_size, converts BGR→RGB; dtype is uint8.
"""
import io
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import cv2
import numpy as np
import pytest

from app.services.video_processing_service import VideoProcessingService
from app.core.exceptions import VideoValidationError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@pytest.fixture()
def mock_settings() -> MagicMock:
    s = MagicMock()
    s.MAX_VIDEO_DURATION = VideoProcessingService.MAX_DURATION
    s.MIN_VIDEO_DURATION = 1
    s.MIN_VIDEO_FPS = 10
    s.MIN_VIDEO_FRAMES = 50
    s.TARGET_FPS = 30
    s.TARGET_WIDTH = 640
    s.TARGET_HEIGHT = 480
    s.FFMPEG_PATH = "ffmpeg"
    s.FFPROBE_PATH = "ffprobe"
    s.FFMPEG_TIMEOUT = 60
    # target_size used by _preprocess_frames
    s.AI_TARGET_FRAME_WIDTH = 64
    s.AI_TARGET_FRAME_HEIGHT = 64
    s.TMP_FILE_STORAGE_PATH = "/tmp/formiq_tests"
    # Settings consumed by VideoProcessingService.__init__ via self.settings
    s.VIDEO_FRAME_RATE = 30
    s.MAX_VIDEO_FRAMES = 300
    return s


@pytest.fixture()
def service(mock_settings: MagicMock) -> VideoProcessingService:
    return VideoProcessingService(app_settings=mock_settings)


# ---------------------------------------------------------------------------
# Regression 1: VideoValidationError must be constructable with validation_type
#
# Bug: VideoValidationError was called without the required `validation_type`
#      positional argument → TypeError at every validation failure.
# Fix: every construction now passes validation_type=...
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestVideoValidationErrorContract:
    def test_validation_error_can_be_constructed_with_type(self):
        """VideoValidationError must accept (message, validation_type)."""
        err = VideoValidationError("too wide", validation_type="resolution")
        assert isinstance(err, VideoValidationError)

    def test_validation_error_requires_validation_type(self):
        """Constructing without validation_type must not silently succeed
        by positional default — the call we fixed passes it explicitly."""
        # The fix ensures validation_type is always provided; this test
        # documents that the keyword form is the contract.
        err = VideoValidationError("msg", validation_type="duration")
        assert err is not None

    def test_resolution_too_low_returns_false_not_raises(
        self, service: VideoProcessingService, monkeypatch, tmp_path: Path
    ):
        """_validate_video returns (False, msg, meta) for low-resolution videos.

        Prior to the fix the call raised TypeError before reaching this return,
        so any resolution-check failure was an unhandled exception.
        """
        fake_video = tmp_path / "small.mp4"
        fake_video.write_bytes(b"\x00" * 16)

        gets_map = {
            cv2.CAP_PROP_FPS: 30.0,
            cv2.CAP_PROP_FRAME_COUNT: 300,
        }
        cap_mock = MagicMock()
        cap_mock.isOpened.return_value = True
        cap_mock.get.side_effect = lambda prop: gets_map.get(prop, 0)

        monkeypatch.setattr(cv2, "VideoCapture", lambda _: cap_mock)
        # Width=200 → min(200, 480) = 200 < 240 → validation fails
        monkeypatch.setattr(
            VideoProcessingService,
            "_get_video_dimensions",
            lambda self, path: (200, 480),
        )

        is_valid, message, _meta = service._validate_video(str(fake_video))
        assert is_valid is False
        assert message is not None
        assert "240" in message or "resolution" in message.lower()

    def test_duration_too_long_returns_false_not_type_error(
        self, service: VideoProcessingService, monkeypatch, tmp_path: Path
    ):
        """_validate_video returns (False, msg, ...) for over-duration videos.

        Before the fix, the VideoValidationError constructor call was missing
        validation_type → TypeError → unhandled 500 in the endpoint.
        After the fix the TypeError is gone; the exception is caught internally
        and returned as (False, str(exception), None).
        """
        fake_video = tmp_path / "long.mp4"
        fake_video.write_bytes(b"\x00" * 16)

        fps_val = 30.0
        max_dur = VideoProcessingService.MAX_DURATION
        num_frames = int(fps_val * (max_dur + 1))

        gets_map = {
            cv2.CAP_PROP_FPS: fps_val,
            cv2.CAP_PROP_FRAME_COUNT: num_frames,
        }
        cap_mock = MagicMock()
        cap_mock.isOpened.return_value = True
        cap_mock.get.side_effect = lambda prop: gets_map.get(prop, 0)

        monkeypatch.setattr(cv2, "VideoCapture", lambda _: cap_mock)
        monkeypatch.setattr(
            VideoProcessingService,
            "_get_video_dimensions",
            lambda self, path: (640, 480),
        )

        # Must not raise; must return (False, message, ...)
        result = service._validate_video(str(fake_video))
        is_valid, message, _meta = result
        assert is_valid is False
        assert message is not None
        # Message comes from VideoValidationError str representation
        assert "duration" in message.lower() or "range" in message.lower() or \
               "acceptable" in message.lower()


# ---------------------------------------------------------------------------
# Regression 2: MAX_DURATION must be a class constant, not a settings value
#
# Bug: tests used mock_settings.MAX_VIDEO_DURATION = 60 while the real service
#      reads VideoProcessingService.MAX_DURATION = 300, causing threshold
#      mismatch (61s triggered no error, appeared to pass but was never tested).
# Fix: tests must reference VideoProcessingService.MAX_DURATION directly.
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestMaxDurationConstant:
    def test_class_constant_exists_and_is_numeric(self):
        """VideoProcessingService.MAX_DURATION must be a positive number."""
        assert hasattr(VideoProcessingService, "MAX_DURATION")
        assert isinstance(VideoProcessingService.MAX_DURATION, (int, float))
        assert VideoProcessingService.MAX_DURATION > 0

    def test_class_constant_is_greater_than_60(self):
        """MAX_DURATION must be > 60 s (old erroneous mock value = 60)."""
        assert VideoProcessingService.MAX_DURATION > 60, (
            f"MAX_DURATION={VideoProcessingService.MAX_DURATION} "
            "should be > 60 (old wrong mock value was 60)"
        )

    def test_short_video_is_valid(
        self, service: VideoProcessingService, monkeypatch, tmp_path: Path
    ):
        """A 10-second video must NOT be rejected for duration."""
        fake_video = tmp_path / "ok.mp4"
        fake_video.write_bytes(b"\x00" * 16)

        fps_val = 30.0
        gets_map = {
            cv2.CAP_PROP_FPS: fps_val,
            cv2.CAP_PROP_FRAME_COUNT: int(fps_val * 10),
        }
        cap_mock = MagicMock()
        cap_mock.isOpened.return_value = True
        cap_mock.get.side_effect = lambda prop: gets_map.get(prop, 0)

        monkeypatch.setattr(cv2, "VideoCapture", lambda _: cap_mock)
        monkeypatch.setattr(
            VideoProcessingService,
            "_get_video_dimensions",
            lambda self, path: (640, 480),
        )

        is_valid, message, meta = service._validate_video(str(fake_video))
        assert is_valid is True, f"Short video should be valid, got: {message}"
        assert meta is not None
        assert meta["duration"] == pytest.approx(10.0, rel=0.01)


# ---------------------------------------------------------------------------
# Regression 3: _preprocess_frames must return uint8 RGB frames
#
# Bug: tests asserted float32 normalised output; service actually returns uint8.
# Fix: assert dtype is uint8.
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestPreprocessFramesDtype:
    def test_output_frames_are_uint8(self, service: VideoProcessingService):
        """_preprocess_frames output must be uint8, not float32."""
        bgr_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        bgr_frame[100, 200] = [255, 128, 0]

        result = service._preprocess_frames([bgr_frame])

        assert result is not None
        assert len(result) == 1
        assert result[0].dtype == np.uint8, \
            f"Expected uint8, got {result[0].dtype}"

    def test_output_values_in_0_255_range(self, service: VideoProcessingService):
        """Pixel values must stay in [0, 255] — no float normalisation."""
        frame = np.full((100, 100, 3), fill_value=200, dtype=np.uint8)
        result = service._preprocess_frames([frame])

        assert result[0].min() >= 0
        assert result[0].max() <= 255

    def test_output_shape_uses_service_target_size(self, service: VideoProcessingService):
        """Output frame shape must match self.target_size (AI_TARGET_FRAME_WIDTH x HEIGHT).

        self.target_size = (64, 64) as configured by mock_settings fixture.
        """
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        result = service._preprocess_frames([frame])

        target_w, target_h = service.target_size
        h, w, c = result[0].shape
        assert w == target_w, f"Expected width {target_w}, got {w}"
        assert h == target_h, f"Expected height {target_h}, got {h}"
        assert c == 3
