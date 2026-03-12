# FormIQ PostureV1 Scoring Pipeline — Complete Reference

> Last updated: 2026-02-24
> Model: PostureV1 CNN-LSTM
> Feature set: 151D temporal biomechanical features
> Canonical entry points: `loader.PostureV1TorchLoader.predict_posture()` and `scoring.compute_full_scores()`

---

## 1. End-to-End Data Flow

```
Video file (MP4)
    │
    ▼
_extract_pose_from_video()          [analysis_tasks.py]
    │   MediaPipe: 33 landmarks per frame {x, y, z, visibility}
    │   pose_data: List[Optional[List[Optional[Dict[str, float]]]]]
    │
    ▼
GATE 1 — Body Visibility Gate       [analysis_tasks._check_body_landmark_visibility]
    │   Joints checked: shoulders (11,12) + hips (23,24) + knees (25,26) + ankles (27,28)
    │   Threshold: mean_body_vis >= 0.3 for >= 50% of frames
    │   FAIL → decision="uncertain", skip all inference
    │
    ▼ (pass)
GATE 2 — Motion Gate                [analysis_tasks._check_minimum_motion]
    │   Joints: hips (23,24), knees (25,26)
    │   Threshold: hip_y_range >= 0.05 OR knee_y_range >= 0.05
    │   FAIL → decision="uncertain", skip all inference
    │
    ▼ (pass)
PostureV1TorchLoader.predict_posture(pose_data)     [loader.py]
    │
    ├── preprocess_pose_data()      [preprocess.py]
    │       parse → [T, 33, 4] (x, y, z, visibility)
    │       clean: trim leading/trailing zeros, interpolate gaps
    │       drop visibility → [T, 33, 3]
    │       hard-truncate at 300 frames OR zero-pad → [300, 33, 3]
    │       sequence_length = min(T_clean, 300)
    │
    ├── GATE 3 — Sequence Length Gate
    │       threshold: sequence_length >= 15 frames (0.5s at 30fps)
    │       FAIL → decision="uncertain"
    │
    ├── GATE 4 — Missing Frame Ratio Gate
    │       threshold: missing_ratio <= 50%
    │       FAIL → decision="uncertain"
    │
    ├── compute_151d_features(keypoints, sequence_length)  [features_151d.py]
    │       151D feature vector — see Section 3 for full layout
    │       apply_scaler=True: StandardScaler from posture_v1_scaler.joblib
    │
    ├── compute_angle_validity(kp_real)
    │       fraction of valid angle frames per angle type
    │
    ├── GATE 5 — Angle Validity Gate
    │       trunk valid ratio >= 10% of padded window
    │       any angle valid ratio >= 5% of padded window
    │       FAIL → decision="uncertain"
    │
    ├── GATE 6 — Outlier Gate (on scaled features)
    │       count |z| > 6: max 40
    │       count |z| > 3: max 100 (of 151 features)
    │       FAIL → decision="uncertain"
    │
    ├── CNN-LSTM Forward Pass (if model loaded)
    │       keypoints [1, 300, 33, 3] → temporal CNN → [1, 64, 300]
    │       → LSTM (2 layers, h=96) → last hidden [1, 96]
    │       concat(lstm_hidden, rep_features[1, 151]) → MLP → logits [1, 2]
    │       prob_fault = sigmoid(logits[:, 1])
    │
    └── returns: {prob_fault, decision, confidence, threshold, quality_flags, ...}

    ▼
GATE 7 — Duration Gate              [analysis_tasks._apply_duration_gate]
    │   n_frames / fps > 6.0s AND is_squat AND decision != "uncertain"
    │   FAIL → decision="uncertain", flag="duration_too_long_single_rep"
    │
    ▼ (pass)
compute_full_scores(prob_fault, features_151d_raw, scaler_mean, scaler_std)  [scoring.py]
    │
    ├── posture_score = int(round(100 * (1 - prob_fault)))   [0–100]
    ├── score_band    = thresholded(posture_score)           [excellent/good/needs_work/poor]
    ├── confidence    = |prob_fault - 0.5| * 2              [0–1, passed through from loader]
    ├── compute_component_scores() → trunk_control, knee_stability, hip_drive
    ├── compute_named_scores()    → torso_stability, knee_symmetry, bottom_control, forward_lean
    └── compute_top_signals()     → up to 5 feature signals with z-scores
```

---

## 2. Score Computation Formulas

### 2.1 posture_score

```
posture_score = int(round(max(0, min(100, 100 × (1 - prob_fault)))))
```

- **Source**: CNN-LSTM `sigmoid(logits[:, 1])` — purely from model output.
- **No fallback**: If model is not loaded, `decision="uncertain"` and `posture_score=None`.
- **AI confidence is NOT used** to compute `posture_score`. Confidence is `|prob_fault - 0.5| × 2` — a metadata field only.

