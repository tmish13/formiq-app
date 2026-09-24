# ML_AUDIT — the FORMIQ form-analysis lifecycle, end to end

**Date:** 2026-09-23 · **Phase 1 (read-only)** · Two codebases: this repo (`backend/`, `bench/`) and
`~/FORMIQ Form Analysis Model/` ("ML repo"). Dataset roots: `~/Desktop/Squat More/Labeled_Dataset/`,
`~/Desktop/squat/`, `~/FORMIQ Form Analysis Model/data/`.

**Citation convention.** `file:cN` = notebook cell index N (0-based, as saved); `file:Lnn` = line;
`file:cN.out` = that cell's saved output. Every number carries one. Where a number appears in a
results file with no generating code, it is marked **NO GENERATING CODE**. Nothing below is
inferred from a filename.

**Builds on, and does not re-derive:** `AUDIT.md` G-21/G-24/G-25/G-28/G-39/G-44/G-45/G-47,
`bench/results/2026-09-19-v1-held-out-evaluation.md`, `2026-09-23-pose-pass-verdict-instability.md`,
`2026-09-23-corpus-duplicates.md`, `2026-09-23-depth-rule-negative-result.md`,
`2026-09-23-corpus-level-negative.md`, `2026-09-23-gates-pipeline-as-instrument.md`,
`backend/app/eval/provenance.py`. Where this audit **contradicts** one of those, it says so in place
(three contradictions: §6.4, §9 row "deployment n=281", §11a).

---

## 0. Six findings that were not in the brief

Read these first; the rest of the document is their evidence.

1. **The shipped weights and the reported test numbers come from different models.**
   `squat_pipeline_posture_stability_goodform_REBUILT.ipynb:c25:L318` saves the best epoch as
   `best_model_state = model.state_dict().copy()` — a *shallow* copy whose tensors share storage with
   the live parameters. Training continued for 15 more epochs and mutated them in place. The `.pt`
   written by `torch.save` at epoch 6 (`c25:L322-340`) is the true epoch-6 model; the in-memory
   "best" model that the notebook then swept for a threshold and scored on test (`c25:L345`,
   `load_state_dict` of the mutated dict) was the **epoch-21** model. Confirmed three ways in §6.4.
   Consequence: `posture_v1_manifest.json`'s `test_f1 0.7237` and the threshold `0.525` were never
   computed on the artifact that ships. On the shipped weights the validation optimum is
   **0.475**, not 0.525 (§7.2).

2. **The `posture_fault` label is a rename of Fitness-AQA's *knees-forward-or-inward* interval
   annotation, and `stability_fault` is a rename of the *knees_inward* folder.** Raw `posture_fault`
   ≡ `error_knees_forward ∪ error_knees_inward` non-empty on 1,375 of 1,383 videos (99.4%); raw
   `stability_fault` ≡ the `stability_faults` folder ≡ `knees_inward` non-empty on 230/230 (§2.3).
   So the model is trained to reproduce "an annotator marked a knee-travel interval" — a behaviour
   present in **65.9 %** of the corpus — after a collapse step that reassigned a third of those
   positives to `depth_fault`. Phase 2 measured that predicate's between-video separability at
   AUROC 0.572 (`2026-09-23-corpus-level-negative.md`). That is the ceiling the model is under.

3. **The collapse to mutually-exclusive classes has no generating code.**
   `processing_summary_corrected_labels.json` (1,837 records, true multi-label) became
   `processing_summary_balanced_3class.json` (1,625 records, single `class_label`) at
   2025-08-04 15:41. The rule is inferable from the data (depth ≻ posture; stability-only and 161
   posture-only videos dropped), and every downstream notebook reads the result; no code in either
   repo writes it (§2.4). **CLAIMED, NOT-REPRODUCIBLE.**

4. **There is no clean, adequately-sized, held-out measurement of PostureV1 anywhere.** The brief's
   "deployment F1 0.5636, n=281" (Gate 2) mixes **199 content-level *train* videos** into the 281.
   The only uncontaminated held-out number is content-level test, **n=41**, F1 0.4516 vs floor
   0.3922, ±0.16 (§9, §11a). The historical n=224 number is adequate in size and 12 % contaminated.
   Both are true; neither is what an interviewer would call "the test F1".

5. **Same-bytes duplicate pairs disagree on *any fault* 77 % of the time** (24 agree / 80 disagree
   over 104 groups) and sit in *different source folders* 62 % of the time. Agreement below 50 % is
   impossible for two independent noisy annotators, so this is not label noise — it is systematic
   cross-filing of identical clips into contrasting categories (§8.2). It bounds what the duplicate
   evidence can and cannot say about the rest of the corpus.

6. **`06f_metrics.json` is fabricated.** Its numbers (macro-F1 0.6089 etc.) exist in no executed cell;
   they appear only as hard-coded `expected_06f_macro_f1 = 0.6089  # Expected from 06f_metrics.json`
   in an unexecuted notebook (`06f_…_polished_FULL.ipynb:c0`), which is circular. The "+0.033 over
   06e" it claims is unsupported (§9).

---

## 1. Notebook and artifact inventory

### 1.1 Scale

151 notebooks in the ML repo (2 unparseable JSON), ~80 loose `.py` scripts, 38 `best_cnn_lstm_binary_
enhanced_cw_f0.5_*.pt` checkpoints plus ~20 other `.pt`, a `models/` directory from an earlier era.
Full machine-readable table: `scratchpad/nb_inventory.json` (generated this session; not committed).

### 1.2 The notebooks that matter

| notebook | mtime | code cells | executed | last exec # | role | writes |
|---|---|---|---|---|---|---|
| `squat_pipeline_posture_stability_goodform_REBUILT.ipynb` | 2026-02-16 | 34 | **34** (c1–c34 = exec 170–205; c30 ran last) | 205 | **PRODUCTION.** Binary posture, 151D, CNN-LSTM | `runs/best_cnn_lstm_binary_enhanced_cw_f0.5_*.pt`, `runs/cnn_lstm_binary_enhanced_cw_results.json`, `runs/model_comparison_results.json` |
| `06_multilabel_CNN_LSTM_refactored.ipynb` | 2025-12-23 | 7 | 6 | 19 | **writes the splits file** (c2, exec 14) | `data/squat_processed/user_level_multilabel_splits.json` |
| `05_advanced_performance_optimization_CNN_LSTM_integrated.ipynb` | 2025-11-23 | 8 | **4 of 8** (c4, c6, c7, c8 never executed) | 7 | multilabel 3-class; writes frame labels (c3, exec 4) | `balanced_3class_frame_labels.json` |
| `06e_phase_features_loss_calibration_v1.ipynb` | 2025-12-30 | 13 | 12 | 33 | multilabel biomech; **real** macro-F1 0.5757 (`c11.out`) | — |
| `06f_…_polished.ipynb` / `_FULL` / `_complete` | 2026-01-02 | 14 / 11 / 3 | 12 / **0** / 1 | 33 / 0 / 1 | see §0 item 6 | `06f_metrics.json` **NO GENERATING CODE** |
| `18`–`21_*_combined_features_*.ipynb` | 2025-12-23/24 | 5–9 | 4–7 | ≤14 | multilabel v2 biomech features, PCA | `runs/combined_*`, `runs/expF*`, `runs/expD*` |
| `notebooks/expC_*`, `expD_*`, `expD2_*` | 2025-12-19/21 | 6–12 | 0–11 | ≤37 | depth-precision experiments | `runs/expC_*`, `runs/expD_*` |
| `export_posture_v1.py` (script) | 2026-09-19 (edited for G-24) | — | run 2026-02-14 (manifest `created_at`) | — | **EXPORT.** Copies checkpoint, refits scaler, writes manifest | `artifacts/posture_v1.pt`, `_scaler.joblib`, `_manifest.json` |

**Not the production notebook**, confirmed: `05_…integrated.ipynb` trains a 3-class multilabel model
(`c6`–`c8`, all `exec=None`), reads `../../data/squat_processed/processing_summary_balanced_3class.json`
(`c2:L45`), and its only executed writes are the frame-label file. It does **not** write a `.pt`.

### 1.3 Artifacts on the serving path

