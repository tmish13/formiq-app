"""The depth verdict: definitional criterion, calibrated measurement.

    AT_DEPTH  <=>  (hip_y - knee_y)/S + offset(view)  >=  0
                                        ^^^^^^^^^^^        ^
                                        FITTED             NOT FITTED

Parallel is a definition, not a hyperparameter. The femur reaching horizontal IS
the criterion, so the threshold is exactly 0 and no amount of data moves it.

What IS fitted is the measurement, for two physical reasons:
  - MediaPipe landmark 23/24 is not the anatomical hip crease, and 25/26 is not
    the top of the knee. There is a systematic offset between "hip landmark level
    with knee landmark" and "hip crease level with knee top".
  - Off-axis camera foreshortens the femur in the image plane, so the offset
    depends on view.

Why the criterion is not fitted to the labels: there is exactly ONE depth
annotation in the corpus, surfaced twice (labels_shallow_depth.json and the
splits file's depth_frames are 100.0% identical -- 1552/1552). There is no second
opinion to cross-check against. Fitting the threshold to it would encode one
annotator's private notion of "parallel" into a production verdict and call it
depth. Fitting only the measurement keeps the criterion public and checkable, and
leaves disagreements with the labels diagnostic rather than minimised.

ABSTENTION IS LOAD-BEARING, and was validated independently before it was
designed in: the Stage 0b provenance gate found the two pose passes agree on only
80% of verdicts raw, but 100% once calls within 0.08 of parallel are declined
(bench/results/2026-09-22-keypoint-provenance.md). The disagreement lives
entirely near parallel -- which is exactly where a human would also decline.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

import numpy as np

from app.rules.indicators import INDICATOR_ORDER, compute_indicators
from app.rules.kinematics import scale_reference, to_array
from app.rules.segmentation import find_bottom
from app.rules.spec import RULES_SPEC_VERSION, rules_spec_hash
from app.rules.types import (
    ABSTAIN_BAD_SCALE,
    ABSTAIN_LOW_COVERAGE,
    ABSTAIN_NEAR_PARALLEL,
    ABSTAIN_NO_BOTTOM,
    ABSTAIN_NO_FRAMES,
    AT_DEPTH,
    SHALLOW,
    UNCERTAIN,
    DepthVerdict,
)
from app.rules.view import estimate_view, view_weight

_EPS = 1e-9
VERDICT_INDICATOR = "I2_hip_knee_delta"


def _round(x: Optional[float], nd: int = 6) -> Optional[float]:
    """Single rounding point on the way out.

    Matches the 6dp the PostureV1 loader reports (loader.py:604) so the two
    checkers quote depth at the same resolution.
    """
    if x is None or not np.isfinite(x):
        return None
    return float(round(float(x), nd))


def _abstain(reason: str, params: Dict[str, Any], spec_hash: str,
             **extra: Any) -> DepthVerdict:
    return DepthVerdict(
        verdict=UNCERTAIN,
        abstain_reason=reason,
        score=extra.get("score"),
        confidence=None,
        coverage=extra.get("coverage", 0.0),
        scale_ref=extra.get("scale_ref"),
        view=extra.get("view"),
        bottom=extra.get("bottom"),
        indicators=extra.get("indicators", []),
        rules_spec_version=RULES_SPEC_VERSION,
        rules_spec_hash=spec_hash,
        params_id=params.get("params_id", "unknown"),
    )


def evaluate_depth(
    pose_data: Sequence,
    fps: float,
    params: Dict[str, Any],
) -> DepthVerdict:
    """Judge one clip. Pure: no I/O, no RNG, no clock, no environment reads.

    Args:
        pose_data: the serving shape -- List[Optional[List[Dict]]], 33 landmarks
                   per frame with x/y/z/visibility, or None where undetected.
        fps:       source frames per second. Used only to size the smoothing
                   window in real time; landmarks are never resampled.
        params:    fitted constants, from app.rules.spec.load_params().
    """
    spec_hash = rules_spec_hash(params)
    min_vis = params["min_visibility"]

    kp = to_array(pose_data)
    if kp.shape[0] == 0:
        return _abstain(ABSTAIN_NO_FRAMES, params, spec_hash)

    scale = scale_reference(kp, min_vis, params["standing_quantile"])
    if scale is None or scale < _EPS:
        return _abstain(ABSTAIN_BAD_SCALE, params, spec_hash)

    window = find_bottom(
        kp, fps, min_vis,
        smooth_seconds=params["smooth_seconds"],
        baseline_quantile=params["baseline_quantile"],
        band_frac=params["bottom_band_frac"],
        max_window_seconds=params["max_window_seconds"],
        min_window_frames=params["min_window_frames"],
        fallback_fps=params["fallback_fps"],
    )
    if window is None:
        return _abstain(ABSTAIN_NO_BOTTOM, params, spec_hash, scale_ref=_round(scale))

    view = estimate_view(
        kp, scale, min_vis,
        standing_quantile=params["standing_quantile"],
        side_max=params["view_side_max"],
        front_min=params["view_front_min"],
    )

    inds = compute_indicators(
        kp, window, scale, min_vis,
        vis_partial=params["visibility_partial"],
        vis_trusted=params["visibility_trusted"],
    )

    # Confidence per indicator = visibility ramp x view suitability.
    weights = params["indicator_weights"]
    floors = params["view_floors"]
    conf: Dict[str, float] = {}
    for name in INDICATOR_ORDER:
        ind = inds[name]
        vw = view_weight(view.kind, floors.get(name, {}))
        conf[name] = float(ind.confidence * vw) if ind.usable else 0.0

    # Coverage: how much of the evidence we actually have, weighted by how much
    # each piece was supposed to matter. This is what the abstain floor tests.
    w_total = sum(weights[n] for n in INDICATOR_ORDER)
    w_have = sum(weights[n] * conf[n] for n in INDICATOR_ORDER)
    coverage = float(w_have / w_total) if w_total > _EPS else 0.0

    evidence: List[Dict[str, Any]] = []
    for name in INDICATOR_ORDER:
        d = inds[name].as_dict()
        d["value"] = _round(d["value"])
        d["confidence"] = _round(conf[name], 4)
        d["weight"] = weights[name]
        d["view_weight"] = _round(view_weight(view.kind, floors.get(name, {})), 4)
        evidence.append(d)

    common = {
        "scale_ref": _round(scale),
        "view": view.as_dict(),
        "bottom": window.as_dict(),
        "indicators": evidence,
        "coverage": _round(coverage, 4),
    }

    if window.n_frames < params["min_bottom_frames"]:
        return _abstain(ABSTAIN_NO_BOTTOM, params, spec_hash, **common)

    verdict_ind = inds[VERDICT_INDICATOR]
    if not verdict_ind.usable or verdict_ind.value is None:
        return _abstain(ABSTAIN_LOW_COVERAGE, params, spec_hash, **common)

    if coverage < params["coverage_floor"]:
        return _abstain(ABSTAIN_LOW_COVERAGE, params, spec_hash, **common)

    # The measurement correction. The THRESHOLD stays 0; only this moves.
    offset = float(params["offset_by_view"].get(
        view.kind, params["offset_by_view"].get("oblique", 0.0)))
    score = float(verdict_ind.value) + offset
    m = float(params["deadband"])

    if score >= m:
        verdict, reason = AT_DEPTH, None
    elif score <= -m:
        verdict, reason = SHALLOW, None
    else:
        # Within the deadband of parallel. This is where the two pose passes
        # disagreed, and where a human would decline too.
        return _abstain(ABSTAIN_NEAR_PARALLEL, params, spec_hash,
                        score=_round(score), **{k: v for k, v in common.items()
                                                if k != "score"})

    decision_conf = coverage * min(1.0, abs(score) / m) if m > _EPS else coverage

    return DepthVerdict(
        verdict=verdict,
        abstain_reason=reason,
        score=_round(score),
        confidence=_round(decision_conf, 4),
        coverage=_round(coverage, 4),
        scale_ref=common["scale_ref"],
        view=common["view"],
        bottom=common["bottom"],
        indicators=evidence,
        rules_spec_version=RULES_SPEC_VERSION,
        rules_spec_hash=spec_hash,
        params_id=params.get("params_id", "unknown"),
    )