### 2.2 score_band

| posture_score | band        |
|---------------|-------------|
| 90–100        | excellent   |
| 75–89         | good        |
| 60–74         | needs_work  |
| 0–59          | poor        |

These thresholds must stay in sync with `frontend/src/pages/AnalysisPage.tsx::getScoreBand()`.

### 2.3 ai_confidence

```
confidence = |prob_fault - 0.5| × 2
```

- Ranges from 0.0 (decision boundary, maximum uncertainty) to 1.0 (fully certain).
- **Not used** to compute any score. Used only by the frontend to display a confidence banner.

### 2.4 Component scores

Each component score is an average of per-feature z-score conversions:

```
z_feature = (raw_feature - scaler_mean[i]) / scaler_std[i]
per_feature_score = 100 × (1 - clamp(z, -2, 2) + 2) / 4)
  where clamp(z, -2, 2) = max(-2, min(2, z))

component_score = int(round(mean(per_feature_scores)))
```

**Mapping:**

| z (standardised) | per_feature_score |
|-------------------|--------------------|
| -2.0 (2σ better)  | 100                |
|  0.0 (average)    |  50                |
| +2.0 (2σ worse)   |   0                |

Features and their components:

**trunk_control** (→ `torso_stability_score`):
- `bottom_trunk_wobble` — MAD of trunk angle at bottom of squat
- `trunk_angle_std` — std of trunk angle over full rep
- `trunk_angle_descent_std` — trunk angle std during descent
- `trunk_angle_bottom_std` — trunk angle std at bottom
- `trunk_angle_ascent_std` — trunk angle std during ascent

**knee_stability** (→ `knee_symmetry_score`):
- `knee_asymmetry_mean` — mean |left_knee - right_knee| angle
- `bottom_knee_asymmetry` — same, bottom phase only
- `left_knee_angle_std` — left knee angle variability
- `right_knee_angle_std` — right knee angle variability
- `left_knee_angle_bottom_std` — left knee at bottom
- `right_knee_angle_bottom_std` — right knee at bottom

**hip_drive** (→ `bottom_control_score`):
- `left_hip_angle_std` — hip angle variability
- `left_hip_angle_descent_std` — hip angle std during descent
- `left_hip_angle_bottom_std` — hip angle std at bottom
- `left_hip_angle_ascent_std` — hip angle std during ascent

**forward_lean** (→ `forward_lean_score`) — **separate single-feature path**:
- `trunk_forward_lean` — mean(|trunk_angles|), NOT in any component group

> **Invariant**: Each feature belongs to exactly ONE component group.
> `trunk_forward_lean` is excluded from `trunk_control` to avoid double-counting.
> Validated by `tests/unit/test_feature_grouping.py`.

### 2.5 top_signals

Whitelist of 11 features scanned by absolute z-score. Only signals with `z > 0.3` (above average in "bad" direction) are reported. Sorted by |z| descending. Top 5 returned.

---

## 3. 151D Feature Vector Layout

```
[0–32]:   xyz-interleaved means for joints 0–10     (33 features)
           joint_j_x_mean, joint_j_y_mean, joint_j_z_mean for j=0..10
[33–65]:  xyz-interleaved stds for joints 0–10      (33 features)
[66–86]:  joint{0..6}_{x,y,z}_range                 (21 features)
[87–146]: 4 angles × 15 stats                        (60 features)
           angles: left_knee, right_knee, trunk, left_hip
           per angle: mean, std, min, max, range, slope (whole-seq)
                    + (mean, std, angular_velocity) × 3 phases
[147]:    bottom_trunk_wobble (MAD, not std)
[148]:    knee_asymmetry_mean
[149]:    bottom_knee_asymmetry
[150]:    trunk_forward_lean (mean |trunk_angles|)

Total: 33 + 33 + 21 + 60 + 4 = 151
```

All features computed on **real frames only** (not zero-padded tail).

---

## 4. What AI Confidence is NOT

**Confidence is not used to compute**:
- `posture_score` (comes from `prob_fault` only)
- `component_scores` (computed from 151D features + z-scoring)
- `named_scores` (derived from component_scores)
- `top_signals` (computed from z-scores of individual features)

**Confidence is only used**:
- As metadata stored in `form_check.confidence_score`
- In the frontend confidence banner (`< 0.4` → yellow warning; `0.4–0.7` → gray text)
- In `_apply_duration_gate()` to set confidence to 0.0 when duration gate fires

---

## 5. Hardcoding Audit — No Hidden Constants

All scoring constants are documented and justified:

