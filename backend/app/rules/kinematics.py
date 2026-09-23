"""Per-side geometry for the depth rule.

PER SIDE, NOT POOLED -- this is the whole point and it was learned the hard way.
The Stage 0b provenance gate first required all eight core landmarks
(11,12,23,24,25,26,27,28) at visibility >= 0.4 and rejected 11 of 30 videos.
Inspection showed why: 32991_2 has left-side visibility 0.93-1.00 and right knee
0.198, right ankle 0.225. That is a SIDE VIEW -- one leg occludes the other --
and a side view is the *best* view for judging depth. The gate was discarding
exactly the most informative videos. Switching to per-side gating took paired
frames from 1,269 to 3,401 and usable coverage from ~50% to 86.9%.
See bench/results/2026-09-22-keypoint-provenance.md.

`app/ml/posture_v1/geometry.py:compute_knee_angles` already gates per side; this
matches it rather than inventing a third convention.

TWO DELIBERATE DIVERGENCES FROM app/ml/posture_v2/features.py -- do not "fix":

1. SCALE IS CONSTANT ACROSS THE REP, not per frame. v2's `normalize_frames`
   divides each frame by that frame's torso length. Image torso length shrinks at
   the bottom of a squat under perspective and forward lean, so a per-frame
   divisor makes every depth measurement a function of trunk lean. Here the
   scale is the median standing torso length, fixed for the clip.

2. NO TEMPORAL RESAMPLING. v2 resamples to 30fps so tempo features are
   fps-independent. Resampling interpolates landmark data, inventing frames that
   were never observed -- and depth is measured on a *single* frame, the bottom.
   Measuring on a synthetic frame is not acceptable. fps-invariance of the
   smoothing window is achieved instead by specifying it in SECONDS and
   converting with the source fps.

Coordinates are MediaPipe normalised image space: **y increases DOWNWARD**, so a
larger y is lower in the frame.
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

# Reused rather than redefined -- this is the same geometry, and three copies of
# an interior-angle function is how they drift apart.
from app.ml.posture_v2.features import angle_3pts

_EPS = 1e-9

# MediaPipe landmark indices, per side.
SIDES: Dict[str, Dict[str, int]] = {
    "L": {"shoulder": 11, "hip": 23, "knee": 25, "ankle": 27},
    "R": {"shoulder": 12, "hip": 24, "knee": 26, "ankle": 28},
}
SIDE_ORDER: Tuple[str, ...] = ("L", "R")   # explicit; never dict iteration order

N_LANDMARKS = 33
X, Y, Z, VIS = 0, 1, 2, 3


def to_array(pose_data: Sequence) -> np.ndarray:
    """[T, 33, 4] float64 from the serving pose_data shape.

    Serving produces `List[Optional[List[Dict]]]` -- one landmark list per frame,
    or None where nothing was detected (analysis_tasks.py:365). Undetected frames
    and short landmark lists become NaN rather than zeros: a zero is a coordinate,
    and would be silently treated as a real position at the origin.
    """
    T = len(pose_data)
    out = np.full((T, N_LANDMARKS, 4), np.nan, dtype=np.float64)
    for t, frame in enumerate(pose_data):
        if not frame or len(frame) < N_LANDMARKS:
            continue
        for i in range(N_LANDMARKS):
            lm = frame[i]
            if not isinstance(lm, dict):
                continue
            out[t, i, X] = lm.get("x", np.nan)
            out[t, i, Y] = lm.get("y", np.nan)
            out[t, i, Z] = lm.get("z", np.nan)
            v = lm.get("visibility", 1.0)
            out[t, i, VIS] = 1.0 if v is None else v
    return out


def usable_sides(frame: np.ndarray, min_vis: float) -> List[str]:
    """Which sides have all four landmarks present and visible enough."""
    ok = []
    for s in SIDE_ORDER:
        idx = SIDES[s]
        good = True
        for j in idx.values():
            lm = frame[j]
            if not np.isfinite(lm[X]) or not np.isfinite(lm[Y]):
                good = False
                break
            if not np.isfinite(lm[VIS]) or lm[VIS] < min_vis:
                good = False
                break
        if good:
            ok.append(s)
    return ok


def side_torso(frame: np.ndarray, side: str) -> Optional[float]:
    """Shoulder-to-hip distance on one side, xy only."""
    idx = SIDES[side]
    sh, hp = frame[idx["shoulder"]], frame[idx["hip"]]
    d = math.hypot(sh[X] - hp[X], sh[Y] - hp[Y])
    return d if d > _EPS and np.isfinite(d) else None


def hip_y(frame: np.ndarray, min_vis: float) -> Optional[float]:
    """Mean hip y over usable sides. Larger = lower in frame = deeper."""
    sides = usable_sides(frame, min_vis)
    if not sides:
        return None
    vals = [frame[SIDES[s]["hip"]][Y] for s in sides]
    return float(np.mean(vals))


def hip_y_series(kp: np.ndarray, min_vis: float) -> np.ndarray:
    """hip_y per frame, NaN where unusable."""
    return np.array(
        [hip_y(kp[t], min_vis) if hip_y(kp[t], min_vis) is not None else np.nan
         for t in range(kp.shape[0])],
        dtype=np.float64,
    )


def moving_average(x: np.ndarray, window: int) -> np.ndarray:
    """Centred moving average that ignores NaN. Deterministic, pure numpy.

    `window` is derived from a duration in seconds and the source fps by the
    caller, which is how smoothing stays fps-invariant without resampling.
    """
    n = len(x)
    if window <= 1 or n == 0:
        return x.astype(np.float64)
    if window % 2 == 0:
        window += 1                      # keep it centred
    half = window // 2
    out = np.full(n, np.nan, dtype=np.float64)
    for i in range(n):
        lo, hi = max(0, i - half), min(n, i + half + 1)
        seg = x[lo:hi]
        seg = seg[np.isfinite(seg)]
        if seg.size:
            out[i] = seg.mean()
    return out


def scale_reference(
    kp: np.ndarray, min_vis: float, standing_quantile: float
) -> Optional[float]:
    """Median standing torso length -- fixed for the clip.

    "Standing" = the frames with the SMALLEST hip_y (highest hips). Using the
    standing torso rather than the per-frame torso is deliberate: see the module
    docstring, divergence 1.
    """
    ys = hip_y_series(kp, min_vis)
    valid = np.flatnonzero(np.isfinite(ys))
    if valid.size < 2:
        return None
    order = valid[np.argsort(ys[valid], kind="mergesort")]   # stable
    k = max(1, int(round(order.size * standing_quantile)))
    torsos: List[float] = []
    for t in order[:k]:
        frame = kp[t]
        for s in usable_sides(frame, min_vis):
            d = side_torso(frame, s)
            if d is not None:
                torsos.append(d)
    if not torsos:
        return None
    return float(np.median(torsos))


def side_knee_angle(frame: np.ndarray, side: str) -> Optional[float]:
    idx = SIDES[side]
    a = angle_3pts(frame[idx["hip"]], frame[idx["knee"]], frame[idx["ankle"]])
    return float(a) if np.isfinite(a) else None


def side_hip_angle(frame: np.ndarray, side: str) -> Optional[float]:
    idx = SIDES[side]
    a = angle_3pts(frame[idx["shoulder"]], frame[idx["hip"]], frame[idx["knee"]])
    return float(a) if np.isfinite(a) else None


def side_femur_incline(frame: np.ndarray, side: str) -> Optional[float]:
    """Thigh angle from horizontal, degrees. Positive = hip ABOVE knee.

    Parallel is 0 by construction. Scale-free because it is an angle.
    """
    idx = SIDES[side]
    hp, kn = frame[idx["hip"]], frame[idx["knee"]]
    femur = math.hypot(kn[X] - hp[X], kn[Y] - hp[Y])
    if femur < _EPS or not np.isfinite(femur):
        return None
    # y grows downward, so (knee_y - hip_y) > 0 means the hip is higher.
    return float(math.degrees(math.asin(max(-1.0, min(1.0, (kn[Y] - hp[Y]) / femur)))))


def side_hip_knee_delta(frame: np.ndarray, side: str, scale: float) -> Optional[float]:
    """(hip_y - knee_y) / scale. Positive = hip BELOW knee = past parallel.

    This is the quantity the definitional criterion is a sign test on. Same sign
    convention as posture_v2's `depth_hip_below_knee_max`.
    """
    if scale is None or scale < _EPS:
        return None
    idx = SIDES[side]
    hp, kn = frame[idx["hip"]], frame[idx["knee"]]
    if not (np.isfinite(hp[Y]) and np.isfinite(kn[Y])):
        return None
    return float((hp[Y] - kn[Y]) / scale)


def mean_visibility(frame: np.ndarray, landmarks: Sequence[int]) -> float:
    vals = [frame[j][VIS] for j in landmarks
            if np.isfinite(frame[j][VIS])]
    return float(np.mean(vals)) if vals else 0.0


def visibility_ramp(v: float, partial: float, trusted: float) -> float:
    """0 below `partial`, linear to 1 at `trusted`, 1 above.

    `partial` and `trusted` come from app/ml/posture_v1/visibility.py (0.4 / 0.7)
    so the codebase keeps one visibility vocabulary.
    """
    if not np.isfinite(v) or v <= partial:
        return 0.0
    if v >= trusted:
        return 1.0
    return float((v - partial) / (trusted - partial))
