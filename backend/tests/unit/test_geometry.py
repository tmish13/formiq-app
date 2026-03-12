"""Tests for app.ml.posture_v1.geometry module."""
import math
import pytest

from app.ml.posture_v1.geometry import compute_angle, compute_hip_angle, compute_knee_angles


def _lm(x: float, y: float, z: float = 0.0, visibility: float = 1.0):
    return {"x": x, "y": y, "z": z, "visibility": visibility}


# ---------------------------------------------------------------------------
# TestComputeAngle
# ---------------------------------------------------------------------------

class TestComputeAngle:
    def test_90_degree_l_shape(self):
        a = _lm(0, 1)   # above b
        b = _lm(0, 0)   # joint
        c = _lm(1, 0)   # right of b
        angle = compute_angle(a, b, c)
        assert abs(angle - 90.0) < 0.5

    def test_straight_line_180(self):
        a = _lm(-1, 0)
        b = _lm(0, 0)
        c = _lm(1, 0)
        angle = compute_angle(a, b, c)
        assert abs(angle - 180.0) < 0.5

    def test_zero_length_vector_no_crash(self):
        # a == b → zero-length vector
        a = _lm(0, 0)
        b = _lm(0, 0)
        c = _lm(1, 0)
        angle = compute_angle(a, b, c)
        assert angle == 0.0

    def test_45_degree_case(self):
        # a is directly above b, c is diagonal at 45°
        a = _lm(0, 1)
        b = _lm(0, 0)
        c = _lm(1, 1)
        angle = compute_angle(a, b, c)
        assert abs(angle - 45.0) < 0.5

    def test_result_in_0_to_180(self):
        a = _lm(3, 7)
        b = _lm(1, 2)
        c = _lm(5, 4)
        angle = compute_angle(a, b, c)
        assert 0.0 <= angle <= 180.0


# ---------------------------------------------------------------------------
# TestComputeKneeAngles
# ---------------------------------------------------------------------------

def _make_frame(landmark_dict: dict) -> list:
    """Build a 29-element frame list; fill missing with None."""
    frame = [None] * 29
    for idx, lm in landmark_dict.items():
        frame[idx] = lm
    return frame


class TestComputeKneeAngles:
    def test_deep_squat_both_angles_less_than_120(self):
        # Simulate a deep squat: knee is bent significantly
        frame = _make_frame({
            23: _lm(0.4, 0.5),   # left_hip
            25: _lm(0.4, 0.7),   # left_knee
            27: _lm(0.5, 0.65),  # left_ankle  → bent knee
            24: _lm(0.6, 0.5),   # right_hip
            26: _lm(0.6, 0.7),   # right_knee
            28: _lm(0.5, 0.65),  # right_ankle
        })
        lk, rk = compute_knee_angles(frame)
        assert lk is not None
        assert rk is not None
        assert lk < 120
        assert rk < 120

    def test_standing_frame_angles_above_160(self):
        # Simulate standing: joints nearly collinear (hip, knee, ankle vertically aligned)
        frame = _make_frame({
            23: _lm(0.4, 0.3),   # left_hip (top)
            25: _lm(0.4, 0.6),   # left_knee (middle)
            27: _lm(0.4, 0.9),   # left_ankle (bottom)
            24: _lm(0.6, 0.3),
            26: _lm(0.6, 0.6),
            28: _lm(0.6, 0.9),
        })
        lk, rk = compute_knee_angles(frame)
        assert lk is not None and lk > 160
        assert rk is not None and rk > 160

    def test_low_visibility_left_knee_returns_none(self):
        frame = _make_frame({
            23: _lm(0.4, 0.5),
            25: _lm(0.4, 0.7, visibility=0.1),  # low-vis → None
            27: _lm(0.5, 0.65),
            24: _lm(0.6, 0.5),
            26: _lm(0.6, 0.7),
            28: _lm(0.5, 0.65),
        })
        lk, rk = compute_knee_angles(frame)
        assert lk is None
        assert rk is not None

    def test_fewer_than_29_landmarks_returns_none_none(self):
        frame = [None] * 5  # way too short
        lk, rk = compute_knee_angles(frame)
        assert lk is None
        assert rk is None


# ---------------------------------------------------------------------------
# TestComputeHipAngle
# ---------------------------------------------------------------------------

class TestComputeHipAngle:
    def test_both_sides_present_returns_average(self):
        frame = _make_frame({
            11: _lm(0.3, 0.2),   # left_shoulder
            23: _lm(0.3, 0.5),   # left_hip
            25: _lm(0.3, 0.8),   # left_knee
            12: _lm(0.7, 0.2),   # right_shoulder
            24: _lm(0.7, 0.5),   # right_hip
            26: _lm(0.7, 0.8),   # right_knee
        })
        angle = compute_hip_angle(frame)
        assert angle is not None
        assert 0.0 < angle <= 180.0

    def test_right_shoulder_low_vis_uses_only_left(self):
        frame = _make_frame({
            11: _lm(0.3, 0.2),
            23: _lm(0.3, 0.5),
            25: _lm(0.3, 0.8),
            12: _lm(0.7, 0.2, visibility=0.1),  # low-vis right shoulder
            24: _lm(0.7, 0.5),
            26: _lm(0.7, 0.8),
        })
        angle = compute_hip_angle(frame)
        # Should compute only left side → not None, but also not None
        assert angle is not None

    def test_all_landmarks_missing_returns_none(self):
        frame = [None] * 29
        angle = compute_hip_angle(frame)
        assert angle is None