| Constant | Value | Location | Justification |
|----------|-------|----------|---------------|
| `DEFAULT_FAULT_THRESHOLD` | 0.525 | loader.py | From training notebook (truth-spec) |
| `MIN_SEQUENCE_LENGTH` | 15 | loader.py | 0.5s at 30fps — minimum for meaningful statistics |
| `MAX_MISSING_FRAME_RATIO` | 0.50 | loader.py | > 50% missing = unreliable pose data |
| `TRUNK_ANGLE_MIN_VALID_RATIO` | 0.10 | loader.py | Minimum trunk angle coverage (over 300-frame window) |
| `ANY_ANGLE_MIN_VALID_RATIO` | 0.05 | loader.py | Any angle below this is out-of-domain |
| `MAX_OUTLIERS_Z6` | 40 | loader.py | More than 40 features at \|z\| > 6 → out-of-distribution |
| `MAX_OUTLIERS_Z3` | 100 | loader.py | > 100 features at \|z\| > 3 → out-of-distribution |
| `gate_sec` | 6.0 | analysis_tasks.py | Training distribution: 2–5s reps; 6s = safe margin |
| `min_body_vis` | 0.3 | analysis_tasks.py | Visibility < 0.3 = MediaPipe hallucination |
| `min_visible_frame_ratio` | 0.5 | analysis_tasks.py | At least half of frames need body visible |
| `min_hip_y_range` | 0.05 | analysis_tasks.py | < 0.05 y-range = effectively static (no squat) |

Score-band thresholds (90/75/60) are product decisions, not model-derived.

---

## 6. Architectural Gaps and Notes

### 6.1 Two scoring paths (parity gap)

`pipeline.py::run_squat_posture_pipeline()` is the clean public API.
`analysis_tasks.py` calls `predict_posture()` and `compute_full_scores()` directly.

The task has **3 extra gates** not in `pipeline.py`: body visibility, motion, duration.
These gates require data (fps, raw pose_data) that the pipeline doesn't receive.
This duplication is intentional and acceptable; `pipeline.py` is for tests/notebooks.

### 6.2 Legacy temporal ML block

`analysis_tasks.py` also runs `_ai_service_instance.analyze_form_sequence()` (temporal ML).
For squats: temporal score stored in `form_check.results["temporal_ml"]` — NOT in `posture_score`.
PostureV1 is the **sole writer** of `form_check.posture_score` for squats.

### 6.3 Visibility in component scores

Prior to the February 2026 visibility hardening sprint:
- Component scores were computed regardless of individual joint visibility.
- A video with partially occluded knees still received a `knee_symmetry_score`.

Post-sprint: per-component visibility is extracted from raw `pose_data` and applied in
`compute_component_scores()`:
- Component visibility ≥ 0.7 → trusted (no flag)
- Component visibility 0.4–0.7 → partially visible (score computed, flag added)
- Component visibility < 0.4 → unreliable (component score set to `None`, flag added)

---

## 7. Determinism Guarantee

Given identical inputs:
- `run_squat_posture_pipeline(pose_data, loader=same_loader)` → **identical output**
- `compute_full_scores(prob_fault, features_151d, scaler_mean, scaler_std)` → **identical output**

No randomness in any scoring path (verified by `tests/unit/test_scoring_determinism.py`).

Model weights are deterministic at inference (`model.eval()`, `torch.no_grad()`).
Phase segmentation uses Savitzky-Golay filter (deterministic).

---

## 8. How to Explain this to Users / Investors

**"How does FormIQ score my squat?"**

> FormIQ's AI was trained on hundreds of labeled squat videos.
> It learned to distinguish good form from common faults — knee caving, trunk wobble, forward lean.
>
> For each video, it:
> 1. Tracks 33 body landmarks using MediaPipe
> 2. Extracts 151 biomechanical measurements — joint angles, stability across three rep phases, asymmetry between sides
> 3. Runs these through a CNN-LSTM neural network trained on squat videos
> 4. Outputs a fault probability → converted to a 0–100 posture score
> 5. Breaks down the score into four components (torso stability, knee symmetry, bottom control, forward lean)
>
> Every number comes from your actual movement data — nothing is assumed or made up.

**"How do you know the scores are real, not random?"**

> - The posture score is `100 × (1 − model_fault_probability)` — a direct mathematical transformation of the model output.
> - Component scores are derived from standardised feature values (z-scores) relative to the training dataset average.
> - Every scoring formula is deterministic: the same video always produces the same score.
> - We run 700+ automated tests that verify this behaviour on every code change.

**"What if the AI can't see my body properly?"**

> - If fewer than 50% of frames show your full body clearly, we skip scoring entirely and show "Analysis Unavailable" — rather than guessing.
> - If individual body parts (e.g. knees) are partially occluded, those specific component scores are marked as unreliable.
> - We prefer showing no score over showing an incorrect one.
