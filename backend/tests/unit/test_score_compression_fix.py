"""Tests for score compression fix (model_score blended with component scores).

Verifies:
  - posture_score varies meaningfully with prob_fault even when component z-scores
    cluster near zero (the "~50 compression" root cause in production).
  - Good squat (low prob_fault) scores higher than bad squat (high prob_fault).
  - Score spread between clearly good/bad is ≥ 20 points.
  - Monotone: lower prob_fault → higher posture_score when components are neutral.
  - Blend weight constant is applied (not reverted to pure component average).
  - Fallback to model_score when all components are None.
"""
import numpy as np
import pytest

from app.ml.posture_v1.scoring import (
    compute_full_scores,
    _MODEL_BLEND_WEIGHT,
)
from app.ml.posture_v1.features_151d import EXPECTED_DIM


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _neutral_scaler_params(dim: int = EXPECTED_DIM):
    """All-constant scaler: mean=0.5, std=0.1.
    Features equal to mean → z=0 → all component scores = 50.
    """
    return (
        np.full(dim, 0.5, dtype=np.float32),  # mean
        np.full(dim, 0.1, dtype=np.float32),  # std
    )


def _neutral_features(scaler_mean: np.ndarray) -> np.ndarray:
    """Features equal to scaler_mean → z=0 → component scores = 50."""
    return scaler_mean.copy()


def _high_fault_features(scaler_mean: np.ndarray, scaler_std: np.ndarray) -> np.ndarray:
    """Features 2 std above mean → z=+2 → component scores = 0 (worst)."""
    return scaler_mean + 2.0 * scaler_std


def _low_fault_features(scaler_mean: np.ndarray, scaler_std: np.ndarray) -> np.ndarray:
    """Features 2 std below mean → z=-2 → component scores = 100 (best)."""
    return scaler_mean - 2.0 * scaler_std


# ---------------------------------------------------------------------------
# 1. Score separation (core regression test)
# ---------------------------------------------------------------------------

class TestScoreSeparation:
    """posture_score must vary with prob_fault even when components = 50."""

    def test_good_squat_scores_higher_than_bad(self):
        """prob_fault=0.25 (good form) must score higher than prob_fault=0.75 (bad)."""
        scaler_mean, scaler_std = _neutral_scaler_params()
        features = _neutral_features(scaler_mean)

        good = compute_full_scores(0.25, features, scaler_mean, scaler_std)
        bad  = compute_full_scores(0.75, features, scaler_mean, scaler_std)

        assert good["posture_score"] > bad["posture_score"], (
            f"Good squat (prob_fault=0.25) should score higher than bad (0.75): "
            f"{good['posture_score']} vs {bad['posture_score']}"
        )

    def test_score_spread_at_least_20_points(self):
        """Score difference between clearly good/bad ≥ 20 when components = 50."""
        scaler_mean, scaler_std = _neutral_scaler_params()
        features = _neutral_features(scaler_mean)

        good = compute_full_scores(0.20, features, scaler_mean, scaler_std)
        bad  = compute_full_scores(0.80, features, scaler_mean, scaler_std)

        spread = good["posture_score"] - bad["posture_score"]
        assert spread >= 20, (
            f"Score spread should be ≥ 20, got {spread} "
            f"(good={good['posture_score']}, bad={bad['posture_score']})"
        )

    def test_good_squat_scores_above_60(self):
        """Good form (prob_fault=0.25, neutral components) → posture_score ≥ 60."""
        scaler_mean, scaler_std = _neutral_scaler_params()
        features = _neutral_features(scaler_mean)

        result = compute_full_scores(0.25, features, scaler_mean, scaler_std)
        assert result["posture_score"] >= 60, (
            f"Good squat (prob_fault=0.25) should score ≥ 60, got {result['posture_score']}"
        )

    def test_bad_squat_scores_below_50(self):
        """Bad form (prob_fault=0.75, neutral components) → posture_score ≤ 50."""
        scaler_mean, scaler_std = _neutral_scaler_params()
        features = _neutral_features(scaler_mean)

        result = compute_full_scores(0.75, features, scaler_mean, scaler_std)
        assert result["posture_score"] <= 50, (
            f"Bad squat (prob_fault=0.75) should score ≤ 50, got {result['posture_score']}"
        )

    def test_near_boundary_prob_fault_scores_near_50(self):
        """prob_fault ≈ 0.5 should produce posture_score near 50."""
        scaler_mean, scaler_std = _neutral_scaler_params()
        features = _neutral_features(scaler_mean)

        result = compute_full_scores(0.50, features, scaler_mean, scaler_std)
        assert 42 <= result["posture_score"] <= 58, (
            f"prob_fault=0.5 with neutral components should score ~50, "
            f"got {result['posture_score']}"
        )


# ---------------------------------------------------------------------------
# 2. Blend formula correctness
# ---------------------------------------------------------------------------

