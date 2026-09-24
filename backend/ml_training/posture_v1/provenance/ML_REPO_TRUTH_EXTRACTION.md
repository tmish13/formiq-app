# ML Repo Truth Extraction — App Wiring Reference
**Source:** `squat_pipeline_posture_stability_goodform_REBUILT.ipynb`
**Best checkpoint:** `runs/best_cnn_lstm_binary_enhanced_cw_f0.5_0.742.pt` (val F0.5=0.742)
**Results JSON:** `runs/cnn_lstm_binary_enhanced_cw_results.json`

---

## 1. SEQUENCE STANDARDIZATION (how you get exactly 300 frames)

**Policy: first-300 truncation + zero-pad tail.**  There is NO resampling, no stride, no center-crop.

### Keypoint loading (`load_keypoints_from_file`)
- Reads JSON → `[T_raw, 33, 4]` (x, y, z, visibility)
- Frames with != 33 landmarks are **zero-filled** (tolerant mode), not dropped
- Only raises if ALL frames are zero

### Cleaning (`clean_keypoints`)
- Trims leading/trailing all-zero frames
- Linearly interpolates internal zero frames (per-joint, per-coordinate)
- Rejects if internal missing rate > 10%
- Output: `[T_cleaned, 33, 4]`

### Feature extraction path (151D features)
```python
keypoints = load_keypoints_from_file(path)           # [T_raw, 33, 4]
keypoints, _ = clean_keypoints(keypoints)             # [T_cleaned, 33, 4]
if len(keypoints) > 300:
    keypoints = keypoints[:300]                       # HARD TRUNCATE first 300
```

### CNN-LSTM __getitem__ path (raw keypoints for the model)
```python
keypoints = load_keypoints_from_file(path)            # [T_raw, 33, 4]
keypoints, _ = clean_keypoints(keypoints)             # [T_cleaned, 33, 4]
keypoints = keypoints[:, :, :3]                       # DROP VISIBILITY → [T, 33, 3]
sequence_length = min(keypoints.shape[0], 300)        # true length BEFORE padding

if keypoints.shape[0] < 300:
    pad = np.zeros((300 - keypoints.shape[0], 33, 3))
    keypoints_padded = np.concatenate([keypoints, pad])  # ZERO-PAD TAIL
else:
    keypoints_padded = keypoints[:300]                    # HARD TRUNCATE first 300

# Returns:
#   keypoints:       [300, 33, 3]  float32  (padded/truncated)
#   sequence_length: scalar int    (true frame count, used for pack_padded_sequence)
```

### Collate function
```python
keypoints_padded = pad_sequence(keypoints_list, batch_first=True, padding_value=0.0)
# → [B, max_seq_in_batch, 33, 3]
sequence_lengths = [item['sequence_length'] for item in batch]  # [B] true lengths
```

### In the model forward pass
```python
packed_input = pack_padded_sequence(
    cnn_features, sequence_lengths.cpu(),
    batch_first=True, enforce_sorted=False
)
```

**App must replicate:** load → clean → drop visibility → first-300 truncate/zero-pad → track true length.

---

## 2. FEATURE NAMES LIST (151 items, exact order)

### 87D baseline block (indices 0–86)
```
[0..32]   joint{0..10}_{x,y,z}_mean  — np.mean(coords, axis=0).flatten()[:33]  (11 joints × 3 coords)
[33..65]  joint{0..10}_{x,y,z}_std   — np.std(coords, axis=0).flatten()[:33]   (11 joints × 3 coords)
[66..86]  joint{0..6}_{x,y,z}_range  — max-min range per coordinate for joints 0–6 (7 joints × 3 dims = 21 features)
```

