"""Unit tests for _check_minimum_motion (inline replica — no imports from tasks module)."""
import pytest
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Inline replica (avoids pulling in Celery/services/settings at import time)
# ---------------------------------------------------------------------------
_HIP_INDICES = [23, 24]
_KNEE_INDICES = [25, 26]


def _check_minimum_motion(
    pose_data: List[Optional[List[Optional[Dict[str, Any]]]]],
    min_hip_y_range: float = 0.05,
    min_knee_y_range: float = 0.05,
) -> "tuple[bool, str]":
    if not pose_data:
        return False, "no_pose_data"

    hip_y: List[float] = []
    knee_y: List[float] = []

    for frame_landmarks in pose_data:
        if not frame_landmarks:
            continue
        for idx in _HIP_INDICES:
            if idx < len(frame_landmarks) and isinstance(frame_landmarks[idx], dict):
                hip_y.append(float(frame_landmarks[idx].get("y", 0.0)))
        for idx in _KNEE_INDICES:
            if idx < len(frame_landmarks) and isinstance(frame_landmarks[idx], dict):
                knee_y.append(float(frame_landmarks[idx].get("y", 0.0)))

    if not hip_y or not knee_y:
        return False, "no_hip_knee_landmarks"

    hip_range = max(hip_y) - min(hip_y)
    knee_range = max(knee_y) - min(knee_y)

    if hip_range < min_hip_y_range and knee_range < min_knee_y_range:
        return (
            False,
            f"no_significant_movement_hip_{hip_range:.3f}_knee_{knee_range:.3f}",
        )

    return True, ""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_frame(hip_y: float, knee_y: float) -> List[Optional[Dict[str, Any]]]:
    """Build a minimal landmark list with hip/knee y values set."""
    frame: List[Optional[Dict[str, Any]]] = [None] * 33
    # left_hip=23, right_hip=24
    frame[23] = {"x": 0.5, "y": hip_y, "z": 0.0, "visibility": 0.9}
    frame[24] = {"x": 0.5, "y": hip_y + 0.01, "z": 0.0, "visibility": 0.9}
    # left_knee=25, right_knee=26
    frame[25] = {"x": 0.5, "y": knee_y, "z": 0.0, "visibility": 0.9}
    frame[26] = {"x": 0.5, "y": knee_y + 0.01, "z": 0.0, "visibility": 0.9}
    return frame


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestCheckMinimumMotion:
    def test_empty_pose_data_returns_false(self):
        ok, reason = _check_minimum_motion([])
        assert ok is False
        assert reason == "no_pose_data"

    def test_none_pose_data_returns_false(self):
        # Falsy input (None treated as empty)
        ok, reason = _check_minimum_motion(None)  # type: ignore[arg-type]
        assert ok is False
        assert reason == "no_pose_data"

    def test_all_none_frames_returns_false(self):
        pose_data = [None, None, None]
        ok, reason = _check_minimum_motion(pose_data)
        assert ok is False
        assert reason == "no_hip_knee_landmarks"

    def test_static_pose_returns_false(self):
        """Hip and knee y constant across all frames → no movement."""
        pose_data = [_make_frame(hip_y=0.5, knee_y=0.7) for _ in range(10)]
        ok, reason = _check_minimum_motion(pose_data)
        assert ok is False
        assert "no_significant_movement" in reason

    def test_good_squat_motion_returns_true(self):
        """Hip y-range = 0.15 → meaningful movement detected."""
        frames = []
        for i in range(20):
            hip_y = 0.5 + (i / 20) * 0.15  # range = 0.15
            knee_y = 0.7 + (i / 20) * 0.20  # range = 0.20
            frames.append(_make_frame(hip_y=hip_y, knee_y=knee_y))
        ok, reason = _check_minimum_motion(frames)
        assert ok is True
        assert reason == ""

    def test_custom_thresholds_respected(self):
        """With a very large threshold, even a wide-range sequence fails."""
        frames = [_make_frame(hip_y=0.5 + i * 0.01, knee_y=0.7 + i * 0.01) for i in range(10)]
        # Default threshold=0.05: hip_range=0.09 → passes
        ok_default, _ = _check_minimum_motion(frames)
        assert ok_default is True
        # Large threshold=0.50: hip_range=0.09 < 0.50 AND knee_range=0.09 < 0.50 → fails
        ok_strict, reason = _check_minimum_motion(frames, min_hip_y_range=0.50, min_knee_y_range=0.50)
        assert ok_strict is False
        assert "no_significant_movement" in reason

    def test_only_hip_moves_returns_true(self):
        """Hip range sufficient even if knee range is below threshold → OR gate."""
        frames = []
        for i in range(10):
            hip_y = 0.5 + i * 0.02   # range = 0.18 (passes hip threshold)
            knee_y = 0.7              # constant (fails knee threshold)
            frames.append(_make_frame(hip_y=hip_y, knee_y=knee_y))
        ok, reason = _check_minimum_motion(frames)
        assert ok is True

    def test_only_knee_moves_returns_true(self):
        """Knee range sufficient even if hip range is below threshold."""
        frames = []
        for i in range(10):
            hip_y = 0.5               # constant (fails hip threshold)
            knee_y = 0.7 + i * 0.02  # range = 0.18 (passes knee threshold)
            frames.append(_make_frame(hip_y=hip_y, knee_y=knee_y))
        ok, reason = _check_minimum_motion(frames)
        assert ok is True
