"""Tests for app.ml.posture_v1.highlight module."""
import pytest

from app.ml.posture_v1.highlight import HighlightFrameInfo, select_highlight_frame


def _lm(x: float, y: float, z: float = 0.0, visibility: float = 1.0):
    return {"x": x, "y": y, "z": z, "visibility": visibility}


def _make_frame(landmark_dict: dict, size: int = 29) -> list:
    frame = [None] * size
    for idx, lm in landmark_dict.items():
        frame[idx] = lm
    return frame


def _standing_frame(y_base: float = 0.5) -> list:
    """Frame with hips and knees at a given y level."""
    return _make_frame({
        23: _lm(0.4, y_base),
        24: _lm(0.6, y_base),
        25: _lm(0.4, y_base + 0.15),
        26: _lm(0.6, y_base + 0.15),
        27: _lm(0.4, y_base + 0.3),
        28: _lm(0.6, y_base + 0.3),
    })


class TestSelectHighlightFrame:
    def test_empty_list_returns_none(self):
        result = select_highlight_frame([])
        assert result is None

    def test_all_none_frames_returns_none(self):
        result = select_highlight_frame([None, None, None])
        assert result is None

    def test_single_valid_frame_returns_frame_index_0(self):
        frame = _standing_frame(0.6)
        result = select_highlight_frame([frame])
        assert result is not None
        assert result.frame_index == 0

    def test_deepest_frame_selected_correctly(self):
        # Frame 3 has hips/knees at y=0.9 → deepest (highest y)
        frames = [
            _standing_frame(0.5),   # frame 0: hips at y=0.5
            _standing_frame(0.6),   # frame 1: hips at y=0.6
            _standing_frame(0.55),  # frame 2: hips at y=0.55
            _standing_frame(0.9),   # frame 3: hips at y=0.9 ← deepest
            _standing_frame(0.7),   # frame 4: hips at y=0.7
        ]
        result = select_highlight_frame(frames)
        assert result is not None
        assert result.frame_index == 3

    def test_two_equal_depth_frames_returns_first(self):
        # Frames 1 and 3 have identical hip+knee y values
        frames = [
            _standing_frame(0.5),
            _standing_frame(0.8),   # frame 1 ← first equal
            _standing_frame(0.5),
            _standing_frame(0.8),   # frame 3 ← second equal
        ]
        result = select_highlight_frame(frames)
        assert result is not None
        assert result.frame_index == 1

    def test_timestamp_sec_computed_from_fps(self):
        frames = [None, None, _standing_frame(0.7)]  # frame 2 is deepest
        result = select_highlight_frame(frames, fps=30.0)
        assert result is not None
        assert result.frame_index == 2
        assert abs(result.timestamp_sec - round(2 / 30.0, 3)) < 1e-6

    def test_custom_fps_60_respected(self):
        frames = [None, _standing_frame(0.8)]  # frame 1 is deepest
        result = select_highlight_frame(frames, fps=60.0)
        assert result is not None
        assert result.frame_index == 1
        assert abs(result.timestamp_sec - round(1 / 60.0, 3)) < 1e-6

    def test_knee_angles_populated_when_visibility_ok(self):
        frame = _make_frame({
            23: _lm(0.4, 0.5),
            25: _lm(0.4, 0.7),
            27: _lm(0.5, 0.65),
            24: _lm(0.6, 0.5),
            26: _lm(0.6, 0.7),
            28: _lm(0.5, 0.65),
        })
        result = select_highlight_frame([frame])
        assert result is not None
        assert result.knee_angle_left is not None
        assert result.knee_angle_right is not None

    def test_knee_angles_none_when_visibility_low(self):
        frame = _make_frame({
            23: _lm(0.4, 0.5),
            25: _lm(0.4, 0.7, visibility=0.1),  # low-vis left knee
            27: _lm(0.5, 0.65),
            24: _lm(0.6, 0.5),
            26: _lm(0.6, 0.7, visibility=0.1),  # low-vis right knee
            28: _lm(0.5, 0.65),
        })
        result = select_highlight_frame([frame])
        assert result is not None
        assert result.knee_angle_left is None
        assert result.knee_angle_right is None

    def test_depth_proxy_stored_in_result(self):
        frame = _standing_frame(0.7)
        result = select_highlight_frame([frame])
        assert result is not None
        assert result.depth_proxy > 0.0

    def test_highlight_frame_info_dataclass_fields_present(self):
        frame = _standing_frame(0.6)
        result = select_highlight_frame([frame], fps=25.0)
        assert result is not None
        assert isinstance(result, HighlightFrameInfo)
        assert hasattr(result, 'frame_index')
        assert hasattr(result, 'timestamp_sec')
        assert hasattr(result, 'knee_angle_left')
        assert hasattr(result, 'knee_angle_right')
        assert hasattr(result, 'hip_angle')
        assert hasattr(result, 'depth_proxy')

    def test_partial_sequence_with_none_frames_skips_none(self):
        frames = [
            None,
            _standing_frame(0.5),
            None,
            _standing_frame(0.8),  # frame 3 ← best valid
            None,
        ]
        result = select_highlight_frame(frames)
        assert result is not None
        assert result.frame_index == 3

    def test_frame_with_no_hip_knee_landmarks_has_zero_proxy(self):
        # Frame with only shoulder landmarks (no hips or knees)
        frame_no_hips = _make_frame({
            11: _lm(0.3, 0.2),
            12: _lm(0.7, 0.2),
        })
        frame_with_hips = _standing_frame(0.6)
        result = select_highlight_frame([frame_no_hips, frame_with_hips])
        assert result is not None
        # frame_with_hips has higher depth_proxy
        assert result.frame_index == 1
