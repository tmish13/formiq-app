"""
Preprocessing for PostureV1 CNN-LSTM model.

MUST match training pipeline exactly:
1. Parse pose_data dicts -> numpy [T, 33, 4] (x, y, z, visibility)
2. clean_keypoints(): trim leading/trailing all-zero frames,
   linearly interpolate internal gaps (tolerant)
3. Drop visibility -> [T, 33, 3]
4. If T > 300: HARD TRUNCATE keypoints[:300]  (NO resampling)
5. If T < 300: ZERO-PAD tail with np.zeros
6. sequence_length = min(T_after_clean, 300) — used for pack_padded_sequence
"""

import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple

import numpy as np

logger = logging.getLogger(__name__)

TARGET_FRAMES: int = 300
NUM_LANDMARKS: int = 33
NUM_COORDS: int = 3  # model input is x, y, z only (visibility dropped)
NUM_COORDS_RAW: int = 4  # parsing includes visibility for cleaning


@dataclass
class PreprocessingResult:
    """Container for preprocessing outputs and quality metadata."""

    keypoints: np.ndarray        # shape [300, 33, 3], dtype float32
    sequence_length: int         # actual valid length before pad (for pack_padded_sequence)
    quality_ok: bool
    quality_flags: List[str] = field(default_factory=list)
    original_frame_count: int = 0
    valid_frame_count: int = 0
    frames_interpolated: int = 0
    frames_padded: int = 0
    frames_truncated: int = 0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def preprocess_pose_data(
    pose_data: List[Optional[List[Optional[Dict[str, float]]]]],
    target_frames: int = TARGET_FRAMES,
) -> PreprocessingResult:
    """
    Full preprocessing pipeline matching training exactly.

    Returns PreprocessingResult with keypoints [300,33,3] and sequence_length.
    """
    original_count = len(pose_data) if pose_data else 0

    # Step 1: parse -> [T, 33, 4] including visibility
    raw4 = _parse_to_array_4d(pose_data)  # [T, 33, 4]
    T = raw4.shape[0]

    if T == 0:
        return PreprocessingResult(
            keypoints=np.zeros((target_frames, NUM_LANDMARKS, NUM_COORDS), dtype=np.float32),
            sequence_length=0,
            quality_ok=False,
            quality_flags=["no_valid_frames"],
            original_frame_count=original_count,
            valid_frame_count=0,
        )

    # Step 2: clean_keypoints — trim leading/trailing all-zero, interpolate internal
    cleaned, n_trimmed, n_interpolated, quality_flags = _clean_keypoints(raw4)
    T_clean = cleaned.shape[0]
    valid_count = T_clean

    if T_clean == 0:
        return PreprocessingResult(
            keypoints=np.zeros((target_frames, NUM_LANDMARKS, NUM_COORDS), dtype=np.float32),
            sequence_length=0,
            quality_ok=False,
            quality_flags=["no_valid_frames_after_clean"],
            original_frame_count=original_count,
            valid_frame_count=0,
        )

    # Step 3: drop visibility -> [T_clean, 33, 3]
    cleaned_xyz = cleaned[:, :, :3]

    # Step 4 & 5: hard truncate or zero-pad
    sequence_length = min(T_clean, target_frames)
    n_truncated = max(0, T_clean - target_frames)
    n_padded = max(0, target_frames - T_clean)

    if T_clean > target_frames:
        # HARD TRUNCATE — NO resampling, NO uniform sampling
        result_kp = cleaned_xyz[:target_frames].copy()
        quality_flags.append(f"truncated_{n_truncated}_frames")
    elif T_clean < target_frames:
        # ZERO-PAD tail
        padding = np.zeros((n_padded, NUM_LANDMARKS, NUM_COORDS), dtype=cleaned_xyz.dtype)
        result_kp = np.concatenate([cleaned_xyz, padding], axis=0)
        quality_flags.append(f"padded_{n_padded}_frames")
    else:
        result_kp = cleaned_xyz.copy()

    assert result_kp.shape == (target_frames, NUM_LANDMARKS, NUM_COORDS)

    quality_ok = "no_valid_frames" not in quality_flags and \
                 "no_valid_frames_after_clean" not in quality_flags

    logger.info(
        "PostureV1 preprocess: original=%d clean=%d seq_len=%d "
        "trimmed=%d interp=%d truncated=%d padded=%d flags=%s",
        original_count, T_clean, sequence_length,
        n_trimmed, n_interpolated, n_truncated, n_padded, quality_flags,
    )

    return PreprocessingResult(
        keypoints=result_kp.astype(np.float32),
        sequence_length=sequence_length,
        quality_ok=quality_ok,
        quality_flags=quality_flags,
        original_frame_count=original_count,
        valid_frame_count=valid_count,
        frames_interpolated=n_interpolated,
        frames_padded=n_padded,
        frames_truncated=n_truncated,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _parse_to_array_4d(
    pose_data: List[Optional[List[Optional[Dict[str, float]]]]],
) -> np.ndarray:
    """
    Parse raw pose_data -> [T, 33, 4] (x, y, z, visibility).

    Frames that are None or have <33 landmarks become all-zero rows.
    """
    T = len(pose_data) if pose_data else 0
    if T == 0:
        return np.zeros((0, NUM_LANDMARKS, NUM_COORDS_RAW), dtype=np.float64)

    arr = np.zeros((T, NUM_LANDMARKS, NUM_COORDS_RAW), dtype=np.float64)

    for i, frame in enumerate(pose_data):
        if frame is None or not isinstance(frame, list) or len(frame) < NUM_LANDMARKS:
            continue  # row stays all-zero
        for j in range(NUM_LANDMARKS):
            lm = frame[j]
            if lm is None or not isinstance(lm, dict):
                # leave this landmark as zero but don't skip entire frame
                continue
            arr[i, j, 0] = lm.get("x", 0.0)
            arr[i, j, 1] = lm.get("y", 0.0)
            arr[i, j, 2] = lm.get("z", 0.0)
            arr[i, j, 3] = lm.get("visibility", 0.0)

    return arr


def _is_zero_frame(frame: np.ndarray) -> bool:
    """Check if a [33, 4] frame is all zeros (no detection)."""
    return np.allclose(frame, 0.0, atol=1e-12)


def _clean_keypoints(
    arr: np.ndarray,
) -> Tuple[np.ndarray, int, int, List[str]]:
    """
    Training-matching clean_keypoints():
    1. Trim leading all-zero frames
    2. Trim trailing all-zero frames
    3. Linearly interpolate internal all-zero gaps (tolerant)

    Returns (cleaned_arr, n_trimmed, n_interpolated, quality_flags).
    """
    T = arr.shape[0]
    quality_flags: List[str] = []

    if T == 0:
        return arr, 0, 0, quality_flags

    # Find first and last non-zero frames
    nonzero_mask = np.array([not _is_zero_frame(arr[i]) for i in range(T)])

    if not nonzero_mask.any():
        return np.zeros((0, NUM_LANDMARKS, NUM_COORDS_RAW), dtype=arr.dtype), T, 0, ["no_valid_frames"]

    first_valid = int(np.argmax(nonzero_mask))
    last_valid = int(T - 1 - np.argmax(nonzero_mask[::-1]))

    n_trimmed = first_valid + (T - 1 - last_valid)
    arr = arr[first_valid:last_valid + 1].copy()
    nonzero_mask = nonzero_mask[first_valid:last_valid + 1]
    T = arr.shape[0]

    # Interpolate internal gaps
    n_interpolated = 0
    i = 0
    while i < T:
        if nonzero_mask[i]:
            i += 1
            continue

        gap_start = i
        while i < T and not nonzero_mask[i]:
            i += 1
        gap_end = i  # exclusive

        left_idx = gap_start - 1 if gap_start > 0 else None
        right_idx = gap_end if gap_end < T else None

        if left_idx is not None and right_idx is not None:
            gap_len = gap_end - gap_start
            for k in range(gap_len):
                alpha = (k + 1) / (gap_len + 1)
                arr[gap_start + k] = arr[left_idx] * (1 - alpha) + arr[right_idx] * alpha
                n_interpolated += 1
        elif left_idx is not None:
            for k in range(gap_start, gap_end):
                arr[k] = arr[left_idx]
                n_interpolated += 1
        elif right_idx is not None:
            for k in range(gap_start, gap_end):
                arr[k] = arr[right_idx]
                n_interpolated += 1

    return arr, n_trimmed, n_interpolated, quality_flags
