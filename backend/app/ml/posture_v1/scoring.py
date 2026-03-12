"""
PostureV1 scoring module.

Computes:
  1) posture_score (0–100) from prob_fault
  2) Component scores (trunk_control, knee_stability, hip_drive) from 151D features
  3) Top signals (up to 5) from z-score magnitudes

All scores derived from real features — no hardcoded mock values.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from app.ml.posture_v1.features_151d import FEATURE_NAMES, EXPECTED_DIM

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Feature subsets for component scores
# ---------------------------------------------------------------------------

# Each value: list of (feature_name, direction)
# direction: "high_is_bad" means higher z → worse score
#            "high_is_good" would invert (not used here — all our metrics are bad-when-high)

_TRUNK_CONTROL_FEATURES: List[Tuple[str, str]] = [
    # trunk_forward_lean is intentionally EXCLUDED here — it belongs solely to
    # forward_lean_score (computed separately via _compute_single_feature_score).
    # This ensures each feature contributes to exactly ONE named component.
    ("bottom_trunk_wobble", "high_is_bad"),
    ("trunk_angle_std", "high_is_bad"),
    ("trunk_angle_descent_std", "high_is_bad"),
    ("trunk_angle_bottom_std", "high_is_bad"),
    ("trunk_angle_ascent_std", "high_is_bad"),
]

_KNEE_STABILITY_FEATURES: List[Tuple[str, str]] = [
    ("knee_asymmetry_mean", "high_is_bad"),
    ("bottom_knee_asymmetry", "high_is_bad"),
    ("left_knee_angle_std", "high_is_bad"),
    ("right_knee_angle_std", "high_is_bad"),
    ("left_knee_angle_bottom_std", "high_is_bad"),
    ("right_knee_angle_bottom_std", "high_is_bad"),
]

_HIP_DRIVE_FEATURES: List[Tuple[str, str]] = [
    ("left_hip_angle_std", "high_is_bad"),
    ("left_hip_angle_descent_std", "high_is_bad"),
    ("left_hip_angle_bottom_std", "high_is_bad"),
    ("left_hip_angle_ascent_std", "high_is_bad"),
]

# Whitelist for top signals
_SIGNAL_WHITELIST: List[Tuple[str, str, str]] = [
    # (feature_name, direction, short_message_template)
    ("bottom_trunk_wobble", "high_is_bad", "Trunk instability at bottom position"),
    ("trunk_forward_lean", "high_is_bad", "Excessive forward lean"),
    ("knee_asymmetry_mean", "high_is_bad", "Knee tracking asymmetry"),
    ("bottom_knee_asymmetry", "high_is_bad", "Knee asymmetry at bottom position"),
    ("trunk_angle_std", "high_is_bad", "Trunk angle inconsistency"),
    ("left_knee_angle_std", "high_is_bad", "Left knee angle variability"),
    ("right_knee_angle_std", "high_is_bad", "Right knee angle variability"),
    ("left_hip_angle_std", "high_is_bad", "Hip drive inconsistency"),
    ("trunk_angle_bottom_std", "high_is_bad", "Trunk instability at bottom"),
    ("left_knee_angle_bottom_std", "high_is_bad", "Left knee instability at bottom"),
    ("right_knee_angle_bottom_std", "high_is_bad", "Right knee instability at bottom"),
]

# Pre-build feature name → index lookup
_NAME_TO_IDX: Dict[str, int] = {name: i for i, name in enumerate(FEATURE_NAMES)}


# ---------------------------------------------------------------------------
# Component ceiling — structural alignment
# ---------------------------------------------------------------------------
#
# posture_score = min(model_score, min_component + CEILING_MARGIN)
#
# This prevents the global model probability from inflating the final score
# when feature-level analysis reveals a severely broken component.
#
# CEILING_MARGIN derivation (from hard constraints):
#   posture_score ≤ 80  when any component < 50  →  50 + 30 = 80  ✓
#   posture_score ≤ 70  when any component < 40  →  40 + 30 = 70  ✓
#
# The formula is monotonically increasing in both model_score and min_component:
# improving any dimension can only raise (never lower) the final score.

_CEILING_MARGIN: int = 30

# None components (from the visibility gate) are treated as this value in the
# ceiling calculation. 50 = training mean (z=0 → score=50). Using the neutral
# value prevents None from both inflating the score (unconstrained) and
# unfairly penalising a squat just because a body region was occluded.
_MISSING_COMPONENT_DEFAULT: int = 50

# ---------------------------------------------------------------------------
# Confidence calibration
# ---------------------------------------------------------------------------

_TEMPERATURE = 1.5  # Softens overconfident predictions; T>1 widens boundary


def _apply_temperature(prob: float, T: float = _TEMPERATURE) -> float:
    """Temperature-scale prob_fault via logit space. T>1 softens predictions."""
    logit = np.log(np.clip(prob, 1e-7, 1 - 1e-7) / (1 - np.clip(prob, 1e-7, 1 - 1e-7)))
    return float(1 / (1 + np.exp(-logit / T)))


def compute_calibrated_confidence(
    prob_fault: float,
    visibility_ratio: float = 1.0,
    temporal_consistency: float = 1.0,
) -> Dict[str, Any]:
    """Composite calibrated confidence (clamped to [0, 1]).

    composite = 0.6 * boundary_score + 0.25 * visibility_ratio + 0.15 * temporal_consistency
    boundary_score = 1 - 2 * |calibrated_prob - 0.5|  (distance from uncertain)
    """
    calibrated_prob = _apply_temperature(prob_fault)
    boundary_score = 1.0 - 2.0 * abs(calibrated_prob - 0.5)
    composite = round(
        0.6 * boundary_score + 0.25 * visibility_ratio + 0.15 * temporal_consistency,
        4,
    )
    composite = float(np.clip(composite, 0.0, 1.0))
    if composite >= 0.80:
        label = "High"
    elif composite >= 0.60:
        label = "Moderate"
    else:
        label = "Low"
    return {"score": composite, "label": label}


# ---------------------------------------------------------------------------
# Level system
# ---------------------------------------------------------------------------

# (low_inclusive, high_exclusive, name, next_threshold)
_LEVELS = [
    (92, 101, "Elite",      None),
    (85, 92,  "Advanced",   92),
    (75, 85,  "Solid",      85),
    (60, 75,  "Developing", 75),
    (0,  60,  "Beginner",   60),
]


def compute_level(posture_score: Optional[float]) -> Dict[str, Any]:
    """Map posture_score to tier and compute percent_to_next_level."""
    if posture_score is None:
        return {"current_level": None, "percent_to_next_level": None}
    for low, high, name, next_threshold in _LEVELS:
        if posture_score >= low:
            if next_threshold is None:
                pct = 100.0
            else:
                band = next_threshold - low
                pct = round(min(100.0, (posture_score - low) / band * 100.0), 1)
            return {"current_level": name, "percent_to_next_level": pct}
    return {"current_level": "Beginner", "percent_to_next_level": round(posture_score / 60.0 * 100, 1)}


# ---------------------------------------------------------------------------
# Core scoring functions
# ---------------------------------------------------------------------------

def compute_posture_score(prob_fault: float) -> int:
    """Map prob_fault to 0–100 raw model score.  Higher = better.

    This is the CNN-LSTM model's global temporal assessment.  The final
    ``posture_score`` returned by ``compute_full_scores()`` may be lower
    after the component ceiling is applied.
    """
    return int(round(max(0, min(100, 100 * (1.0 - prob_fault)))))


def compute_score_band(posture_score: int) -> str:
    """Map 0-100 posture score to qualitative band.

    Thresholds (must stay in sync with frontend getScoreBand()):
        90–100 → "excellent"
        75–89  → "good"
        60–74  → "needs_work"
        0–59   → "poor"
    """
    if posture_score >= 90:
        return "excellent"
    if posture_score >= 75:
        return "good"
    if posture_score >= 60:
        return "needs_work"
    return "poor"


def _apply_component_ceiling(
    model_score: int,
    component_scores: Dict[str, Any],
) -> int:
    """Apply a smooth linear ceiling to the model score based on the weakest component.

    Formula::

        effective_min = min(component if not None else MISSING_COMPONENT_DEFAULT)
        ceiling       = effective_min + CEILING_MARGIN
        posture_score = min(model_score, ceiling)

    Rationale:
        The global model probability (prob_fault) captures temporal sequence
        dynamics that engineered features cannot fully represent.  However,
        the feature-level components can detect specific severe biomechanical
        faults the model may underweight (e.g. knee asymmetry not separable
        from a single CNN-LSTM logit).

        This ceiling enforces: a squat cannot be rated "solid overall" when
        a core biomechanical component is severely broken.  The final score
        is the pessimistic intersection of both sources of evidence.

    Properties:
        - Monotonic: increasing any component can only raise or maintain the
          ceiling — it never lowers posture_score.
        - Conservative for None: missing (visibility-gated) components are
          treated as 50 (training mean), preventing both inflation and
          unfair penalisation.
        - Cannot inflate: posture_score ≤ model_score always.

    Args:
        model_score: Raw score from compute_posture_score(prob_fault), 0–100.
        component_scores: Dict {component_name: int|None} from
            compute_component_scores().  Empty dict → model_score returned.

    Returns:
        Adjusted posture_score ≤ model_score, in [0, 100].
    """
    if not component_scores:
        return model_score

    effective_min = min(
        v if v is not None else _MISSING_COMPONENT_DEFAULT
        for v in component_scores.values()
    )
    ceiling = effective_min + _CEILING_MARGIN
    return int(min(model_score, ceiling))


def _z_to_score(z: float, direction: str = "high_is_bad") -> float:
    """Convert a standardized z-score to 0–100 using monotonic clamped mapping.

    For "high_is_bad":
        z = -2 → score = 100 (very good)
        z =  0 → score =  50
        z = +2 → score =   0 (very bad)
    """
    z_clamped = max(-2.0, min(2.0, z))
    if direction == "high_is_bad":
        return 100.0 * (1.0 - (z_clamped + 2.0) / 4.0)
    else:
        # high_is_good (not used currently, but for completeness)
        return 100.0 * ((z_clamped + 2.0) / 4.0)


def compute_component_scores(
    features_151d: np.ndarray,
    scaler_mean: Optional[np.ndarray] = None,
    scaler_std: Optional[np.ndarray] = None,
    component_visibility: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """Compute trunk_control, knee_stability, hip_drive from 151D features.

    Args:
        features_151d: raw (un-scaled) 151D feature vector.
        scaler_mean: per-feature means from the training scaler.
        scaler_std: per-feature stds from the training scaler.
        component_visibility: optional dict {component_name: mean_visibility}
            from visibility.compute_component_visibility(). When provided,
            components whose joints are below the VISIBILITY_PARTIAL threshold
            (0.4) are set to None to avoid reporting unreliable scores.

    Returns:
        Dict with component score values (0–100 or None).
        None means either features are missing or visibility is unreliable.
    """
    if features_151d is None or len(features_151d) != EXPECTED_DIM:
        return {"trunk_control": None, "knee_stability": None, "hip_drive": None}

    # Import threshold lazily to avoid circular dependency
    try:
        from app.ml.posture_v1.visibility import VISIBILITY_PARTIAL as _VIS_PARTIAL
    except ImportError:
        _VIS_PARTIAL = 0.4

    # Compute z-scores
    if scaler_mean is not None and scaler_std is not None:
        safe_std = np.where(scaler_std < 1e-8, 1.0, scaler_std)
        z_scores = (features_151d - scaler_mean) / safe_std
    else:
        # Without scaler, use raw features (less accurate but functional)
        z_scores = features_151d

    results: Dict[str, Any] = {}

    for component_name, feature_defs in [
        ("trunk_control", _TRUNK_CONTROL_FEATURES),
        ("knee_stability", _KNEE_STABILITY_FEATURES),
        ("hip_drive", _HIP_DRIVE_FEATURES),
    ]:
        scores = []
        for feat_name, direction in feature_defs:
            idx = _NAME_TO_IDX.get(feat_name)
            if idx is not None:
                scores.append(_z_to_score(float(z_scores[idx]), direction))

        if scores:
            computed = int(round(np.mean(scores)))
        else:
            computed = None

        # Visibility gate: null out component if joints are unreliable
        if (
            computed is not None
            and component_visibility is not None
            and component_visibility.get(component_name, 1.0) < _VIS_PARTIAL
        ):
            results[component_name] = None
            logger.debug(
                "Component '%s' set to None: visibility=%.2f < %.2f threshold",
                component_name,
                component_visibility.get(component_name, 0.0),
                _VIS_PARTIAL,
            )
        else:
            results[component_name] = computed

    return results


def compute_top_signals(
    features_151d: np.ndarray,
    scaler_mean: Optional[np.ndarray] = None,
    scaler_std: Optional[np.ndarray] = None,
    max_signals: int = 5,
) -> List[Dict[str, Any]]:
    """Return top signals sorted by absolute z-score magnitude.

    Each signal: {name, value, z, direction, message_short}.
    """
    if features_151d is None or len(features_151d) != EXPECTED_DIM:
        return []

    if scaler_mean is not None and scaler_std is not None:
        safe_std = np.where(scaler_std < 1e-8, 1.0, scaler_std)
        z_scores = (features_151d - scaler_mean) / safe_std
    else:
        z_scores = features_151d

    candidates = []
    for feat_name, direction, message in _SIGNAL_WHITELIST:
        idx = _NAME_TO_IDX.get(feat_name)
        if idx is None:
            continue
        z = float(z_scores[idx])
        abs_z = abs(z)
        # Only report signals where the feature is "bad" (positive z for high_is_bad)
        if direction == "high_is_bad" and z > 0.3:
            candidates.append({
                "name": feat_name,
                "value": round(float(features_151d[idx]), 4),
                "z": round(z, 3),
                "direction": direction,
                "message_short": message,
            })

    # Sort by z magnitude descending
    candidates.sort(key=lambda s: abs(s["z"]), reverse=True)
    return candidates[:max_signals]


def _compute_single_feature_score(
    feat_name: str,
    features_151d: np.ndarray,
    scaler_mean: Optional[np.ndarray],
    scaler_std: Optional[np.ndarray],
) -> Optional[int]:
    """Compute a 0-100 score from a single named feature's z-score."""
    idx = _NAME_TO_IDX.get(feat_name)
    if idx is None:
        return None
    if scaler_mean is not None and scaler_std is not None:
        safe_std = scaler_std[idx] if scaler_std[idx] > 1e-8 else 1.0
        z = (float(features_151d[idx]) - float(scaler_mean[idx])) / safe_std
    else:
        z = float(features_151d[idx])
    return int(round(_z_to_score(z, "high_is_bad")))


