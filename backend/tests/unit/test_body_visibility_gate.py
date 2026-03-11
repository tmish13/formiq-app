"""Unit tests for the PostureV1 body visibility gate.

Tests the behavioral contract of ``_check_body_landmark_visibility`` from
``app.tasks.analysis_tasks``.  The function is replicated inline here to
avoid importing the heavyweight Celery/DB-bound module.

If ``_check_body_landmark_visibility`` changes, update the inline copy to match.
"""

from typing import Optional, Dict, Any, List

# ---------------------------------------------------------------------------
# Reference implementation (mirrors analysis_tasks._check_body_landmark_visibility)
# ---------------------------------------------------------------------------

_BODY_LANDMARK_INDICES_FOR_VIS_GATE = [11, 12, 23, 24, 25, 26, 27, 28]


def _check_body_landmark_visibility(
    pose_data: List[Optional[List[Optional[Dict[str, Any]]]]],
    min_body_vis: float = 0.3,
    min_visible_frame_ratio: float = 0.5,
) -> "tuple[bool, str]":
    if not pose_data:
        return False, "no_pose_data"

    total_frames = 0
    visible_frames = 0

    for frame_landmarks in pose_data:
        if not frame_landmarks:
            continue
        total_frames += 1

        vis_scores = []
        for idx in _BODY_LANDMARK_INDICES_FOR_VIS_GATE:
            if idx < len(frame_landmarks) and isinstance(frame_landmarks[idx], dict):
                vis_scores.append(float(frame_landmarks[idx].get("visibility", 0.0)))

        if vis_scores and (sum(vis_scores) / len(vis_scores)) >= min_body_vis:
            visible_frames += 1

    if total_frames == 0:
        return False, "no_valid_frames"

    visible_ratio = visible_frames / total_frames
    if visible_ratio < min_visible_frame_ratio:
        return False, f"body_visibility_ratio_{visible_ratio:.2f}"

    return True, ""


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

def _make_landmark(x=0.5, y=0.5, z=0.0, visibility=0.9):
    return {"x": x, "y": y, "z": z, "visibility": visibility}


def _make_frame(body_visibility: float, n_landmarks: int = 33) -> List[Optional[Dict]]:
    """Create a frame with specified visibility for body landmarks (indices 11,12,23-28)."""
    frame = []
    for i in range(n_landmarks):
        if i in _BODY_LANDMARK_INDICES_FOR_VIS_GATE:
            frame.append(_make_landmark(visibility=body_visibility))
        else:
            frame.append(_make_landmark(visibility=0.9))
    return frame


def _make_pose_data(n_frames: int, body_visibility: float) -> List:
    return [_make_frame(body_visibility) for _ in range(n_frames)]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCheckBodyLandmarkVisibility:
    def test_empty_pose_data(self):
        ok, reason = _check_body_landmark_visibility([])
        assert ok is False
        assert reason == "no_pose_data"

    def test_none_pose_data(self):
        ok, reason = _check_body_landmark_visibility(None)
        assert ok is False
        assert reason == "no_pose_data"

    def test_all_none_frames(self):
        ok, reason = _check_body_landmark_visibility([None, None, None])
        assert ok is False
        assert reason == "no_valid_frames"

    def test_good_body_visibility_passes(self):
        pose_data = _make_pose_data(n_frames=30, body_visibility=0.85)
        ok, reason = _check_body_landmark_visibility(pose_data)
        assert ok is True
        assert reason == ""

    def test_face_only_video_fails(self):
        """Face-only video: body landmarks have near-zero visibility."""
        pose_data = _make_pose_data(n_frames=30, body_visibility=0.05)
        ok, reason = _check_body_landmark_visibility(pose_data)
        assert ok is False
        assert "body_visibility_ratio" in reason

    def test_exactly_at_threshold_passes(self):
        """Exactly 50% frames above 0.3 visibility — boundary passes."""
        pose_data = (
            _make_pose_data(n_frames=15, body_visibility=0.9)  # visible
            + _make_pose_data(n_frames=15, body_visibility=0.1)  # not visible
        )
        ok, reason = _check_body_landmark_visibility(pose_data, min_visible_frame_ratio=0.5)
        assert ok is True

    def test_just_below_threshold_fails(self):
        """49% frames above visibility — fails."""
        pose_data = (
            _make_pose_data(n_frames=49, body_visibility=0.9)
            + _make_pose_data(n_frames=51, body_visibility=0.1)
        )
        ok, reason = _check_body_landmark_visibility(pose_data, min_visible_frame_ratio=0.5)
        assert ok is False
        assert "body_visibility_ratio" in reason

    def test_missing_body_landmarks_in_frame(self):
        """Frame with fewer than 33 landmarks — missing body indices → zero visibility contribution."""
        # Only 10 landmarks per frame (body indices 11,12,23-28 all missing)
        pose_data = [[_make_landmark() for _ in range(10)] for _ in range(20)]
        ok, reason = _check_body_landmark_visibility(pose_data)
        # No body landmarks → vis_scores empty → frame not counted as visible
        assert ok is False

    def test_custom_thresholds(self):
        """Custom min_body_vis=0.1, so even low visibility passes."""
        pose_data = _make_pose_data(n_frames=30, body_visibility=0.15)
        ok, _ = _check_body_landmark_visibility(pose_data, min_body_vis=0.1, min_visible_frame_ratio=0.5)
        assert ok is True

    def test_reason_string_contains_ratio(self):
        """Reason string embeds the actual visibility ratio."""
        pose_data = _make_pose_data(n_frames=10, body_visibility=0.05)
        ok, reason = _check_body_landmark_visibility(pose_data)
        assert not ok
        # Ratio is 0.00 since no frames pass 0.3 visibility
        assert "0.00" in reason
