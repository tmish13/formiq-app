"""The depth indicators, each computed over the bottom window.

`I2` carries the verdict. The rest corroborate and feed the confidence.

Why `I2` and not the others:

  I1 femur incline   the most direct statement of "parallel" -- but it FAILED the
                     provenance gate at n=30 (r=0.8952) and passed at n=40
                     (r=0.9124). An indicator whose gate verdict moves with
                     sample size is not load-bearing, so it corroborates only.
  I2 hip-knee delta  r=+0.9413, the best of the four across pose passes, and it
                     is the quantity the definitional criterion is a sign test
                     on. Parallel is exactly 0.
  I3 knee flexion    r=+0.9290, an interior angle so the most view-robust, but it
                     answers "how bent" rather than "how deep" -- a tall lifter
                     with long femurs reaches parallel at a different knee angle.
  I4 hip flexion     r=+0.9206, but confounded by trunk lean: the same depth with
                     a more upright torso reads differently. Expect a small
                     weight; if the fit puts it near zero, drop it rather than
                     carry a passenger.
  I5 hip drop ratio  travel rather than posture. Robust to limb proportion,
                     sensitive to camera pitch. Not gate-tested (it has no
                     single-frame analogue), so corroboration only.

All values are aggregated over the bottom window by the statistic that matches
the physics: the deepest reading, not the mean, because depth is achieved at an
instant and averaging over the window dilutes it toward the ascent.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import numpy as np

from app.rules.kinematics import (
    SIDES,
    SIDE_ORDER,
    Y,
    mean_visibility,
    side_femur_incline,
    side_hip_angle,
    side_hip_knee_delta,
    side_knee_angle,
    usable_sides,
    visibility_ramp,
)
from app.rules.types import IndicatorResult

# Explicit order. Never dict iteration order -- the spec hash depends on it.
INDICATOR_ORDER: Tuple[str, ...] = (
    "I1_femur_incline",
    "I2_hip_knee_delta",
    "I3_knee_flexion",
    "I4_hip_flexion",
    "I5_hip_drop_ratio",
)

# Which landmarks each indicator actually reads, for its visibility confidence.
_LANDMARKS: Dict[str, Tuple[int, ...]] = {
    "I1_femur_incline": (23, 24, 25, 26),
    "I2_hip_knee_delta": (23, 24, 25, 26),
    "I3_knee_flexion": (23, 24, 25, 26, 27, 28),
    "I4_hip_flexion": (11, 12, 23, 24, 25, 26),
    "I5_hip_drop_ratio": (23, 24),
}

_EPS = 1e-9


def _per_side_over_window(kp, window, min_vis, fn) -> List[float]:
    """Collect an indicator across the window, over usable sides only."""
    vals: List[float] = []
    for t in range(window.start, window.end + 1):
        frame = kp[t]
        for s in usable_sides(frame, min_vis):
            v = fn(frame, s)
            if v is not None and np.isfinite(v):
                vals.append(float(v))
    return vals


def compute_indicators(
    kp: np.ndarray,
    window,
    scale_ref: float,
    min_vis: float,
    vis_partial: float,
    vis_trusted: float,
) -> Dict[str, IndicatorResult]:
    """Raw indicator values plus their visibility confidence.

    View suitability is applied later, in depth.py, because it is a property of
    the clip rather than of the indicator.
    """
    out: Dict[str, IndicatorResult] = {}

    # Visibility confidence, averaged over the window, per indicator's landmarks.
    vis_conf: Dict[str, float] = {}
    for name, lms in _LANDMARKS.items():
        per_frame = [
            mean_visibility(kp[t], lms)
            for t in range(window.start, window.end + 1)
        ]
        mv = float(np.mean(per_frame)) if per_frame else 0.0
        vis_conf[name] = visibility_ramp(mv, vis_partial, vis_trusted)

    # --- I1: femur incline, degrees. Parallel = 0, positive = hip above knee.
    vals = _per_side_over_window(kp, window, min_vis, side_femur_incline)
    out["I1_femur_incline"] = IndicatorResult(
        name="I1_femur_incline",
        value=float(np.min(vals)) if vals else None,   # deepest = smallest
        confidence=vis_conf["I1_femur_incline"],
        usable=bool(vals),
        detail={"n_readings": len(vals), "aggregate": "min", "parallel_at": 0.0},
    )

    # --- I2: (hip_y - knee_y)/S. Parallel = 0, positive = hip BELOW knee.
    vals = _per_side_over_window(
        kp, window, min_vis, lambda f, s: side_hip_knee_delta(f, s, scale_ref))
    out["I2_hip_knee_delta"] = IndicatorResult(
        name="I2_hip_knee_delta",
        value=float(np.max(vals)) if vals else None,   # deepest = largest
        confidence=vis_conf["I2_hip_knee_delta"],
        usable=bool(vals),
        detail={"n_readings": len(vals), "aggregate": "max", "parallel_at": 0.0,
                "carries_verdict": True},
    )

    # --- I3: knee flexion, degrees. Smaller = deeper.
    vals = _per_side_over_window(kp, window, min_vis, side_knee_angle)
    out["I3_knee_flexion"] = IndicatorResult(
        name="I3_knee_flexion",
        value=float(np.min(vals)) if vals else None,
        confidence=vis_conf["I3_knee_flexion"],
        usable=bool(vals),
        detail={"n_readings": len(vals), "aggregate": "min"},
    )

    # --- I4: hip flexion, degrees. Smaller = deeper. Trunk-lean confounded.
    vals = _per_side_over_window(kp, window, min_vis, side_hip_angle)
    out["I4_hip_flexion"] = IndicatorResult(
        name="I4_hip_flexion",
        value=float(np.min(vals)) if vals else None,
        confidence=vis_conf["I4_hip_flexion"],
        usable=bool(vals),
        detail={"n_readings": len(vals), "aggregate": "min"},
    )

    # --- I5: hip travel from standing, in torso lengths. Larger = deeper.
    drop = None
    if scale_ref and scale_ref > _EPS:
        drop = (window.hip_y_at_bottom - window.baseline_hip_y) / scale_ref
    out["I5_hip_drop_ratio"] = IndicatorResult(
        name="I5_hip_drop_ratio",
        value=float(drop) if drop is not None and np.isfinite(drop) else None,
        confidence=vis_conf["I5_hip_drop_ratio"],
        usable=bool(drop is not None and np.isfinite(drop)),
        detail={"aggregate": "bottom_vs_standing"},
    )

    return out
