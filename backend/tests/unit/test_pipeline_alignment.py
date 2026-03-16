"""
Pipeline alignment tests (Phase 6).

Assert rough score ranges for synthetic fixtures with known properties:

  - A "perfect form" fixture (all feature deviations = 0): expect all component
    scores around 50 (z=0 → score=50, since 0 is the training mean).
  - A "bad form" fixture (features spiked high — all "high_is_bad" features at +3σ):
    expect low component scores (near 0) because z=+3 → clamped to 2 → score = 0.
  - A "good form" fixture (features spiked negative — all features at -2σ):
    expect high component scores (near 100) because z=-2 → score = 100.
  - Verify: posture_score is independent of component scores.
  - Verify: score_band matches posture_score at all boundaries.
  - Verify: for a knee-fault fixture, knee_stability_score is the lowest component.
  - Verify: for a trunk-fault fixture, torso_stability_score is the lowest component.

No model files needed. Uses compute_full_scores() with synthetic 151D vectors.
"""
from __future__ import annotations

import numpy as np
import pytest

from app.ml.posture_v1.features_151d import EXPECTED_DIM
from app.ml.posture_v1.scoring import (
    _NAME_TO_IDX,
    _TRUNK_CONTROL_FEATURES,
    _KNEE_STABILITY_FEATURES,
    _HIP_DRIVE_FEATURES,
    compute_full_scores,
    compute_score_band,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _zero_features() -> np.ndarray:
    return np.zeros(EXPECTED_DIM, dtype=np.float32)


def _features_all_components_bad(value: float = 3.0) -> np.ndarray:
    """Spike ALL component features high (bad direction)."""
    vec = np.zeros(EXPECTED_DIM, dtype=np.float32)
    all_features = (
        list(_TRUNK_CONTROL_FEATURES)
        + list(_KNEE_STABILITY_FEATURES)
        + list(_HIP_DRIVE_FEATURES)
    )
    for name, _ in all_features:
        idx = _NAME_TO_IDX.get(name)
        if idx is not None:
            vec[idx] = value
    return vec


def _features_all_components_good(value: float = -2.0) -> np.ndarray:
    """Spike ALL component features low (good direction)."""
    vec = np.zeros(EXPECTED_DIM, dtype=np.float32)
    all_features = (
        list(_TRUNK_CONTROL_FEATURES)
        + list(_KNEE_STABILITY_FEATURES)
        + list(_HIP_DRIVE_FEATURES)
    )
    for name, _ in all_features:
        idx = _NAME_TO_IDX.get(name)
        if idx is not None:
            vec[idx] = value
    return vec


def _features_knee_fault_only(value: float = 4.0) -> np.ndarray:
    """Spike ONLY knee_stability features to simulate knee fault."""
    vec = np.zeros(EXPECTED_DIM, dtype=np.float32)
    for name, _ in _KNEE_STABILITY_FEATURES:
        idx = _NAME_TO_IDX.get(name)
        if idx is not None:
            vec[idx] = value
    return vec


def _features_trunk_fault_only(value: float = 4.0) -> np.ndarray:
    """Spike ONLY trunk_control features to simulate trunk fault."""
    vec = np.zeros(EXPECTED_DIM, dtype=np.float32)
    for name, _ in _TRUNK_CONTROL_FEATURES:
        idx = _NAME_TO_IDX.get(name)
        if idx is not None:
            vec[idx] = value
    return vec


def _run(prob_fault: float, features: np.ndarray) -> dict:
    return compute_full_scores(
        prob_fault=prob_fault,
        features_151d=features,
        scaler_mean=None,
        scaler_std=None,
    )


# ===========================================================================
# Class A — Baseline (z=0 features)
# ===========================================================================

class TestBaselineFixture:
    """All features = 0 → z = 0 → component score = 50 (training average)."""

    def test_trunk_control_at_average(self):
        r = _run(0.3, _zero_features())
        # _z_to_score(0.0) = 100 * (1 - 2/4) = 50
        assert r["component_scores"]["trunk_control"] == 50

    def test_knee_stability_at_average(self):
        r = _run(0.3, _zero_features())
        assert r["component_scores"]["knee_stability"] == 50

    def test_hip_drive_at_average(self):
        r = _run(0.3, _zero_features())
        assert r["component_scores"]["hip_drive"] == 50

    def test_named_scores_at_average(self):
        r = _run(0.3, _zero_features())
        ns = r["named_scores"]
        assert ns["torso_stability_score"] == 50
        assert ns["knee_symmetry_score"] == 50
        assert ns["bottom_control_score"] == 50

    def test_posture_score_at_baseline(self):
        """Zero features → all components = 50; blend with model_score gives intermediate value.

        model_score = 70 (prob_fault=0.3).
        component_weighted = 50 (all z=0).
        Blend: 0.65*70 + 0.35*50 = 45.5 + 17.5 = 63.
        """
        r = _run(0.3, _zero_features())
        assert r["posture_score"] == 63
        assert r["model_score"] == 70
        assert r["component_weighted_score"] == 50


# ===========================================================================
# Class B — Bad form fixture
# ===========================================================================

class TestBadFormFixture:
    """All component features spiked to +3σ → component scores near 0."""

    def test_trunk_control_low_when_all_trunk_features_bad(self):
        feats = _features_all_components_bad(value=3.0)
        r = _run(0.85, feats)
        # z=3 → clamped to 2 → score = 100*(1-4/4) = 0
        # mean of [0, 0, 0, 0, 0] = 0
        assert r["component_scores"]["trunk_control"] <= 10, (
            f"Expected trunk_control <= 10, got {r['component_scores']['trunk_control']}"
        )

    def test_knee_stability_low_when_all_knee_features_bad(self):
        feats = _features_all_components_bad(value=3.0)
        r = _run(0.85, feats)
        assert r["component_scores"]["knee_stability"] <= 10

    def test_hip_drive_low_when_all_hip_features_bad(self):
        feats = _features_all_components_bad(value=3.0)
        r = _run(0.85, feats)
        assert r["component_scores"]["hip_drive"] <= 10

    def test_score_band_poor_for_high_prob_fault(self):
        r = _run(0.85, _zero_features())
        assert r["score_band"] == "poor"


# ===========================================================================
# Class C — Good form fixture
# ===========================================================================

class TestGoodFormFixture:
    """All component features at -2σ → component scores near 100."""

    def test_trunk_control_high_when_features_excellent(self):
        feats = _features_all_components_good(value=-2.0)
        r = _run(0.05, feats)
        # z=-2 → clamped to -2 → score = 100*(1-0/4) = 100
        assert r["component_scores"]["trunk_control"] >= 90

    def test_knee_stability_high_when_features_excellent(self):
        feats = _features_all_components_good(value=-2.0)
        r = _run(0.05, feats)
        assert r["component_scores"]["knee_stability"] >= 90

    def test_score_band_excellent_for_low_prob_fault(self):
        # Requires good features so all components ≈ 100, ceiling ≥ 130 → posture_score=95.
        # Zero features would cap at 80 ("good") because components=50 → ceiling=80.
        feats = _features_all_components_good(value=-2.0)
        r = _run(0.05, feats)
        assert r["score_band"] == "excellent"


# ===========================================================================
# Class D — Fault specificity
# ===========================================================================

class TestFaultSpecificity:
    """Faults in one area must show lowest score in the corresponding component."""

    def test_knee_fault_gives_lowest_knee_score(self):
        """Spiking only knee features → knee_stability is the lowest component."""
        feats = _features_knee_fault_only(value=4.0)
        r = _run(0.3, feats)
        cs = r["component_scores"]
        assert cs["knee_stability"] is not None
        assert cs["trunk_control"] is not None
        assert cs["hip_drive"] is not None
        assert cs["knee_stability"] < cs["trunk_control"], (
            "knee fault fixture: knee_stability should be lower than trunk_control"
        )
        assert cs["knee_stability"] < cs["hip_drive"], (
            "knee fault fixture: knee_stability should be lower than hip_drive"
        )

    def test_trunk_fault_gives_lowest_trunk_score(self):
        """Spiking only trunk features → trunk_control is the lowest component."""
        feats = _features_trunk_fault_only(value=4.0)
        r = _run(0.3, feats)
        cs = r["component_scores"]
        assert cs["trunk_control"] < cs["knee_stability"], (
            "trunk fault fixture: trunk_control should be lower than knee_stability"
        )
        assert cs["trunk_control"] < cs["hip_drive"], (
            "trunk fault fixture: trunk_control should be lower than hip_drive"
        )

    def test_forward_lean_score_responds_to_trunk_forward_lean_feature(self):
        """forward_lean_score comes from trunk_forward_lean — NOT trunk_control."""
        from app.ml.posture_v1.scoring import _TRUNK_CONTROL_FEATURES
        # Ensure trunk_forward_lean is NOT in trunk_control features (invariant)
        trunk_names = [name for name, _ in _TRUNK_CONTROL_FEATURES]
        assert "trunk_forward_lean" not in trunk_names, (
            "trunk_forward_lean must NOT be in _TRUNK_CONTROL_FEATURES"
        )
        # Verify it still produces a forward_lean_score via the single-feature path
        vec = _zero_features()
        idx = _NAME_TO_IDX.get("trunk_forward_lean")
        assert idx is not None
        vec[idx] = 2.0  # spike it
        r = _run(0.3, vec)
        r_baseline = _run(0.3, _zero_features())
        assert r["named_scores"]["forward_lean_score"] < r_baseline["named_scores"]["forward_lean_score"], (
            "Spiking trunk_forward_lean should lower forward_lean_score"
        )

    def test_knee_top_signal_appears_for_knee_fault(self):
        """When knee features are spiked, top_signals must include a knee-related feature."""
        feats = _features_knee_fault_only(value=4.0)
        r = _run(0.3, feats)
        knee_signal_names = {
            "knee_asymmetry_mean", "bottom_knee_asymmetry",
            "left_knee_angle_std", "right_knee_angle_std",
            "left_knee_angle_bottom_std", "right_knee_angle_bottom_std",
        }
        top_names = {s["name"] for s in r.get("top_signals", [])}
        assert top_names & knee_signal_names, (
            f"Expected knee signal in top_signals, got: {top_names}"
        )


# ===========================================================================
# Class E — score_band consistency
# ===========================================================================

class TestScoreBandConsistency:
    """score_band in compute_full_scores must always match compute_score_band(posture_score)."""

    @pytest.mark.parametrize("prob_fault", [0.0, 0.05, 0.15, 0.25, 0.4, 0.5, 0.6, 0.75, 1.0])
    def test_score_band_consistent_with_posture_score(self, prob_fault: float):
        r = _run(prob_fault, _zero_features())
        expected_band = compute_score_band(r["posture_score"])
        assert r["score_band"] == expected_band, (
            f"prob_fault={prob_fault}: score_band={r['score_band']} "
            f"but compute_score_band({r['posture_score']})={expected_band}"
        )
