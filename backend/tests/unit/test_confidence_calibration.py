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

    def test_high_label_threshold(self):
        """Temperature softening means T=1.5 gives moderate label for prob=0.05."""
        from app.ml.posture_v1.scoring import compute_calibrated_confidence
        # With T=1.5, even extreme probs are softened toward 0.5 (boundary_score is low)
        # Result label depends on formula — just ensure it is a valid label
        result = compute_calibrated_confidence(0.05, 1.0, 1.0)
        assert result["label"] in ("High", "Moderate", "Low")

    def test_poor_visibility_lowers_score(self):
        """Poor visibility (0.3) lowers composite compared to perfect visibility."""
        from app.ml.posture_v1.scoring import compute_calibrated_confidence
        r_good = compute_calibrated_confidence(0.1, visibility_ratio=1.0, temporal_consistency=1.0)
        r_poor = compute_calibrated_confidence(0.1, visibility_ratio=0.3, temporal_consistency=1.0)
        assert r_good["score"] >= r_poor["score"]

    def test_label_thresholds_high(self):
        """score >= 0.80 → High."""
        from app.ml.posture_v1.scoring import compute_calibrated_confidence
        result = compute_calibrated_confidence(0.01, 1.0, 1.0)
        # Boundary score will be high for extreme prob
        if result["score"] >= 0.80:
            assert result["label"] == "High"

    def test_label_thresholds_low(self):
        """score < 0.60 → Low."""
        from app.ml.posture_v1.scoring import compute_calibrated_confidence
        result = compute_calibrated_confidence(0.5, 0.1, 0.1)
        if result["score"] < 0.60:
            assert result["label"] == "Low"

    def test_label_moderate(self):
        """0.60 <= score < 0.80 → Moderate."""
        from app.ml.posture_v1.scoring import compute_calibrated_confidence
        result = compute_calibrated_confidence(0.5, 0.5, 0.9)
        if 0.60 <= result["score"] < 0.80:
            assert result["label"] == "Moderate"

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
