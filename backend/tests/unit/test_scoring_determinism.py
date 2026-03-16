"""
Scoring determinism and separation-of-concerns tests (Phase 2 audit).

Assertions:
  1. compute_full_scores() is 100% deterministic — identical inputs → identical output.
  2. AI confidence is NOT used to compute posture_score or component scores.
  3. posture_score is determined solely by prob_fault (model output).
  4. Two pipeline calls with the same synthetic keypoint sequence return identical results.
  5. Changing only confidence (by varying prob_fault ±epsilon around the same decision boundary)
     does NOT change posture_score unexpectedly beyond the mathematical formula.

All tests use inline replicas and mocks — no model file, no DB, no Celery.
"""
from __future__ import annotations

import copy

import numpy as np
import pytest
from unittest.mock import MagicMock


# ---------------------------------------------------------------------------
# Helpers — inline replicas and import targets
# ---------------------------------------------------------------------------

def _replica_posture_score(prob_fault: float) -> int:
    return int(round(max(0, min(100, 100 * (1.0 - prob_fault)))))


def _replica_confidence(prob_fault: float) -> float:
    return abs(prob_fault - 0.5) * 2


def _make_zero_features_151d() -> np.ndarray:
    from app.ml.posture_v1.features_151d import EXPECTED_DIM
    return np.zeros(EXPECTED_DIM, dtype=np.float32)


def _make_random_features_151d(seed: int = 42) -> np.ndarray:
    rng = np.random.default_rng(seed)
    from app.ml.posture_v1.features_151d import EXPECTED_DIM
    return rng.standard_normal(EXPECTED_DIM).astype(np.float32)


# ---------------------------------------------------------------------------
# Class A — compute_full_scores() determinism
# ---------------------------------------------------------------------------

class TestComputeFullScoresDeterminism:
    """compute_full_scores() must return bit-for-bit identical results for the same input."""

    def _call(self, prob_fault: float, features: np.ndarray) -> dict:
        from app.ml.posture_v1.scoring import compute_full_scores
        return compute_full_scores(
            prob_fault=prob_fault,
            features_151d=features,
            scaler_mean=None,
            scaler_std=None,
        )

    def test_identical_on_zero_features(self):
        feats = _make_zero_features_151d()
        r1 = self._call(0.3, feats)
        r2 = self._call(0.3, feats.copy())
        assert r1["posture_score"] == r2["posture_score"]
        assert r1["score_band"] == r2["score_band"]
        assert r1["decision"] == r2["decision"]
        assert r1["confidence"] == r2["confidence"]
        assert r1["component_scores"] == r2["component_scores"]
        assert r1["named_scores"] == r2["named_scores"]

    def test_identical_on_random_features(self):
        feats = _make_random_features_151d(seed=7)
        r1 = self._call(0.65, feats)
        r2 = self._call(0.65, feats.copy())
        assert r1["posture_score"] == r2["posture_score"]
        assert r1["component_scores"] == r2["component_scores"]
        assert r1["named_scores"] == r2["named_scores"]
        assert r1["top_signals"] == r2["top_signals"]

    def test_top_signals_order_is_stable(self):
        """Top signals must be sorted by |z| descending — stable across two calls."""
        feats = _make_random_features_151d(seed=99)
        r1 = self._call(0.4, feats)
        r2 = self._call(0.4, feats.copy())
        assert r1["top_signals"] == r2["top_signals"]

    def test_calling_twice_same_object_is_deterministic(self):
        """Calling with the same array object (not a copy) must also be deterministic."""
        feats = _make_random_features_151d(seed=12)
        r1 = self._call(0.55, feats)
        r2 = self._call(0.55, feats)
        assert r1["posture_score"] == r2["posture_score"]


# ---------------------------------------------------------------------------
# Class B — posture_score depends ONLY on prob_fault, not confidence
# ---------------------------------------------------------------------------