> **CORRECTED 2026-09-19.** This block previously read `joint{0..32}_x_mean —
> np.mean(coords, axis=0)[:, 0]`, i.e. "x-coordinate means for each of 33 joints".
> That is **not** what the code does. `joint_means` is `[33, 3]`; a row-major
> `.flatten()` yields `j0_x, j0_y, j0_z, j1_x, …`, so `[:33]` takes **joints 0–10
> × (x, y, z)**. Both readings give 33 values, which is why the error survived.
>
> Two consequences worth knowing:
> 1. The serving implementation (`app/ml/posture_v1/features_151d.py`) always
>    matched the real behaviour, so there was **no train/serve skew** — this was a
>    documentation defect only. Verified and pinned by
>    `backend/tests/unit/test_train_serve_parity.py`, which recomputes all 87
>    static features from their own names.
> 2. MediaPipe pose landmarks 0–10 are NOSE, both eyes, both ears and both mouth
>    corners; body landmarks start at index 11 (LEFT_SHOULDER). Indices 0–86 are
>    therefore **87 raw face-landmark coordinates with zero body joints** — 57% of
>    the model's tabular input. All squat biomechanics live in the 64 temporal
>    features. Measured impact of removing the whole face block: −0.052 F1
>    (see `bench/results/2026-09-19-face-block-ablation.md`).

Where `coords = keypoints[:, :, :3]` (shape `[T, 33, 3]` after visibility is dropped).

**Construction code:**
```python
features = []
joint_means = np.mean(coords, axis=0)  # [33, 3]
joint_stds  = np.std(coords, axis=0)   # [33, 3]

features.extend(joint_means.flatten()[:33])   # joints 0–10 × (x,y,z) → 33D
features.extend(joint_stds.flatten()[:33])    # joints 0–10 × (x,y,z) → 33D

for j in range(7):                            # joints 0–6
    for dim in range(3):                      # x, y, z
        features.append(max - min for joint j, dim)  # → 21D

rep_features_87d = np.array(features[:87])    # clamp to exactly 87
```

### 64D temporal angle block (indices 87–150)

Four angles computed per frame, then summarized:
- `left_knee_angle`  (joints: hip=23, knee=25, ankle=27)
- `right_knee_angle` (joints: hip=24, knee=26, ankle=28)
- `trunk_angle`      (joints: hip_center=(23+24)/2, shoulder_center=(11+12)/2)
- `left_hip_angle`   (joints: shoulder=11, hip=23, knee=25)

**For each of the 4 angles — 15 features (indices within temporal block):**
```
{angle}_mean                          # whole sequence mean
{angle}_std                           # whole sequence std
{angle}_min                           # whole sequence min
{angle}_max                           # whole sequence max
{angle}_range                         # max - min
{angle}_slope                         # linear fit slope
{angle}_descent_mean                  # descent phase mean
{angle}_descent_std                   # descent phase std
{angle}_descent_angular_velocity      # descent phase avg |diff|
{angle}_bottom_mean                   # bottom phase mean
{angle}_bottom_std                    # bottom phase std
{angle}_bottom_angular_velocity       # bottom phase avg |diff|
{angle}_ascent_mean                   # ascent phase mean
{angle}_ascent_std                    # ascent phase std
{angle}_ascent_angular_velocity       # ascent phase avg |diff|
```

**4 special posture features (last 4, indices 147–150):**
```
bottom_trunk_wobble          # mean |deviation from mean| of trunk angle during bottom phase
knee_asymmetry_mean          # mean |left_knee - right_knee| over whole sequence
bottom_knee_asymmetry        # same, but only during bottom phase
trunk_forward_lean           # mean |trunk_angle| over whole sequence
```

**Complete ordered list (87 + 60 + 4 = 151):**
```
Index  Feature
-----  -------
0      joint0_x_mean
1      joint0_y_mean
2      joint0_z_mean
3      joint1_x_mean
...
32     joint10_z_mean
33     joint0_x_std
34     joint0_y_std
35     joint0_z_std
...
65     joint10_z_std
66     joint0_x_range
67     joint0_y_range
68     joint0_z_range
69     joint1_x_range
70     joint1_y_range
71     joint1_z_range
...
84     joint6_x_range
85     joint6_y_range
86     joint6_z_range
87     left_knee_angle_mean
88     left_knee_angle_std
89     left_knee_angle_min
90     left_knee_angle_max
91     left_knee_angle_range
92     left_knee_angle_slope
93     left_knee_angle_descent_mean
94     left_knee_angle_descent_std
95     left_knee_angle_descent_angular_velocity
96     left_knee_angle_bottom_mean
97     left_knee_angle_bottom_std
98     left_knee_angle_bottom_angular_velocity
99     left_knee_angle_ascent_mean
100    left_knee_angle_ascent_std
101    left_knee_angle_ascent_angular_velocity
102    right_knee_angle_mean
...    (same 15 pattern for right_knee_angle)
116    right_knee_angle_ascent_angular_velocity
117    trunk_angle_mean
...    (same 15 pattern for trunk_angle)
131    trunk_angle_ascent_angular_velocity
132    left_hip_angle_mean
...    (same 15 pattern for left_hip_angle)
146    left_hip_angle_ascent_angular_velocity
147    bottom_trunk_wobble
148    knee_asymmetry_mean
149    bottom_knee_asymmetry
150    trunk_forward_lean
```

