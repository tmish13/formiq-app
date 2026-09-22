# Depth-label inventory, one-rep confirmation, and the fitting decision

**Date:** 2026-09-22 · **Branch:** `audit/phase2-depth-rule`
**Scope:** full sweep of `~/Desktop/Squat More`, every nested folder and file type

## 1. Every depth label that exists

| file | contents | depth label? |
|---|---|---|
| `Labeled_Dataset/Shallow_Squat_Error_Dataset/labels_shallow_depth.json` | 3,611 per-frame `{video}_{frame} → 0\|1` | **YES — the only one** |
| `…/Shallow_Squat_Error_Dataset/splits/{train,val,test}_ids.json` | 2,542 / 529 / 540 frame ids | split assignment only |
| `…/Shallow_Squat_Error_Dataset/ReadMe.md.docx` | *"0: no error 1: erroneous"* | the official semantics |
| `Labeled_Dataset/Labels/error_knees_forward.json` | 1,623 videos → `[[start, end], …]` sec | no — **knee** error |
| `Labeled_Dataset/Labels/error_knees_inward.json` | 1,623 videos → `[[start, end], …]` sec | no — **knee** error |
| `Labeled_Dataset/Labels/ReadMe.md.txt` | *"[Video number]: [error_start_time, error_end_time]"* | format doc |
| `Labeled_Dataset/Splits/{train,val,test}_keys.json` | 1,136 + val + test video ids | split only |
| `Labeled_Dataset/Splits/traj_nan.json` | 19 bad-trajectory files | exclusion list |
| `Labeled_Dataset/processed_videos/processing_summary.json` | 1,711 × `{video_name, path, frame_count, keypoints_path}` | no labels |
| `Unlabeled_Dataset/bar_trajectories_raw/*.json` | 4,970 × bar-height series | **unlabeled subset** |
| `Explanation.txt` | *"Fitness-AQA Dataset"* provenance | — |

Directory sizes: `Labeled_Dataset/videos` 1,724 · `processed_videos/keypoints` 1,739
(+ an identical `keypoints copy`) · `crops_unaligned` 3,738 · `Unlabeled_Dataset/videos` 4,966.

**There are no CSV files anywhere in the tree.**

### There is exactly one depth annotation, surfaced twice

`labels_shallow_depth.json` and the ML repo's `depth_frames` / `depth_fault` class are the **same
annotation** — 1552/1552 = 100.0% identity, measured in
`bench/results/2026-09-22-label-polarity.md`. The video-level `depth_fault` class is derived from
the per-frame marks, not independent of them.

So there is no second opinion to cross-check against. Any agreement number is agreement with
*this* annotator's judgement, not with ground truth about biomechanics.

## 2. One rep per video — confirmed three ways

| evidence | value |
|---|---|
| clip length | median **106 frames / 3.5 s** (min 32, max 405) |
| span of marked frames, first → last | median **7 frames (0.23 s)**, max 40 |
| bar trajectory shape | single descent-and-return: `302 → 165 → 201` |

A multi-rep clip would spread marked frames across seconds, not 0.23 s. The 1–6 marked frames per
video are a tight cluster around **one** bottom.

**Consequence — a large simplification.** Rep segmentation collapses to
`argmax(smoothed hip_y)`. Deleted from the design: prominence thresholds, minimum rep separation,
the bottom-band contiguous-run search, `agg_mode`, and `worst_confident` cross-rep aggregation.

## 3. The fitting decision: criterion by definition, measurement calibrated

**Parallel is a definition, not a hyperparameter.** At depth ⟺ the femur reaches horizontal ⟺
`hip_y ≥ knee_y` at the bottom (image coords, y down). The threshold is **0**, and it is 0 because
that is what parallel *means* — not because 0 maximised F1 on 1,115 frames.

**But the measurement needs correcting**, for two physical reasons:

1. **Landmark offset.** MediaPipe's landmark 23/24 is not the anatomical hip crease, and 25/26 is
   not the top of the knee. There is a systematic offset between "hip landmark level with knee
   landmark" and "hip crease level with knee top".
2. **View foreshortening.** Off-axis camera compresses the femur in the image, so 0° in the image
   is not 0° in reality.

**What gets fitted, and what does not:**

```
AT_DEPTH  ⟺  (hip_y − knee_y)/S + offset(view) ≥ 0
                                   ^^^^^^^^^^^      ^
                                   FITTED           NOT FITTED — stays 0 = parallel
```

- **Fitted (train split only):** the landmark-offset correction and its view dependence.
- **Not fitted:** the decision threshold, which is 0 by definition.
- **Not fitted:** the abstain policy is driven by landmark visibility and view confidence —
  physical quantities — not tuned to hit a target precision.

**Report the offset's magnitude.** If it is large, that is itself a finding about MediaPipe's
landmark placement on squatting subjects, and worth stating plainly. If it is near zero, the
definitional rule needed no help and that is a cleaner result still.

**Why this is the right call here.** The labels are a single annotator's judgement, with no
second opinion available (§1). Fitting a decision threshold to them would encode that annotator's
private notion of "parallel" into a production verdict and call it depth. Fitting only the
measurement keeps the criterion public and checkable, and leaves disagreements with the labels
*diagnostic* rather than *minimised*.

`P_target = 0.85` on `AT_DEPTH` is therefore a **measurement**, not a target to tune toward. If
the definitional rule misses it, the gap gets reported along with why.

## 4. Consequence for the provenance gate (Stage 0b)

The gate becomes **central rather than precautionary**. The entire calibration is now a landmark
offset measured on dataset keypoints; if the dataset's pose pass differs from the container's
MediaPipe, that offset does not transfer and the rule is mis-calibrated in production by exactly
the amount the two passes disagree.

So Stage 0b must measure not just correlation but **bias** — the Bland–Altman mean difference on
`(hip_y − knee_y)/S` specifically — because that bias adds directly to the fitted offset.

## Reproduce

```bash
python bench/label_polarity_probe.py           # §1 semantics, §2 marked-frame spans
find ~/Desktop/"Squat More" -type f \( -name '*.csv' -o -name '*.json' -o -name '*.txt' \) \
  | grep -v /frames/ | grep -v /keypoints
```