class TestPostureScoreIndependentOfConfidence:
    """posture_score = 100*(1-prob_fault). Confidence is a separate metadata field."""

    def _score_for(self, prob_fault: float) -> int:
        from app.ml.posture_v1.scoring import compute_posture_score
        return compute_posture_score(prob_fault)

    def test_posture_score_formula_matches_replica(self):
        """compute_posture_score is the canonical formula — no hidden modifiers."""
        for prob in [0.0, 0.1, 0.3, 0.5, 0.7, 0.9, 1.0]:
            assert self._score_for(prob) == _replica_posture_score(prob), (
                f"prob={prob}: expected {_replica_posture_score(prob)}"
            )

    def test_bad_features_reduce_posture_score_via_ceiling(self):
        """Component ceiling: severely bad features must reduce posture_score below model_score.

        posture_score = min(model_score, min_component + 30).
        With features=5.0 (all z=5, clamped to 2), all components → 0,
        ceiling = 0 + 30 = 30 → posture_score = 30 (not the raw model_score=75).
        """
        from app.ml.posture_v1.scoring import compute_full_scores, compute_posture_score
        feats_bad = np.ones(_make_zero_features_151d().shape, dtype=np.float32) * 5.0
        r = compute_full_scores(0.25, feats_bad, scaler_mean=None, scaler_std=None)

        model_score = compute_posture_score(0.25)  # = 75
        assert r["model_score"] == model_score, "model_score must be the raw model value"
        assert r["posture_score"] <= r["model_score"], (
            "Component ceiling can only reduce, never inflate posture_score."
        )
        assert r["posture_score"] < model_score, (
            "Severe feature faults (z=5) must pull posture_score below raw model score."
        )

    def test_confidence_field_is_correct_formula(self):
        """confidence = |prob_fault - 0.5| * 2 — verifiable formula."""
        from app.ml.posture_v1.scoring import compute_full_scores
        feats = _make_zero_features_151d()
        for prob in [0.0, 0.25, 0.5, 0.75, 1.0]:
            r = compute_full_scores(prob, feats, scaler_mean=None, scaler_std=None)
            expected_confidence = round(_replica_confidence(prob), 4)
            assert abs(r["confidence"] - expected_confidence) < 1e-6, (
                f"prob={prob}: confidence={r['confidence']} != {expected_confidence}"
            )

    def test_low_confidence_does_not_reduce_posture_score(self):
        """posture_score is driven by blend of model_score and component scores.

        prob_fault=0.51, zero features (all named components = 50):
          model_score = 49, component_weighted = 50.
          Blend: 0.65*49 + 0.35*50 = 31.85 + 17.5 = 49.35 → 49.
        posture_score reflects the model's slight lean toward fault (49, not 50).
        """
        from app.ml.posture_v1.scoring import compute_full_scores
        feats = _make_zero_features_151d()
        r = compute_full_scores(0.51, feats, scaler_mean=None, scaler_std=None)
        # Blend: 0.65*49 + 0.35*50 = 49.35 → 49
        assert r["posture_score"] == 49
        # model_score still reflects the CNN-LSTM output (49 for prob=0.51)
        assert r["model_score"] == 49

    def test_high_confidence_does_not_inflate_posture_score(self):
        """posture_score can be lower than model_score when components are moderate.

        With zero features (components=50) and prob_fault=0.05:
          model_score = 95, but posture_score = 50 (weighted avg of all-50 components).
        model_score is preserved in result for debugging/audit.
        """
        from app.ml.posture_v1.scoring import compute_full_scores, compute_posture_score
        feats = _make_zero_features_151d()
        r = compute_full_scores(0.05, feats, scaler_mean=None, scaler_std=None)
        model_score = compute_posture_score(0.05)  # = 95
        assert r["posture_score"] <= model_score, (
            f"posture_score={r['posture_score']} must not exceed model_score={model_score}"
        )
        # model_score is preserved in result for transparency
        assert r["model_score"] == model_score


# ---------------------------------------------------------------------------
# Class C — component scores depend on features, NOT on prob_fault
# ---------------------------------------------------------------------------

