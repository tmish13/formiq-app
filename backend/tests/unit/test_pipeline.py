"""
Unit tests for:
  1) compute_score_band() — updated 90/75/60 thresholds
  2) run_squat_posture_pipeline() — structure, field types, uncertain path

These tests use inline replicas of the scoring logic to stay completely
independent of the heavy ML/Celery stack (no model files, no DB).
"""

import pytest
from unittest.mock import MagicMock, patch
import numpy as np


# ===========================================================================
# Part A — compute_score_band thresholds
# ===========================================================================

# Inline replica to test boundary math independent of import side-effects
def _compute_score_band(posture_score: int) -> str:
    """Inline replica of scoring.compute_score_band (thresholds 90/75/60)."""
    if posture_score >= 90:
        return "excellent"
    if posture_score >= 75:
        return "good"
    if posture_score >= 60:
        return "needs_work"
    return "poor"


class TestComputeScoreBand:
    """Verify the updated 90/75/60 score-band boundaries."""

    def test_excellent_lower_boundary(self):
        assert _compute_score_band(90) == "excellent"

    def test_excellent_top(self):
        assert _compute_score_band(100) == "excellent"

    def test_good_at_boundary(self):
        assert _compute_score_band(75) == "good"

    def test_good_mid(self):
        assert _compute_score_band(82) == "good"

    def test_good_just_below_excellent(self):
        assert _compute_score_band(89) == "good"

    def test_needs_work_at_boundary(self):
        assert _compute_score_band(60) == "needs_work"

    def test_needs_work_mid(self):
        assert _compute_score_band(67) == "needs_work"

    def test_needs_work_just_below_good(self):
        assert _compute_score_band(74) == "needs_work"

    def test_poor_at_boundary(self):
        assert _compute_score_band(59) == "poor"

    def test_poor_zero(self):
        assert _compute_score_band(0) == "poor"

    def test_poor_mid(self):
        assert _compute_score_band(30) == "poor"

    def test_imported_function_matches_replica(self):
        """The imported function must match the inline replica exactly."""
        from app.ml.posture_v1.scoring import compute_score_band
        for score in range(0, 101, 5):
            assert compute_score_band(score) == _compute_score_band(score), \
                f"Mismatch at score={score}"


# ===========================================================================
# Part B — compute_posture_score formula
# ===========================================================================

def _compute_posture_score(prob_fault: float) -> int:
    return int(round(max(0, min(100, 100 * (1.0 - prob_fault)))))


class TestComputePostureScore:
    def test_zero_fault(self):
        assert _compute_posture_score(0.0) == 100

    def test_full_fault(self):
        assert _compute_posture_score(1.0) == 0

    def test_half_fault(self):
        assert _compute_posture_score(0.5) == 50

    def test_good_form_boundary_prob(self):
        # prob_fault = 0.475 → 100 * 0.525 = 52.5 → rounds to 52 (banker's rounding)
        # With new 60-threshold: 52 < 60 → "poor"
        score = _compute_posture_score(0.475)
        assert score == 52
        assert _compute_score_band(score) == "poor"

    def test_excellent_requires_prob_le_010(self):
        # posture_score >= 90 requires prob_fault <= 0.10
        score = _compute_posture_score(0.10)
        assert score == 90
        assert _compute_score_band(score) == "excellent"

    def test_good_band_range(self):
        # good: 75-89 → prob_fault 0.11-0.25
        for prob in [0.11, 0.20, 0.24]:
            score = _compute_posture_score(prob)
            assert _compute_score_band(score) == "good", \
                f"Expected good for prob={prob}, got score={score} band={_compute_score_band(score)}"

    def test_imported_formula_matches_replica(self):
        from app.ml.posture_v1.scoring import compute_posture_score
        for prob in [0.0, 0.1, 0.25, 0.5, 0.75, 1.0]:
            assert compute_posture_score(prob) == _compute_posture_score(prob)


# ===========================================================================
# Part C — run_squat_posture_pipeline() structure tests
# (uses inline replica to avoid model file dependency)
# ===========================================================================

