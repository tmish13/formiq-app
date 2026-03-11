"""
151-dimensional temporal feature extractor for PostureV1.

EXACT layout (matches training export_posture_v1.py):
  [0–86]:   87D original biomechanical features
    [0–32]:   flatten(np.mean(coords, axis=0))[:33]
              = xyz-interleaved means for joints 0-10
              (joint0_x, joint0_y, joint0_z, joint1_x, ..., joint10_z)
    [33–65]:  flatten(np.std(coords, axis=0))[:33]
              = xyz-interleaved stds for joints 0-10
    [66–86]:  joint{0..6}_{x,y,z}_range  (7 joints × 3 coords = 21 features)
  [87–146]: 64D temporal angle features
    4 angles × 15 stats each   (60 features)
      angles: left_knee, right_knee, trunk, left_hip
      per angle: 6 whole-seq stats + 3 phases × 3 stats = 15
      whole-seq: mean, std, min, max, range, SLOPE (NOT median)
      per-phase: mean, std, ANGULAR_VELOCITY (NOT range)
    + 4 derived: bottom_trunk_wobble, knee_asymmetry_mean,
                 bottom_knee_asymmetry, trunk_forward_lean
  [147–150]: 4 derived features

Total: 33 + 33 + 21 + 60 + 4 = 151

CRITICAL training-matching details:
  - 87D features computed on REAL frames only (not zero-padded tail)
  - Angles computed on 2D (x,y) coordinates, NOT 3D
  - trunk_angle = angle between shoulder-hip vector and vertical [0,-1]
  - left_hip_angle = shoulder_center→left_hip→left_knee (2D)
  - Phase segmentation uses Savitzky-Golay smoothed hip y (scipy.signal.savgol_filter)
  - Valid angle masking: (>0) & (<220) & isfinite
  - 6th whole-seq stat = slope (linear regression), NOT median
  - 3rd phase stat = angular_velocity (mean|diff|), NOT range
  - bottom_trunk_wobble = MAD (mean absolute deviation), NOT std
  - trunk_forward_lean = mean(|trunk_angles|), NOT shoulder_y - hip_y

Features MUST be normalized with posture_v1_scaler.joblib before inference.
"""

import logging
from pathlib import Path
from typing import Optional, List, Dict

import numpy as np

logger = logging.getLogger(__name__)

EXPECTED_DIM = 151

# MediaPipe landmark indices
_LM = {
    "nose": 0,
    "left_eye_inner": 1, "left_eye": 2, "left_eye_outer": 3,
    "right_eye_inner": 4, "right_eye": 5, "right_eye_outer": 6,
    "left_shoulder": 11, "right_shoulder": 12,
    "left_elbow": 13, "right_elbow": 14,
    "left_wrist": 15, "right_wrist": 16,
    "left_hip": 23, "right_hip": 24,
    "left_knee": 25, "right_knee": 26,
    "left_ankle": 27, "right_ankle": 28,
}

# 7 joints for range features [66–86]: indices 0..6 in MediaPipe ordering
_RANGE_JOINTS = [0, 1, 2, 3, 4, 5, 6]  # nose through right_eye_outer

_SCALER_FILENAME = "posture_v1_scaler.joblib"
_scaler_cache: dict = {}


# ---------------------------------------------------------------------------
# Ordered feature names (for validation / debugging)
# ---------------------------------------------------------------------------

def get_feature_names() -> List[str]:
    """Return the 151 feature names in exact training order."""
    names: List[str] = []

    # [0–32]: xyz-interleaved means for joints 0-10
    # Training: np.mean(coords, axis=0).flatten()[:33]
    for j in range(11):
        for coord in ["x", "y", "z"]:
            names.append(f"joint{j}_{coord}_mean")

    # [33–65]: xyz-interleaved stds for joints 0-10
    for j in range(11):
        for coord in ["x", "y", "z"]:
            names.append(f"joint{j}_{coord}_std")

    # [66–86]: joint{0..6}_{x,y,z}_range
    for i in _RANGE_JOINTS:
        for coord in ["x", "y", "z"]:
            names.append(f"joint{i}_{coord}_range")

    # [87–146]: 4 angles × 15 stats
    angle_names = ["left_knee", "right_knee", "trunk", "left_hip"]
    whole_stats = ["mean", "std", "min", "max", "range", "slope"]
    phase_names = ["descent", "bottom", "ascent"]
    phase_stats = ["mean", "std", "angular_velocity"]
    for aname in angle_names:
        for s in whole_stats:
            names.append(f"{aname}_angle_{s}")
        for pname in phase_names:
            for ps in phase_stats:
                names.append(f"{aname}_angle_{pname}_{ps}")

    # [147–150]
    names.append("bottom_trunk_wobble")
    names.append("knee_asymmetry_mean")
    names.append("bottom_knee_asymmetry")
    names.append("trunk_forward_lean")

    assert len(names) == EXPECTED_DIM, f"Feature names count {len(names)} != {EXPECTED_DIM}"
    return names