---

## 3. CHECKPOINT SAVING FORMAT

```python
torch.save({
    'epoch': best_epoch,                              # int
    'model_state_dict': best_model_state,             # OrderedDict
    'optimizer_state_dict': optimizer.state_dict(),    # OrderedDict
    'val_f0_5': best_val_f0_5,                        # float
    'history': history,                                # dict of lists
    'use_class_weights': USE_CLASS_WEIGHTS,            # bool (True)
    'weight_decay': ENHANCED_WEIGHT_DECAY,             # float (5e-4)
    'model_config': {
        'sequence_length': 300,
        'num_joints': 33,
        'joint_dim': 3,
        'feature_dim': 151,
        'cnn_channels': [32, 64],
        'lstm_hidden': 96,
        'mlp_dims': [256, 128],
        'output_dim': 2,
        'cnn_dropout': 0.4,
        'mlp_dropout': 0.4
    }
}, checkpoint_path)
```

**Filename pattern:** `best_cnn_lstm_binary_enhanced_cw_f0.5_{val_f05:.3f}.pt`

**To load:**
```python
ckpt = torch.load(path, map_location='cpu', weights_only=False)
# weights_only=False needed because history contains numpy scalars
config = ckpt['model_config']
model = BinarySquatCNNLSTM(**config)
model.load_state_dict(ckpt['model_state_dict'])
model.eval()
```

**State dict layer map (38 keys):**
```
cnn_1d.0.weight:   [32, 99, 5]     # Conv1d(99→32, k=5)
cnn_1d.4.weight:   [64, 32, 5]     # Conv1d(32→64, k=5)
lstm.weight_ih_l0: [384, 64]       # LSTM layer 0 (384 = 4×96)
lstm.weight_ih_l1: [384, 96]       # LSTM layer 1
fusion_mlp.0.weight: [256, 247]    # Linear(96+151=247 → 256)
fusion_mlp.4.weight: [128, 256]    # Linear(256 → 128)
fusion_mlp.8.weight: [2, 128]      # Linear(128 → 2) output logits
```

---

## 4. MODEL CLASS DEFINITION + FORWARD SIGNATURE

### BinarySquatCNNLSTM

```python
class BinarySquatCNNLSTM(nn.Module):
    def __init__(self,
                 sequence_length=300,
                 num_joints=33,
                 joint_dim=3,
                 feature_dim=151,        # FEATURE_DIM_BINARY
                 cnn_channels=[32, 64],
                 lstm_hidden=96,
                 mlp_dims=[256, 128],
                 output_dim=2,
                 cnn_dropout=0.4,
                 mlp_dropout=0.4):
```

### Forward signature
```python
def forward(self, keypoints, rep_features, sequence_lengths):
    """
    Args:
        keypoints:        [B, T, 33, 3]  padded keypoint sequences (NO visibility)
        rep_features:     [B, 151]        enhanced features (NORMALIZED by train scaler)
        sequence_lengths: [B]             true frame counts (for pack_padded_sequence)

    Returns:
        logits:           [B, 2]          raw logits [good_form_logit, posture_fault_logit]
    """
```

