"""
Unit tests for the squat_score_engine canonical weighted-average scorer.

8 tests covering:
  1. All 4 components present → weighted avg
  2. One component None → weights renormalize
  3. All components None → fallback to model_score
  4. Specific numeric example: torso=59, knee=48, bottom=55, lean=52
  5. compute_projected_score improves component and recomputes
  6. compute_projected_score when target component is None → None
  7. Excluded components listed in score_exclusions
  8. Monotonicity: improving any component never lowers overall
"""
from __future__ import annotations

import pytest

from app.services.scoring.squat_score_engine import (
    COMPONENT_WEIGHTS,
    compute_projected_score,
    compute_weighted_overall,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ALL_50 = {
    "torso_stability_score": 50,
    "knee_symmetry_score":   50,
    "bottom_control_score":  50,
    "forward_lean_score":    50,
}

_EXAMPLE = {
    "torso_stability_score": 59,
    "knee_symmetry_score":   48,
    "bottom_control_score":  55,
    "forward_lean_score":    52,
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestComputeWeightedOverall:

    def test_all_four_components_present(self):
        """All 4 valid → overall = exact weighted average."""
        result = compute_weighted_overall(_ALL_50)
        assert result["overall_score"] == 50
        assert result["valid_component_count"] == 4
        assert result["score_exclusions"] == []
        # Weights should sum to ~1.0
        assert abs(sum(result["weights_used"].values()) - 1.0) < 1e-6

    def test_one_component_none_renormalizes(self):
        """One None → remaining weights renormalize; overall still computed."""
        scores = {**_ALL_50, "knee_symmetry_score": None}
        result = compute_weighted_overall(scores)
        # 3 components at 50, renormalized → overall still 50
        assert result["overall_score"] == 50
        assert result["valid_component_count"] == 3
        assert "knee_symmetry_score" in result["score_exclusions"]
        assert "knee_symmetry_score" not in result["weights_used"]
        assert abs(sum(result["weights_used"].values()) - 1.0) < 1e-6

    def test_all_components_none_falls_back_to_model_score(self):
        """All None → overall_score == fallback_model_score."""
        scores = {k: None for k in COMPONENT_WEIGHTS}
        result = compute_weighted_overall(scores, fallback_model_score=35)
        assert result["overall_score"] == 35
        assert result["valid_component_count"] == 0
        assert result["weights_used"] == {}
        assert set(result["score_exclusions"]) == set(COMPONENT_WEIGHTS.keys())

    def test_specific_numeric_example(self):
        """torso=59, knee=48, bottom=55, lean=52 → expected weighted avg ≈ 54."""
        # Manual: 0.30*59 + 0.25*48 + 0.25*55 + 0.20*52
        #        = 17.7 + 12.0 + 13.75 + 10.4 = 53.85 → rounds to 54
        result = compute_weighted_overall(_EXAMPLE)
        assert result["overall_score"] == 54
        assert result["valid_component_count"] == 4

    def test_score_exclusions_lists_none_components(self):
        """score_exclusions contains exactly the None-valued component keys."""
        scores = {
            "torso_stability_score": 60,
            "knee_symmetry_score":   None,
            "bottom_control_score":  None,
            "forward_lean_score":    70,
        }
        result = compute_weighted_overall(scores)
        assert set(result["score_exclusions"]) == {
            "knee_symmetry_score",
            "bottom_control_score",
        }
        assert result["valid_component_count"] == 2

    def test_all_none_no_fallback_returns_none(self):
        """All None with no fallback → overall_score is None."""
        scores = {k: None for k in COMPONENT_WEIGHTS}
        result = compute_weighted_overall(scores)
        assert result["overall_score"] is None

    def test_monotonicity_improving_any_component(self):
        """Improving any component never lowers the overall score."""
        base = {
            "torso_stability_score": 40,
            "knee_symmetry_score":   50,
            "bottom_control_score":  60,
            "forward_lean_score":    55,
        }
        base_result = compute_weighted_overall(base)
        base_overall = base_result["overall_score"]

        for key in COMPONENT_WEIGHTS:
            improved = {**base, key: base[key] + 20}
            improved_result = compute_weighted_overall(improved)
            assert improved_result["overall_score"] >= base_overall, (
                f"Improving {key} from {base[key]} to {base[key]+20} lowered "
                f"overall from {base_overall} to {improved_result['overall_score']}"
            )


class TestComputeProjectedScore:

    def test_projects_improvement_correctly(self):
        """Improving knee_symmetry from 48→75 raises the projected overall."""
        current = compute_weighted_overall(_EXAMPLE)["overall_score"]
        projected = compute_projected_score(_EXAMPLE, "knee_symmetry_score", 75)
        assert projected is not None
        assert projected > current

    def test_target_already_above_target_value(self):
        """If current score ≥ target_value, projection = unchanged weighted avg."""
        scores = {**_EXAMPLE, "knee_symmetry_score": 80}
        projected = compute_projected_score(scores, "knee_symmetry_score", 75)
        # Knee stays at 80 (max(80, 75) = 80); result should equal the weighted avg
        direct = compute_weighted_overall(scores)["overall_score"]
        assert projected == direct

    def test_returns_none_when_target_component_is_none(self):
        """Cannot project when the target component is None."""
        scores = {**_EXAMPLE, "knee_symmetry_score": None}
        assert compute_projected_score(scores, "knee_symmetry_score") is None

    def test_projection_uses_correct_weights(self):
        """Projected score respects the canonical weights (0.25 for knee_symmetry)."""
        scores = {
            "torso_stability_score": 50,
            "knee_symmetry_score":   50,
            "bottom_control_score":  50,
            "forward_lean_score":    50,
        }
        # Improve knee from 50→75: expected weighted avg:
        # 0.30*50 + 0.25*75 + 0.25*50 + 0.20*50
        # = 15 + 18.75 + 12.5 + 10 = 56.25 → rounds to 56
        projected = compute_projected_score(scores, "knee_symmetry_score", 75)
        assert projected == 56