class TestBlendFormula:
    """Verify the 65/35 blend is applied as documented."""

    def test_blend_constant_is_correct(self):
        """Module-level blend weight must be 0.65."""
        assert _MODEL_BLEND_WEIGHT == 0.65, (
            f"Expected _MODEL_BLEND_WEIGHT=0.65, got {_MODEL_BLEND_WEIGHT}"
        )

    def test_blend_applied_when_components_present(self):
        """When 4 valid components exist, posture_score = 0.65*model + 0.35*components."""
        scaler_mean, scaler_std = _neutral_scaler_params()
        features = _neutral_features(scaler_mean)  # all components = 50

        prob = 0.30  # model_score = 70
        result = compute_full_scores(prob, features, scaler_mean, scaler_std)

        model_score = int(round(100 * (1 - prob)))  # 70
        component_weighted = result["component_weighted_score"]  # should be ~50

        expected = int(round(0.65 * model_score + 0.35 * component_weighted))
        assert result["posture_score"] == expected, (
            f"Expected blend {expected} (0.65*{model_score} + 0.35*{component_weighted}), "
            f"got posture_score={result['posture_score']}"
        )

    def test_model_score_preserved_in_result(self):
        """model_score must always be present in result dict."""
        scaler_mean, scaler_std = _neutral_scaler_params()
        features = _neutral_features(scaler_mean)

        result = compute_full_scores(0.40, features, scaler_mean, scaler_std)
        assert "model_score" in result
        assert result["model_score"] == 60  # int(round(100 * 0.6))

    def test_component_weighted_score_preserved_in_result(self):
        """component_weighted_score must be present when features are valid."""
        scaler_mean, scaler_std = _neutral_scaler_params()
        features = _neutral_features(scaler_mean)

        result = compute_full_scores(0.40, features, scaler_mean, scaler_std)
        assert "component_weighted_score" in result
        assert result["component_weighted_score"] is not None

    def test_no_features_posture_score_equals_model_score(self):
        """When features_151d is None → posture_score == model_score."""
        prob = 0.30
        result = compute_full_scores(prob, features_151d=None)
        model_score = int(round(100 * (1 - prob)))
        assert result["posture_score"] == model_score, (
            f"No-features fallback should give model_score={model_score}, "
            f"got {result['posture_score']}"
        )


# ---------------------------------------------------------------------------
# 3. Monotone ordering
# ---------------------------------------------------------------------------

class TestMonotoneOrdering:
    """Lower prob_fault always → higher posture_score (when components neutral)."""

    @pytest.mark.parametrize("prob_fault", [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9])
    def test_score_in_range(self, prob_fault):
        """posture_score always in [0, 100]."""
        scaler_mean, scaler_std = _neutral_scaler_params()
        features = _neutral_features(scaler_mean)
        result = compute_full_scores(prob_fault, features, scaler_mean, scaler_std)
        assert 0 <= result["posture_score"] <= 100

    def test_monotone_across_prob_range(self):
        """Scores are non-increasing as prob_fault increases (neutral components)."""
        scaler_mean, scaler_std = _neutral_scaler_params()
        features = _neutral_features(scaler_mean)

        probs = [0.1, 0.3, 0.5, 0.7, 0.9]
        scores = [
            compute_full_scores(p, features, scaler_mean, scaler_std)["posture_score"]
            for p in probs
        ]
        for i in range(len(scores) - 1):
            assert scores[i] >= scores[i + 1], (
                f"Scores not monotone at prob={probs[i]}->{probs[i+1]}: "
                f"{scores[i]} -> {scores[i+1]}"
            )


# ---------------------------------------------------------------------------
# 4. Component severity still adjusts final score
# ---------------------------------------------------------------------------

class TestComponentSeverityEffect:
    """Components with strong z-scores pull posture_score away from model-only."""

    def test_severe_fault_components_lower_score(self):
        """High-fault features (z=+2 → components=0) reduce posture_score vs neutral."""
        scaler_mean, scaler_std = _neutral_scaler_params()
        neutral_features = _neutral_features(scaler_mean)
        fault_features   = _high_fault_features(scaler_mean, scaler_std)

        prob = 0.45  # near threshold
        neutral_result = compute_full_scores(prob, neutral_features, scaler_mean, scaler_std)
        fault_result   = compute_full_scores(prob, fault_features,   scaler_mean, scaler_std)

        assert fault_result["posture_score"] < neutral_result["posture_score"], (
            f"Severe fault features should lower posture_score: "
            f"fault={fault_result['posture_score']} vs neutral={neutral_result['posture_score']}"
        )

    def test_good_form_components_raise_score(self):
        """Low-fault features (z=-2 → components=100) raise posture_score vs neutral."""
        scaler_mean, scaler_std = _neutral_scaler_params()
        neutral_features = _neutral_features(scaler_mean)
        good_features    = _low_fault_features(scaler_mean, scaler_std)

        prob = 0.55  # slightly above threshold
        neutral_result = compute_full_scores(prob, neutral_features, scaler_mean, scaler_std)
        good_result    = compute_full_scores(prob, good_features,    scaler_mean, scaler_std)

        assert good_result["posture_score"] > neutral_result["posture_score"], (
            f"Good-form features should raise posture_score: "
            f"good={good_result['posture_score']} vs neutral={neutral_result['posture_score']}"
        )
