"""Finding the bottom of the rep.

ONE REP PER CLIP. Confirmed three ways across the corpus
(bench/results/2026-09-22-depth-label-inventory.md): clips are median 106 frames
/ 3.5 s; human-marked depth frames span a median of 7 frames (0.23 s), max 40;
and the bar trajectories are a single descent-and-return. A multi-rep clip would
spread its marked frames across seconds, not a quarter of one.

So this is `argmax(smoothed hip_y)` and a band around it. Deleted from the
original design, because single-rep clips need none of it: prominence
thresholds, minimum rep separation, multi-bottom search, cross-rep aggregation
(`agg_mode`, `worst_confident`). Every one of those was a free parameter that
would have had to be justified against data that cannot distinguish it.

The window is defined by DISPLACEMENT, not frame count -- frames whose hip_y is
within `band_frac` of the bottom's drop from standing. A fixed +/-N-frame window
(which is what posture_v2's `segment_phases` uses) widens with a slow rep and
narrows with a fast one, measuring different fractions of the movement depending
on tempo.

Independently checkable: for the 469 depth_fault videos the corpus carries
`depth_frames` -- the timestamps a human marked. The detected window should
overlap them. That validates the mechanism separately from the verdict, and
matters more than usual here because the negative class (bottoms of good_form
clips) does not exist until this function produces it.
"""
from __future__ import annotations

from typing import Optional

import numpy as np

from app.rules.kinematics import hip_y_series, moving_average
from app.rules.types import BottomWindow

_EPS = 1e-9


def smoothing_window_frames(
    smooth_seconds: float, fps: float, fallback_fps: float
) -> int:
    """Convert a duration to an odd frame count.

    Specifying the window in SECONDS is how smoothing stays fps-invariant
    without resampling the landmarks -- see kinematics.py, divergence 2.
    """
    if fps is None or not np.isfinite(fps) or fps <= 0:
        fps = fallback_fps
    w = int(round(smooth_seconds * fps))
    if w < 1:
        w = 1
    if w % 2 == 0:
        w += 1
    return w


def find_bottom(
    kp: np.ndarray,
    fps: float,
    min_vis: float,
    smooth_seconds: float,
    baseline_quantile: float,
    band_frac: float,
    max_window_seconds: float,
    min_window_frames: int,
    fallback_fps: float,
    scale_ref: float,
    min_descent_ratio: float,
) -> Optional[BottomWindow]:
    """The single deepest moment, and the frames around it worth measuring.

    Returns None when there is no usable hip trajectory at all -- the caller
    turns that into an explicit abstention rather than a guess.
    """
    ys = hip_y_series(kp, min_vis)
    if np.count_nonzero(np.isfinite(ys)) < 2:
        return None

    sm = moving_average(ys, smoothing_window_frames(smooth_seconds, fps, fallback_fps))
    finite = np.flatnonzero(np.isfinite(sm))
    if finite.size == 0:
        return None

    # y grows downward, so the bottom of the squat is the MAXIMUM hip_y.
    bottom = int(finite[np.argmax(sm[finite])])

    baseline = float(np.quantile(sm[finite], baseline_quantile))
    depth_at_bottom = sm[bottom] - baseline
    if not np.isfinite(depth_at_bottom) or depth_at_bottom <= _EPS:
        # Flat trajectory: no descent to speak of. Not a bottom.
        return None

    # The hip must actually TRAVEL, measured against the person's own torso.
    # MEASURED FAILURE: 37941_3 has a hip_y range of 0.003 -- the subject barely
    # moves -- yet depth_at_bottom > _EPS passed and the rule confidently
    # measured "the bottom" of a clip containing no squat, scoring -0.747.
    # An epsilon test asks "did anything change"; this asks "was that a rep".
    if scale_ref and scale_ref > _EPS:
        if (depth_at_bottom / scale_ref) < min_descent_ratio:
            return None

    cutoff = sm[bottom] - band_frac * depth_at_bottom

    # Contiguous run around the bottom that stays below the cutoff (i.e. deep).
    start = bottom
    while start - 1 >= 0 and np.isfinite(sm[start - 1]) and sm[start - 1] >= cutoff:
        start -= 1
    end = bottom
    n = len(sm)
    while end + 1 < n and np.isfinite(sm[end + 1]) and sm[end + 1] >= cutoff:
        end += 1

    # Cap the window so a long pause at the bottom does not dominate.
    max_frames = max(min_window_frames,
                     smoothing_window_frames(max_window_seconds, fps, fallback_fps))
    if (end - start + 1) > max_frames:
        half = max_frames // 2
        start = max(0, bottom - half)
        end = min(n - 1, bottom + half)

    return BottomWindow(
        index=bottom,
        start=int(start),
        end=int(end),
        n_frames=int(end - start + 1),
        hip_y_at_bottom=float(sm[bottom]),
        baseline_hip_y=baseline,
    )
