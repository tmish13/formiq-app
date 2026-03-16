"""Tests for deterministic inference — same input → same output."""
import pytest


class TestInferenceDeterminism:
    def test_compute_posture_score_is_pure(self):
        """compute_posture_score(0.45) called 100x returns identical value."""
        from app.ml.posture_v1.scoring import compute_posture_score
        results = [compute_posture_score(0.45) for _ in range(100)]
        assert len(set(results)) == 1

    def test_compute_full_scores_identical_inputs_identical_output(self):
        """compute_full_scores() with same prob_fault → same dict keys."""
        from app.ml.posture_v1.scoring import compute_full_scores
        import numpy as np
        features = np.zeros(151, dtype=np.float32)
        r1 = compute_full_scores(0.4, features)
        r2 = compute_full_scores(0.4, features)
        assert r1["posture_score"] == r2["posture_score"]
        assert r1["decision"] == r2["decision"]

    def test_compute_full_scores_different_prob_different_model_score(self):
        """Different prob_fault → different model_score AND different posture_score.

        Zero features (all components=50).
        prob=0.1: model_score=90, blend=0.65*90+0.35*50=76. decision=good_form.
        prob=0.9: model_score=10, blend=0.65*10+0.35*50=24. decision=fault.
        posture_score now varies with prob_fault (model_score is 65% of the blend).
        """
        from app.ml.posture_v1.scoring import compute_full_scores
        import numpy as np
        features = np.zeros(151, dtype=np.float32)
        r_good = compute_full_scores(0.1, features)
        r_fault = compute_full_scores(0.9, features)
        # model_score differs (90 vs 10)
        assert r_good["model_score"] > r_fault["model_score"]
        # decision differs
        assert r_good["decision"] == "good_form"
        assert r_fault["decision"] == "fault"
        # posture_score now also differs — model_score is 65% of the blend
        assert r_good["posture_score"] > r_fault["posture_score"], (
            f"Good squat should score higher than fault: "
            f"{r_good['posture_score']} vs {r_fault['posture_score']}"
        )
        assert r_good["posture_score"] == 76
        assert r_fault["posture_score"] == 24

    def test_compute_posture_score_boundary_values(self):
        """Boundary values do not crash and stay in [0, 100]."""
        from app.ml.posture_v1.scoring import compute_posture_score
        for prob in [0.0, 0.5, 1.0]:
            s = compute_posture_score(prob)
            assert 0 <= s <= 100