| artifact | sha256[:16] | size | produced by | matches |
|---|---|---|---|---|
| `backend/app/ml/posture_v1/artifacts/posture_v1.pt` | `b7375ca49a932799` | 3,169,130 | `export_posture_v1.py:L371` (`shutil.copy2` of `runs/best_cnn_lstm_binary_enhanced_cw_f0.5_0.736.pt`) | **byte-identical** to `runs/…0.736.pt` and `ML/artifacts/posture_v1.pt` (VERIFIED) |
| `posture_v1_scaler.joblib` | — | 40,966 | `export_posture_v1.py:L380-410`, refit on 767 train videos | manifest `scaler_stats.n_training_videos_used = 767` = notebook `c30.out` "n_samples_seen_=767" (VERIFIED) |
| `posture_v1_manifest.json` | `7563b3ad34106916` | 2,992 | `export_posture_v1.py:L420-470` from `runs/cnn_lstm_binary_enhanced_cw_results.json` | `training_metrics` = results JSON exactly (VERIFIED); those numbers' provenance is §6.4 |
| `posture_v1_splits.json` | `ee28d014824623b5` | 40,966 | recovered from `user_level_multilabel_splits.json` | 1,625/1,625 assignments identical (VERIFIED this session) |

Checkpoint internals (loaded with `torch.load`, this session): `posture_v1.pt` → `epoch=6`,
`val_f0_5=0.7363`, `history` has **6** epochs `[0.704, 0.690, 0.714, 0.705, 0.735, 0.736]`, weight
hash `93d7c48b3983`, 261,446 params. Those six values match `REBUILT.ipynb:c25.out` epochs 1–6 exactly.

### 1.4 Dependency graph, edge by edge

```
raw videos ──(A)──► per-frame JPEGs ──(B)──► *_keypoints.json ──(C)──► clean/trim/interp ──(D)──► 151D features
                                                                                        │
labels: intervals ──(E)──► video_level flags ──(F)──► balanced class_label ──(G)──► multilabel_targets ──(H)──► binary targets
                                                                                                                       │
                                        user_level_multilabel_splits.json ◄──(I)──┘        train ──(J)──► .pt ──(K)──► artifacts ──(L)──► serving
```

| edge | what | status | evidence |
|---|---|---|---|
| A | Squat More `videos/*.mp4` → `processed_videos/frames/<v>/frame_*.jpg` | **CLAIMED** | 1,739 frame dirs; per-video JPEG count == keypoint count == `cv2` frame count (85/85/85, 120/120/120, 83/83/83) → every frame, no sampling. Same mtime as keypoints (2025-07-08 13:55). **No script in either repo writes this directory.** |
| B | frames → `*_keypoints.json` (`[{frame_index, landmarks[33]{x,y,z,visibility}}]`) | **CLAIMED** | No script writes this format. The two MediaPipe scripts present write `pose_data.json` per video with `static_image_mode=True` (`scripts/extract_and_pose.py:L106-110` complexity 1; `scripts/expand_public_squats.py:L165` complexity 2). Penn keypoints (`data/squat_processed/keypoints/`, 243 files, 2025-06-18) have the same format and also no writer; `scripts/batch_process_videos.py:L125` produces `*_processed.json` via the app's `smooth_and_interpolate_poses` — a different shape and a *smoothed* pass. |
| C | `load_keypoints_from_file` + `clean_keypoints` | VERIFIED | `REBUILT.ipynb:c3`, `c4`; mirrored by `export_posture_v1.py:L82-140` and `backend/app/ml/posture_v1/preprocess.py:L171-233` (one divergence, §3.3) |
| D | 87D + 64D → 151D | VERIFIED | `export_posture_v1.py:L143-330`; serving `features_151d.py`; parity 0.0 max-diff on 3 fixtures (`ML/scripts/output/feature_parity_*.json`) |
| E | Fitness-AQA interval files → `enhanced_labels.temporal_faults` | VERIFIED by identity | §2.3: 99.4 % / 100 % / 100 % agreement |
| F | intervals → `video_level` flags | VERIFIED | `data/squat_processed/fix_inconsistent_labels.py:L24-50` (190 fixes) |
| G | multi-label flags → single `class_label` ("balanced 3-class") | **CLAIMED — NO GENERATING CODE** | §2.4 |
| H | `class_label` → one-hot `multilabel_targets` | VERIFIED | `06_multilabel_CNN_LSTM_refactored.ipynb:c2:L19-24` `create_multilabel_targets` (`y_depth = 1 if class_label == 'depth_fault'`) |
| I | user-level split | VERIFIED | `06_…refactored.ipynb:c2` exec 14, `train_test_split(..., stratify=user_primary_classes, random_state=42)` L73-85; output "Saved user-level splits" |
| J | training | VERIFIED | `REBUILT.ipynb:c25` (output saved) |
| K | export | VERIFIED | `export_posture_v1.py` |
| L | serving | VERIFIED | `loader.py`, `pipeline.py`; `test_train_serve_parity.py` |

Two upstream edges (A, B) — the ones that produce the model's raw input — are the ones with no code.

---

## 2. Data provenance

### 2.1 Sources and counts

| source | on disk | in raw record (1,837) | in splits (1,625) | classes in splits | how it got here |
|---|---|---|---|---|---|
| **Squat More** (= Fitness-AQA, Parmar et al.; label files dated 2022-11-18) | 1,724 mp4 (`~/Desktop/Squat More/Labeled_Dataset/videos`), 1,739 keypoint files | 1,711 | **1,499** | good 452 / posture 578 / depth 469 | folder categories `good_form` (706), `posture_faults` (901), `stability_faults` (230); `processing_summary.json` (1,711, 2025-07-08) |
| **Penn Action** squats (IDs 1660–1889) | 168 mp4 in `data/penn_action_squats/` (`scripts/process_penn_action.py`) | 124 | **124** | **good_form 124 / 0 / 0** | `source_dataset="formiq"`, 4-digit names; keypoints in `data/squat_processed/keypoints/` |
| **YouTube scrape** (`data/scraping_log.jsonl`, 341 entries, `form_type: mixed_form`) | 233 raw → 223 clipped | 2 | **2** | good_form 2 | e.g. `iIIqHDGH0B8_good_rep_2` |
| InfiniteRep, MM-Fit | 0 files / 1 zip | 0 | 0 | — | never ingested |
| `~/Desktop/squat/` | label copies + zipped videos (2022) | — | — | — | a second copy of the Fitness-AQA download; `Unlabeled_Dataset/videos.zip` 1.6 GB never used |

`source_dataset` in the splits file has two values: `squat_more` 1,499, `formiq` 126 (`user_level_multilabel_splits.json`, computed this session). **All 126 `formiq` videos are `good_form`.** This is the population fact behind G-30.

### 2.2 The three annotation schemes

- **Fitness-AQA / Squat More:** per-video interval lists in seconds, `[[start,end],…]`, empty when no
  error: `Labels/error_knees_forward.json` (1,623 videos), `Labels/error_knees_inward.json` (1,623),
  and per-frame binary `Shallow_Squat_Error_Dataset/labels_shallow_depth.json` (3,611 frames, 623
  videos) with its own train/val/test id lists. Format doc: `Labels/ReadMe.md.txt`.
- **Penn Action:** class from folder (`good_form`) only; no fault annotation exists for Penn.
- **FORMIQ-collected (YouTube):** `form_type: mixed_form` in the scrape log; the two that survived
  are named `*_good_rep_*` and labelled `good_form` by folder.

### 2.3 How they were merged — traced, and what the labels actually mean

`enhanced_labels.temporal_faults` carries `posture_intervals`, `stability_intervals`, `depth_frames`.
`fix_inconsistent_labels.py:L24-50` sets each `video_level` flag to `len(intervals) > 0` — the video
label is *derived from* the intervals, not annotated separately. Cross-tab against the source files
(this session, `user_level_multilabel_splits.json` × `Labels/*.json`):

| raw flag | ≡ | agreement |
|---|---|---|
| `posture_fault` | `knees_forward` ∪ `knees_inward` interval non-empty | **1,375 / 1,383 = 99.4 %** (8 videos have an interval but no flag; 0 the reverse) |
| `stability_fault` | `knees_inward` interval non-empty ≡ `stability_faults` **folder** | **230 / 230**; nothing outside that folder has either |
| `depth_fault` | any frame labelled `1` in `labels_shallow_depth.json` | **469 / 469**; matches Phase 2's Route A (1,552/1,552 `depth_frames` ↔ label-1) |

So the label space is Fitness-AQA's three error types under new names: **posture = knee travel
(forward or inward), stability = knee valgus, depth = shallow.** "Posture" is not a posture label.

### 2.4 Where mutual exclusivity came from — and where the code is not

