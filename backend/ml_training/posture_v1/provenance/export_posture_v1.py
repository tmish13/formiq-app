#!/usr/bin/env python3
"""
Export posture_v1 production artifacts from ML training repo.

Produces:
  artifacts/posture_v1.pt              — checkpoint (model_state_dict + model_config)
  artifacts/posture_v1_scaler.joblib   — StandardScaler fitted on training 151D features
  artifacts/posture_v1_manifest.json   — metadata manifest
"""

import json
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
from scipy.signal import savgol_filter
from sklearn.preprocessing import StandardScaler

# ── Paths ────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent
SPLITS_FILE = PROJECT_ROOT / "data/squat_processed/user_level_multilabel_splits.json"
LABELS_FILE = PROJECT_ROOT / "data/squat_processed/balanced_3class_frame_labels.json"
CHECKPOINT_SRC = PROJECT_ROOT / "runs/best_cnn_lstm_binary_enhanced_cw_f0.5_0.736.pt"
RESULTS_FILE = PROJECT_ROOT / "runs/cnn_lstm_binary_enhanced_cw_results.json"
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"

ARTIFACTS_DIR.mkdir(exist_ok=True)

# ── Output paths ─────────────────────────────────────────────────────────────
CHECKPOINT_DST = ARTIFACTS_DIR / "posture_v1.pt"
SCALER_DST = ARTIFACTS_DIR / "posture_v1_scaler.joblib"
MANIFEST_DST = ARTIFACTS_DIR / "posture_v1_manifest.json"


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 0: Load splits + frame_labels_data, derive training video list
# ═══════════════════════════════════════════════════════════════════════════════

print("=" * 70)
print("POSTURE V1 ARTIFACT EXPORT")
print("=" * 70)

print("\n[0] Loading splits and labels...")

with open(SPLITS_FILE) as f:
    splits_data = json.load(f)

with open(LABELS_FILE) as f:
    frame_labels_data = json.load(f)

train_video_names = splits_data["splits"]["train"]["video_names"]
val_video_names = splits_data["splits"]["validation"]["video_names"]
test_video_names = splits_data["splits"]["test"]["video_names"]

original_train_targets = splits_data["splits"]["train"]["multilabel_targets"]

# Binary transform: keep only [good_form, posture_fault], drop depth_fault
# Then filter [0,0] samples (neither label active)
binary_train_targets = []
filtered_train_names = []
for name, target in zip(train_video_names, original_train_targets):
    gf, pf = target[0], target[1]  # good_form, posture_fault
    if gf == 0 and pf == 0:
        continue  # filter "neither" samples
    filtered_train_names.append(name)
    binary_train_targets.append(pf)  # posture_fault = positive class

train_video_names = filtered_train_names
binary_train_targets = np.array(binary_train_targets, dtype=np.int32)

print(f"   Training videos (after [0,0] filter): {len(train_video_names)}")
print(f"   Positive class (posture_fault): {np.sum(binary_train_targets)}/{len(binary_train_targets)}")


# ═══════════════════════════════════════════════════════════════════════════════
# FEATURE EXTRACTION FUNCTIONS (copied verbatim from notebook cells 3,4,5,12,13)
# ═══════════════════════════════════════════════════════════════════════════════

def load_keypoints_from_file(keypoints_path: str) -> np.ndarray:
    """Load MediaPipe keypoints — tolerant version (zero-fills bad frames)."""
    kp_path = Path(keypoints_path)
    if not kp_path.exists():
        raise FileNotFoundError(f"Keypoints file not found: {keypoints_path}")
    with open(kp_path) as f:
        frames_data = json.load(f)
    if not frames_data:
        raise ValueError(f"Empty keypoints file: {keypoints_path}")
    T = len(frames_data)
    keypoints = np.zeros((T, 33, 4), dtype=np.float32)
    zero_frames = 0
    for t, frame in enumerate(frames_data):
        landmarks = frame.get("landmarks", [])
        if len(landmarks) != 33:
            zero_frames += 1
            continue
        for j, lm in enumerate(landmarks):
            keypoints[t, j, 0] = lm["x"]
            keypoints[t, j, 1] = lm["y"]
            keypoints[t, j, 2] = lm["z"]
            keypoints[t, j, 3] = lm["visibility"]
    if zero_frames == T:
        raise ValueError(f"All {T} frames have missing landmarks in {keypoints_path}")
    return keypoints


