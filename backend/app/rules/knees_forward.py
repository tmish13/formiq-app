"""Knees travelling past the toes: a DESCRIPTIVE, UNFITTED observation.

WHAT THIS CLAIMS AND WHAT IT REFUSES TO CLAIM
---------------------------------------------
It claims: at the bottom of this rep, the knee was N torso-lengths forward of
the toes, and here is when that peaked.

It refuses to claim: that this is a fault. That claim was tested and does not
survive. On 407 train+validation clips
(bench/results/2026-09-23-corpus-level-negative.md):

  * within-video, self-controlled -- 215/268 clips (80.2%) show more
    knee-past-toe travel inside the human-marked interval than outside it,
    median delta +0.0785 torso-lengths. The predicate measures the intended
    thing and its polarity is confirmed.
  * between-video -- AUROC 0.572 against a prevalence of 68.3%, whose
    all-positive trivial floor is F1 0.812. No video-level threshold on this
    quantity beats calling every squat positive.

So: the predicate knows WHEN the travel happens, not WHICH clips have a fault.
Nearly every squat contains some knee-forward travel; the annotator is marking
where it becomes *excessive*, a judgement about degree against a standard that
is not in the geometry.

Consequently this checker is `fitted: false` and ADVISORY. The combiner may use
it as evidence and may never let it set a verdict. The threshold in the params
file is a hand-set descriptive cut, not a decision boundary fitted to anything,
and it is labelled as such in the artifact and on the stored decision row.

THE PREDICATE, stated before it was measured
--------------------------------------------
    dir_s = sign(foot_index_x - heel_x)          the way that foot points
    fwd_s = ((knee_x - foot_index_x) * dir_s) / S

Positive = knee is forward of the toes. Taking the direction from the foot's own
orientation makes the sign safe regardless of which way the subject faces or
which leg is measured -- the alternative, a raw `knee_x - ankle_x`, flips sign
between legs and flips again when the subject turns around.

Normalised by the standing torso length S, side-gated by visibility, averaged
over usable sides: the same machinery as the depth rule, for the same reasons
(see app/rules/kinematics.py).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

import numpy as np

from app.rules.kinematics import (
    SIDES,
    SIDE_ORDER,
    VIS,
    X,
    mean_visibility,
    scale_reference,
    to_array,
    usable_sides,
    visibility_ramp,
)
from app.rules.segmentation import find_bottom
from app.rules.spec import RULES_SPEC_VERSION, rules_spec_hash
from app.rules.types import (
    ABSTAIN_BAD_SCALE,
    ABSTAIN_LOW_COVERAGE,
    ABSTAIN_NO_BOTTOM,
    ABSTAIN_NO_FRAMES,
    NOT_OBSERVED,
    OBSERVED,
    UNCERTAIN,
    RuleVerdict,
)
from app.rules.view import estimate_view, view_weight

TARGET = "knees_forward"
CHECKER_NAME = "knees_forward_v0"

#: Foot landmarks, per side. Not in kinematics.SIDES because the depth rule has
#: no use for them and a shared dict that half the callers ignore is how
#: landmark sets drift.
FOOT: Dict[str, Dict[str, int]] = {
    "L": {"heel": 29, "toe": 31},
    "R": {"heel": 30, "toe": 32},
}

_EPS = 1e-9


def _round(x: Optional[float], nd: int = 6) -> Optional[float]:
    if x is None or not np.isfinite(x):
        return None
    return float(round(float(x), nd))


def forward_travel(frame: np.ndarray, scale: float, min_vis: float,
                   min_foot_length: float) -> Optional[float]:
    """The predicate for one frame: mean over usable sides, or None."""
    if scale is None or scale < _EPS:
        return None
    vals: List[float] = []
    for s in usable_sides(frame, min_vis):
        heel, toe = frame[FOOT[s]["heel"]], frame[FOOT[s]["toe"]]
        knee = frame[SIDES[s]["knee"]]
        if not (np.isfinite(heel[X]) and np.isfinite(toe[X]) and np.isfinite(knee[X])):
            continue
        # A foot we cannot see cannot define a forward direction. Without this
        # the sign is taken from noise and the measurement silently inverts.
        if not (np.isfinite(heel[VIS]) and heel[VIS] >= min_vis
                and np.isfinite(toe[VIS]) and toe[VIS] >= min_vis):
            continue
        span = toe[X] - heel[X]
        if abs(span) < min_foot_length:
            continue
        direction = 1.0 if span > 0 else -1.0
        vals.append(((knee[X] - toe[X]) * direction) / scale)
    return float(np.mean(vals)) if vals else None


def _abstain(reason: str, params: Dict[str, Any], spec_hash: str,
             **extra: Any) -> RuleVerdict:
    return RuleVerdict(
        target=TARGET,
        decision=UNCERTAIN,
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
        fitted=bool(params.get("fitted", False)),
    )


def evaluate_knees_forward(
    pose_data: Sequence,
    fps: float,
    params: Dict[str, Any],
) -> RuleVerdict:
    """Measure knee-past-toe travel at the bottom. Pure: no I/O, RNG or clock.

    The returned `decision` is OBSERVED / NOT_OBSERVED / UNCERTAIN, which are
    descriptions and not verdicts. `fitted` is carried on the result so a caller
    cannot lose track of that.
    """
    spec_hash = rules_spec_hash(params)
    min_vis = params["min_visibility"]

    kp = to_array(pose_data)
    if kp.shape[0] == 0:
        return _abstain(ABSTAIN_NO_FRAMES, params, spec_hash)

    scale = scale_reference(
        kp, min_vis, params["standing_quantile"],
        min_usable_frames=params["min_usable_frames_for_scale"],
        min_standing_frames=params["min_standing_frames"],
    )
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
        scale_ref=scale,
        min_descent_ratio=params["min_descent_ratio"],
    )
    if window is None:
        return _abstain(ABSTAIN_NO_BOTTOM, params, spec_hash,
                        scale_ref=_round(scale))

    view = estimate_view(
        kp, scale, min_vis,
        standing_quantile=params["standing_quantile"],
        side_max=params["view_side_max"],
        front_min=params["view_front_min"],
    )

    # Peak travel inside the bottom window, and where it happened. The clip-wide
    # peak is NOT used: the between-video comparison that produced AUROC 0.572
    # showed that a max over a longer span is larger by construction, which is
    # the methodology error the valgus run made and corrected
    # (bench/results/2026-09-23-valgus-polarity.md).
    min_foot = params["min_foot_length"]
    best_val: Optional[float] = None
    best_idx: Optional[int] = None
    n_measured = 0
    vis_ramps: List[float] = []
    foot_landmarks = [FOOT[s][k] for s in SIDE_ORDER for k in ("heel", "toe")]
    for t in range(window.start, window.end + 1):
        v = forward_travel(kp[t], scale, min_vis, min_foot)
        if v is None:
            continue
        n_measured += 1
        vis_ramps.append(visibility_ramp(
            mean_visibility(kp[t], foot_landmarks),
            params["visibility_partial"], params["visibility_trusted"]))
        if best_val is None or v > best_val:
            best_val, best_idx = v, t

    # Coverage: how much of the bottom window we could actually measure, times
    # how well we could see the feet, times how suitable the view is.
    frames_frac = (n_measured / window.n_frames) if window.n_frames else 0.0
    vis_w = float(np.mean(vis_ramps)) if vis_ramps else 0.0
    vw = view_weight(view.kind, params["view_floors"].get(TARGET, {}))
    coverage = float(frames_frac * vis_w * vw)

    peak_time = (best_idx / fps) if (best_idx is not None and fps and fps > 0) \
        else None
    evidence = [{
        "name": "K1_knee_past_toe",
        "value": _round(best_val),
        "confidence": _round(vis_w, 4),
        "usable": best_val is not None,
        "detail": {
            "peak_frame": best_idx,
            "peak_time_sec": _round(peak_time, 3),
            "frames_measured": n_measured,
            "window_frames": window.n_frames,
            "view_weight": _round(vw, 4),
            # Stated on every decision so the limit travels with the evidence
            # rather than living only in a results file nobody opens.
            "validated": "polarity only (80.2% within-video, n=268); "
                         "between-video AUROC 0.572 vs trivial floor F1 0.812",
        },
    }]

    common = {
        "scale_ref": _round(scale),
        "view": view.as_dict(),
        "bottom": window.as_dict(),
        "indicators": evidence,
        "coverage": _round(coverage, 4),
    }

    if best_val is None or n_measured < params["min_measured_frames"]:
        return _abstain(ABSTAIN_NO_BOTTOM, params, spec_hash, **common)
    if coverage < params["coverage_floor"]:
        return _abstain(ABSTAIN_LOW_COVERAGE, params, spec_hash,
                        score=_round(best_val),
                        **{k: v for k, v in common.items() if k != "score"})

    cut = float(params["observation_cut"])
    decision = OBSERVED if best_val >= cut else NOT_OBSERVED

    return RuleVerdict(
        target=TARGET,
        decision=decision,
        abstain_reason=None,
        score=_round(best_val),
        confidence=_round(coverage, 4),
        coverage=_round(coverage, 4),
        scale_ref=common["scale_ref"],
        view=common["view"],
        bottom=common["bottom"],
        indicators=evidence,
        rules_spec_version=RULES_SPEC_VERSION,
        rules_spec_hash=spec_hash,
        params_id=params.get("params_id", "unknown"),
        fitted=bool(params.get("fitted", False)),
        threshold=cut,
    )