# Pre-compute once at import time for fast assertions
FEATURE_NAMES: List[str] = get_feature_names()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_151d_features(
    keypoints: np.ndarray,
    artifacts_dir: Optional[Path] = None,
    apply_scaler: bool = True,
    sequence_length: Optional[int] = None,
) -> np.ndarray:
    """
    Compute 151D feature vector in exact training order.

    Args:
        keypoints: [T, 33, 3] array (x, y, z) — output of preprocess.
        artifacts_dir: Path to directory with posture_v1_scaler.joblib.
        apply_scaler: Whether to normalize with the training scaler.
        sequence_length: Actual valid frame count before padding. If None,
            uses full T (backward compat). Training computes features on
            real frames only, so this should be set when input is padded.

    Returns:
        1D float32 array of shape [151].
    """
    T = keypoints.shape[0]
    if T == 0:
        logger.warning("compute_151d_features: 0-frame input, returning zeros")
        return np.zeros(EXPECTED_DIM, dtype=np.float32)

    # Use only real frames (exclude zero-padding) — matches training
    real_len = sequence_length if sequence_length is not None else T
    real_len = min(real_len, T)
    if real_len <= 0:
        logger.warning("compute_151d_features: seq_len=0, returning zeros")
        return np.zeros(EXPECTED_DIM, dtype=np.float32)

    kp_real = keypoints[:real_len]  # [real_len, 33, 3]

    features: List[float] = []

    # --- [0–32]: flatten(np.mean(coords, axis=0))[:33] ---
    # Training: coords = kp[:,:,:3]; joint_means = np.mean(coords, axis=0)  # [33,3]
    #           features.extend(joint_means.flatten()[:33])
    # This produces xyz-interleaved means for joints 0-10 (11 joints × 3 = 33)
    joint_means = np.mean(kp_real, axis=0)  # [33, 3]
    features.extend(joint_means.flatten()[:33].tolist())

    # --- [33–65]: flatten(np.std(coords, axis=0))[:33] ---
    joint_stds = np.std(kp_real, axis=0)  # [33, 3]
    features.extend(joint_stds.flatten()[:33].tolist())

    # --- [66–86]: joint{0..6}_{x,y,z}_range ---
    for j in _RANGE_JOINTS:
        for c in range(3):
            features.append(float(np.ptp(kp_real[:, j, c])))

    # --- [87–146]: 4 angles × 15 stats ---
    # Compute on real frames only (matches training)
    angles_dict = _compute_key_angles(kp_real)
    phases = _segment_squat_phases(kp_real)

    angle_order = ["left_knee_angle", "right_knee_angle", "trunk_angle", "left_hip_angle"]
    for angle_name in angle_order:
        angle_series = angles_dict.get(angle_name, np.zeros(real_len))
        features.extend(_angle_15_stats(angle_series, phases, real_len))

    # --- [147–150]: 4 derived features ---
    features.extend(_derived_features(kp_real, angles_dict, phases))

    vec = np.array(features, dtype=np.float64)
    assert vec.shape[0] == EXPECTED_DIM, f"Feature dim {vec.shape[0]} != {EXPECTED_DIM}"

    vec = np.nan_to_num(vec, nan=0.0, posinf=0.0, neginf=0.0)

    if apply_scaler:
        vec = _apply_scaler(vec, artifacts_dir)

    return vec.astype(np.float32)


# ---------------------------------------------------------------------------
# Angle computation — matches training notebook exactly
# ---------------------------------------------------------------------------

