"""
Canonical squat scoring engine.

Computes the overall posture_score as a weighted average of the four named
component scores (torso_stability, knee_symmetry, bottom_control, forward_lean).

This replaces the old model_score ceiling formula, ensuring the overall score is
always derivable from — and coherent with — the component scores shown in the UI.
"""
from typing import Dict, List, Optional

COMPONENT_WEIGHTS: Dict[str, float] = {
    "torso_stability_score": 0.30,
    "knee_symmetry_score":   0.25,
    "bottom_control_score":  0.25,
    "forward_lean_score":    0.20,
}


def compute_weighted_overall(
    named_scores: Dict[str, Optional[int]],
    fallback_model_score: Optional[int] = None,
) -> Dict:
    """Weighted average of valid (non-None) named component scores.

    Renormalizes weights when components are excluded due to visibility gating.
    Falls back to fallback_model_score if ALL components are None.

    Args:
        named_scores: Dict mapping component name → score (0-100) or None.
            Expected keys: torso_stability_score, knee_symmetry_score,
            bottom_control_score, forward_lean_score.
        fallback_model_score: Score to use when all components are None.
            Typically the raw CNN-LSTM model score (100 * (1 - prob_fault)).

    Returns:
        Dict with:
            overall_score: int | None
            weights_used: Dict[str, float] — normalized weights for valid components
            score_exclusions: List[str] — components excluded (None values)
            valid_component_count: int
    """
    valid = {
        k: v
        for k, v in named_scores.items()
        if v is not None and k in COMPONENT_WEIGHTS
    }
    excluded: List[str] = [
        k for k in named_scores
        if named_scores[k] is None and k in COMPONENT_WEIGHTS
    ]

    if not valid:
        return {
            "overall_score": fallback_model_score,
            "weights_used": {},
            "score_exclusions": excluded,
            "valid_component_count": 0,
        }

    total_weight = sum(COMPONENT_WEIGHTS[k] for k in valid)
    normalized = {k: COMPONENT_WEIGHTS[k] / total_weight for k in valid}
    overall = round(sum(v * normalized[k] for k, v in valid.items()))

    return {
        "overall_score": int(overall),
        "weights_used": {k: round(w, 4) for k, w in normalized.items()},
        "score_exclusions": excluded,
        "valid_component_count": len(valid),
    }


def compute_projected_score(
    named_scores: Dict[str, Optional[int]],
    target_component_key: str,
    target_value: int = 75,
) -> Optional[int]:
    """Project overall score if target component improves to target_value.

    Uses the same weighted average engine. Returns None if the target component
    is currently None (cannot project from unknown baseline).

    Args:
        named_scores: Current component scores dict.
        target_component_key: The named_scores key for the component to improve
            (e.g. "knee_symmetry_score").
        target_value: The hypothetical improved value (default 75).

    Returns:
        Projected overall_score as int, or None if target component is None.
    """
    if named_scores.get(target_component_key) is None:
        return None
    improved = {
        **named_scores,
        target_component_key: max(named_scores[target_component_key], target_value),
    }
    result = compute_weighted_overall(improved)
    return result["overall_score"]