`processing_summary_corrected_labels.json` (2025-07-28, 1,837 records) has true multi-label flags:
posture-only 608, none 578, depth+posture 293, posture+stability 150, depth-only 128, triple 40,
stability-only 32, depth+stability 8. `processing_summary_balanced_3class.json` (2025-08-04 15:41,
1,625 records) has one `class_label` each and preserves `original_multi_label`. The mapping, computed
from the two files:

| raw combination | n | → assigned | rule implied |
|---|---|---|---|
| none | 578 | good_form | — |
| posture only | 608 → **447** | posture_fault | **161 dropped** to reach 578 = good_form count ("Balance quality: Excellent, imbalance ratio 1.23:1", `05_…integrated.ipynb:c2.out`) |
| depth + posture | 293 | **depth_fault** | depth ≻ posture |
| posture + stability | 150 → **131** | posture_fault | 19 dropped; stability discarded |
| depth only | 128 | depth_fault | — |
| depth + posture + stability | 40 | depth_fault | depth ≻ posture ≻ stability |
| stability only | 32 | **dropped** | no class for it |
| depth + stability | 8 | depth_fault | — |

It is a **design choice** (deliberate undersampling to balance, plus a priority order), not a bug of
the merge. But no code produces it. Searched: every `.py` and `.ipynb` in the ML repo for a `json.dump`
targeting the file or the string `balanced_3class` near a write; the two revamped cells
(`data/squat_processed/cell_2_revamped.ipynb`, `cell_2.5_revamped.ipynb`, both `exec=None`) contain an
`elif has_posture and has_depth …` ladder for *frame* labels but write a different file; `enhanced_cells/
cell_2_5_with_depth_features.py:L167-216` *reads* `class_label`. **CLAIMED.**

Consequences that follow directly from this table:
- **333 videos whose annotator marked a knee interval are labelled `depth_fault`** and, in the binary
  task, are *dropped* (`REBUILT.ipynb:c2:L150-163`, "[0,0] neither" filter: 328 train / 70 val / 71
  test). The model never sees posture faults that co-occur with shallow depth.
- At deployment those videos are scored. G-29's "50 of 71 test depth_fault videos carry
  `posture_fault: True`" is this table's row 3.
- The 600 "disagreements" between `category` and `multilabel_targets` found in Stage C are all
  explained here: 293 + 131 + 128 + 48 = 600 exactly.

### 2.5 `depth_frames` and `labels_shallow_depth.json` — who consumed them

- `05_…integrated.ipynb:c3` (exec 4) converts `depth_frames` seconds → per-frame class 2 and writes
  `balanced_3class_frame_labels.json` (output "Saved 1625 processed video labels"). That file is
  read by the production notebook (`c1:L88`) **only for `keypoints_path`**; frame labels are never
  used by it (binary task drops depth, `c2`).
- `labels_shallow_depth.json` is read by `biomechanical_modules/depth_feature_extractor.py`,
  `enhanced_cells/cell_1_enhanced_imports.py`, `src/enhanced_dataset.py` — the multilabel/depth
  experiment line (06b–06h, 09, 10), none shipped.
- No notebook ever trained a *frame-level* depth model that reached an artifact.

---

## 3. Preprocessing and keypoint extraction

### 3.1 The pose pass that made the training keypoints — not recoverable

| property | training keypoints (Squat More) | training keypoints (Penn, `formiq`) | serving (`app/core/pose_pass.py`) | calibration corpus (`bench/cache/keypoints_live`) |
|---|---|---|---|---|
| MediaPipe version | **unknown** | unknown | 0.10.18 | 0.10.18 |
| `static_image_mode` | **unknown**; frames dir + per-frame count suggests static pass over JPEGs | unknown; `batch_process_videos.py` path is video mode + smoothing, but that writes a different format | `False` (tracking) | `False` |
| `model_complexity` | unknown | unknown | 2 (was silently 1 before G-21) | 2 |
| confidences | unknown | unknown | 0.5 / 0.5 | 0.5 / 0.5 |
| fps handling | every frame, no sampling (85=85=85) | every frame | every frame ≤300 | every frame |
| tracker | unknown | unknown | reset per video (G-31) | reset per video |
| generating code | **NONE FOUND** | **NONE FOUND** | `analysis_tasks._extract_pose_from_video` | `bench/extract_keypoints.py` |
| `pose_pass_id` | n/a | n/a | `pp1_f9850424580ae186` | `pp1_f9850424580ae186` |

`processed_videos/processing_summary.json` (1,711 entries) records only `{video_name, video_path,
category, frame_count, keypoints_path, status}` — no extraction parameters. The Phase 2 provenance gate
measured dataset-vs-live agreement at r ≥ 0.90 on all four depth indicators with +0.0108 bias and
**14.9 % verdict flips** (`2026-09-22-keypoint-provenance.md`, `2026-09-23-pose-pass-verdict-instability.md`).
That is the only quantitative statement available about the training pass.

### 3.2 Cleaning, interpolation, normalisation — traced both sides

| step | training (`REBUILT.ipynb`) | serving (`backend/app/ml/posture_v1/`) | same? |
|---|---|---|---|
| frames with ≠33 landmarks | zero-filled (`c3:L34-36`) | zero-filled (`preprocess.py:_parse_to_array_4d`) | yes |
| trim leading/trailing zero frames | `c4:L42-55` | `preprocess.py:L192-199` | yes |
| internal zero frames | linear `np.interp` per dim over good indices (`c4:L78-90`) | gap-wise linear blend (`preprocess.py:L204-231`) | mathematically identical for interior gaps; edge gaps: notebook has none after trim, serving copies neighbour |
| **reject if internal missing > 10 %** | **yes** — `raise ValueError` (`c4:L64-75`); dropped 42 train / 9 val / 11 test (`c30.out` §F) | **no** — always interpolates and scores | **NO** — see 3.3 |
| sequence length | first-300 truncate, zero-pad tail, `sequence_length=min(T,300)` for `pack_padded_sequence` (`c23:L98-115`) | identical (`preprocess.py` docstring, `L1-11`) | yes |
| visibility | dropped before model (`c23:L100`) | dropped (`NUM_COORDS=3`) | yes |
| resampling / smoothing / normalisation of coordinates | **none** — raw MediaPipe 0–1 (`manifest.input_spec.keypoint_normalization: none_raw_mediapipe_0_1`) | none | yes |
| feature scaling | `StandardScaler` fit on 767 train (`c7`, `c30.out` §D2) | `posture_v1_scaler.joblib`, same 767 | yes |
| `posture_v2/features.py` (hip-centred, torso-normalised, 30 fps resample) | not used | **not used** — DRAFT (`features.py:L4`) | n/a |

### 3.3 One train/serve skew that survived G-24

Training refuses any video with more than 10 % internal missing frames; serving does not. On the
notebook's validation split, **8 of 174** videos (4.6 %) fall in that band and were never seen in
training or validation, yet receive a verdict at serving (this session, `scratchpad/val_check_posture_v1.json`,
`skipped.notebook_would_reject_gt10pct_missing = 8`). Small, but it is a population the model has
no evidence about, and the app's quality gates (`loader.py:L327`, "forcing uncertain" at a *different*
missing threshold) do not reproduce the training rule.

### 3.4 Feature parity — exact

`ML/scripts/compare_backend_vs_ml_features.py` runs both extractors on the same fixtures:
`scripts/output/feature_parity_{33499_1_good,45959_1_posture_fault,50852_1_good}.json` → `max_diff = 0.0`,
`n_mismatch_001 = 0/151`, `scaled_max_diff ≈ 1e-6`. Pinned in-repo by
`backend/tests/unit/test_train_serve_parity.py` (`test_every_static_feature_name_means_what_it_says`,
`test_static_feature_block_contains_only_face_landmarks`).

---

## 4. Feature construction — every set ever built

