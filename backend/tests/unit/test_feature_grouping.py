"""
Unit tests for component feature boundary invariants (Part 5).

Asserts that:
  1. Every feature belongs to at most ONE component group.
  2. The forward_lean feature (trunk_forward_lean) is NOT in any component group
     (it is computed via a dedicated single-feature path in compute_named_scores).
  3. Component scores respond only to their own features, not to unrelated ones.

All tests use inline replicas and direct imports — no DB, no model files.
"""
from __future__ import annotations

import pytest
import numpy as np


# ---------------------------------------------------------------------------
# Helpers — import the real feature lists from scoring.py
# ---------------------------------------------------------------------------

from app.ml.posture_v1.scoring import (
    _TRUNK_CONTROL_FEATURES,
    _KNEE_STABILITY_FEATURES,
    _HIP_DRIVE_FEATURES,
    _NAME_TO_IDX,
    _z_to_score,
    compute_component_scores,
    compute_named_scores,
    FEATURE_NAMES,
    EXPECTED_DIM,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _feature_names_only(feature_list):
    """Extract just feature name strings from a list of (name, direction) tuples."""
    return [name for name, _ in feature_list]


def _make_zero_features():
    """Return a 151-D zero vector (all-average, i.e. z=0 when not scaled)."""
    return np.zeros(EXPECTED_DIM, dtype=np.float32)


def _features_with_spike(feat_name: str, value: float = 5.0):
    """Return a 151-D vector with one feature spiked to `value`."""
    vec = _make_zero_features()
    idx = _NAME_TO_IDX.get(feat_name)
    assert idx is not None, f"Feature '{feat_name}' not found in FEATURE_NAMES"
    vec[idx] = value
    return vec


# ---------------------------------------------------------------------------
# Class A — No-overlap invariant
# ---------------------------------------------------------------------------

class TestNoFeatureOverlap:
    """Every feature must appear in at most ONE component group."""

    ALL_GROUPS = {
        "trunk_control": _feature_names_only(_TRUNK_CONTROL_FEATURES),
        "knee_stability": _feature_names_only(_KNEE_STABILITY_FEATURES),
        "hip_drive":      _feature_names_only(_HIP_DRIVE_FEATURES),
    }

    def test_no_feature_in_two_groups(self):
        seen = {}
        for group, names in self.ALL_GROUPS.items():
            for name in names:
                if name in seen:
                    pytest.fail(
                        f"Feature '{name}' appears in both '{seen[name]}' and '{group}'. "
                        "Each feature must belong to exactly one component group."
                    )
                seen[name] = group

    def test_trunk_forward_lean_not_in_component_groups(self):
        """trunk_forward_lean must NOT be in any component group — it has its own path."""
        overlap_feat = "trunk_forward_lean"
        for group, names in self.ALL_GROUPS.items():
            assert overlap_feat not in names, (
                f"'{overlap_feat}' found in '{group}' component group. "
                "It must be computed exclusively via _compute_single_feature_score "
                "for forward_lean_score."
            )

    def test_all_component_features_exist_in_feature_names(self):
        """Every feature listed in a component group must be in the 151-D feature set."""
        for group, names in self.ALL_GROUPS.items():
            for name in names:
                assert name in _NAME_TO_IDX, (
                    f"Feature '{name}' in group '{group}' not found in FEATURE_NAMES. "
                    "Check for typos in _*_FEATURES lists."
                )

    def test_groups_are_non_empty(self):
        for group, names in self.ALL_GROUPS.items():
            assert len(names) > 0, f"Component group '{group}' has no features."


# ---------------------------------------------------------------------------
# Class B — Component isolation
# ---------------------------------------------------------------------------

class TestComponentIsolation:
    """Spiking a feature should only change its own component, not others."""

    def _scores(self, feat_vec):
        comp = compute_component_scores(feat_vec, scaler_mean=None, scaler_std=None)
        return comp

    def test_trunk_spike_does_not_change_knee_score(self):
        baseline = self._scores(_make_zero_features())
        spiked   = self._scores(_features_with_spike("bottom_trunk_wobble", value=3.0))

        assert spiked["trunk_control"] != baseline["trunk_control"], \
            "Spiking a trunk feature should change trunk_control score."
        # knee_stability must remain at the same level (both computed from z=0 or the spike)
        # Technically, knee features are untouched so the score should be identical.
        assert spiked["knee_stability"] == baseline["knee_stability"], \
            "Spiking a trunk feature should NOT change knee_stability score."

    def test_knee_spike_does_not_change_trunk_score(self):
        baseline = self._scores(_make_zero_features())
        spiked   = self._scores(_features_with_spike("knee_asymmetry_mean", value=3.0))

        assert spiked["knee_stability"] != baseline["knee_stability"], \
            "Spiking a knee feature should change knee_stability score."
        assert spiked["trunk_control"] == baseline["trunk_control"], \
            "Spiking a knee feature should NOT change trunk_control score."

    def test_hip_spike_does_not_change_knee_score(self):
        baseline = self._scores(_make_zero_features())
        spiked   = self._scores(_features_with_spike("left_hip_angle_std", value=3.0))

        assert spiked["hip_drive"] != baseline["hip_drive"], \
            "Spiking a hip feature should change hip_drive score."
        assert spiked["knee_stability"] == baseline["knee_stability"], \
            "Spiking a hip feature should NOT change knee_stability score."

    def test_forward_lean_spike_does_not_change_trunk_control(self):
        """trunk_forward_lean must no longer affect trunk_control."""
        baseline = self._scores(_make_zero_features())
        spiked   = self._scores(_features_with_spike("trunk_forward_lean", value=3.0))

        # After the fix, trunk_control should be unchanged because trunk_forward_lean
        # is removed from _TRUNK_CONTROL_FEATURES.
        assert spiked["trunk_control"] == baseline["trunk_control"], (
            "trunk_forward_lean should NOT affect trunk_control. "
            "Make sure it is removed from _TRUNK_CONTROL_FEATURES."
        )


# ---------------------------------------------------------------------------
# Class C — named_scores boundary
# ---------------------------------------------------------------------------

class TestNamedScoresBoundary:
    """forward_lean_score is computed from trunk_forward_lean via its own path."""

    def _named(self, feat_vec):
        comp = compute_component_scores(feat_vec, scaler_mean=None, scaler_std=None)
        return compute_named_scores(feat_vec, scaler_mean=None, scaler_std=None, component_scores=comp)

    def test_forward_lean_score_is_computed(self):
        vec = _features_with_spike("trunk_forward_lean", value=2.0)
        named = self._named(vec)
        # forward_lean_score must be present and reflect the spike
        assert named.get("forward_lean_score") is not None
        baseline_named = self._named(_make_zero_features())
        assert named["forward_lean_score"] < baseline_named["forward_lean_score"], \
            "A spike in trunk_forward_lean should lower forward_lean_score (high=bad)."

    def test_torso_stability_not_affected_by_forward_lean_spike(self):
        """After the fix, torso_stability_score should be independent of trunk_forward_lean."""
        baseline = self._named(_make_zero_features())
        spiked   = self._named(_features_with_spike("trunk_forward_lean", value=3.0))
        assert spiked["torso_stability_score"] == baseline["torso_stability_score"], (
            "torso_stability_score should not change when only trunk_forward_lean is spiked. "
            "trunk_forward_lean must be removed from _TRUNK_CONTROL_FEATURES."
        )

    def test_all_four_named_scores_returned(self):
        named = self._named(_make_zero_features())
        for key in ("torso_stability_score", "knee_symmetry_score",
                    "bottom_control_score", "forward_lean_score"):
            assert key in named, f"Missing key '{key}' in named_scores."