### Forward data flow
```
keypoints [B, 300, 33, 3]
    → view [B, 300, 99]
    → transpose [B, 99, 300]
    → Conv1d(99→32, k=5, pad=2) → ReLU → BN → Dropout(0.4)
    → Conv1d(32→64, k=5, pad=2) → ReLU → BN → Dropout(0.4)
    → transpose [B, 300, 64]
    → pack_padded_sequence(sequence_lengths)
    → LSTM(64→96, 2 layers, dropout=0.3)
    → h_n[-1] → lstm_output [B, 96]

rep_features [B, 151]

cat([lstm_output, rep_features]) → [B, 247]
    → Linear(247→256) → ReLU → BN → Dropout(0.4)
    → Linear(256→128) → ReLU → BN → Dropout(0.4)
    → Linear(128→2) → logits [B, 2]
```

### Inference
```python
with torch.no_grad():
    logits = model(keypoints, rep_features, sequence_lengths)  # [B, 2]
    probs = torch.sigmoid(logits)                              # [B, 2]
    posture_fault_prob = probs[:, 1]                           # [B]
    is_fault = (posture_fault_prob >= threshold)                # threshold from val sweep
```

**Threshold:** stored in results JSON as `best_threshold: 0.525`

---

## 5. INPUT NORMALIZATION

### Keypoint coordinates
- **NO normalization.** Raw MediaPipe normalized coordinates (0–1 range) used directly.
- No pelvis centering, no torso-length scaling, no z-normalization.
- Visibility channel **dropped** before model input (only x, y, z used).

### 151D features (rep_features)
- **Normalized** using a train-only StandardScaler:
```python
normalizer = {
    'mean': scaler.mean_,     # [151] fitted on train videos only
    'std':  scaler.scale_,    # [151] fitted on train videos only
}
normalized = (features - mean) / (std + 1e-8)
```
- The normalizer is fitted in `fit_training_normalizer_enhanced()` on all successfully extracted training videos.
- **App must ship the same mean/std arrays** or refit identically.

---

## 6. PostureMLP (alternative simpler model)

```python
class PostureMLP(nn.Module):
    def __init__(self, input_dim=151, hidden_dims=(128, 64), dropout=0.3):
        # Linear(151→128) → ReLU → Dropout(0.3)
        # Linear(128→64)  → ReLU → Dropout(0.3)
        # Linear(64→2)    → logits [good_form, posture_fault]

    def forward(self, rep_features):  # [B, 151] → [B, 2]
```
- Takes ONLY the 151D features (no raw keypoints, no sequence_lengths).
- Same normalization as CNN-LSTM rep_features.
- No checkpoint saved to disk (lives in `model_enhanced` variable only).

---

## 7. PHASE SEGMENTATION (used for temporal features)

```python
# Uses hip center y-position (joints 23+24 averaged)
# Smoothed with Savitzky-Golay filter
# Bottom = argmax(hip_y_smoothed) ± 10% of frames
# Descent = start → bottom_start
# Ascent  = bottom_end → end
```

**MediaPipe joint indices used:**
- 11: left_shoulder, 12: right_shoulder
- 23: left_hip, 24: right_hip
- 25: left_knee, 26: right_knee
- 27: left_ankle, 28: right_ankle

---

## CRITICAL APP WIRING CHECKLIST

| # | Check | Match requirement |
|---|-------|-------------------|
| 1 | Frame policy | First-300 truncate + zero-pad tail, track true length |
| 2 | Visibility | DROP channel → [T, 33, 3] not [T, 33, 4] |
| 3 | Feature order | Exactly 87D base + 64D temporal as listed above |
| 4 | Normalization | Ship train-fitted mean[151] + std[151], apply `(x-mean)/(std+1e-8)` |
| 5 | Checkpoint load | `weights_only=False`, use `model_config` dict to construct model |
| 6 | Forward call | `model(keypoints_tensor, features_tensor, lengths_tensor)` — 3 args |
| 7 | Output interpretation | `sigmoid(logits[:, 1])` = posture_fault probability |
| 8 | Threshold | 0.525 from validation sweep (store as config, not hardcoded) |
| 9 | Batch dim | Even for single video, unsqueeze to `[1, ...]` |
| 10 | Device | Match model device (model.to(device) before inference) |
