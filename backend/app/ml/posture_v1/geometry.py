"""Geometry helpers for joint-angle computation on MediaPipe pose landmarks."""
from __future__ import annotations

import numpy as np
from typing import Dict, List, Optional, Tuple

Landmark = Dict[str, float]  # {x, y, z, visibility}


def compute_angle(a: Landmark, b: Landmark, c: Landmark) -> float:
    """Return angle at joint b (degrees) formed by a-b-c, in [0, 180]."""
    va = np.array([a["x"] - b["x"], a["y"] - b["y"]])
    vc = np.array([c["x"] - b["x"], c["y"] - b["y"]])
    denom = np.linalg.norm(va) * np.linalg.norm(vc)
    if denom < 1e-9:
        return 0.0
    cos_angle = np.clip(np.dot(va, vc) / denom, -1.0, 1.0)
    return float(np.degrees(np.arccos(cos_angle)))


def compute_knee_angles(frame: list) -> Tuple[Optional[float], Optional[float]]:
    """Return (left_knee_deg, right_knee_deg) for a single frame.

    Indices: left_hip=23, left_knee=25, left_ankle=27
             right_hip=24, right_knee=26, right_ankle=28
    Returns None for a side when any landmark is missing or visibility < 0.3.
    """

    def _safe(idx: int) -> Optional[Landmark]:
        if idx < len(frame) and isinstance(frame[idx], dict):
            lm = frame[idx]
            return lm if lm.get("visibility", 1.0) >= 0.3 else None
        return None

    lh, lk, la = _safe(23), _safe(25), _safe(27)
    rh, rk, ra = _safe(24), _safe(26), _safe(28)
    left = compute_angle(lh, lk, la) if lh and lk and la else None
    right = compute_angle(rh, rk, ra) if rh and rk and ra else None
    return left, right


def compute_hip_angle(frame: list) -> Optional[float]:
    """Average left+right hip flexion (shoulder-hip-knee), or None.

    Indices: left_shoulder=11, left_hip=23, left_knee=25
             right_shoulder=12, right_hip=24, right_knee=26
    """

    def _safe(idx: int) -> Optional[Landmark]:
        if idx < len(frame) and isinstance(frame[idx], dict):
            lm = frame[idx]
            return lm if lm.get("visibility", 1.0) >= 0.3 else None
        return None

    angles = []
    ls, lh, lk = _safe(11), _safe(23), _safe(25)
    rs, rh, rk = _safe(12), _safe(24), _safe(26)
    if ls and lh and lk:
        angles.append(compute_angle(ls, lh, lk))
    if rs and rh and rk:
        angles.append(compute_angle(rs, rh, rk))
    return float(np.mean(angles)) if angles else None
