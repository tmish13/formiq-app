"""
Unit tests for visibility-aware component scoring (Phase 6).

Tests:
  A. compute_joint_visibility() — correct averaging, frame limit, zero frames.
  B. compute_component_visibility() — per-component mapping from joint visibility.
  C. get_visibility_quality_flags() — correct flag emission at thresholds.
  D. compute_component_scores() with visibility gate —
       - Low visibility joints null out the relevant component.
       - High visibility leaves scores unchanged.
       - Only the affected component is nulled (others intact).

All tests are inline (no DB, no model files).
"""
from __future__ import annotations

import numpy as np
import pytest

from app.ml.posture_v1.visibility import (
    COMPONENT_JOINTS,
    VISIBILITY_PARTIAL,
    VISIBILITY_TRUSTED,
    compute_component_visibility,
    compute_joint_visibility,
    get_visibility_quality_flags,
)
from app.ml.posture_v1.features_151d import EXPECTED_DIM
from app.ml.posture_v1.scoring import compute_component_scores


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_pose_data(n_frames: int, visibility: float = 0.9) -> list:
    """Build synthetic pose_data with uniform visibility on all 33 joints."""
    frame = [{"x": 0.5, "y": 0.5, "z": 0.0, "visibility": visibility} for _ in range(33)]
    return [frame] * n_frames


def _make_pose_data_per_joint(n_frames: int, joint_visibilities: dict) -> list:
    """
    Build pose_data where each joint has a specific visibility.
    joint_visibilities: {joint_index: visibility_value, ...}
    Missing joints default to 0.9.
    """
    frames = []
    for _ in range(n_frames):
        frame = [
            {
                "x": 0.5, "y": 0.5, "z": 0.0,
                "visibility": joint_visibilities.get(j, 0.9),
            }
            for j in range(33)
        ]
        frames.append(frame)
    return frames


def _zero_features() -> np.ndarray:
    return np.zeros(EXPECTED_DIM, dtype=np.float32)


def _spiked_features(feat_name: str, value: float = 4.0) -> np.ndarray:
    from app.ml.posture_v1.scoring import _NAME_TO_IDX
    vec = np.zeros(EXPECTED_DIM, dtype=np.float32)
    idx = _NAME_TO_IDX.get(feat_name)
    assert idx is not None, f"Feature '{feat_name}' not in FEATURE_NAMES"
    vec[idx] = value
    return vec


# ===========================================================================
# Class A — compute_joint_visibility
# ===========================================================================

class TestComputeJointVisibility:

    def test_uniform_visibility_all_joints(self):
        pose = _make_pose_data(30, visibility=0.8)
        jv = compute_joint_visibility(pose)
        assert jv.shape == (33,)
        np.testing.assert_allclose(jv, 0.8, atol=1e-5)

    def test_zero_visibility_all_joints(self):
        pose = _make_pose_data(30, visibility=0.0)
        jv = compute_joint_visibility(pose)
        np.testing.assert_allclose(jv, 0.0, atol=1e-5)

    def test_empty_pose_data(self):
        jv = compute_joint_visibility([])
        assert jv.shape == (33,)
        np.testing.assert_allclose(jv, 0.0)

    def test_none_frames_are_skipped(self):
        pose = [None] * 10
        jv = compute_joint_visibility(pose)
        np.testing.assert_allclose(jv, 0.0)

    def test_sequence_length_limits_frames(self):
        """Only the first sequence_length frames should be used."""
        high_vis = [{"x": 0.0, "y": 0.0, "z": 0.0, "visibility": 0.9} for _ in range(33)]
        low_vis  = [{"x": 0.0, "y": 0.0, "z": 0.0, "visibility": 0.1} for _ in range(33)]
        pose = [high_vis] * 5 + [low_vis] * 5   # 10 frames total
        # With sequence_length=5, only high_vis frames are used
        jv = compute_joint_visibility(pose, sequence_length=5)
        np.testing.assert_allclose(jv, 0.9, atol=1e-5)
        # With sequence_length=10, mixed
        jv_all = compute_joint_visibility(pose, sequence_length=10)
        np.testing.assert_allclose(jv_all, 0.5, atol=1e-5)

    def test_per_joint_specificity(self):
        """Only joint 25 (left_knee) has low visibility; others are high."""
        pose = _make_pose_data_per_joint(20, {25: 0.1})
        jv = compute_joint_visibility(pose)
        assert jv[25] < 0.2, "Joint 25 should have low visibility"
        assert jv[11] > 0.8, "Other joints should have high visibility"

    def test_returns_float32(self):
        pose = _make_pose_data(10)
        jv = compute_joint_visibility(pose)
        assert jv.dtype == np.float32


