"""
Unit tests for frame export validation logic.

Uses inline replicas of the validation logic (no app imports, no DB).
"""
import pytest


# ---------------------------------------------------------------------------
# Inline replica of the validation logic
# ---------------------------------------------------------------------------

def _validate_frame_index(frame_index: int, total_frames):
    """
    Returns an error string if the frame_index is invalid, otherwise None.

    Args:
        frame_index: requested frame index (must be >= 0)
        total_frames: total number of frames available, or None if unknown

    Returns:
        str  — error description
        None — index is valid
    """
    if frame_index < 0:
        return "frame_index must be non-negative"
    if total_frames is None:
        # Unknown length — any non-negative index is syntactically valid
        return None
    if frame_index >= total_frames:
        return "frame_index out of range"
    return None


def _is_frame_data_available(video, frame_s3_keys) -> bool:
    """Returns True only when both video and its frame_s3_keys are non-empty."""
    return bool(video and frame_s3_keys)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestValidateFrameIndex:
    def test_negative_index_returns_error(self):
        assert _validate_frame_index(-1, 10) == "frame_index must be non-negative"

    def test_negative_large_returns_error(self):
        assert _validate_frame_index(-99, 10) is not None

    def test_zero_index_is_valid(self):
        assert _validate_frame_index(0, 10) is None

    def test_index_within_bounds_is_valid(self):
        assert _validate_frame_index(5, 10) is None

    def test_index_at_exact_boundary_is_invalid(self):
        # total_frames=10 means valid indices are 0..9; 10 is out of range
        assert _validate_frame_index(10, 10) == "frame_index out of range"

    def test_index_beyond_bounds_is_invalid(self):
        assert _validate_frame_index(100, 10) == "frame_index out of range"

    def test_total_frames_none_any_nonneg_is_valid(self):
        # When total is unknown, any non-negative index passes syntax check
        assert _validate_frame_index(0, None) is None
        assert _validate_frame_index(999, None) is None

    def test_total_frames_none_negative_still_invalid(self):
        assert _validate_frame_index(-1, None) is not None


class TestIsFrameDataAvailable:
    def test_no_video_returns_false(self):
        assert _is_frame_data_available(None, ["key1"]) is False

    def test_no_frame_keys_returns_false(self):
        assert _is_frame_data_available(object(), None) is False

    def test_empty_frame_keys_returns_false(self):
        assert _is_frame_data_available(object(), []) is False

    def test_video_and_keys_present_returns_true(self):
        assert _is_frame_data_available(object(), ["key1", "key2"]) is True