def _make_mock_loader(
    prob_fault: float = 0.3,
    decision: str = "good_form",
    quality_flags: list | None = None,
    features_151d=None,
) -> MagicMock:
    """Build a mock PostureV1TorchLoader that returns a controlled raw result."""
    loader = MagicMock()

    # Build raw result similar to what PostureV1TorchLoader.predict_posture() returns
    raw = {
        "prob_fault": prob_fault,
        "decision": decision,
        "confidence": round(abs(prob_fault - 0.5) * 2, 4),
        "threshold": 0.525,
        "quality_flags": quality_flags or [],
        "quality_ok": len(quality_flags or []) == 0,
        "model_version": "posture_v1",
        "feature_version": "151d_v1",
        "latency_ms": 40.0,
        "preprocessing": {"original_frames": 90, "valid_frames": 90, "sequence_length": 90},
        "_raw_features_151d": features_151d,
    }
    loader.predict_posture.return_value = raw
    # Scaler params — None means compute_full_scores uses raw features as z-scores
    loader.get_scaler_params.return_value = (None, None)
    return loader


class TestRunSquatPosturePipeline:
    """Tests for pipeline.run_squat_posture_pipeline() return structure."""

    def _run(self, **kwargs) -> dict:
        """Run pipeline with a mocked loader."""
        from app.ml.posture_v1.pipeline import run_squat_posture_pipeline
        loader = _make_mock_loader(**kwargs)
        return run_squat_posture_pipeline([], loader=loader)

    def test_returns_dict(self):
        result = self._run()
        assert isinstance(result, dict)

    def test_has_all_required_keys(self):
        result = self._run()
        for key in ("posture_score", "ai_confidence", "score_band", "components",
                    "feature_insights", "quality_flags", "decision"):
            assert key in result, f"Missing key: {key}"

    def test_components_has_all_sub_keys(self):
        result = self._run()
        for key in ("torso_stability", "knee_symmetry", "bottom_control", "forward_lean"):
            assert key in result["components"], f"Missing components.{key}"

    def test_uncertain_path_returns_none_scores(self):
        result = self._run(decision="uncertain", quality_flags=["short_video"])
        assert result["decision"] == "uncertain"
        assert result["posture_score"] is None
        assert result["ai_confidence"] is None
        assert result["score_band"] is None
        assert all(v is None for v in result["components"].values())
        assert result["feature_insights"] == []
        assert "short_video" in result["quality_flags"]

    def test_good_form_posture_score_positive(self):
        result = self._run(prob_fault=0.2, decision="good_form")
        assert result["decision"] == "good_form"
        assert result["posture_score"] is not None
        assert result["posture_score"] > 0

    def test_posture_score_is_int(self):
        result = self._run(prob_fault=0.3)
        assert isinstance(result["posture_score"], int)

    def test_ai_confidence_is_float_in_0_1(self):
        result = self._run(prob_fault=0.3)
        c = result["ai_confidence"]
        assert isinstance(c, float)
        assert 0.0 <= c <= 1.0

    def test_score_band_matches_posture_score(self):
        result = self._run(prob_fault=0.05)  # score ≈ 95 → excellent
        assert result["score_band"] == _compute_score_band(result["posture_score"])

    def test_fault_decision_at_high_prob(self):
        result = self._run(prob_fault=0.80, decision="fault")
        assert result["decision"] == "fault"
        assert result["posture_score"] == _compute_posture_score(0.80)
        assert result["score_band"] == "poor"

    def test_feature_insights_is_list_of_strings(self):
        result = self._run()
        assert isinstance(result["feature_insights"], list)
        for item in result["feature_insights"]:
            assert isinstance(item, str)

    def test_quality_flags_is_list(self):
        result = self._run(quality_flags=["truncated_10_frames"])
        assert isinstance(result["quality_flags"], list)
        assert "truncated_10_frames" in result["quality_flags"]

    def test_inference_error_returns_uncertain(self):
        """If predict_posture() raises, pipeline returns uncertain result."""
        from app.ml.posture_v1.pipeline import run_squat_posture_pipeline
        loader = MagicMock()
        loader.predict_posture.side_effect = RuntimeError("model not loaded")
        result = run_squat_posture_pipeline([], loader=loader)
        assert result["decision"] == "uncertain"
        assert result["posture_score"] is None
        assert "inference_error" in result["quality_flags"]

    def test_pipeline_score_band_uses_new_thresholds(self):
        """Verify score_band reflects 90/75/60 thresholds via pipeline."""
        # prob=0.15 → score=85 → good (not excellent — 85 < 90 in new thresholds)
        result = self._run(prob_fault=0.15, decision="good_form")
        assert result["posture_score"] == 85
        assert result["score_band"] == "good"  # was "excellent" in old (85) thresholds

        # prob=0.10 → score=90 → excellent
        result = self._run(prob_fault=0.10, decision="good_form")
        assert result["posture_score"] == 90
        assert result["score_band"] == "excellent"
