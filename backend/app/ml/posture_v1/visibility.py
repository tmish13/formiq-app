"""
Per-component joint visibility scoring for PostureV1.

Extracts visibility from raw pose_data (MediaPipe {x,y,z,visibility} dicts)
and maps it to per-component quality scores.  Used to:

  1. Null out component scores when the joints driving that component are
     poorly visible (< VISIBILITY_UNRELIABLE_THRESHOLD = 0.4).
  2. Add informational quality flags when visibility is partial (0.4–0.7).
  3. Leave scores untouched when visibility is good (>= 0.7).

MediaPipe visibility is in [0, 1]:
  ~0.9+ = landmark clearly in frame
  ~0.5  = landmark detected but partially occluded
  ~0.1  = MediaPipe guessing (landmark not in frame)

Joint indices (MediaPipe 33-landmark model):
  11 = left_shoulder   12 = right_shoulder
  23 = left_hip        24 = right_hip
  25 = left_knee       26 = right_knee
  27 = left_ankle      28 = right_ankle
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------

VISIBILITY_TRUSTED: float = 0.7
"""Component visibility >= this: scores are trusted, no flag added."""

VISIBILITY_PARTIAL: float = 0.4
"""0.4 <= visibility < 0.7: score computed but quality flag added."""

# Below VISIBILITY_PARTIAL: component set to None (unreliable).


# ---------------------------------------------------------------------------
# Joint groups per component
#
# Each tuple lists the MediaPipe joint indices whose visibility determines
# how reliable the feature signals for that component are.
#
# Rationale:
#   trunk_control  — trunk_angle uses shoulder–hip vector
#   knee_stability — knee angle (hip-knee-ankle), asymmetry (both knees)
#   hip_drive      — left_hip_angle (shoulder_center→left_hip→left_knee)
#   forward_lean   — same trunk vector as trunk_control
# ---------------------------------------------------------------------------

COMPONENT_JOINTS: Dict[str, List[int]] = {
    "trunk_control": [11, 12, 23, 24],           # L/R shoulder, L/R hip
    "knee_stability": [23, 24, 25, 26, 27, 28],  # hips + knees + ankles
    "hip_drive": [11, 12, 23, 24, 25, 26],        # shoulders + hips + knees
    "forward_lean": [11, 12, 23, 24],             # same as trunk_control
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_joint_visibility(
    pose_data: List[Optional[List[Optional[Dict[str, Any]]]]],
    sequence_length: Optional[int] = None,
) -> np.ndarray:
    """Compute per-joint mean visibility from raw pose_data.

    Args:
        pose_data: frames → landmarks → {x, y, z, visibility}
        sequence_length: use only the first N frames (real, not zero-padded).
            Pass the value from PreprocessingResult.sequence_length when
            available to avoid averaging over padded-zero frames.

    Returns:
        Float32 array of shape [33], values in [0, 1].
        0.0 for joints that were never observed.
    """
    T = len(pose_data) if pose_data else 0
    if T == 0:
        return np.zeros(33, dtype=np.float32)

    limit = min(int(sequence_length), T) if sequence_length is not None else T

    vis_sum = np.zeros(33, dtype=np.float64)
    count = np.zeros(33, dtype=np.float64)

    for i in range(limit):
        frame = pose_data[i]
        if frame is None or not isinstance(frame, list):
            continue
        for j, lm in enumerate(frame[:33]):
            if lm is None or not isinstance(lm, dict):
                continue
            vis = float(lm.get("visibility", 0.0))
            vis_sum[j] += vis
            count[j] += 1

    # Use np.maximum to avoid divide-by-zero in the evaluated-but-masked branch of np.where
    joint_vis = np.where(count > 0, vis_sum / np.maximum(count, 1e-10), 0.0).astype(np.float32)
    return joint_vis


def compute_component_visibility(
    joint_visibility: np.ndarray,
) -> Dict[str, float]:
    """Map per-joint visibility to per-component mean visibility.

    Args:
        joint_visibility: [33] float array from compute_joint_visibility().

    Returns:
        dict {component_name: mean_visibility} for the four components.
    """
    result: Dict[str, float] = {}
    for component, joint_indices in COMPONENT_JOINTS.items():
        vis_values = [
            float(joint_visibility[idx])
            for idx in joint_indices
            if idx < len(joint_visibility)
        ]
        result[component] = float(np.mean(vis_values)) if vis_values else 0.0
    return result


def get_visibility_quality_flags(
    component_visibility: Dict[str, float],
) -> List[str]:
    """Return quality flags for components with low or partial visibility.

    Flags emitted:
      ``{component}_visibility_unreliable`` — visibility < VISIBILITY_PARTIAL (0.4)
      ``{component}_visibility_partial``    — VISIBILITY_PARTIAL <= visibility < VISIBILITY_TRUSTED (0.7)

    No flag for trusted (>= 0.7).
    """
    flags: List[str] = []
    for component, vis in component_visibility.items():
        if vis < VISIBILITY_PARTIAL:
            flags.append(f"{component}_visibility_unreliable")
        elif vis < VISIBILITY_TRUSTED:
            flags.append(f"{component}_visibility_partial")
    return flags