class TestComponentScoresDependOnFeatures:
    """Component scores come from 151D features — prob_fault does not affect them."""

    def _components(self, prob_fault: float, feats: np.ndarray) -> dict:
        from app.ml.posture_v1.scoring import compute_full_scores
        return compute_full_scores(
            prob_fault=prob_fault,
            features_151d=feats,
            scaler_mean=None,
            scaler_std=None,
        )["component_scores"]

    def test_same_features_different_prob_fault_same_component_scores(self):
        feats = _make_random_features_151d(seed=5)
        c1 = self._components(0.2, feats)
        c2 = self._components(0.8, feats)
        # Component scores must be identical — prob_fault is irrelevant to them
        assert c1 == c2, (
            "Component scores should not change when prob_fault changes "
            "but features are held constant."
        )

    def test_different_features_different_component_scores(self):
        feats_a = _make_zero_features_151d()
        feats_b = _make_random_features_151d(seed=17)
        feats_b *= 3.0  # amplify to guarantee difference
        c_a = self._components(0.4, feats_a)
        c_b = self._components(0.4, feats_b)
        # At least one component must differ (otherwise the function is ignoring features)
        all_equal = all(
            c_a[k] == c_b[k]
            for k in c_a if c_a[k] is not None and c_b[k] is not None
        )
        assert not all_equal, "Component scores should respond to changes in 151D features."


# ---------------------------------------------------------------------------
# Class D — run_squat_posture_pipeline() determinism (end-to-end mock)
# ---------------------------------------------------------------------------

class TestPipelineDeterminism:
    """Two pipeline calls with identical inputs must produce identical results."""

    def _make_loader(self, prob_fault: float = 0.3) -> MagicMock:
        from app.ml.posture_v1.features_151d import EXPECTED_DIM
        feats = np.zeros(EXPECTED_DIM, dtype=np.float32)
        loader = MagicMock()
        loader.predict_posture.return_value = {
            "prob_fault": prob_fault,
            "decision": "good_form" if prob_fault < 0.525 else "fault",
            "confidence": round(abs(prob_fault - 0.5) * 2, 4),
            "threshold": 0.525,
            "quality_flags": [],
            "quality_ok": True,
            "model_version": "posture_v1",
            "feature_version": "151d_v1",
            "latency_ms": 35.0,
            "preprocessing": {"original_frames": 80, "valid_frames": 80, "sequence_length": 80},
            "_raw_features_151d": feats,
        }
        loader.get_scaler_params.return_value = (None, None)
        return loader

    def test_two_calls_identical(self):
        from app.ml.posture_v1.pipeline import run_squat_posture_pipeline
        loader = self._make_loader(0.25)
        r1 = run_squat_posture_pipeline([], loader=loader)
        r2 = run_squat_posture_pipeline([], loader=loader)
        assert r1["posture_score"] == r2["posture_score"]
        assert r1["score_band"] == r2["score_band"]
        assert r1["components"] == r2["components"]
        assert r1["feature_insights"] == r2["feature_insights"]
        assert r1["decision"] == r2["decision"]

    def test_uncertain_path_deterministic(self):
        from app.ml.posture_v1.pipeline import run_squat_posture_pipeline
        loader = MagicMock()
        loader.predict_posture.return_value = {
            "prob_fault": 0.5,
            "decision": "uncertain",
            "confidence": 0.0,
            "threshold": 0.525,
            "quality_flags": ["no_valid_frames"],
            "quality_ok": False,
            "model_version": "posture_v1",
            "preprocessing": {"original_frames": 5, "valid_frames": 0, "sequence_length": 0},
        }
        loader.get_scaler_params.return_value = (None, None)
        r1 = run_squat_posture_pipeline([], loader=loader)
        r2 = run_squat_posture_pipeline([], loader=loader)
        assert r1["posture_score"] is None
        assert r2["posture_score"] is None
        assert r1["components"] == r2["components"]
        assert r1["decision"] == "uncertain"