def _compute_key_angles(kp: np.ndarray) -> Dict[str, np.ndarray]:
    """
    Compute 4 angle time-series matching training notebook compute_key_angles().

    CRITICAL: Training uses 2D (x,y) coordinates only.
    """
    T = kp.shape[0]
    angles: Dict[str, np.ndarray] = {}

    try:
        # Extract 2D positions (x, y only) — matches training
        left_hip = kp[:, _LM["left_hip"], :2]
        right_hip = kp[:, _LM["right_hip"], :2]
        left_knee = kp[:, _LM["left_knee"], :2]
        right_knee = kp[:, _LM["right_knee"], :2]
        left_ankle = kp[:, _LM["left_ankle"], :2]
        right_ankle = kp[:, _LM["right_ankle"], :2]
        left_shoulder = kp[:, _LM["left_shoulder"], :2]
        right_shoulder = kp[:, _LM["right_shoulder"], :2]

        hip_center = (left_hip + right_hip) / 2
        shoulder_center = (left_shoulder + right_shoulder) / 2

        # 1. Left knee angle (hip-knee-ankle) — 2D
        angles["left_knee_angle"] = _angle_at_vertex_2d(left_hip, left_knee, left_ankle)

        # 2. Right knee angle (hip-knee-ankle) — 2D
        angles["right_knee_angle"] = _angle_at_vertex_2d(right_hip, right_knee, right_ankle)

        # 3. Trunk angle = angle of shoulder-hip vector with vertical [0, -1]
        trunk_angles = np.zeros(T)
        vertical = np.array([0.0, -1.0])
        for t in range(T):
            trunk_vector = shoulder_center[t] - hip_center[t]
            norm = np.linalg.norm(trunk_vector)
            if norm > 1e-6:
                cos_angle = np.dot(trunk_vector, vertical) / norm
                cos_angle = np.clip(cos_angle, -1.0, 1.0)
                trunk_angles[t] = np.degrees(np.arccos(cos_angle))
            else:
                trunk_angles[t] = 90.0
        angles["trunk_angle"] = trunk_angles

        # 4. Left hip angle (shoulder_center→left_hip→left_knee) — 2D
        angles["left_hip_angle"] = _angle_at_vertex_2d(shoulder_center, left_hip, left_knee)
    except Exception:
        for name in ["left_knee_angle", "right_knee_angle", "trunk_angle", "left_hip_angle"]:
            angles[name] = np.zeros(T)

    return angles


def _angle_at_vertex_2d(
    point_a: np.ndarray, vertex: np.ndarray, point_c: np.ndarray,
) -> np.ndarray:
    """
    Compute angle at vertex for each frame using 2D coords.
    Matches training: v1 = a - vertex, v2 = c - vertex, angle = arccos(dot/norms).
    """
    T = point_a.shape[0]
    angles = np.zeros(T)
    for t in range(T):
        v1 = point_a[t] - vertex[t]
        v2 = point_c[t] - vertex[t]
        n1 = np.linalg.norm(v1)
        n2 = np.linalg.norm(v2)
        if n1 > 1e-6 and n2 > 1e-6:
            cos_angle = np.dot(v1, v2) / (n1 * n2)
            cos_angle = np.clip(cos_angle, -1.0, 1.0)
            angles[t] = np.degrees(np.arccos(cos_angle))
        else:
            angles[t] = 0.0
    return angles


# ---------------------------------------------------------------------------
# Phase segmentation — matches training segment_squat_phases()
# ---------------------------------------------------------------------------

