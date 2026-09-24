"""Tests for confidence calibration functions."""
import pytest
import numpy as np


class TestApplyTemperature:
    def test_midpoint_unchanged(self):
        """prob=0.5 → T-scaled = 0.5 (symmetric)."""
        from app.ml.posture_v1.scoring import _apply_temperature
        result = _apply_temperature(0.5)
        assert abs(result - 0.5) < 1e-6

    def test_high_prob_softened(self):
        """prob=0.9, T=1.5 → result < 0.9 (softened toward midpoint)."""
        from app.ml.posture_v1.scoring import _apply_temperature
        result = _apply_temperature(0.9, T=1.5)
        assert result < 0.9

    def test_low_prob_softened(self):
        """prob=0.1, T=1.5 → result > 0.1 (softened toward midpoint)."""
        from app.ml.posture_v1.scoring import _apply_temperature
        result = _apply_temperature(0.1, T=1.5)
        assert result > 0.1

    def test_boundary_zero_no_crash(self):
        """prob=0.0 → no crash (clip prevents log(0))."""
        from app.ml.posture_v1.scoring import _apply_temperature
        result = _apply_temperature(0.0)
        assert 0.0 <= result <= 1.0

    def test_boundary_one_no_crash(self):
        """prob=1.0 → no crash (clip prevents log(0))."""
        from app.ml.posture_v1.scoring import _apply_temperature
        result = _apply_temperature(1.0)
        assert 0.0 <= result <= 1.0


class TestComputeCalibratedConfidence:
    def test_output_always_in_range(self):
        """Output score always in [0.0, 1.0]."""
        from app.ml.posture_v1.scoring import compute_calibrated_confidence
        for prob in [0.0, 0.1, 0.5, 0.9, 1.0]:
            result = compute_calibrated_confidence(prob)
            assert 0.0 <= result["score"] <= 1.0

    # G-50: fixed points instead of conditional asserts. The previous versions of
    # these tests were `if score >= 0.80: assert label == "High"` -- they could
    # not fail, and the formula was inverted underneath them for as long as they
    # existed.
    def test_coin_flip_is_low_confidence(self):
        """p = 0.5 with perfect visibility/consistency is LOW: the model has no opinion."""
        from app.ml.posture_v1.scoring import compute_calibrated_confidence
        result = compute_calibrated_confidence(0.5, 1.0, 1.0)
        assert result["label"] == "Low", result
        assert result["score"] < 0.60

    def test_decisive_predictions_are_high_confidence(self):
        """p = 0.02 and p = 0.98 are HIGH, and symmetric."""
        from app.ml.posture_v1.scoring import compute_calibrated_confidence
        lo = compute_calibrated_confidence(0.02, 1.0, 1.0)
        hi = compute_calibrated_confidence(0.98, 1.0, 1.0)
        assert lo["label"] == "High" and hi["label"] == "High", (lo, hi)
        assert abs(lo["score"] - hi["score"]) < 1e-6

    def test_confidence_increases_with_distance_from_the_boundary(self):
        """Monotonic in |p - 0.5|: farther from 0.5 => never lower confidence."""
        from app.ml.posture_v1.scoring import compute_calibrated_confidence
        scores = [compute_calibrated_confidence(p, 1.0, 1.0)["score"]
                  for p in (0.5, 0.6, 0.7, 0.8, 0.9, 0.99)]
        assert scores == sorted(scores), scores

    def test_poor_visibility_lowers_score(self):
        """Poor visibility (0.3) lowers composite compared to perfect visibility."""
        from app.ml.posture_v1.scoring import compute_calibrated_confidence
        r_good = compute_calibrated_confidence(0.1, visibility_ratio=1.0, temporal_consistency=1.0)
        r_poor = compute_calibrated_confidence(0.1, visibility_ratio=0.3, temporal_consistency=1.0)
        assert r_good["score"] > r_poor["score"]

    def test_label_bands(self):
        """score >= 0.80 High; 0.60 <= score < 0.80 Moderate; else Low -- at fixed inputs."""
        from app.ml.posture_v1.scoring import compute_calibrated_confidence
        assert compute_calibrated_confidence(0.98, 1.0, 1.0)["label"] == "High"
        assert compute_calibrated_confidence(0.5, 0.1, 0.1)["label"] == "Low"
        mid = compute_calibrated_confidence(0.98, 0.5, 0.5)   # 0.6*0.96ish + 0.125 + 0.075
        assert mid["label"] == "Moderate", mid

    def test_dict_structure(self):
        """Result has 'score' and 'label' keys."""
        from app.ml.posture_v1.scoring import compute_calibrated_confidence
        result = compute_calibrated_confidence(0.3, 0.8, 0.9)
        assert "score" in result
        assert "label" in result
        assert result["label"] in ("High", "Moderate", "Low")

    def test_score_is_float(self):
        """Score is a float."""
        from app.ml.posture_v1.scoring import compute_calibrated_confidence
        result = compute_calibrated_confidence(0.4)
        assert isinstance(result["score"], float)
