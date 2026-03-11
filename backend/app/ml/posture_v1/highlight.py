"""Select the deepest-squat frame for the evidence overlay."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from app.ml.posture_v1.geometry import compute_hip_angle, compute_knee_angles

_HIP_IDX = [23, 24]
_KNEE_IDX = [25, 26]


@dataclass
class HighlightFrameInfo:
    frame_index: int
    timestamp_sec: float
    knee_angle_left: Optional[float]
    knee_angle_right: Optional[float]
    hip_angle: Optional[float]
    depth_proxy: float


def _depth_proxy(frame: list) -> float:
    """Mean y of hip+knee landmarks. Higher y = lower body = deeper squat."""
    ys = []
    for idx in _HIP_IDX + _KNEE_IDX:
        if idx < len(frame) and isinstance(frame[idx], dict):
            ys.append(float(frame[idx].get("y", 0.0)))
    return float(sum(ys) / len(ys)) if ys else 0.0


def select_highlight_frame(
    pose_sequence: List[Optional[List[Optional[Dict[str, Any]]]]],
    fps: float = 30.0,
) -> Optional[HighlightFrameInfo]:
    """Return the deepest-squat frame (max mean hip+knee y). Deterministic."""
    best_idx, best_proxy = -1, -1.0
    for i, frame in enumerate(pose_sequence):
        if not frame:
            continue
        p = _depth_proxy(frame)
        if p > best_proxy:
            best_proxy, best_idx = p, i

    if best_idx < 0:
        return None

    frame = pose_sequence[best_idx]
    lk, rk = compute_knee_angles(frame)
    hip = compute_hip_angle(frame)
    return HighlightFrameInfo(
        frame_index=best_idx,
        timestamp_sec=round(best_idx / fps, 3),
        knee_angle_left=round(lk, 1) if lk is not None else None,
        knee_angle_right=round(rk, 1) if rk is not None else None,
        hip_angle=round(hip, 1) if hip is not None else None,
        depth_proxy=round(best_proxy, 4),
    )