| feature set | dims | where built | executed? | manifest correct? | serving reproduces? | ablation |
|---|---|---|---|---|---|---|
| RFECV 5-feature XGBoost inputs | 5 | Jun-2025 era, `models/adaptive_feature_sets.json` | yes (models saved 2025-06-26) | n/a | not served | none |
| **87D "baseline"** — `joint{0..10}_{x,y,z}_mean/std` + `joint{0..6}_{x,y,z}_range` | 87 | `REBUILT.ipynb:c5`; `export_posture_v1.py:L143-190` | yes | **corrected 2026-09-19** (G-24); manifest `feature_order.0_32` now reads `joint{0..10}_{x,y,z}_mean (11 FACE joints × 3)` | bit-exact (§3.4) | **only** `bench/results/2026-09-19-face-block-ablation.md`: freeze [0:87] → F1 0.7692 → 0.7170 (−0.052), n=50, **7/50 contaminated** (G-45) |
| 64D temporal — 4 angles × 15 stats + 4 derived | 64 | `REBUILT.ipynb:c12-13`; `export_posture_v1.py:L193-330` | yes | yes | bit-exact | none |
| **151D = 87 + 64** (shipped) | 151 | `build_canonical_151d` | yes | yes | bit-exact | as above |
| 87D-only CNN-LSTM inputs | 87 | earlier binary run | yes — `runs/best_cnn_lstm_binary_posture_f0.5_0.{606,630,653,699}.pt` (2026-02-05, `feature_dim: 87`, `lstm_hidden: 128`, 347,974 params) | no manifest | not served | none |
| 9D / 19D / 22D / 32D / 35D biomech ("depth precision") | 9–35 | `biomechanical_modules/`, `06b`–`10_*`, `expC/D/F` | partly | n/a | not served | `runs/expF2_ablation` (macro-F1 0.5037–0.5469 across six removals, baseline 0.5111 — all within ±0.035), `runs/expD_precision` (D1 7D vs D0 9D: 0.5088 vs 0.5162) |
| combined / PCA 18D | 18 | `19`–`21_*` | yes | n/a | not served | `runs/18d_vs_baseline_comparison.json`: +0.02 macro-F1 |
| **posture_v2 body-only, camera-invariant** | 20-ish | `backend/app/ml/posture_v2/features.py` | **never trained, never served** (`L4`: "STATUS: DRAFT") | has `spec_hash()` | n/a | none |