def compute_named_scores(
    features_151d: np.ndarray,
    scaler_mean: Optional[np.ndarray] = None,
    scaler_std: Optional[np.ndarray] = None,
    component_scores: Optional[Dict[str, Any]] = None,
) -> Dict[str, Optional[int]]:
    """Map internal component scores to user-facing named scores.

    Returns dict with keys: torso_stability_score, knee_symmetry_score,
    bottom_control_score, forward_lean_score.
    """
    cs = component_scores or {}
    return {
        "torso_stability_score": cs.get("trunk_control"),
        "knee_symmetry_score": cs.get("knee_stability"),
        "bottom_control_score": cs.get("hip_drive"),
        "forward_lean_score": _compute_single_feature_score(
            "trunk_forward_lean", features_151d, scaler_mean, scaler_std,
        ),
    }


# ---------------------------------------------------------------------------
# Public API: full scoring pipeline
# ---------------------------------------------------------------------------

def compute_full_scores(
    prob_fault: float,
    features_151d: Optional[np.ndarray],
    scaler_mean: Optional[np.ndarray] = None,
    scaler_std: Optional[np.ndarray] = None,
    threshold: float = 0.525,
    model_version: str = "posture_v1",
    component_visibility: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """Compute all scores for a squat analysis.

    ``posture_score`` is the weighted average of the four named component scores
    (torso_stability, knee_symmetry, bottom_control, forward_lean).  This
    ensures the overall score is always coherent with the per-component values
    shown in the UI — no more "overall=35 while all components show 48-59".

    When components are None (visibility-gated), their weights are renormalized
    across the remaining valid components.  If ALL four are None, the raw
    ``model_score`` (100 * (1 - prob_fault)) is used as a fallback.

    The ``model_score`` is still preserved in the result dict for debugging and
    audit purposes.  ``_apply_component_ceiling()`` is kept intact for tests
    but is no longer used to compute ``posture_score``.

    Returns a dict suitable for storing in FormCheck.results["posture_v1"].
    """
    from app.services.scoring.squat_score_engine import compute_weighted_overall

    # Step 1 — Model-derived score (global temporal assessment via CNN-LSTM)
    model_score = compute_posture_score(prob_fault)
    decision = "fault" if prob_fault >= threshold else "good_form"
    confidence = round(abs(prob_fault - 0.5) * 2, 4)

    result: Dict[str, Any] = {
        "decision": decision,
        "confidence": confidence,
        "prob_fault": round(prob_fault, 6),
        "threshold": threshold,
        # Raw model-derived score — kept for debugging/audit; no longer drives
        # posture_score directly (weighted component average does now).
        "model_score": model_score,
    }

    # Step 2 — Component scores from engineered 151D features
    if features_151d is not None and len(features_151d) == EXPECTED_DIM:
        component_scores = compute_component_scores(
            features_151d, scaler_mean, scaler_std,
            component_visibility=component_visibility,
        )
        result["component_scores"] = component_scores
        result["top_signals"] = compute_top_signals(
            features_151d, scaler_mean, scaler_std
        )
        named_scores = compute_named_scores(
            features_151d, scaler_mean, scaler_std,
            component_scores=component_scores,
        )
        result["named_scores"] = named_scores
        if component_visibility is not None:
            result["component_visibility"] = component_visibility

        # Step 3 — Weighted average of named component scores.
        # When components are excluded (None), weights renormalize automatically.
        # Falls back to model_score only when every component is None.
        engine_result = compute_weighted_overall(
            named_scores, fallback_model_score=model_score
        )
        posture_score = engine_result["overall_score"]
        result["weights_used"] = engine_result["weights_used"]
        result["score_exclusions"] = engine_result["score_exclusions"]
        result["valid_component_count"] = engine_result["valid_component_count"]
    else:
        result["component_scores"] = {
            "trunk_control": None,
            "knee_stability": None,
            "hip_drive": None,
        }
        result["top_signals"] = []
        result["named_scores"] = {
            "torso_stability_score": None,
            "knee_symmetry_score": None,
            "bottom_control_score": None,
            "forward_lean_score": None,
        }
        result["weights_used"] = {}
        result["score_exclusions"] = [
            "torso_stability_score",
            "knee_symmetry_score",
            "bottom_control_score",
            "forward_lean_score",
        ]
        result["valid_component_count"] = 0
        # No component data available — use model score directly.
        posture_score = model_score

    result["posture_score"] = posture_score
    result["score_band"] = compute_score_band(posture_score)
    return result
