# The Squat More (Fitness-AQA) dataset's temporal labels, scanned and used once — 2026-09-24

## What the folder contains (`~/Desktop/Squat More`, scanned in full)

| path | what it is |
|---|---|
| `Explanation.txt` | "Fitness-AQA Dataset": per-exercise directories with splits and labels; barbell trajectories for the unlabeled subset |
| `Labeled_Dataset/videos/` | 1,725 `.mp4` (the corpus; 1,487 are in our content-level splits after de-duplication) |
| `Labeled_Dataset/Labels/error_knees_forward.json` | **1,623 videos → list of `[start_s, end_s]` intervals**, empty = no error (format: `Labels/ReadMe.md.txt`) |
| `Labeled_Dataset/Labels/error_knees_inward.json` | same format, knee valgus |
| `Labeled_Dataset/Splits/{train,val,test}_keys.json`, `traj_nan.json` | Fitness-AQA's own splits: 1,136 / 243 / 244 |
| `Labeled_Dataset/processed_videos/keypoints/` (+ an identical `keypoints copy/`) | 1,739 per-video JSON: `[{frame_index, landmarks[33]{x,y,z,visibility}}, …]` — the earlier pipeline's pose pass (Stage 0b gate: r 0.91–0.94 against the container's MediaPipe, `2026-09-22-keypoint-provenance.md`; not the serving pass) |
| `Labeled_Dataset/processed_videos/frames/` | 203,277 `.jpg`, one per frame |
| `Labeled_Dataset/Shallow_Squat_Error_Dataset/` | **per-frame** binary depth labels: `labels_shallow_depth.json` (3,611 frame ids `<video>_<frame>` → 0/1), 3,738 frame crops, its own frame-level splits 2,542 / 529 / 540 |
| `Unlabeled_Dataset/` | 4,967 videos + 4,970 barbell y-trajectory JSONs (one float per frame) |
| `squat_pipeline_…_REBUILT.ipynb` / `.md` | an older copy of the trainer (2026-02-06); the executed one is imported under `backend/ml_training/` |

So the fault labels are **temporal**: a knees-forward error is a start and an end time, which is a
frame range once multiplied by fps. The corpus flag every model here was trained on is
`len(intervals) > 0` (traced in ML_AUDIT §2.3: `posture_fault` ≡ knees_forward ∪ knees_inward
non-empty, 99.4 %; `stability_fault` ≡ knees_inward; `depth_fault` ≡ any frame labelled 1). The
notebook pipeline expanded the intervals into per-frame arrays (`frame_labels` in
`balanced_3class_frame_labels.json`) and then collapsed every video to one class. **The timing
and the duration of the intervals were never used, by the model or by any evaluation.**

Interval facts (all 1,623 labelled videos): knees-forward present in 1,109 (68.3 %), median 1
interval per video (max 3), median duration 1.35 s (IQR 0.98–1.99, max 8.6 s); knees-inward present
in 232 (14.3 %), median 1.26 s. Both faults: 192; forward only: 917; inward only: 40; neither: 474.
Where the serving cache gives the clip length (n = 905), the knees-forward intervals cover a median
41 % of the clip (IQR 29–56 %); only 1.9 % of clips are in error for ≥ 80 % of their length.
Our content-level test split shares 34 of its 196 videos with Fitness-AQA's official test list;
129 of our train videos are in their test list (we re-split by content hash after de-duplication).

## Command

```bash
# one row per content hash from form_checks.results (serving pose pass pp1_f9850424580ae186): the
# knees-forward rule's decision / peak_time_sec / view and posture_v1.prob_fault, joined to videos.filename
psql ... \copy (...) to kf_export.csv        # query in the session log; 1,164 judged videos
docker run ... deployment-worker:latest python /repo/bench/interval_labels.py --export kf_export.csv \
  --labels "~/Desktop/Squat More/Labeled_Dataset/Labels" --cache bench/cache/keypoints_live \
  --splits bench/results/content_level_splits.json --test-names bench/results/retrain/test_clip_names.txt
```

The test split is excluded by name (both our content-level test and `test_clip_names.txt`); no test
read happened. Population: 972 judged videos with Fitness-AQA labels, 769 in our train, 190 in our
validation, 13 withheld.

## Raw output