**The face block, re-examined.** `features_151d.py:L1-20` and `export_posture_v1.py:L143-160`
document it correctly now: indices 0–86 are raw image coordinates of MediaPipe landmarks 0–10
(nose, eyes, ears, mouth), 57 % of the tabular input, **zero body joints**. Training-time
justification: none — `REBUILT.ipynb:c5` calls it "baseline 87D" and `c33` ("TEMPORAL ENHANCEMENT
SUMMARY") never mentions that the base block is facial. **A body-only alternative was never trained**:
grep of every notebook and script for `body_only|no_face|BODY_JOINTS|face_block|[:, 11:` returns
nothing outside the v2 draft and the service-repo ablation. The multilabel line (06–21) used *only*
biomech features (9–35D, no face) and scored macro-F1 0.50–0.58 — a different task (3-class, with
depth), so not a controlled comparison.

---

## 5. Splits and leakage — content level

### 5.1 The split files

Five split files exist in `data/squat_processed/`. All five carry the **identical** 1137/244/244
assignment (this session, set comparison): `user_level_multilabel_splits.json` (sha `614699213368`),
`balanced_3class_train_test_splits.json`, `combined_features_multilabel_splits.json`,
`final_combined_features_multilabel_splits.json`, `combined_features_complete_multilabel_splits.json`.

Generator: `06_multilabel_CNN_LSTM_refactored.ipynb:c2` (exec 14) — `train_test_split(user_ids,
user_primary_classes, stratify=…, random_state=42)` twice (`L73-85`); `metadata.creation_date`
`2025-12-23T18:49:07` matches the file mtime. It is **not** Fitness-AQA's official split
(`Splits/{train,val,test}_keys.json`, 1136/243/244): only **752 of 1,383** shared videos (54.4 %) land
in the same split under both.

### 5.2 Contamination, at content level

Using `bench/results/corpus_duplicates.json` (105 byte-identical duplicates, 45 spanning splits):

| split file | test n | test videos with a byte-twin in **train** | rate |
|---|---|---|---|
| all five above (identical) | 244 | **27** | **11.1 %** |
| → evaluated 224 (pinned F1 0.6131) | 224 | 27 | 12.0 % (19 same-label, 8 conflicting) |
| → manifest binary population (test − depth) | 173 | 18 | 10.4 % |
| → ablation fixtures | 50 | 7 | 14.0 % |
| `bench/results/content_level_splits.json` (repaired, `minimal`) | 196 | **0** | 0 % (161 conflicted + 138 no-file withheld; 11 videos moved) |

### 5.3 Notebook × split × test-touched-during-fitting

| notebook / run | split file | test contamination | early-stop / checkpoint criterion | threshold selected on | model/run selected on | test touched during fitting? |
|---|---|---|---|---|---|---|
| `REBUILT.ipynb` (production) | user_level | 11.1 % | val F0.5, patience 15 (`c25:L233-236`) | val, 25-pt grid (`c25:L155-190`) — **on the wrong weights** (§6.4) | **test** — `c31.out` sorts 10 configs by `test_f05`, "🥇 Best overall: CNN-LSTM … Test F0.5=0.735"; classical models `c28` report val *and* test per config; choice among ≥38 training runs undocumented | **YES (selection)**; NO (threshold, early stop) |
| `06e_…v1.ipynb` | user_level | 11.1 % | val | c10–c11 val; c11, c12 also reference test (`c11:L114-119`) | — | **unclear** (test referenced in threshold cells) |
| `notebooks/expD_depth_precision_recovery.ipynb` + `runs/expD_precision/ablation_summary.json` | user_level | 11.1 % | val precision s.t. recall ≥ 0.8 | val | **"tie-break with test macro_f1"** (`ablation_summary.json:selection_criteria`) | **YES (explicit)** |
| `notebooks/expC_eval_threshold_tuning.ipynb` | user_level | 11.1 % | — | c5, c6, c8, c9 reference test objects in threshold cells | — | **unclear → likely YES** |
| `07_threshold_optimization_report_fixed.ipynb` | user_level | 11.1 % | — | c7, c8 reference test | — | **unclear** |
| `runs/expF1_comparison` | user_level | 11.1 % | — | val, constraint grid (`val_thresholds.json:method`) | — | NO |
| `05_…integrated.ipynb` | balanced_3class (identical) | 11.1 % | never trained (`c6-c8 exec=None`) | — | — | n/a |
| Jun-2025 XGBoost trio (`models/`) | 112/28/36 Penn+YouTube (`production_metadata.json`) | unknown (pre-duplicate-map era; Penn-only) | — | — | — | unknear |
| `bench/eval_v1_test_split.py` (service) | user_level | 12.0 % of 224 | — | 0.525 inherited | — | NO (one read) |
| `bench/cycle_turn.py` (Gate 3) | content_level | 0 % | — | val only, n=41 | — | NO (one read, negative result) |

The production notebook's own leakage audit (`c30`, exec 205, run last) checks video-name and
user-id overlap and passes — it is the origin of the name-level guarantee G-45 later found
insufficient.

---

## 6. Model training — every model, honestly

### 6.1 Chronology

| era | models | data | features | headline (as recorded) | artifact | shipped? |
|---|---|---|---|---|---|---|
| **2025-06-26** | XGBoost ×3 (binary / posture / stability), "adaptive_feature_selection v2.0.0" | **112 train / 28 val / 36 test**, Penn + YouTube (`models/production_metadata.json`) | RFECV 5-feature | binary F1 0.856, posture F1 0.897, stability F1 0.725 (`models/model_performance_metrics.json`) — **n=36** | `models/*_pipeline.joblib` | no |
| 2025-07-17/18 | CNN-LSTM "breakthrough", sequential binary/posture/stability `.pth` | Penn era | ? | none recorded | `models/cnn_lstm_form_analyzer_*.pth` | no |
| 2025-07-31 → 08-04 | 5-fold binary / multi-label / "rules_compliant" | leak-free multilabel dataset (`ml_ready_datasets_multilabel_leak_free/`) | 70D / 50D / 20D | `models/cell_7_v2_*`, `final_production_results` | `.pth` folds | no |
| **2025-11** | 3-class multilabel CNN-LSTM (`05_…integrated.ipynb`) | Squat More + formiq, balanced 1,625 | frame labels | **never trained** (c6–c8 unexecuted) | none | no |
| **2025-12** | multilabel hybrid CNN-LSTM, biomech features: 06b/c/d/e/f/h, 09, 10, 15–21, expC/D/D2/F | user_level split | 9–35D biomech, 18D combined | macro-F1 **0.50–0.58**: 06e 0.5757 (`06e:c11.out`), 18d 0.5568, expC 0.5677, expD2 0.5310–0.5684, expF2 0.5111, expEnhanced22D 0.5103–0.5147 | `runs/*.pt`, `runs/*/best_model.pt` | no |
| 2026-02-05 | binary posture CNN-LSTM, **87D**, lstm 128, dropout 0.3 | user_level, depth dropped | 87 | val F0.5 0.606 / 0.630 / 0.653 / 0.699 (checkpoint names; `epoch=4` for 0.699) | `runs/best_cnn_lstm_binary_posture_f0.5_*.pt` | no |
| **2026-02-05 → 02-11** | binary posture CNN-LSTM "enhanced_cw", **151D**, lstm 96, dropout 0.4, wd 5e-4, class weights | user_level, depth dropped; 767/165/162 after cleaning | 151 | **≥ 20 runs**: val F0.5 0.589 … 0.742 (checkpoint names, each a distinct run — e.g. 0.742 has 15 recorded epochs `[0.711, 0.682, …, 0.742]`, 0.736 has 6) | `runs/best_cnn_lstm_binary_enhanced_cw_f0.5_*.pt` | **0.736 shipped** |

### 6.2 The shipped model, exactly

`REBUILT.ipynb:c24` `BinarySquatCNNLSTM`: Conv1d(k=5)×2 [32, 64] + BatchNorm + Dropout1d(0.4) →
LSTM(96) via `pack_padded_sequence` → concat with 151D scaled features → MLP [256, 128] + BatchNorm +
Dropout(0.4) → 2 logits; 261,446 params. Loss: `posture_only_bce_loss` (`c9:L2-40`) — BCEWithLogits
over both outputs on `[1,0]`/`[0,1]` samples only, per-sample class weight. Adam lr 1e-3, wd 5e-4,
`ReduceLROnPlateau(mode='max', factor=0.5, patience=7)`, grad-clip 1.0, batch 4 (`c6:L7`), max 100
epochs, early stop patience 15 on val F0.5 at threshold 0.5 (`c25:L228-236`). **No `torch.manual_seed`
or `np.random.seed` anywhere in the notebook** (only sklearn `random_state=42` in c27/c28/c30) — which
is why the same code produced ≥20 checkpoints with val F0.5 from 0.589 to 0.742.

Training set: 767 videos (404 good / 405 posture before cleaning → 767 after; `c23.out`, `c30.out` §F),
prevalence ≈ 0.50. Recorded run (`c25.out`): 21 epochs, best epoch 6, val F0.5 0.736.

### 6.3 Which artifact ships, and does it match

`artifacts/posture_v1.pt` == `runs/…0.736.pt` == service `posture_v1.pt`, sha256 `b7375ca49a932799`
(VERIFIED, §1.3). `ML_REPO_TRUTH_EXTRACTION.md:L3` says "**Best checkpoint:** …0.742.pt (val F0.5=0.742)"
— a different, better-on-validation run (epoch 15, weights `d4a96161ccd1`) that is **not** the one
exported. `runs/cnn_lstm_binary_enhanced_cw_results.json:model_path` points at 0.736. No file records
why 0.736 was chosen over 0.742; the notebook's saved outputs are the 0.736 run's. **The truth doc
and the manifest disagree about which model is the model.**

### 6.4 The reported test numbers were computed on different weights than the artifact

Evidence, three independent lines:

1. **Code.** `c25:L318` `best_model_state = model.state_dict().copy()`. `state_dict()` returns detached
   tensors that *share storage* with the parameters; `dict.copy()` is shallow. The optimizer's in-place
   updates over epochs 7–21 mutate that "saved" state. `torch.save` at `L322` serialised the storage
   *at epoch 6* — correct on disk. `L345` `model.load_state_dict(best_model_state)` then loads the
   mutated (epoch-21) values — a no-op. Everything after — the threshold sweep (`L355`), the test
   evaluation (`L362`), the results JSON, the manifest — ran on epoch-21 weights.
2. **The notebook's own numbers are inconsistent with one model.** `c25.out`: epoch-6 val F0.5 at
   threshold 0.5 = **0.736**; the post-training sweep over `np.linspace(0.2, 0.8, 25)` — a grid that
   *contains* 0.5 — reports best = 0.718 at 0.525. A sweep on the epoch-6 weights would have found
   ≥ 0.736 at 0.5. It did not; so it ran on other weights. Epoch-21 val F0.5 at 0.5 was 0.703
   (`c25.out` last row), and 0.718 at 0.525 is consistent with that model.
3. **Direct check on the shipped weights** (this session, serving loader, validation split only,
   notebook's 10 % rejection rule applied, n=166 vs the notebook's 165; test not read):
   F0.5 @0.500 = **0.7298** (notebook epoch 6: 0.736) · @0.525 = **0.7159** (notebook sweep: 0.718)
   · grid optimum = **0.7495 @ 0.475**. On these weights 0.500 beats 0.525 by 0.014 — the notebook's
   sweep could not have chosen 0.525 from them. `scratchpad/val_check_posture_v1.json`.

G-28 is consistent with this and I now read it differently from its own headline: on the shipped
weights the binary-task population gives TP **61**, FP 19, F1 **0.7349**; the manifest records TP
**55**, FP 19, F1 **0.7237**. FP matching was taken as "reproduces"; TP differing by 6 on ~160 videos
is what two different weight sets look like. **Contradiction with G-28's title:** the manifest's
0.7237 does *not* reproduce from the artifact; it is consistent with a sibling model.

Also: `threshold_tuning.validation_f0_5_gain = −0.0187` (`results.json`) — the 0.525 threshold was
adopted although the notebook's own sweep reported it made validation *worse* than the training-time
0.5. `c25:L350-358` picks `max(f0_5)` over the grid unconditionally and never compares to the
baseline it printed one line earlier.

### 6.5 Reproducibility verdicts

| number | reproduces from a stored artifact? |
|---|---|
| val F0.5 0.736 @0.5 (epoch 6) | **REPRODUCED-WITH-CAVEAT** — 0.7298 on n=166 via serving pipeline (population +1, tolerant preprocess) |
| threshold 0.525 | **NOT-REPRODUCIBLE** — optimum on the artifact is 0.475 |
| test P 0.7432 / R 0.7051 / F1 0.7237 / F0.5 0.7353, n=162 | **NOT-REPRODUCIBLE** — computed on epoch-21 weights that were never saved |
| classical table (`model_comparison_results.json`) | REPRODUCED-WITH-CAVEAT — deterministic (`random_state=42`) but features depend on the unrecorded pose pass |
| 0.742 run | no results file; weights exist; **NOT-REPRODUCIBLE** as a result |
| 06f_metrics.json | **NOT-REPRODUCIBLE** (fabricated, §0.6) |

---

## 7. Evaluation integrity

### 7.1 Metric implementations — nine, now one on the serving side

| where | implementation | zero-denominator | F-β | covered-only vs abstain |
|---|---|---|---|---|
| `REBUILT.ipynb:c9:L44-66` `compute_binary_metrics_posture_only` | sklearn `precision/recall/f1/fbeta_score` | `zero_division=0.0` | β=0.5 | no abstention concept |
| `REBUILT.ipynb:c28:L8-26` `f05` for classical models | sklearn `fbeta_score` | `zero_division=0.0` | 0.5 | — |
| `REBUILT.ipynb:c30:L232-238` audit permutation test | sklearn | 0.0 | 0.5 | — |
| `06e:c10-12`, `18:c5`, `21:c7` | sklearn per head + **hand-rolled** `if precision + recall` (`06e:c11:L119`) | mixed | 1 | — |
| `05:c7-8` | sklearn `precision_recall_fscore_support`, `f1_score(zero_division=…)` | ? | 1 | — |
| service repo, five copies → `app/eval/metrics.py` (C.1) | numpy, pinned to sklearn parity | 0.0 | `f_beta` | **both views always** (`coverage_metrics`) |

No notebook models abstention; `uncertain` is a serving-side construct (`loader.py:L327`, quality
gates). Every notebook number is therefore covered-only by construction, and no notebook reports a
trivial floor or a confidence interval.

### 7.2 Where 0.525 comes from

`c25:find_best_posture_threshold`: max F0.5 over `np.linspace(0.2, 0.8, 25)` (step 0.025; 0.525 is
index 13) on the validation loader, computed on the epoch-21 weights (§6.4). Recorded gain vs the
training-time 0.5: **−0.019**. On the shipped weights the validation-optimal threshold is **0.475**
(F0.5 0.7495 vs 0.7159 at 0.525). Serving reads `manifest.threshold = 0.525`
(`loader.py:L110-131`) and offers named modes (`L41-43`) but no re-derivation.

### 7.3 Numbers chosen on test

- `c31.out` ranks ten configurations by **test** F0.5 and declares the winner.
- `runs/expD_precision/ablation_summary.json`: "tie-break with test macro_f1".
- Threshold cells that reference test objects: `06e:c11-12`, `expC_eval_threshold_tuning:c5,6,8,9`,
  `07_threshold_optimization_report_fixed:c7-8` — flagged **unclear**, not traced line-by-line.

### 7.4 Bootstrap CIs

Present: `bench/results/2026-09-19-v1-held-out-evaluation.md` (F1 CI [0.5291, 0.6872]), G-28 (binary
task [0.658, 0.802]), pose-pass paired CIs, Gate 3 paired CI. **Absent in every notebook.** The only
CI on a content-level (uncontaminated) number is Gate 3's ±0.16 at n=41.

---

## 8. Label quality

### 8.1 Inter-source agreement where two sources labelled the same video

| pair | n | agreement | reading |
|---|---|---|---|
| raw `posture_fault` flag ↔ knees interval non-empty | 1,383 | 99.4 % | not two sources — the flag was *derived* from the interval (`fix_inconsistent_labels.py`) |
| raw `depth_fault` ↔ any label-1 shallow frame | 598 | 100 % | same annotation surfaced twice (Phase 2) |
| raw `stability_fault` ↔ `stability_faults` folder ↔ knees_inward | 230 | 100 % | same |
| `labels_override.json` (expert review, 14 labels) ↔ corpus | **0** map by name | — | the override covers `backend/test_videos/` smoke fixtures, none in the corpus |
| `category` (folder) ↔ assigned `class_label` | 1,625 | 63.1 % | the 600 disagreements are the collapse (§2.4), not annotation |

**There is exactly one annotation per video for each fault type.** Every "second field" in the corpus
is a deterministic function of the first. No inter-annotator agreement can be measured from within
the corpus except through the duplicates.

### 8.2 The duplicates — the only second opinion, and it is not one

104 byte-identical groups (`bench/corpus_duplicates.py`), raw flags compared within group:

| flag | agree | disagree | pairwise agreement |
|---|---|---|---|
| **any fault** | 24 | **80** | **23.1 %** |
| posture_fault | 40 | 64 | 38.5 % |
| depth_fault | 57 | 47 | 54.8 % |
| stability_fault | 94 | 10 | 90.4 % |
| source folder | 40 | 64 | 38.5 % |

Two independent annotators with symmetric error rate *e* agree with probability *e² + (1−e)²* ≥ 0.5.
**23 % is below the floor of independent noise**, so these are not noisy re-labels; the identical clip
was *filed into a different folder* 62 % of the time and labelled to match. That is a dataset-
construction artifact (in Fitness-AQA or in the copy), not annotator variance, and it means the
duplicate-pair disagreement rate **cannot be extrapolated** to the other 1,383 videos.

### 8.3 Label-noise floor

Hard bound (`scratchpad` computation, oracle = perfect on unconflicted, coin-flip on each video whose
byte-twin carries a different label):

| basis | target | n | pos | conflicted | oracle F1 | trivial floor |
|---|---|---|---|---|---|---|
| user-level test (every historical number) | posture_fault | 244 | 86 | 29 (6 pos, 23 neg) | **0.920** | 0.521 |
| user-level test | depth_fault | 244 | 71 | 29 | 0.901 | 0.451 |
| content-level test (withholds conflicts) | posture_fault | 196 | 78 | 0 | 1.000 (by construction) | 0.569 |

**Extension.** Because §8.2 rules out treating the pair disagreement as a noise *rate*, the honest
statement is: the measured conflicts cap the historical test F1 at ≈ 0.92; the true ceiling on the
remaining videos is **unknown**, because no second annotation exists. What *is* known about the
underlying construct: the knees-forward predicate the label is derived from has between-video AUROC
0.572 at 68 % prevalence (`2026-09-23-corpus-level-negative.md`). A label that is a degree judgement
on a near-universal behaviour has a low ceiling for reasons that are not noise.

---

## 9. Reconciliation — every reported number

| # | value | source | split / population | n | contamination | metric impl. | reproduces today? |
|---|---|---|---|---|---|---|---|
| 1 | binary F1 0.856 / posture 0.897 / stability 0.725 | `ML/models/model_performance_metrics.json` (2025-06-26) | Penn + YouTube, 112/28/36 | **36** | unknown; pre-Squat-More | unknown (no code) | **NOT-REPRODUCIBLE** — no test set stored, different corpus, no generating cell |
| 2 | multilabel macro-F1 0.5757 (06e) | `06e_…v1.ipynb:c11.out` (exec 32) | user_level test | 244 | 11.1 % | hand-rolled + sklearn | REPRODUCED-WITH-CAVEAT (executed output; artifact not re-run) |
| 3 | 06f macro-F1 0.6089, "+0.033 vs 06e" | `06f_metrics.json` | — | — | — | — | **NOT-REPRODUCIBLE — NO GENERATING CODE** (§0.6) |
| 4 | expC/expD/expD2/expF macro-F1 0.5088–0.5785 | `runs/*/test_metrics.json` etc. | user_level test | 242 | 11.1 % | sklearn/hand-rolled | REPRODUCED-WITH-CAVEAT; expD selected with test tie-break |
| 5 | val F0.5 0.736 @0.5, epoch 6 | `REBUILT.ipynb:c25.out` | user_level val, after filters | 165 | (val) | `c9` sklearn | **REPRODUCED-WITH-CAVEAT** — 0.7298 on n=166 via serving loader (this session) |
| 6 | threshold 0.525 | `c25.out`; `results.json`; manifest | val sweep on **epoch-21** weights | 165 | — | — | **NOT-REPRODUCIBLE** — optimum on the artifact is 0.475 (0.7495) |
| 7 | test P 0.7432 R 0.7051 F1 0.7237 F0.5 0.7353 | `results.json`; `posture_v1_manifest.json:training_metrics` | user_level test, depth removed | 162 | 10.4 % (of 173) | `c9` sklearn | **NOT-REPRODUCIBLE** — computed on unsaved epoch-21 weights (§6.4); artifact gives TP 61 / F1 0.7349 on the same population (G-28) |
| 8 | classical: LogReg 0.694, XGB 0.687, MLP 0.673 … test F0.5 | `runs/model_comparison_results.json`; `c31.out` | user_level test | 162 | 10.4 % | `c28` sklearn | REPRODUCED-WITH-CAVEAT (seeded; features depend on unrecorded pose pass) |
| 9 | "Best checkpoint 0.742" | `ML_REPO_TRUTH_EXTRACTION.md:L3` | val | 165 | — | — | **contradicts manifest** (shipped = 0.736); no results file for 0.742 |
| 10 | F1 0.6131 CI [0.5291, 0.6872], AUROC 0.7184, floor 0.5548 | `bench/results/2026-09-19-v1-held-out-evaluation.md` | user_level test, all classes | 224 | **27 (12.0 %)** | `app/eval/metrics.py` | **REPRODUCED bit-exact** (`test_metrics_parity.py`) — upper bound (G-44 caveat attached) |
| 11 | binary-task F1 0.7349 [0.658, 0.802], AUROC 0.7619, floor 0.7197 | `2026-09-19-g28-closed-manifest-reproduces.md` | user_level test − depth | 153 | 18 of 173 (10.4 %) | same | REPRODUCED-WITH-CAVEAT |
| 12 | face-block ablation 0.7692 → 0.7170 (−0.052) | `2026-09-19-face-block-ablation.md`; `2026-09-19-ablation-summary.json` | 50 balanced fixtures | 50 | **7 (14.0 %)** | `bench/ablate_face_block.py` | REPRODUCED-WITH-CAVEAT (retracted as an absolute, G-25; relative delta survives) |
| 13 | Penn shortcut: prob_fault 0.239 vs 0.428; face-freeze +0.177; AUROC 0.762 → 0.801 | `2026-09-19-v1-final-numbers-and-penn-shortcut.md` | held-out good-form by source | 20 / 67 | relative | `bench/penn_shortcut_test.py` | REPRODUCED (relative comparison; contamination common to both arms) |
| 14 | live-keypoint F1 0.5905, CI lower 0.5096, floor 0.5508 | `2026-09-23-posev1-pose-pass-delta.md` | user_level test, live pose pass | 221 | ~12 % | same | REPRODUCED-WITH-CAVEAT (test read once) |
| 15 | 33/221 verdicts flip (14.9 %) between passes | `2026-09-23-pose-pass-verdict-instability.md` | paired | 221 | n/a | `bench/posepass_flip.py` | REPRODUCED |
| 16 | **deployment F1 0.5636 covered / 0.5322 abstain-as-neg, P 0.4526, coverage 0.911** | `2026-09-23-gates-pipeline-as-instrument.md` (Gate 2) | content-level **train+val+test mixed** | 281 | 0 % byte-twins **but 199 of the stored decisions are content-level TRAIN videos** | `eval_runner.py` | REPRODUCED — **and CONTRADICTS the brief: this is not a held-out number** |
| 17 | content-level **test** F1 0.4516 @0.525 vs floor 0.3922; ΔF1 −0.0349 CI [−0.2172, +0.1135] for 0.65 | `bench/cycle_turn.py` (Gate 3) | content-level test | **41** | 0 % | `app/eval/metrics.py` | REPRODUCED — the only clean held-out number that exists |
| 18 | depth AUROC 0.578 (best of 10) / valgus 0.533 / knees-forward 0.572 vs floor 0.812 | `2026-09-23-corpus-level-negative.md` | train + val | 407–719 | n/a (test unopened) | same | REPRODUCED |
| 19 | 24-video e2e F1 0.182, recall 0.111 | `AUDIT.md:L616`, `backend/scripts/output/` | formiq fixtures | 24 | n/a | script-local | REPRODUCED-WITH-CAVEAT (pre-G-21 complexity fallback) |
| 20 | CV: "100+ concurrent uploads", "sub-300 ms", "99.9 %", "25 % latency" | `AUDIT.md` G-01 | — | — | — | — | **NOT-REPRODUCIBLE**; measured API ceiling < 20 (G-36), worker OOM 1 % (G-46). The CV makes **no model-accuracy claim** (`AUDIT.md:L645`) |

---

## 10. Diagnosis — why the scores are what they are

Ranked by estimated share of the gap between what is reported (0.72–0.74) and what is honest (≈ floor
+0.02 to +0.06). Estimates are bounded by evidence, not fitted.

| rank | cause | evidence | how much it explains | fixable by |
|---|---|---|---|---|
| **1** | **The task is ill-posed as labelled.** `posture_fault` = "an annotator marked a knee-forward/inward interval", present in 65.9 % of the corpus; the label encodes a judgement of *degree* on a near-universal behaviour. | §2.3 identity (99.4 %); Phase 2: within-video 80.2 % but **between-video AUROC 0.572** for the underlying predicate; every geometric rule refuted; corpus prevalence 0.659 vs assigned 0.356 | **Sets the ceiling.** A classifier cannot recover a degree threshold that lives in the annotator's head from geometry that the annotator's own interval placement only weakly tracks between clips. The honest numbers hovering at floor+0.02–0.06 are what "some signal, no separable class boundary" looks like. | **re-scoping** (define the target from the predicate that *is* recoverable — localisation, or "any fault" — or relabel against a stated standard); not by retraining on this label |
| **2** | **The mutually-exclusive collapse removed co-occurrence.** 333 knee-interval videos became `depth_fault` and were *dropped* from the binary task; 161 pure posture faults were dropped for balance; 51 stability videos discarded. | §2.4 table; `REBUILT.ipynb:c2.out` 328/70/71 dropped; G-29: 50/71 test depth videos carry posture; 46.5 % of them flagged at deployment | Explains the population gap **0.73 → 0.61** (G-28) and the 0.54 deployment precision: the model is scored on a population it was trained to never see, and its "false positives" there are largely correct per the raw labels. | **retraining** on `original_multi_label` (multilabel targets, no collapse, no undersampling) |
| **3** | **Run-to-run variance with no seed, then selection on it.** The identical notebook produced ≥ 20 runs with val F0.5 **0.589 → 0.742**; the shipped run was chosen by an unrecorded criterion; classical models were ranked on test; the threshold was chosen on the wrong weights and made validation worse. | `c25` (no `manual_seed`); checkpoint list; §6.3–6.4; `c31.out`; `results.json` gain −0.0187 | Explains why *reported* ≫ *honest*: a max over 20 draws with σ ≈ 0.04 sits ~+0.07 above the mean; every "improvement" in the multilabel line (±0.02–0.03) is inside this band (expF2: six ablations span 0.5037–0.5469). | **protocol** (seed, one run or a reported distribution, selection on val only, artifact = evaluated weights) |
| **4** | **Face features carry a domain shortcut.** 87/151 inputs are raw face coordinates; 124 of 126 non-Squat-More videos are Penn and all `good_form`. | §4; G-30: Penn prob_fault 0.239 vs AQA 0.428, freeze shifts +0.177, AUROC 0.762 → 0.801 on mixed populations; −0.052 in-domain when frozen | Explains external recall 0.111 and part of the in-domain number (the model can read "Penn framing = good"). Relative evidence is robust to contamination (common to both arms). | **retraining** body-only (`posture_v2` spec) with Penn either dropped or given fault examples |
| **5** | **Contamination.** 27/244 test videos have a byte-twin in train (19 same-label); 7/50 ablation fixtures; every split file identical. | G-44/G-45; §5.2; `test_eval_split_integrity.py` was green by name | Bounds every historical number as an **upper bound**; magnitude unknown but the 19 same-label twins are memorisable. Does not explain the *honest* number being low. | **content-level splits** (built: `content_level_splits.json`, 11 moves) |
| **6** | **Pose-pass sensitivity.** Training keypoints came from an unrecorded pass; serving uses tracking mode; 14.9 % of verdicts flip on identical input. | §3.1; `2026-09-23-pose-pass-verdict-instability.md`; 11/33 flips from > 0.10 margin | Aggregate −0.025 F1 (CI spans zero); per-user it is the dominant reliability defect. | partly — **train on the serving pass** (`pose_pass_id` recorded), accept the residual as per-item variance to report |
| **7** | **Small n, high floor.** Test n = 41 (clean) / 162–244 (contaminated); prevalence 0.34–0.56 → floors 0.39–0.72; CI half-width 0.07–0.16. | §7.4; Gate 3 | Nothing below ~0.07 is measurable on the contaminated basis, nothing below ~0.16 on the clean one. | **data** (run the remaining ~1,000 videos through the pipeline: Gate 1b) |
| **8** | **Train/serve residue.** Training rejects > 10 % internal missing; serving scores those videos. G-21 (complexity fallback) was real and is fixed. | §3.3; G-21 | 8/174 val videos (4.6 %) fall in the unseen band; effect unmeasured but small. | serving-side rule mirror, or drop the training rule and retrain |
| **9** | **Measured label noise.** Both-ways duplicate pairs cap the historical test at oracle F1 ≈ 0.92. | §8.3 | **Not a cause** of near-floor performance on the evidence available: the cap is 0.4 above the floor. The *unmeasured* portion is unknowable from within (one annotation source). | relabelling (80 second opinions on the conflicted pairs is the cheap first step) |

**Irreducible on this corpus:** cause 1's ceiling under the current label definition; the unknown
part of cause 9. **Fixable by retraining:** 2, 4, partly 6. **Fixable by protocol/data, not by a
model:** 3, 5, 7, 8. **Fixable only by relabelling or re-scoping:** 1, 9.

---

## 11. Recommendation

### 11a. Best honest result available today

There is **no clean, adequately-sized, held-out measurement of PostureV1**. The two candidates:

| candidate | metric | split | n | contamination | CI | verdict |
|---|---|---|---|---|---|---|
| content-level test, shipped weights, threshold 0.525 | F1 **0.4516** (P 0.333, R 0.700) vs trivial floor **0.3922**; majority-class acc 0.756 vs model 0.585 | `content_level_splits.json` test | **41** | **0 %** | ±0.16 (paired bootstrap, `cycle_turn.json`) | **clean but uninformative** — the interval covers the floor |
| user-level test, all classes | F1 **0.6131** [0.5291, 0.6872], AUROC 0.7184, floor 0.5548 | `user_level_multilabel_splits.json` test | 224 | **12.0 %** (27 twins; 19 same-label) | CI lower bound below the floor | **adequately sized but an upper bound** |

The brief's "deployment F1 0.5636 / P 0.4526, n=281" is **not held out**: 199 of its 281 decisions
are content-level *train* videos (§9 #16). It measures what the deployment does on the corpus, which
is a legitimate operational number, but it must not be quoted as generalisation.

Best honest single line: *"On the largest uncontaminated held-out set that exists (n=41, content-level
test), PostureV1 scores F1 0.45 against a 0.39 floor, ±0.16. On the larger contaminated basis (n=224,
12 % of test seen in training) it scores 0.61 [0.53, 0.69] against 0.55, AUROC 0.72. Both are
consistent with a model that has some signal and no usable decision boundary."*

### 11b. Is retraining worth it?

**Ceiling from measured label conflicts: ≥ 0.92** on the historical test (§8.3) — not within 0.05 of
the floor, so **label noise as measured does not preclude retraining.** But the ceiling that matters
is cause 1's, and it is not a noise ceiling: the construct behind `posture_fault` separates videos at
AUROC 0.572. **Retraining on the same label, the same collapse, and the same face block will not move
the honest number**, and given cause 3 any apparent movement below ~0.07 is indistinguishable from
a re-draw.

So: **retrain, but only as a controlled experiment after re-scoping, with a negative-result contract.**
The experiment is worth running because causes 2 and 4 are real, measured, and fixable by training,
and because nothing yet establishes whether the body-only multilabel formulation clears the floor.
Expected outcome, stated in advance: a modest gain on `any_fault` and on posture-with-co-occurrence,
and *no* gain on depth (Phase 2's finding stands regardless of features).

### 11c. What changes, exactly

**Step 0 — make the instrument adequate (no modelling).** Gate 1b: push the remaining ~1,000 usable
videos through the live pipeline so content-level test grows from 41 to ~190 and the CI halves.
Without this no retrain result is measurable.

**Data.**
1. Splits: `bench/results/content_level_splits.json` (`minimal` mode; 11 moves), never the user-level
   file. Dedup map applied first; the 161 conflicted videos stay withheld.
2. Targets: rebuild from `enhanced_labels.original_multi_label` — three independent binary heads
   (`posture` = knee interval, `stability` = knees-inward, `depth` = shallow), **no collapse, no
   undersampling**, plus a derived `any_fault`. Restore the 161 posture-only and 51 stability videos.
3. Penn: exclude the 124 all-good-form Penn videos from training (or include them only with a
   domain feature and a domain-parity gate on the good-form score). Without Penn faults they are a
   shortcut, not data.
4. Pose pass: re-extract training keypoints with the **serving** pass so `pose_pass_id` matches
   (`pp1_f9850424580ae186`); record it in the artifact. The 719-clip calibration cache already is.

**Features.** Body-only (`app/ml/posture_v2/features.py` spec; hip-centred, torso-normalised, 30 fps
resampled), `spec_hash` in the artifact. Drop the 87-D face block entirely; keep the 64-D temporal
angles as a second arm so the delta is attributable.

**Training protocol.** Seed everything; train N ≥ 5 seeds and report the distribution, not the max;
early-stop and threshold on validation only; **save the evaluated weights** (`copy.deepcopy(state_dict)`
or reload from disk before any post-training evaluation — the exact bug in §6.4); one artifact, its
threshold derived on validation from *those* weights.

**Evaluation.** AUROC primary (threshold-free), F1 with bootstrap CI, **both** coverage views, trivial
floor and majority-class accuracy always, per-item flip rate against a second pass, all via
`app/eval/metrics.py`; test read exactly once behind `--final`, the read logged. Acceptance: beat the
incumbent's CI *lower* bound on the same content-level test, else it is a negative and is written up
as one.

**Re-scoping the product claim (independent of the retrain).** The predicate that *is* recoverable
is temporal: 80.2 % within-video agreement for knees-forward. Ship localisation ("knees travelled
forward at 1.4 s") as the claim, and `any_fault` as the only binary verdict, until a per-video
posture verdict clears its floor on a clean test with n ≥ 190.

---

## 12. Gap list — ranked by how much fixing it moves the honest number

| # | gap | evidence | if fixed | effort |
|---|---|---|---|---|
| 1 | Label defines a degree judgement on a near-universal behaviour (posture = knee interval) | §2.3, §10.1, AUROC 0.572 | changes what is being asked; only route to a verdict that clears the floor | **L** (relabel or re-scope) |
| 2 | Collapse drops 333 co-occurring posture faults + 161 pure ones from training; no code for it | §2.4 | restores ~45 % more positives and the co-occurrence the deployment sees; expected to close much of the 0.73→0.61 population gap | **M** (rebuild targets from `original_multi_label`) |
| 3 | No held-out measurement of adequate size exists (clean n=41) | §11a | makes any other fix measurable | **S** compute (Gate 1b) |
| 4 | 87-D face block, Penn all-good-form | §4, G-30 | removes a measured shortcut; −0.052 in-domain is the cost of losing a proxy, not of losing signal | **M** (v2 spec exists; retrain) |
| 5 | No seed; ≥ 20 runs; shipped run chosen by unrecorded criterion; classical ranked on test | §6.2–6.3, §7.3 | every future delta becomes interpretable | **S** |
| 6 | Shipped weights ≠ evaluated weights (shallow copy); threshold from wrong model; val-optimal is 0.475 | §6.4, §7.2 | manifest numbers become reproducible; threshold correction is free (+0.034 val F0.5) — but do **not** re-tune on the contaminated basis | **S** code / **M** re-export |
| 7 | Training pose pass unrecorded; serving pass differs; 14.9 % flips | §3.1 | per-user reliability; retrain on serving pass removes the train/serve component | **M** (re-extract; cache exists for 719) |
| 8 | Test contaminated 11–14 % in every historical split file | §5.2 | already fixed by `content_level_splits.json`; historical numbers stay caveated | done / **S** to adopt |
| 9 | Training's > 10 % missing-frame rejection not mirrored at serving | §3.3 | 4.6 % of inputs currently scored blind | **S** |
| 10 | 80 same-clip pairs labelled both ways; 62 % cross-filed | §8.2 | 80 second opinions resolve the only measurable label conflicts; also tells whether the source dataset or the copy did this | **S** (annotation) |
| 11 | `06f_metrics.json` fabricated; `ML_REPO_TRUTH_EXTRACTION.md` names the wrong checkpoint | §0.6, §6.3 | removes two false statements from the record | **S** |
| 12 | Depth: no recoverable signal on this corpus; 47 pairs labelled both ways | Phase 2, §8 | none by modelling; leave `depth_score` NULL | — |
| 13 | Jun-2025 XGBoost numbers (F1 0.86–0.90, n=36) still on disk with no provenance | §9 #1 | none; retire | **S** |

---

*End of Phase 1. Nothing was modified except this file. No branch, no commit. Phase 2 waits for "go".*

---

## Addendum — Phase 2 Step 0 executed (2026-09-23, branch `ml/gate1b-full-corpus`)

§11a said no clean, adequately-sized held-out number existed. Gate 1b pushed the remaining
1,021 usable videos (plus a 263-video recovery batch, see G-48) through the live pipeline. The
content-level **test** split now has **n = 188** stored PostureV1 decisions (was 41); the
evaluation reads `checker_decisions` through `backend/scripts/eval_runner.py --splits content`,
metrics from `app/eval/metrics.py`, bootstrap n=2000 seed 0.

| split | n | covered | prevalence | AUROC [95 % CI] | F1 covered-only [95 % CI] | F1 abstain-as-neg [95 % CI] | floor F1 |
|---|---|---|---|---|---|---|---|
| **test** | 188 | 177 (94.1 %) | 0.415 | **0.7057 [0.6246, 0.7808]** | **0.6036 [0.5135, 0.6854]** | 0.5829 [0.4937, 0.6630] | 0.5865 |
| validation | 212 | 189 (89.2 %) | 0.387 | 0.7783 [0.7072, 0.8469] | 0.6333 [0.5484, 0.7097] | 0.6000 [0.5161, 0.6796] | 0.5578 |
| train | 901 | 823 (91.3 %) | 0.422 | 0.7611 [0.7266, 0.7954] | 0.6380 [0.5974, 0.6762] | 0.5950 [0.5534, 0.6341] | 0.5933 |

**Best honest single line now:** *On a clean content-level held-out set of 188 videos, PostureV1
separates posture faults at AUROC 0.71 [0.62, 0.78] and scores F1 0.60 [0.51, 0.69] at its
shipped threshold against an all-positive floor of 0.59. The F1 interval contains the floor; the
AUROC interval does not contain 0.5.* Some signal, no usable decision boundary — the §11a reading,
now at an n that can carry it. The contaminated user-level number (F1 0.6131, AUROC 0.7184, n=224)
sits within 0.02 of the clean one, so G-44's caveat stands but its practical effect on the posture
figure was small.

A second cycle turn at this n (`bench/cycle_turn.py`) is still a negative: threshold 0.69 chosen on
validation, ΔF1 on test −0.0509 [−0.1349, +0.0272]. The interval halved and the answer did not
change: the incumbent's threshold is not the lever. The controlled retrain (§11c) is the next step
and was pre-registered before this addendum was written (`bench/retrain/PREREGISTRATION.md`).
