"""Camera-view estimation, from the subject rather than from metadata.

Depth is measured in the image plane, so the camera angle changes what the
measurement means. A true side view shows the femur at its full length; a
front-on view foreshortens it toward zero, and `(hip_y - knee_y)` shrinks with
it even when the squat is identical.

Estimated from the shoulder separation relative to the standing torso length:
side-on the shoulders nearly overlap, front-on they are at their widest. Both
are measured on the SAME standing frames used for the scale reference, so the
two quantities are consistent.

There are no view labels anywhere in the corpus -- `video_data` carries only
`category` / `subcategory` (both `squat_more` / class name). So the two cut
points are fitted as ordinary rule parameters on the train split rather than
hand-set or hand-labelled. That is the honest option available.
"""
from __future__ import annotations

import math
from typing import List, Optional

import numpy as np

from app.rules.kinematics import (
    SIDES,
    VIS,
    X,
    Y,
    hip_y_series,
    usable_sides,
)
from app.rules.types import ViewEstimate

_EPS = 1e-9

SIDE = "side"
OBLIQUE = "oblique"
FRONT = "front"


def _standing_frames(kp: np.ndarray, min_vis: float, quantile: float) -> np.ndarray:
    """Indices of the highest-hip frames -- the same set the scale uses."""
    ys = hip_y_series(kp, min_vis)
    valid = np.flatnonzero(np.isfinite(ys))
    if valid.size == 0:
        return valid
    order = valid[np.argsort(ys[valid], kind="mergesort")]
    k = max(1, int(round(order.size * quantile)))
    return order[:k]


def estimate_view(
    kp: np.ndarray,
    scale_ref: Optional[float],
    min_vis: float,
    standing_quantile: float,
    side_max: float,
    front_min: float,
) -> ViewEstimate:
    """Classify the camera view from shoulder separation / torso length.

    Args:
        side_max:  ratio at or below which the view is treated as side-on
        front_min: ratio at or above which it is treated as front-on
                   (both FITTED, not hand-chosen -- see module docstring)
    """
    if scale_ref is None or scale_ref < _EPS:
        return ViewEstimate(kind=OBLIQUE, shoulder_ratio=None, confidence=0.0)

    idx = _standing_frames(kp, min_vis, standing_quantile)
    ratios: List[float] = []
    for t in idx:
        frame = kp[t]
        ls, rs = frame[SIDES["L"]["shoulder"]], frame[SIDES["R"]["shoulder"]]
        # Shoulders must both be present; visibility is NOT required here --
        # an occluded shoulder in a side view is signal, not noise, and
        # demanding both be visible would bias the estimate toward front views.
        if not (np.isfinite(ls[X]) and np.isfinite(rs[X])
                and np.isfinite(ls[Y]) and np.isfinite(rs[Y])):
            continue
        ratios.append(math.hypot(ls[X] - rs[X], ls[Y] - rs[Y]) / scale_ref)

    if not ratios:
        return ViewEstimate(kind=OBLIQUE, shoulder_ratio=None, confidence=0.0)

    r = float(np.median(ratios))
    if r <= side_max:
        kind = SIDE
    elif r >= front_min:
        kind = FRONT
    else:
        kind = OBLIQUE

    # Confidence is how far the ratio sits from the nearest cut point, scaled by
    # the band width -- a clip right on a boundary is genuinely ambiguous.
    band = max(front_min - side_max, _EPS)
    if kind == SIDE:
        conf = min(1.0, (side_max - r) / band + 0.5)
    elif kind == FRONT:
        conf = min(1.0, (r - front_min) / band + 0.5)
    else:
        mid = 0.5 * (side_max + front_min)
        conf = max(0.0, 0.5 - abs(r - mid) / band)
    return ViewEstimate(kind=kind, shoulder_ratio=r, confidence=float(max(0.0, conf)))


def view_weight(kind: str, floors: dict) -> float:
    """Per-indicator view suitability in [0, 1].

    `floors` maps view kind -> multiplier for one indicator, and comes from the
    fitted params. Indicators that read the femur in the image plane (femur
    incline, hip-knee delta) are suppressed front-on; knee flexion is an interior
    angle and degrades far less.
    """
    return float(floors.get(kind, floors.get(OBLIQUE, 1.0)))