```
judged videos: 1164; after excluding the test split by name and videos without Fitness-AQA labels: 972
of which in our content-level train: 769, validation: 190, unassigned/withheld: 13

## 1. Knees-forward rule timing vs the labelled intervals (train+validation)
OBSERVED with a peak time: 436; of those with >=1 labelled interval: 330
peak inside a labelled interval (±0.25s): 238/330 = 0.721  95% Wilson [0.670, 0.767]
|peak - nearest interval midpoint| s: median 0.57, p75 1.30, p90 1.63
chance level (interval coverage of the clip, ±tol, mean over the same videos): 0.595  (n=330)
video level: P(OBSERVED | interval) = 330/641 = 0.515;  P(OBSERVED | no interval) = 106/331 = 0.320
by view: {'oblique': '206/283=0.73', 'side': '32/47=0.68'}

## 2. PostureV1 stored probability vs interval-derived labels (validation split; train shown as in-sample)

### validation (n judged = 190)
| label definition | n | prevalence | AUROC [95% CI] | all-positive F1 floor |
|---|---|---|---|---|
| presence: any knees_forward interval | 190 | 0.663 | 0.7453 [0.6755, 0.8127] | 0.797 |
| presence: forward OR inward interval (the corpus posture flag) | 190 | 0.663 | 0.7453 [0.6755, 0.8127] | 0.797 |
| degree: fraction of clip in error >= 0.5 | 190 | 0.211 | 0.6319 [0.5458, 0.7181] | 0.348 |
| degree: fraction of clip in error >= 0.35 | 190 | 0.421 | 0.6769 [0.6005, 0.7557] | 0.593 |
| degree: longest interval >= 1.5 s | 190 | 0.374 | 0.7368 [0.6623, 0.8057] | 0.544 |
| degree: longest interval >= 2.0 s | 190 | 0.200 | 0.7820 [0.7026, 0.8555] | 0.333 |
| degree: total error time >= 2.0 s | 190 | 0.216 | 0.7690 [0.6867, 0.8463] | 0.355 |

### train (n judged = 769)  -- IN-SAMPLE for the incumbent
| label definition | n | prevalence | AUROC [95% CI] | all-positive F1 floor |
|---|---|---|---|---|
| presence: any knees_forward interval | 769 | 0.658 | 0.7650 [0.7327, 0.7988] | 0.794 |
| presence: forward OR inward interval (the corpus posture flag) | 769 | 0.666 | 0.7725 [0.7402, 0.8062] | 0.799 |
| degree: fraction of clip in error >= 0.5 | 769 | 0.226 | 0.6177 [0.5733, 0.6629] | 0.369 |
| degree: fraction of clip in error >= 0.35 | 769 | 0.421 | 0.6263 [0.5858, 0.6650] | 0.593 |
| degree: longest interval >= 1.5 s | 769 | 0.315 | 0.7286 [0.6929, 0.7669] | 0.479 |
| degree: longest interval >= 2.0 s | 769 | 0.196 | 0.7317 [0.6899, 0.7743] | 0.328 |
| degree: total error time >= 2.0 s | 769 | 0.217 | 0.7357 [0.6957, 0.7756] | 0.357 |
```

## What it says

1. **The shipped localisation, checked against ground-truth timing for the first time.** When the
   knees-forward rule says OBSERVED, its `peak_time_sec` lands inside a labelled knees-forward interval
   (± 0.25 s) in **238 of 330 videos = 72.1 % [67.0, 76.7]**. The chance level on the same videos —
   a peak placed anywhere in the clip — is **59.5 %**, because the intervals cover 41 % of a clip on
   average. The median distance from the peak to the nearest interval midpoint is 0.57 s. At video
   level the rule fires on 51.5 % of videos with an interval and on 32.0 % without one. The
   "80.2 % within-video agreement" that the localisation claim rests on (`ACCEPTANCE_BAR.md` §A3) is
   a pose-pass *repeatability* number, not accuracy against these labels; against the labels the
   timing is about 12 points above chance. Filed as **G-57**.
2. **A degree label derived from the intervals does not clearly beat presence, on validation.**
   PostureV1's stored probability, validation n = 190: presence AUROC 0.7453 [0.6755, 0.8127];
   "longest interval ≥ 2.0 s" 0.7820 [0.7026, 0.8555]; "total error ≥ 2.0 s" 0.7690; fraction-of-clip
   definitions are worse (0.63–0.68). On the in-sample train split the ordering reverses (presence
   0.765, longest ≥ 2 s 0.732). Overlapping intervals, opposite directions across splits: no lift
   to claim. The human severity pilot stays the intervention; an interval-derived label is at most
   an extra pre-registered arm for Gate 2, not a replacement for annotators.
3. **Frame-level evaluation is now possible without new labels.** The intervals give a per-frame
   mask for 1,623 videos; the per-frame depth labels cover 3,611 frames. Nothing in the repo is
   evaluated per frame yet: PostureV1 is per video, and the rule emits one peak. A per-frame
   knees-forward detector (or the rule's per-frame indicator) can be scored as interval IoU / hit
   rate against these masks, on train/validation, before any product claim about *where*.

## Not done

- No test read. No retrain. The intervals were not fed to any model.
- The 13 withheld and the 192 double-fault videos are counted in the population but not analysed
  separately.