# ===========================================================================
# Class B — compute_component_visibility
# ===========================================================================

class TestComputeComponentVisibility:

    def test_all_high_visibility(self):
        jv = np.ones(33, dtype=np.float32) * 0.9
        cv = compute_component_visibility(jv)
        for comp in ("trunk_control", "knee_stability", "hip_drive", "forward_lean"):
            assert cv[comp] > 0.8

    def test_all_zero_visibility(self):
        jv = np.zeros(33, dtype=np.float32)
        cv = compute_component_visibility(jv)
        for comp in cv:
            assert cv[comp] == pytest.approx(0.0)

    def test_knee_joints_low_affects_knee_stability(self):
        """Setting knee + ankle joints (but NOT hips) to low visibility pulls
        knee_stability down while trunk_control (which uses only shoulders+hips) stays high.

        knee_stability joints = [23, 24, 25, 26, 27, 28]
        With joints 25,26,27,28 at 0.1 and hips 23,24 at 0.9:
          knee_stability mean = (0.9+0.9+0.1+0.1+0.1+0.1)/6 ≈ 0.37 → below VISIBILITY_PARTIAL
        trunk_control joints = [11, 12, 23, 24] all at 0.9 → unaffected
        """
        jv = np.ones(33, dtype=np.float32) * 0.9
        # Only set knee + ankle joints low (NOT hips, which are shared with trunk_control)
        for idx in [25, 26, 27, 28]:
            jv[idx] = 0.1
        cv = compute_component_visibility(jv)
        # knee_stability mean = (0.9+0.9+0.1+0.1+0.1+0.1)/6 ≈ 0.367
        assert cv["knee_stability"] < VISIBILITY_PARTIAL, (
            f"knee_stability should be below {VISIBILITY_PARTIAL}, got {cv['knee_stability']:.3f}"
        )
        assert cv["trunk_control"] > 0.7, "trunk_control should be unaffected"

    def test_trunk_joints_low_affects_trunk_and_forward_lean(self):
        """Shoulder/hip visibility affects trunk_control AND forward_lean (same joints)."""
        jv = np.ones(33, dtype=np.float32) * 0.9
        for idx in [11, 12, 23, 24]:
            jv[idx] = 0.2
        cv = compute_component_visibility(jv)
        assert cv["trunk_control"] < 0.4
        assert cv["forward_lean"] < 0.4
        # knee_stability also affected since it uses hips (23,24)
        # hip_drive also affected since it uses shoulders+hips

    def test_all_components_present(self):
        jv = np.zeros(33, dtype=np.float32)
        cv = compute_component_visibility(jv)
        for comp in ("trunk_control", "knee_stability", "hip_drive", "forward_lean"):
            assert comp in cv


# ===========================================================================
# Class C — get_visibility_quality_flags
# ===========================================================================

class TestGetVisibilityQualityFlags:

    def test_no_flags_when_all_trusted(self):
        cv = {comp: 0.9 for comp in COMPONENT_JOINTS}
        assert get_visibility_quality_flags(cv) == []

    def test_unreliable_flag_below_partial_threshold(self):
        cv = {"trunk_control": 0.3, "knee_stability": 0.9,
              "hip_drive": 0.9, "forward_lean": 0.9}
        flags = get_visibility_quality_flags(cv)
        assert "trunk_control_visibility_unreliable" in flags
        # Others should not have flags
        assert "knee_stability_visibility_unreliable" not in flags
        assert "knee_stability_visibility_partial" not in flags

    def test_partial_flag_between_thresholds(self):
        cv = {"trunk_control": 0.9, "knee_stability": 0.55,
              "hip_drive": 0.9, "forward_lean": 0.9}
        flags = get_visibility_quality_flags(cv)
        assert "knee_stability_visibility_partial" in flags
        assert "knee_stability_visibility_unreliable" not in flags

    def test_no_flag_at_partial_threshold_boundary(self):
        """Exactly at VISIBILITY_PARTIAL (0.4): should get unreliable, not partial."""
        cv = {comp: VISIBILITY_PARTIAL for comp in COMPONENT_JOINTS}
        flags = get_visibility_quality_flags(cv)
        # 0.4 < 0.4 is False, so we get partial (0.4 < 0.7)
        for comp in COMPONENT_JOINTS:
            assert f"{comp}_visibility_partial" in flags
            assert f"{comp}_visibility_unreliable" not in flags

    def test_no_flag_at_trusted_boundary(self):
        """Exactly at VISIBILITY_TRUSTED (0.7): no flag."""
        cv = {comp: VISIBILITY_TRUSTED for comp in COMPONENT_JOINTS}
        flags = get_visibility_quality_flags(cv)
        assert flags == []

    def test_all_unreliable(self):
        cv = {comp: 0.1 for comp in COMPONENT_JOINTS}
        flags = get_visibility_quality_flags(cv)
        for comp in COMPONENT_JOINTS:
            assert f"{comp}_visibility_unreliable" in flags