def clean_keypoints(keypoints: np.ndarray, max_internal_missing_rate: float = 0.10):
    """Trim leading/trailing zero frames + interpolate internal missing."""
    T = keypoints.shape[0]
    frame_is_zero = np.all(keypoints.reshape(T, -1) == 0, axis=1)
    n_zero = int(np.sum(frame_is_zero))
    if n_zero == 0:
        return keypoints, {"zero_frames_total": 0}
    if n_zero == T:
        raise ValueError("All frames zero")
    first_good = 0
    while first_good < T and frame_is_zero[first_good]:
        first_good += 1
    last_good = T - 1
    while last_good >= 0 and frame_is_zero[last_good]:
        last_good -= 1
    trimmed = keypoints[first_good : last_good + 1].copy()
    T2 = trimmed.shape[0]
    internal_zero = np.all(trimmed.reshape(T2, -1) == 0, axis=1)
    n_internal = int(np.sum(internal_zero))
    if n_internal == 0:
        return trimmed, {"zero_frames_total": n_zero}
    if n_internal / T2 > max_internal_missing_rate:
        raise ValueError(f"Internal missing rate {n_internal/T2:.1%} > {max_internal_missing_rate:.0%}")
    missing_idx = np.where(internal_zero)[0]
    good_idx = np.where(~internal_zero)[0]
    flat = trimmed.reshape(T2, -1)
    for dim in range(flat.shape[1]):
        flat[missing_idx, dim] = np.interp(missing_idx, good_idx, flat[good_idx, dim])
    return flat.reshape(T2, 33, 4), {"zero_frames_total": n_zero, "interpolated": n_internal}


def extract_rep_features_87d(keypoints_path: str, max_seq: int = 300) -> np.ndarray:
    """Baseline 87D features: 87 raw MediaPipe FACE-landmark coordinates.

    CORRECTED 2026-09-19. This docstring previously read "33 x-means + 33 x-stds
    + 21 joint ranges", which is not what the code below does.

        [0:33]   joint{0..10}_{x,y,z}_mean
        [33:66]  joint{0..10}_{x,y,z}_std
        [66:87]  joint{0..6}_{x,y,z}_range

    `joint_means` is [33, 3]; a row-major `.flatten()` yields
    j0_x, j0_y, j0_z, j1_x, ... so `[:33]` takes joints 0-10 x (x, y, z) --
    NOT 33 joints' x-values. Both readings give 33 values, which is why the
    error went unnoticed and was copied into the shipped manifest and into
    ML_REPO_TRUTH_EXTRACTION.md.

    The serving implementation (app/ml/posture_v1/features_151d.py) always
    matched the real behaviour, so there was no train/serve skew.

    Note on composition: MediaPipe landmarks 0-10 are nose, both eyes, both ears
    and both mouth corners; body landmarks start at index 11 (LEFT_SHOULDER).
    This entire 87D block therefore contains ZERO body joints. All squat
    biomechanics live in the 64 temporal features appended later. Measured cost
    of removing the whole block: -0.052 F1 on 50 balanced in-domain fixtures.
    """
    kp = load_keypoints_from_file(keypoints_path)
    kp, _ = clean_keypoints(kp)
    if len(kp) > max_seq:
        kp = kp[:max_seq]
    T = kp.shape[0]
    if T == 0:
        return np.zeros(87, dtype=np.float32)
    coords = kp[:, :, :3]
    features = []
    joint_means = np.mean(coords, axis=0)  # [33, 3]
    joint_stds = np.std(coords, axis=0)
    # Row-major flatten of [33, 3] -> j0_x, j0_y, j0_z, j1_x, ...
    # so [:33] is joints 0-10 x (x, y, z), i.e. FACE landmarks only.
    features.extend(joint_means.flatten()[:33])  # joint{0..10}_{x,y,z}_mean
    features.extend(joint_stds.flatten()[:33])   # joint{0..10}_{x,y,z}_std
    for j in range(7):                           # joints 0-6 = nose + both eyes
        jc = coords[:, j, :]
        for dim in range(3):
            features.append(float(np.max(jc[:, dim]) - np.min(jc[:, dim])))
    arr = np.array(features[:87], dtype=np.float32)
    if len(arr) < 87:
        arr = np.concatenate([arr, np.zeros(87 - len(arr), dtype=np.float32)])
    return np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0)