def _segment_squat_phases(kp: np.ndarray) -> Dict[str, list]:
    """
    Segment squat into descent/bottom/ascent using hip-based detection.
    Matches training notebook segment_squat_phases() exactly:
    - Uses savgol_filter for smoothing (not moving average)
    - No knee-angle confirmation (training doesn't have it)
    """
    T = kp.shape[0]

    if T < 10:
        return {
            "descent_idx": list(range(T // 3)),
            "bottom_idx": list(range(T // 3, 2 * T // 3)),
            "ascent_idx": list(range(2 * T // 3, T)),
        }

    try:
        from scipy.signal import savgol_filter

        # Hip center y-position
        hip_y = (kp[:, _LM["left_hip"], 1] + kp[:, _LM["right_hip"], 1]) / 2

        # Savitzky-Golay smoothing — matches training exactly
        wl = min(11, T // 3 if T // 3 % 2 == 1 else T // 3 + 1)
        wl = max(3, wl)
        hip_smooth = savgol_filter(hip_y, wl, 2) if wl < T else hip_y.copy()

        # Deepest point (max y)
        bottom_frame = int(np.argmax(hip_smooth))

        # Bottom window
        bw = max(T // 10, 3)
        bs = max(0, bottom_frame - bw)
        be = min(T, bottom_frame + bw)

        ds, de = 0, bs
        asc_s, asc_e = be, T

        # Ensure non-empty phases
        if de <= ds:
            de = min(T // 3, T)
        if asc_s >= asc_e:
            asc_s = max(2 * T // 3, 0)

        return {
            "descent_idx": list(range(ds, de)),
            "bottom_idx": list(range(bs, be)),
            "ascent_idx": list(range(asc_s, asc_e)),
        }

    except Exception:
        return {
            "descent_idx": list(range(T // 3)),
            "bottom_idx": list(range(T // 3, 2 * T // 3)),
            "ascent_idx": list(range(2 * T // 3, T)),
        }


# ---------------------------------------------------------------------------
# Angle statistics — matches training exactly
# ---------------------------------------------------------------------------

def _angle_15_stats(
    angle_series: np.ndarray,
    phases: Dict[str, list],
    T: int,
) -> List[float]:
    """
    6 whole-sequence stats + 3 phases × 3 stats = 15 features per angle.

    Training matching:
      whole-seq: mean, std, min, max, range, SLOPE
      per-phase: mean, std, ANGULAR_VELOCITY
      Valid angle masking: (>0) & (<220) & isfinite
    """
    stats: List[float] = []

    # Valid angle masking (matches training)
    valid_mask = (angle_series > 0) & (angle_series < 220) & np.isfinite(angle_series)

    if valid_mask.sum() < max(T // 3, 1):
        # Not enough valid frames — return zeros (matches training skip logic)
        return [0.0] * 15

    valid_angles = angle_series[valid_mask]

    # === 6 whole-sequence stats: mean, std, min, max, range, slope ===
    stats.append(float(np.mean(valid_angles)))
    stats.append(float(np.std(valid_angles)))
    stats.append(float(np.min(valid_angles)))
    stats.append(float(np.max(valid_angles)))
    stats.append(float(np.ptp(valid_angles)))

    # slope: linear regression of angle vs frame index
    valid_indices = np.where(valid_mask)[0]
    if len(valid_indices) > 1:
        x = valid_indices.astype(np.float64)
        y = valid_angles.astype(np.float64)
        slope = float(np.polyfit(x, y, 1)[0])
    else:
        slope = 0.0
    stats.append(slope)

    # === 3 phases × 3 stats (mean, std, angular_velocity) ===
    whole_mean = stats[0]  # fallback for empty phases
    for phase_name in ["descent", "bottom", "ascent"]:
        phase_indices = phases.get(f"{phase_name}_idx", [])

        if not phase_indices:
            # No frames in this phase — match training fallback
            stats.extend([whole_mean, 0.0, 0.0])
            continue

        phase_angles = angle_series[phase_indices]
        phase_valid_mask = (phase_angles > 0) & (phase_angles < 220) & np.isfinite(phase_angles)

        if phase_valid_mask.sum() == 0:
            stats.extend([whole_mean, 0.0, 0.0])
            continue

        phase_valid_angles = phase_angles[phase_valid_mask]

        # Phase mean
        stats.append(float(np.mean(phase_valid_angles)))
        # Phase std
        stats.append(float(np.std(phase_valid_angles)) if len(phase_valid_angles) > 1 else 0.0)
        # Angular velocity: mean of |diff(angles)|
        if len(phase_valid_angles) > 1:
            phase_velocity = np.abs(np.diff(phase_valid_angles))
            stats.append(float(np.mean(phase_velocity)))
        else:
            stats.append(0.0)

    assert len(stats) == 15
    return stats


# ---------------------------------------------------------------------------
# Derived features [147–150] — matches training exactly
# ---------------------------------------------------------------------------

def _derived_features(
    kp: np.ndarray,
    angles_dict: Dict[str, np.ndarray],
    phases: Dict[str, list],
) -> List[float]:
    """
    4 derived biomechanical features matching training notebook:
      [147] bottom_trunk_wobble: MAD of trunk angle in bottom phase
      [148] knee_asymmetry_mean: mean |left_knee - right_knee| (valid only)
      [149] bottom_knee_asymmetry: same but bottom phase only
      [150] trunk_forward_lean: mean(|trunk_angles|) (deviation from vertical)
    """
    T = kp.shape[0]
    bottom_idx = phases.get("bottom_idx", [])

    # Trunk angle
    trunk_angles = angles_dict.get("trunk_angle", np.zeros(T))

    # [147] bottom_trunk_wobble: MAD of trunk angle in bottom phase (NOT std)
    if len(bottom_idx) > 1:
        bottom_trunk = trunk_angles[bottom_idx]
        valid_bottom = bottom_trunk[(bottom_trunk > 0) & (bottom_trunk < 200)]
        if len(valid_bottom) > 1:
            bottom_trunk_wobble = float(np.mean(np.abs(valid_bottom - np.mean(valid_bottom))))
        else:
            bottom_trunk_wobble = 0.0
    else:
        bottom_trunk_wobble = 0.0

    # Knee angles for asymmetry
    left_knee = angles_dict.get("left_knee_angle", np.zeros(T))
    right_knee = angles_dict.get("right_knee_angle", np.zeros(T))

    # Valid mask for BOTH knees (matches training)
    valid_mask_both = (
        (left_knee > 0) & (left_knee < 220) &
        (right_knee > 0) & (right_knee < 220) &
        np.isfinite(left_knee) & np.isfinite(right_knee)
    )

    if valid_mask_both.sum() > 0:
        knee_asymmetry_mean = float(np.mean(
            np.abs(left_knee[valid_mask_both] - right_knee[valid_mask_both])
        ))

        # [149] bottom_knee_asymmetry
        if len(bottom_idx) > 0:
            bottom_mask = np.zeros(T, dtype=bool)
            bm_indices = [idx for idx in bottom_idx if idx < T]
            bottom_mask[bm_indices] = True
            bottom_valid = valid_mask_both & bottom_mask
            if bottom_valid.sum() > 0:
                bottom_knee_asymmetry = float(np.mean(
                    np.abs(left_knee[bottom_valid] - right_knee[bottom_valid])
                ))
            else:
                bottom_knee_asymmetry = knee_asymmetry_mean
        else:
            bottom_knee_asymmetry = knee_asymmetry_mean
    else:
        knee_asymmetry_mean = 0.0
        bottom_knee_asymmetry = 0.0

    # [150] trunk_forward_lean: mean of |trunk_angles| (deviation from vertical)
    valid_trunk = trunk_angles[(trunk_angles > 0) & (trunk_angles < 200)]
    if len(valid_trunk) > 0:
        trunk_forward_lean = float(np.mean(np.abs(valid_trunk)))
    else:
        trunk_forward_lean = 0.0

    return [bottom_trunk_wobble, knee_asymmetry_mean, bottom_knee_asymmetry, trunk_forward_lean]


# ---------------------------------------------------------------------------
# Diagnostic: angle validity ratios and outlier counts
# ---------------------------------------------------------------------------

def compute_angle_validity(keypoints: np.ndarray) -> Dict[str, float]:
    """
    Compute the fraction of valid frames for each key angle.

    Valid = (angle > 0) & (angle < 220) & isfinite.
    Returns dict: {angle_name: valid_ratio} where ratio is in [0, 1].
    """
    T = keypoints.shape[0]
    if T == 0:
        return {"trunk_angle": 0.0, "left_knee_angle": 0.0,
                "right_knee_angle": 0.0, "left_hip_angle": 0.0}

    angles_dict = _compute_key_angles(keypoints)
    result = {}
    for name in ["trunk_angle", "left_knee_angle", "right_knee_angle", "left_hip_angle"]:
        series = angles_dict.get(name, np.zeros(T))
        valid_mask = (series > 0) & (series < 220) & np.isfinite(series)
        result[name] = float(valid_mask.sum()) / T
    return result


def compute_outlier_counts(
    scaled_features: np.ndarray,
) -> Dict[str, int]:
    """
    Count features with |z| > 3 and |z| > 6 in already-scaled feature vector.
    """
    abs_z = np.abs(scaled_features)
    return {
        "count_z3": int((abs_z > 3).sum()),
        "count_z6": int((abs_z > 6).sum()),
    }


# ---------------------------------------------------------------------------
# Scaler
# ---------------------------------------------------------------------------

def _apply_scaler(features: np.ndarray, artifacts_dir: Optional[Path]) -> np.ndarray:
    """Load and apply StandardScaler if the artifact exists."""
    if artifacts_dir is None:
        artifacts_dir = Path(__file__).parent / "artifacts"

    scaler_path = artifacts_dir / _SCALER_FILENAME
    cache_key = str(scaler_path)

    if cache_key not in _scaler_cache:
        if scaler_path.exists():
            try:
                import joblib
                scaler = joblib.load(scaler_path)
                _scaler_cache[cache_key] = scaler
                logger.info("Loaded PostureV1 feature scaler from %s", scaler_path)
            except Exception as e:
                logger.warning("Failed to load scaler from %s: %s", scaler_path, e)
                _scaler_cache[cache_key] = None
        else:
            logger.debug(
                "No scaler artifact at %s — features will be used unscaled.",
                scaler_path,
            )
            _scaler_cache[cache_key] = None

    scaler = _scaler_cache[cache_key]
    if scaler is not None:
        try:
            return scaler.transform(features.reshape(1, -1)).flatten()
        except Exception as e:
            logger.warning("Scaler transform failed, using raw features: %s", e)

    return features