# ===========================================================================
# Class D — compute_component_scores with visibility gate
# ===========================================================================

class TestComponentScoresVisibilityGate:
    """The visibility gate in compute_component_scores() must null unreliable components."""

    def _scores(self, features: np.ndarray, component_visibility: dict | None) -> dict:
        return compute_component_scores(
            features,
            scaler_mean=None,
            scaler_std=None,
            component_visibility=component_visibility,
        )

    def test_no_visibility_param_returns_normal_scores(self):
        feats = _spiked_features("bottom_trunk_wobble", 3.0)
        scores = self._scores(feats, None)
        assert scores["trunk_control"] is not None

    def test_high_visibility_leaves_scores_intact(self):
        high_vis = {comp: 0.9 for comp in COMPONENT_JOINTS}
        feats = _spiked_features("bottom_trunk_wobble", 3.0)
        scores = self._scores(feats, high_vis)
        assert scores["trunk_control"] is not None

    def test_low_trunk_visibility_nulls_trunk_control(self):
        """trunk_control visibility < 0.4 → trunk_control score becomes None."""
        low_vis = {
            "trunk_control": 0.2,   # unreliable
            "knee_stability": 0.9,
            "hip_drive": 0.9,
            "forward_lean": 0.9,
        }
        feats = _spiked_features("bottom_trunk_wobble", 3.0)
        scores = self._scores(feats, low_vis)
        assert scores["trunk_control"] is None, (
            "trunk_control should be None when trunk visibility < 0.4"
        )
        # Other components must be unaffected
        assert scores["knee_stability"] is not None
        assert scores["hip_drive"] is not None

    def test_low_knee_visibility_nulls_knee_stability(self):
        low_vis = {
            "trunk_control": 0.9,
            "knee_stability": 0.15,   # unreliable
            "hip_drive": 0.9,
            "forward_lean": 0.9,
        }
        feats = _spiked_features("knee_asymmetry_mean", 3.0)
        scores = self._scores(feats, low_vis)
        assert scores["knee_stability"] is None, (
            "knee_stability should be None when knee visibility < 0.4"
        )
        assert scores["trunk_control"] is not None

    def test_low_hip_visibility_nulls_hip_drive(self):
        low_vis = {
            "trunk_control": 0.9,
            "knee_stability": 0.9,
            "hip_drive": 0.1,   # unreliable
            "forward_lean": 0.9,
        }
        feats = _spiked_features("left_hip_angle_std", 3.0)
        scores = self._scores(feats, low_vis)
        assert scores["hip_drive"] is None
        assert scores["knee_stability"] is not None

    def test_partial_visibility_keeps_score(self):
        """Partial visibility (0.4–0.7) should NOT null the score (just flag it)."""
        partial_vis = {
            "trunk_control": 0.55,   # partial — score kept
            "knee_stability": 0.9,
            "hip_drive": 0.9,
            "forward_lean": 0.9,
        }
        feats = _spiked_features("bottom_trunk_wobble", 3.0)
        scores = self._scores(feats, partial_vis)
        # Score should still be there (not nulled by partial visibility)
        assert scores["trunk_control"] is not None, (
            "partial visibility (>= 0.4) should not null the component score"
        )

    def test_all_low_visibility_nulls_all_components(self):
        all_low = {comp: 0.05 for comp in COMPONENT_JOINTS}
        feats = _zero_features()
        scores = self._scores(feats, all_low)
        assert scores["trunk_control"] is None
        assert scores["knee_stability"] is None
        assert scores["hip_drive"] is None

    def test_only_affected_component_is_nulled(self):
        """One component low visibility must not cascade to unrelated components."""
        mixed = {
            "trunk_control": 0.1,   # unreliable — nulled
            "knee_stability": 0.85,
            "hip_drive": 0.80,
            "forward_lean": 0.9,
        }
        feats = _zero_features()
        scores = self._scores(feats, mixed)
        assert scores["trunk_control"] is None
        assert scores["knee_stability"] is not None
        assert scores["hip_drive"] is not None
