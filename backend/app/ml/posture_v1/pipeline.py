"""
PostureV1 squat posture pipeline — public API.

Wraps PostureV1TorchLoader + compute_full_scores into a single callable
that returns a canonical dict.  Use this function:

  1) In backend tasks (analysis_tasks.py) as the single source of truth.
  2) In tests to verify notebook ↔ backend parity.
  3) As a reference implementation for external callers.

Usage::

    from app.ml.posture_v1.pipeline import run_squat_posture_pipeline

    result = run_squat_posture_pipeline(pose_data)
    # result["posture_score"]    → int 0-100
    # result["ai_confidence"]    → float 0-1
    # result["score_band"]       → "excellent"|"good"|"needs_work"|"poor"|None
    # result["components"]       → {torso_stability, knee_symmetry,
    #                               bottom_control, forward_lean} each int|None
    # result["feature_insights"] → List[str] of top-signal feature names
    # result["quality_flags"]    → List[str] of gate/visibility flags
    # result["decision"]         → "good_form"|"fault"|"uncertain"
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Canonical uncertain result — returned whenever gates fire or inference fails.
_UNCERTAIN_RESULT: Dict[str, Any] = {
    "posture_score": None,
    "ai_confidence": None,
    "score_band": None,
    "components": {
        "torso_stability": None,
        "knee_symmetry": None,
        "bottom_control": None,
        "forward_lean": None,
    },
    "feature_insights": [],
    "quality_flags": [],
    "decision": "uncertain",
}


def run_squat_posture_pipeline(
    keypoints_sequence: List[Any],
    *,
    loader: Optional["PostureV1TorchLoader"] = None,
) -> Dict[str, Any]:
    """Run the full PostureV1 squat posture scoring pipeline.

    This is the single source of truth for squat posture scoring.  The
    notebook ``squat_pipeline_posture_stability_goodform_REBUILT.ipynb``
    should import and call this function rather than duplicating the logic.

    Args:
        keypoints_sequence: Raw pose_data in backend format —
            ``List[Optional[List[Optional[Dict[str, float]]]]]``
            (frames → landmarks → {x, y, z, visibility}).
        loader: Optional :class:`PostureV1TorchLoader` instance.  When
            ``None``, the module-level singleton from ``loader.py`` is used.

    Returns:
        Dict with keys:

        - ``posture_score``    (int 0-100, None if uncertain)
        - ``ai_confidence``    (float 0-1, None if uncertain)
        - ``score_band``       ("excellent"|"good"|"needs_work"|"poor"|None)
        - ``components``       (dict of four component scores, each int|None)
        - ``feature_insights`` (List[str] of top-signal feature names)
        - ``quality_flags``    (List[str] of gate/visibility issue codes)
        - ``decision``         ("good_form"|"fault"|"uncertain")
        - ``_raw``             (full internal result dict for debugging)
    """
    from app.ml.posture_v1.scoring import compute_full_scores

    # ------------------------------------------------------------------ #
    # Resolve loader — create a default instance when none provided
    # ------------------------------------------------------------------ #
    if loader is None:
        from app.ml.posture_v1.loader import PostureV1TorchLoader
        from app.core.config import get_settings
        loader = PostureV1TorchLoader(get_settings())

    # ------------------------------------------------------------------ #
    # Raw inference (preprocessing + gates + CNN-LSTM forward pass)
    # ------------------------------------------------------------------ #
    try:
        raw = loader.predict_posture(keypoints_sequence)
    except Exception as exc:
        logger.error("PostureV1 predict_posture failed: %s", exc, exc_info=True)
        result = dict(_UNCERTAIN_RESULT)
        result["quality_flags"] = ["inference_error"]
        return result

    decision = raw.get("decision", "uncertain")
    quality_flags: List[str] = raw.get("quality_flags") or []

    if decision == "uncertain":
        result = dict(_UNCERTAIN_RESULT)
        result["quality_flags"] = quality_flags
        result["_raw"] = raw
        return result

    # ------------------------------------------------------------------ #
    # Full scoring (component scores, top signals, score_band)
    # ------------------------------------------------------------------ #
    prob_fault: float = raw["prob_fault"]
    raw_features = raw.get("_raw_features_151d")
    component_visibility: Optional[Dict[str, Any]] = raw.get("_component_visibility") or None
    scaler_mean, scaler_std = loader.get_scaler_params()

    scoring = compute_full_scores(
        prob_fault=prob_fault,
        features_151d=raw_features,
        scaler_mean=scaler_mean,
        scaler_std=scaler_std,
        threshold=raw.get("threshold", 0.525),
        model_version=raw.get("model_version", "posture_v1"),
        component_visibility=component_visibility,
    )

    named = scoring.get("named_scores") or {}
    top_signals: List[Dict[str, Any]] = scoring.get("top_signals") or []

    # Attach any per-component visibility quality flags from the raw result
    try:
        from app.ml.posture_v1.visibility import get_visibility_quality_flags
        vis_flags = get_visibility_quality_flags(component_visibility or {})
    except Exception:
        vis_flags = []
    all_quality_flags = quality_flags + vis_flags

    return {
        "posture_score": scoring["posture_score"],
        "ai_confidence": scoring["confidence"],
        "score_band": scoring.get("score_band"),
        "components": {
            "torso_stability": named.get("torso_stability_score"),
            "knee_symmetry": named.get("knee_symmetry_score"),
            "bottom_control": named.get("bottom_control_score"),
            "forward_lean": named.get("forward_lean_score"),
        },
        "component_visibility": component_visibility,
        "feature_insights": [s["name"] for s in top_signals],
        "quality_flags": all_quality_flags,
        "decision": scoring["decision"],
        # Full internal result for advanced consumers (not stored in DB)
        "_raw": raw,
        "_scoring": scoring,
    }