def segment_squat_phases(keypoints):
    """Segment squat into descent/bottom/ascent using hip center y."""
    T = keypoints.shape[0]
    if T < 10:
        return {
            "descent_idx": list(range(T // 3)),
            "bottom_idx": list(range(T // 3, 2 * T // 3)),
            "ascent_idx": list(range(2 * T // 3, T)),
        }
    try:
        hip_y = (keypoints[:, 23, 1] + keypoints[:, 24, 1]) / 2
        wl = min(11, T // 3 if T // 3 % 2 == 1 else T // 3 + 1)
        wl = max(3, wl)
        hip_smooth = savgol_filter(hip_y, wl, 2) if wl < T else hip_y.copy()
        bottom_frame = int(np.argmax(hip_smooth))
        bw = max(T // 10, 3)
        bs, be = max(0, bottom_frame - bw), min(T, bottom_frame + bw)
        ds, de = 0, bs
        asc_s, asc_e = be, T
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


def compute_key_angles(keypoints):
    """Compute 4 angle time-series from keypoints [T, 33, 4]."""
    T = keypoints.shape[0]
    angles = {}
    try:
        lh, rh = keypoints[:, 23, :2], keypoints[:, 24, :2]
        lk, rk = keypoints[:, 25, :2], keypoints[:, 26, :2]
        la, ra = keypoints[:, 27, :2], keypoints[:, 28, :2]
        ls, rs = keypoints[:, 11, :2], keypoints[:, 12, :2]
        hc, sc = (lh + rh) / 2, (ls + rs) / 2

        def _angle_series(a, vertex, b):
            out = []
            for t in range(T):
                v1, v2 = a[t] - vertex[t], b[t] - vertex[t]
                n1, n2 = np.linalg.norm(v1), np.linalg.norm(v2)
                if n1 > 1e-6 and n2 > 1e-6:
                    c = np.clip(np.dot(v1, v2) / (n1 * n2), -1, 1)
                    out.append(float(np.degrees(np.arccos(c))))
                else:
                    out.append(0.0)
            return np.array(out)

        angles["left_knee_angle"] = _angle_series(lh, lk, la)
        angles["right_knee_angle"] = _angle_series(rh, rk, ra)
        angles["left_hip_angle"] = _angle_series(sc, lh, lk)

        # Trunk angle (vs vertical)
        trunk = []
        vert = np.array([0.0, -1.0])
        for t in range(T):
            tv = sc[t] - hc[t]
            n = np.linalg.norm(tv)
            if n > 1e-6:
                c = np.clip(np.dot(tv, vert) / n, -1, 1)
                trunk.append(float(np.degrees(np.arccos(c))))
            else:
                trunk.append(90.0)
        angles["trunk_angle"] = np.array(trunk)
    except Exception:
        for name in ["left_knee_angle", "right_knee_angle", "trunk_angle", "left_hip_angle"]:
            angles[name] = np.zeros(T)
    return angles


def compute_temporal_angle_features(keypoints):
    """64D temporal feature dict from angle time-series + phase segmentation."""
    T = keypoints.shape[0]
    if T == 0:
        return {}
    angles = compute_key_angles(keypoints)
    phases = segment_squat_phases(keypoints)
    tf = {}
    for aname in ["left_knee_angle", "right_knee_angle", "trunk_angle", "left_hip_angle"]:
        if aname not in angles:
            continue
        s = angles[aname]
        vm = (s > 0) & (s < 220) & np.isfinite(s)
        if vm.sum() < T // 3:
            continue
        va = s[vm]
        tf[f"{aname}_mean"] = float(np.mean(va))
        tf[f"{aname}_std"] = float(np.std(va))
        tf[f"{aname}_min"] = float(np.min(va))
        tf[f"{aname}_max"] = float(np.max(va))
        tf[f"{aname}_range"] = float(np.max(va) - np.min(va))
        tp = np.arange(T)[vm]
        tf[f"{aname}_slope"] = float(np.polyfit(tp, va, 1)[0]) if len(tp) > 1 else 0.0
        for pname in ["descent", "bottom", "ascent"]:
            pidx = phases[f"{pname}_idx"]
            if not pidx:
                tf[f"{aname}_{pname}_mean"] = tf[f"{aname}_mean"]
                tf[f"{aname}_{pname}_std"] = 0.0
                tf[f"{aname}_{pname}_angular_velocity"] = 0.0
                continue
            pa = s[pidx]
            pvm = (pa > 0) & (pa < 220) & np.isfinite(pa)
            if pvm.sum() == 0:
                tf[f"{aname}_{pname}_mean"] = tf[f"{aname}_mean"]
                tf[f"{aname}_{pname}_std"] = 0.0
                tf[f"{aname}_{pname}_angular_velocity"] = 0.0
                continue
            pva = pa[pvm]
            tf[f"{aname}_{pname}_mean"] = float(np.mean(pva))
            tf[f"{aname}_{pname}_std"] = float(np.std(pva)) if len(pva) > 1 else 0.0
            tf[f"{aname}_{pname}_angular_velocity"] = float(np.mean(np.abs(np.diff(pva)))) if len(pva) > 1 else 0.0

    # Special features
    if "trunk_angle" in angles and len(phases["bottom_idx"]) > 1:
        bt = angles["trunk_angle"][phases["bottom_idx"]]
        vbt = bt[(bt > 0) & (bt < 200)]
        tf["bottom_trunk_wobble"] = float(np.mean(np.abs(vbt - np.mean(vbt)))) if len(vbt) > 1 else 0.0
    else:
        tf["bottom_trunk_wobble"] = 0.0

    if "left_knee_angle" in angles and "right_knee_angle" in angles:
        lk, rk = angles["left_knee_angle"], angles["right_knee_angle"]
        both = (lk > 0) & (lk < 220) & (rk > 0) & (rk < 220) & np.isfinite(lk) & np.isfinite(rk)
        if both.sum() > 0:
            tf["knee_asymmetry_mean"] = float(np.mean(np.abs(lk[both] - rk[both])))
            bm = np.zeros(T, dtype=bool)
            bm[phases["bottom_idx"]] = True
            bv = both & bm
            tf["bottom_knee_asymmetry"] = float(np.mean(np.abs(lk[bv] - rk[bv]))) if bv.sum() > 0 else tf["knee_asymmetry_mean"]
        else:
            tf["knee_asymmetry_mean"] = 0.0
            tf["bottom_knee_asymmetry"] = 0.0
    else:
        tf["knee_asymmetry_mean"] = 0.0
        tf["bottom_knee_asymmetry"] = 0.0

    if "trunk_angle" in angles:
        ts = angles["trunk_angle"]
        vt = ts[(ts > 0) & (ts < 200)]
        tf["trunk_forward_lean"] = float(np.mean(np.abs(vt))) if len(vt) > 0 else 0.0
    else:
        tf["trunk_forward_lean"] = 0.0

    return tf


# Canonical 64D temporal feature ordering
EXPECTED_TEMPORAL_FEATURES = []
for _aname in ["left_knee_angle", "right_knee_angle", "trunk_angle", "left_hip_angle"]:
    EXPECTED_TEMPORAL_FEATURES.extend([
        f"{_aname}_mean", f"{_aname}_std", f"{_aname}_min",
        f"{_aname}_max", f"{_aname}_range", f"{_aname}_slope",
    ])
    for _phase in ["descent", "bottom", "ascent"]:
        EXPECTED_TEMPORAL_FEATURES.extend([
            f"{_aname}_{_phase}_mean",
            f"{_aname}_{_phase}_std",
            f"{_aname}_{_phase}_angular_velocity",
        ])
EXPECTED_TEMPORAL_FEATURES.extend([
    "bottom_trunk_wobble", "knee_asymmetry_mean",
    "bottom_knee_asymmetry", "trunk_forward_lean",
])
assert len(EXPECTED_TEMPORAL_FEATURES) == 64


def build_canonical_151d(keypoints_path: str, max_seq: int = 300) -> np.ndarray:
    """Build the 151D feature vector: 87D base + 64D temporal."""
    base_87 = extract_rep_features_87d(keypoints_path, max_seq)
    kp = load_keypoints_from_file(keypoints_path)
    kp, _ = clean_keypoints(kp)
    if len(kp) > max_seq:
        kp = kp[:max_seq]
    tf = compute_temporal_angle_features(kp)
    temporal_vec = np.array(
        [tf.get(fname, 0.0) for fname in EXPECTED_TEMPORAL_FEATURES],
        dtype=np.float32,
    )
    enhanced = np.concatenate([base_87, temporal_vec])
    return np.nan_to_num(enhanced, nan=0.0, posinf=0.0, neginf=0.0)


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 1: Copy checkpoint as posture_v1.pt
# ═══════════════════════════════════════════════════════════════════════════════

print("\n[1] Copying checkpoint as posture_v1.pt...")
assert CHECKPOINT_SRC.exists(), f"Checkpoint not found: {CHECKPOINT_SRC}"
shutil.copy2(CHECKPOINT_SRC, CHECKPOINT_DST)
print(f"   {CHECKPOINT_DST.name}: {CHECKPOINT_DST.stat().st_size:,} bytes")


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 2: Re-derive StandardScaler from training 151D features
# ═══════════════════════════════════════════════════════════════════════════════

print("\n[2] Extracting 151D features from training videos to fit StandardScaler...")

training_features = []
success = 0
fail = 0

for i, video_name in enumerate(train_video_names):
    if video_name not in frame_labels_data["videos"]:
        fail += 1
        continue
    kp_path = frame_labels_data["videos"][video_name].get("keypoints_path")
    if not kp_path or not Path(kp_path).exists():
        fail += 1
        continue
    try:
        feat = build_canonical_151d(kp_path, 300)
        assert feat.shape == (151,), f"Expected (151,), got {feat.shape}"
        training_features.append(feat)
        success += 1
    except Exception as e:
        fail += 1
    if (i + 1) % 100 == 0:
        print(f"   ... {i + 1}/{len(train_video_names)} processed ({success} ok, {fail} fail)")

print(f"   Total: {success} succeeded, {fail} failed out of {len(train_video_names)}")

assert success > 0, "No training features extracted!"
X_train = np.array(training_features)  # [N, 151]
print(f"   Feature matrix shape: {X_train.shape}")

scaler = StandardScaler()
scaler.fit(X_train)

# Validate scaler
assert scaler.mean_.shape == (151,), f"Scaler mean shape: {scaler.mean_.shape}"
assert scaler.scale_.shape == (151,), f"Scaler std shape: {scaler.scale_.shape}"
print(f"   Scaler mean range: [{scaler.mean_.min():.4f}, {scaler.mean_.max():.4f}]")
print(f"   Scaler std range:  [{scaler.scale_.min():.6f}, {scaler.scale_.max():.4f}]")
print(f"   Non-zero std features: {np.sum(scaler.scale_ > 1e-6)}/151")

joblib.dump(scaler, SCALER_DST)
print(f"   {SCALER_DST.name}: {SCALER_DST.stat().st_size:,} bytes")


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 3: Create manifest
# ═══════════════════════════════════════════════════════════════════════════════

print("\n[3] Creating manifest...")

with open(RESULTS_FILE) as f:
    results = json.load(f)

test_results = results["test_results"]

manifest = {
    "model_name": "posture_v1",
    "version": "v1",
    "threshold": 0.525,
    "created_at": datetime.now(timezone.utc).isoformat(),
    "source_checkpoint": CHECKPOINT_SRC.name,
    "input_spec": {
        "keypoints_shape": [300, 33, 3],
        "feature_dim": 151,
        "sequence_policy": "first_300_truncate_zero_pad_tail",
        "uses_sequence_length": True,
        "visibility_dropped": True,
        "keypoint_normalization": "none_raw_mediapipe_0_1",
        "feature_normalization": "standard_scaler_train_only",
    },
    "feature_order_version": "truth_spec_151d_v1",
    "feature_order": {
        # CORRECTED 2026-09-19: these previously read "joint{0..32}_x_mean" /
        # "joint{0..32}_x_std", copied from a mistaken comment in
        # extract_rep_features_87d. flatten()[:33] of a [33,3] array is
        # joints 0-10 x (x,y,z). See that function's docstring.
        "0_32": "joint{0..10}_{x,y,z}_mean (11 FACE joints * 3 = 33)",
        "33_65": "joint{0..10}_{x,y,z}_std (11 FACE joints * 3 = 33)",
        "66_86": "joint{0..6}_{x,y,z}_range (7 FACE joints * 3 = 21)",
        "87_146": "4_angles_x_15_stats (left_knee, right_knee, trunk, left_hip)",
        "147_150": "bottom_trunk_wobble, knee_asymmetry_mean, bottom_knee_asymmetry, trunk_forward_lean",
    },
    "model_config": {
        "sequence_length": 300,
        "num_joints": 33,
        "joint_dim": 3,
        "feature_dim": 151,
        "cnn_channels": [32, 64],
        "lstm_hidden": 96,
        "mlp_dims": [256, 128],
        "output_dim": 2,
        "cnn_dropout": 0.4,
        "mlp_dropout": 0.4,
    },
    "training_metrics": {
        "val_f0_5": results["training"]["best_val_f0_5"],
        "test_precision": test_results["posture_precision"],
        "test_recall": test_results["posture_recall"],
        "test_f1": test_results["posture_f1"],
        "test_f0_5": test_results["posture_f0_5"],
        "test_samples": test_results["labeled_samples"],
        "training_epochs": results["training"]["epochs"],
    },
    "split_sizes": {
        "train": len(train_video_names),
        "val": len(val_video_names),
        "test": len(test_video_names),
    },
    "scaler_file": "posture_v1_scaler.joblib",
    "scaler_stats": {
        "n_training_videos_used": success,
        "mean_range": [float(scaler.mean_.min()), float(scaler.mean_.max())],
        "std_range": [float(scaler.scale_.min()), float(scaler.scale_.max())],
    },
}

with open(MANIFEST_DST, "w") as f:
    json.dump(manifest, f, indent=2)
print(f"   {MANIFEST_DST.name}: {MANIFEST_DST.stat().st_size:,} bytes")


# ═══════════════════════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("ARTIFACT EXPORT COMPLETE")
print("=" * 70)
print(f"\n  posture_v1.pt            : {CHECKPOINT_DST}")
print(f"    size: {CHECKPOINT_DST.stat().st_size:,} bytes")
print(f"\n  posture_v1_scaler.joblib : {SCALER_DST}")
print(f"    size: {SCALER_DST.stat().st_size:,} bytes")
print(f"\n  posture_v1_manifest.json : {MANIFEST_DST}")
print(f"    size: {MANIFEST_DST.stat().st_size:,} bytes")
print()
