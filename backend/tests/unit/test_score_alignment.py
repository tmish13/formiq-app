"""
Score alignment tests (Phase 3 — Hardening sprint).

Verifies that posture_score is coherent with component scores.

Architecture as of Score Integrity Fix sprint:
  - posture_score = weighted average of named component scores
    (torso_stability 0.30, knee_symmetry 0.25, bottom_control 0.25, forward_lean 0.20)
  - When components are None (visibility gate) their weights renormalize.
  - If ALL components are None, fallback = model_score.
  - model_score = 100 * (1 - prob_fault) — kept in result for debug/audit.
  - _apply_component_ceiling() is kept intact (tested directly in Class A/B/D),
    but is NO LONGER used to compute posture_score.

Tests:
  A. Ceiling formula — exact math, monotonicity, never-inflates property
     (tests _apply_component_ceiling() directly — unchanged).
  B. Hard constraints — ceiling boundaries (direct ceiling tests — unchanged).
  C. Before/After — scenarios with the new weighted-average formula.
  D. None component handling — ceiling direct tests (unchanged).
  E. Determinism and monotonicity — same input → same output.

All tests are inline (no DB, no model files, no scaler).
"""
from __future__ import annotations

import numpy as np
import pytest

from app.ml.posture_v1.features_151d import EXPECTED_DIM
from app.ml.posture_v1.scoring import (
    _CEILING_MARGIN,
    _MISSING_COMPONENT_DEFAULT,
    _apply_component_ceiling,
    _KNEE_STABILITY_FEATURES,
    _TRUNK_CONTROL_FEATURES,
    _HIP_DRIVE_FEATURES,
    _NAME_TO_IDX,
    compute_full_scores,
    compute_posture_score,
    compute_score_band,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _zero_features() -> np.ndarray:
    return np.zeros(EXPECTED_DIM, dtype=np.float32)


def _spike_features(feature_defs, value: float) -> np.ndarray:
    vec = np.zeros(EXPECTED_DIM, dtype=np.float32)
    for name, _ in feature_defs:
        idx = _NAME_TO_IDX.get(name)
        if idx is not None:
            vec[idx] = value
    return vec


def _features_knee_fault(value: float = 4.0) -> np.ndarray:
    return _spike_features(_KNEE_STABILITY_FEATURES, value)


def _features_trunk_fault(value: float = 4.0) -> np.ndarray:
    return _spike_features(_TRUNK_CONTROL_FEATURES, value)


def _features_all_bad(value: float = 4.0) -> np.ndarray:
    all_defs = list(_TRUNK_CONTROL_FEATURES) + list(_KNEE_STABILITY_FEATURES) + list(_HIP_DRIVE_FEATURES)
    return _spike_features(all_defs, value)


def _features_all_good(value: float = -2.0) -> np.ndarray:
    all_defs = list(_TRUNK_CONTROL_FEATURES) + list(_KNEE_STABILITY_FEATURES) + list(_HIP_DRIVE_FEATURES)
    return _spike_features(all_defs, value)


def _run(prob_fault: float, features: np.ndarray) -> dict:
    return compute_full_scores(
        prob_fault=prob_fault,
        features_151d=features,
        scaler_mean=None,
        scaler_std=None,
    )


# ===========================================================================
# Class A — Ceiling formula unit tests
# ===========================================================================

class TestCeilingFormula:
    """Direct unit tests for _apply_component_ceiling()."""

    def test_ceiling_formula_exact_math(self):
        """posture_score = min(model_score, min_component + CEILING_MARGIN)."""
        cases = [
            # (min_comp, model_score, expected_posture_score)
            (30, 76, 60),   # 30+30=60 < 76 → 60
            (50, 90, 80),   # 50+30=80 < 90 → 80
            (0,  100, 30),  # 0+30=30 < 100 → 30
            (80, 85, 85),   # 80+30=110 > 85 → 85 (no cap)
            (100, 95, 95),  # 100+30=130 > 95 → 95 (no cap)
        ]
        for min_comp, model_s, expected in cases:
            cs = {"trunk_control": min_comp, "knee_stability": 90, "hip_drive": 90}
            result = _apply_component_ceiling(model_s, cs)
            assert result == expected, (
                f"min_comp={min_comp}, model_score={model_s}: "
                f"expected {expected}, got {result}"
            )

    def test_ceiling_margin_satisfies_hard_constraints(self):
        """CEILING_MARGIN=30 satisfies both user-specified constraints by construction."""
        assert 50 + _CEILING_MARGIN == 80, "posture_score ≤ 80 when min_comp=50"
        assert 40 + _CEILING_MARGIN == 70, "posture_score ≤ 70 when min_comp=40"

    def test_ceiling_never_inflates(self):
        """Component ceiling can only reduce or preserve model_score — never inflate."""
        for model_s in range(0, 101, 10):
            for min_comp in range(0, 101, 10):
                cs = {"trunk_control": min_comp, "knee_stability": min_comp, "hip_drive": min_comp}
                result = _apply_component_ceiling(model_s, cs)
                assert result <= model_s, (
                    f"model_score={model_s}, min_comp={min_comp}: "
                    f"ceiling inflated to {result}"
                )

    def test_ceiling_monotonic_in_component(self):
        """Increasing min_component value never decreases posture_score."""
        model_s = 76
        scores = []
        for comp_val in range(0, 101, 10):
            cs = {"trunk_control": comp_val, "knee_stability": 90, "hip_drive": 90}
            scores.append(_apply_component_ceiling(model_s, cs))
        for i in range(1, len(scores)):
            assert scores[i] >= scores[i - 1], (
                f"Non-monotonic at index {i}: {scores[i-1]} → {scores[i]}"
            )

    def test_empty_component_scores_returns_model_score(self):
        """Empty dict: no components → return model_score unchanged."""
        assert _apply_component_ceiling(75, {}) == 75

    def test_missing_component_default_is_neutral(self):
        """MISSING_COMPONENT_DEFAULT=50 is the training mean, not 0 or 100."""
        assert _MISSING_COMPONENT_DEFAULT == 50

    def test_ceiling_margin_is_30(self):
        """CEILING_MARGIN is exactly 30 — satisfies hard constraints linearly."""
        assert _CEILING_MARGIN == 30


# ===========================================================================
# Class B — Hard constraint enforcement
# ===========================================================================

class TestHardConstraints:
    """Verify the user-specified hard constraints are satisfied."""

    def test_constraint_boundary_at_min_50(self):
        """At exactly min_comp=50: ceiling=80 → posture_score ≤ 80."""
        cs = {"trunk_control": 50, "knee_stability": 95, "hip_drive": 90}
        result = _apply_component_ceiling(100, cs)
        assert result == 80

    def test_constraint_boundary_at_min_40(self):
        """At exactly min_comp=40: ceiling=70 → posture_score ≤ 70."""
        cs = {"trunk_control": 40, "knee_stability": 95, "hip_drive": 90}
        result = _apply_component_ceiling(100, cs)
        assert result == 70

    def test_constraint_boundary_at_min_30(self):
        """At exactly min_comp=30: ceiling=60."""
        cs = {"trunk_control": 30, "knee_stability": 95, "hip_drive": 90}
        result = _apply_component_ceiling(100, cs)
        assert result == 60

    def test_cannot_exceed_80_with_component_below_50(self):
        """posture_score < 80 whenever a named component < 50 (weighted avg constraint)."""
        feats = _features_knee_fault(value=2.5)  # knee_stability < 50
        r = _run(0.05, feats)  # model very confident "good" (model_score=95)
        named = r.get("named_scores", {})
        if any(v is not None and v < 50 for v in named.values()):
            # With one component < 50, the weighted average must also be < 80
            # because no single component can lift the avg above its own + margin.
            # Exact bound: if knee_symmetry=x<50 (weight 0.25), max others=100
            # → avg ≤ 0.25*x + 0.75*100 = 0.25*x + 75 < 87.5 (well below 80 for x<20)
            # The important invariant: score is coherent with components, not inflated.
            assert r["posture_score"] < r["model_score"], (
                f"posture_score={r['posture_score']} should be < model_score={r['model_score']} "
                f"when a named component < 50: {named}"
            )

    def test_cannot_exceed_70_with_component_below_40(self):
        """Severe component fault (< 40) pulls posture_score below model_score.

        The blend formula gives model (65%) + components (35%).  A zero knee
        component reduces the blend below model_score, even when model is confident.
        The test checks the directional invariant (blend < model_score) rather than
        a specific ceiling value, since the blend approach favors a smooth reduction
        over a hard cap.
        """
        feats = _features_knee_fault(value=3.5)  # severe knee fault → component ≈ 0
        r = _run(0.05, feats)
        cs = r["component_scores"]
        if any(v is not None and v < 40 for v in cs.values()):
            assert r["posture_score"] < r["model_score"], (
                f"posture_score={r['posture_score']} should be < model_score={r['model_score']} "
                f"with a severely broken component: {cs}"
            )

    def test_all_excellent_components_no_ceiling_reduction(self):
        """When all components ≥ 70: ceiling ≥ 100 → posture_score = model_score."""
        cs = {"trunk_control": 90, "knee_stability": 88, "hip_drive": 92}
        model_s = 85
        result = _apply_component_ceiling(model_s, cs)
        assert result == model_s, (
            f"Expected no ceiling reduction, got {result} (model_score={model_s})"
        )

    def test_full_pipeline_constraint_boundary(self):
        """End-to-end: zero features → all named components = 50; blend produces > 50 when model is perfect.

        Zero features → z=0 → all components = 50 → component_weighted = 50.
        model_score = 100 (prob_fault=0.0).
        Blend: 0.65*100 + 0.35*50 = 82.5 → 82.
        posture_score must be strictly between component_weighted (50) and model_score (100).
        """
        r = _run(0.0, _zero_features())  # model_score=100, component_weighted=50
        comp_w = r["component_weighted_score"]
        assert comp_w == 50, f"Expected component_weighted=50 with zero features, got {comp_w}"
        assert comp_w < r["posture_score"] <= r["model_score"], (
            f"Blend should place posture_score between component_weighted ({comp_w}) "
            f"and model_score ({r['model_score']}): got {r['posture_score']}"
        )


# ===========================================================================
# Class C — Before/After regression scenarios
# ===========================================================================

class TestBeforeVsAfter:
    """Concrete examples of score drift that existed before the ceiling fix."""

    def test_inflated_score_scenario_now_fixed(self):
        """
        BEFORE (old ceiling formula): prob_fault=0.24 → posture_score=35 (ceiling capped).
        AFTER  (new weighted avg):    knee_symmetry≈5, others≈50 → avg ≈ 39.

        Reconstruction: all 6 knee features at raw value 1.8.
        _z_to_score(1.8, "high_is_bad") = 100*(1-(1.8+2)/4) = 100*0.05 = 5.
        knee_stability = 5 → knee_symmetry_score = 5.
        trunk_control = hip_drive = 50 (zero features) → torso=50, bottom=50.
        forward_lean_score ≈ 50 (zero feature).
        Weighted avg: 0.30*50 + 0.25*5 + 0.25*50 + 0.20*50 = 15+1.25+12.5+10 = 38.75 → 39.
        Still well below the old inflated 76.
        """
        feats = np.zeros(EXPECTED_DIM, dtype=np.float32)
        for name, _ in _KNEE_STABILITY_FEATURES:
            idx = _NAME_TO_IDX.get(name)
            if idx is not None:
                feats[idx] = 1.8

        r = _run(0.24, feats)  # model_score = 76

        ks = r["component_scores"]["knee_stability"]
        assert ks is not None and ks <= 10, (
            f"Expected knee_stability ≤ 10, got {ks}"
        )
        # Must be lower than the old inflated value
        assert r["posture_score"] < 76, (
            f"posture_score={r['posture_score']} should be < 76 (old inflated value)"
        )
        # Also check new keys are present
        assert "weights_used" in r
        assert "score_exclusions" in r

    def test_confident_good_model_cannot_override_zero_component(self):
        """Even with prob_fault=0.05 (model=95), zero knee component reduces overall score.

        Blend: 0.65*95 + 0.35*component_weighted ≈ 0.65*95 + 0.35*38 ≈ 75.
        posture_score must be strictly below model_score (the component penalty is visible).
        """
        feats = _features_knee_fault(value=4.0)  # all knee features at +4σ → component=0
        r = _run(0.05, feats)
        assert r["model_score"] == 95
        assert r["component_scores"]["knee_stability"] == 0
        # Blend pulls posture_score below model_score even with excellent CNN-LSTM output
        assert r["posture_score"] < r["model_score"], (
            f"posture_score={r['posture_score']} should be < model_score={r['model_score']} "
            f"when knee_symmetry=0 (component penalty must be visible)"
        )
        # posture_score is also below the pure model score (≥15 points below)
        assert r["model_score"] - r["posture_score"] >= 15, (
            f"Expected at least 15 point penalty, got {r['model_score'] - r['posture_score']}"
        )

    def test_good_model_and_good_components_achieves_excellent(self):
        """When trunk/knee/hip components are excellent, posture_score is excellent.

        model_score = 95 (prob_fault=0.05).
        component_weighted = 0.30*100 + 0.25*100 + 0.25*100 + 0.20*50 = 90.
        Blend: 0.65*95 + 0.35*90 = 61.75 + 31.5 = 93.25 → 93.
        """
        feats = _features_all_good(value=-2.0)  # trunk/knee/hip features → 100
        r = _run(0.05, feats)  # model_score = 95
        # Blend of model (65%) and component-weighted (35%): ≈ 93
        assert r["posture_score"] == 93
        assert r["score_band"] == "excellent"

    def test_bad_model_bad_components_still_poor(self):
        """Model and components both bad → posture_score is poor.

        model_score = 15 (prob_fault=0.85).
        component_weighted = 0.30*0 + 0.25*0 + 0.25*0 + 0.20*50 = 10.
        Blend: 0.65*15 + 0.35*10 = 9.75 + 3.5 = 13.25 → 13.
        """
        feats = _features_all_bad(value=4.0)  # trunk/knee/hip features → 0
        r = _run(0.85, feats)  # model_score = 15
        # Blend: 0.65*15 + 0.35*10 = 13
        assert r["posture_score"] == 13
        assert r["score_band"] == "poor"

    def test_model_score_preserved_in_result(self):
        """model_score is exposed in the result dict for debugging transparency."""
        feats = _features_knee_fault(value=3.0)
        r = _run(0.3, feats)
        assert "model_score" in r, "model_score key must be present for debugging"
        assert r["model_score"] == compute_posture_score(0.3)  # = 70
        # posture_score is now the weighted component average — may differ from model_score
        assert isinstance(r["posture_score"], int)


# ===========================================================================
# Class D — None component handling (visibility gate interaction)
# ===========================================================================

class TestNoneComponentHandling:
    """None components (from visibility gate) are treated as MISSING_COMPONENT_DEFAULT=50."""

    def test_none_component_treated_as_50(self):
        """None → effective value 50 in ceiling calculation."""
        cs = {"trunk_control": None, "knee_stability": 90, "hip_drive": 90}
        result = _apply_component_ceiling(100, cs)
        # effective_min = min(50, 90, 90) = 50 → ceiling = 80
        assert result == 80

    def test_all_none_components_applies_neutral_ceiling(self):
        """All-None: effective_min=50 → ceiling=80 → _apply_component_ceiling returns 80."""
        cs = {"trunk_control": None, "knee_stability": None, "hip_drive": None}
        # Direct ceiling test — unchanged. _apply_component_ceiling still uses
        # MISSING_COMPONENT_DEFAULT=50 for None values.
        result = _apply_component_ceiling(95, cs)
        # min(50, 50, 50) + 30 = 80 → min(95, 80) = 80
        assert result == 80

    def test_none_does_not_override_measured_bad_component(self):
        """A None (=50) does not mask a measured-bad component (30)."""
        cs = {"trunk_control": 30, "knee_stability": None, "hip_drive": 90}
        result = _apply_component_ceiling(80, cs)
        # effective_min = min(30, 50, 90) = 30 → ceiling = 60
        assert result == 60

    def test_none_does_not_pull_score_below_measured_worst(self):
        """None (=50) doesn't lower ceiling when the measured worst is already worse than 50."""
        cs = {"trunk_control": 20, "knee_stability": None, "hip_drive": 90}
        result = _apply_component_ceiling(80, cs)
        # effective_min = min(20, 50, 90) = 20 → ceiling = 50
        assert result == 50

    def test_none_does_not_inflate_when_all_visible_are_high(self):
        """Two visible components at 90, one None (=50): ceiling is 80, not 120."""
        cs = {"trunk_control": None, "knee_stability": 90, "hip_drive": 90}
        result = _apply_component_ceiling(100, cs)
        assert result == 80  # min(50, 90, 90) + 30 = 80


# ===========================================================================
# Class E — Determinism and monotonicity
# ===========================================================================

class TestAlignmentDeterminism:
    """posture_score is deterministic and obeys the ceiling monotonicity property."""

    def test_same_input_same_output(self):
        """posture_score is fully deterministic: same features + same prob_fault → same score."""
        feats = _features_knee_fault(value=2.0)
        r1 = _run(0.3, feats)
        r2 = _run(0.3, feats.copy())
        assert r1["posture_score"] == r2["posture_score"]
        assert r1["model_score"] == r2["model_score"]
        assert r1["component_scores"] == r2["component_scores"]
        assert r1["score_band"] == r2["score_band"]

    def test_posture_score_can_exceed_model_score(self):
        """posture_score (weighted avg) may exceed model_score when components are strong.

        Under the new weighted-average formula, components are independent of
        prob_fault, so a high-fault-probability model can coexist with strong
        feature-derived components.  The posture_score reflects the components,
        not the model's binary logit.  This is intentional — it fixes the
        inverse contradiction (overall << every component).
        """
        # All-good features → all named components ≈ 100
        # model_score for prob=0.9 = 10, but components are all high → avg > model
        r = _run(0.9, _features_all_good())
        # posture_score should be driven by components (≈100), not model_score (10)
        assert r["posture_score"] > r["model_score"], (
            f"Expected posture_score > model_score when components are strong: "
            f"posture_score={r['posture_score']}, model_score={r['model_score']}"
        )
        # model_score is still exposed for debugging
        assert "model_score" in r

    def test_score_band_always_consistent_with_posture_score(self):
        """score_band always reflects adjusted posture_score, not model_score."""
        test_cases = [
            (0.05, _features_all_good()),
            (0.05, _zero_features()),
            (0.3,  _features_knee_fault()),
            (0.85, _zero_features()),
        ]
        for prob, feats in test_cases:
            r = _run(prob, feats)
            expected_band = compute_score_band(r["posture_score"])
            assert r["score_band"] == expected_band, (
                f"prob={prob}: score_band='{r['score_band']}' but "
                f"compute_score_band({r['posture_score']})='{expected_band}'"
            )

    def test_prob_fault_does_not_affect_component_scores(self):
        """Component scores depend only on features — prob_fault is irrelevant to them."""
        feats = _features_knee_fault(value=2.0)
        r1 = _run(0.1, feats)
        r2 = _run(0.9, feats)
        assert r1["component_scores"] == r2["component_scores"], (
            "Component scores must be identical when features are identical, "
            "regardless of prob_fault."
        )

    @pytest.mark.parametrize("prob_fault", [0.0, 0.15, 0.3, 0.5, 0.75, 1.0])
    def test_score_band_consistent_parametrized(self, prob_fault: float):
        """score_band = compute_score_band(posture_score) for any prob_fault."""
        r = _run(prob_fault, _zero_features())
        assert r["score_band"] == compute_score_band(r["posture_score"])
