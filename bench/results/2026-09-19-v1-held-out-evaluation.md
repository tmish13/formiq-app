# v1 on the recovered held-out test split — the manifest's 0.724 does not reproduce

> **⚠️ G-44 — these figures were measured on contaminated data.** 45 cross-split
> byte-identical duplicate videos were discovered *after* this was written. 27 of the
> 224 videos in the pinned evaluation (12.0%) have a byte-identical twin in the TRAIN
> split — 19 share the `posture_fault` label (memorisation, optimistic) and 8 carry a
> conflicting label (direction unclear), so the bias is predominantly but not purely
> optimistic. The duplicate scan covered 1,487 of 1,625 corpus entries, so 27 is a
> **lower bound**. Every number below is an **upper bound on true performance, not an
> estimate**. Deliberately **not re-measured**: re-measuring after a data change is how a
> negative result quietly becomes a positive one.
> See `bench/results/2026-09-23-corpus-duplicates.md` and `bench/contamination_scope.py`.

**Date:** 2026-09-19
**Scripts:** `bench/eval_v1_test_split.py`, `bench/one_video_diff.py`
**Raw:** `2026-09-19-v1-test-split.json`, `2026-09-19-one-video-diff.json`
**Audit refs:** G-25 (reframed again), G-28 (new)

---

## Headline

| metric | measured (224/244) | manifest claims (244) |
|---|---|---|
| **F1** | **0.6131**  95% CI **[0.5291, 0.6872]** | 0.7237 |
| precision | **0.5398** | 0.7432 |
| recall | **0.7093** | 0.7051 |
| AUROC | 0.7184 | — |
| TP/FP/TN/FN | 61 / 52 / 86 / 25 | — |
| trivial floor (always-fault) | 0.5548 | — |

**The 95% CI excludes 0.7237.** This is a statistically meaningful shortfall, not
sampling noise. The model sits **0.058 above the trivial always-predict-fault
floor**, and the CI's lower bound (0.529) is *below* that floor.

## Coverage — report this as "224/244, Fitness-AQA only"

224 of the 244 test videos have keypoints. The missing 20 are **exactly the 20
Penn Action clips** in the test split (4-digit ids `1660…1874`); every one of the
224 present is Fitness-AQA. They are not "videos that failed MediaPipe" — they
are a different source dataset that is not in the `Squat More` folder.

**Label mix of the missing 20: 0 posture_fault, 20 not_fault — all negatives.**

That matters for the direction of the bias, and it is the opposite of a free
pass. F1 ignores true negatives, so adding the 20 back can only hold F1 constant
(if all become TN) or lower it (each FP hurts precision):

    all 20 -> TN :  F1 stays 0.6131
    all 20 -> FP :  F1 falls to 0.5568

**So 0.6131 is an upper bound on the true 244-video F1, which lies in
[0.557, 0.613].** Never quote this as "test F1"; quote it as
"F1 0.613 on 224 of 244 held-out videos, Fitness-AQA only, upper bound".

## The specific defect: recall reproduces, precision does not

Reconstructing the manifest's confusion matrix from its own precision/recall on
86 positives:

```
manifest-implied : TP ~61   FP ~21
measured         : TP  61   FP  52
```

**Identical true positives. ~31 extra false positives.** Recall matches almost
exactly (0.7093 vs 0.7051); precision collapses (0.540 vs 0.743).

The model finds the same faults the original evaluation found — it additionally
flags 31 good squats as faults. **Serving skews high on `prob_fault`.**

## The one-video diff independently confirms the same direction

Target: `T6ad8Et3C5Q_good_rep_1.mp4` — eval CSV `prob_fault 0.0001`, serving `0.3347`.

The `frames=89` vs `orig_frames=90` lead is **dead**:

- At complexity 2 the container now gets **90/90 valid detections** (it was 66/90
  at complexity 1, so the G-21 fix closed that gap), matching the CSV's 89.
- `sequence_length` sweep from 60 to 300 spans **[0.1469, 0.6166]**.
  **0.0001 is outside that entire range** — sequence length alone cannot produce it.
- 89 vs 90 frames moves `prob_fault` by only **+0.014** (0.3206 → 0.3347).

The features that move are all temporal angle statistics
(`left_hip_angle_ascent_mean`, `right_knee_angle_bottom_std`, …), which confirms
the earlier ablation finding that the effect acts through the engineered
features rather than the LSTM — but the magnitude is nowhere near enough.

Both measurements point the same way: **serving produces systematically higher
`prob_fault` than whatever produced the original numbers.**

## What this means for G-25

The earlier framing ("serving reproduces training-time performance; the gap is
the eval set") was based on the n=50 balanced fixture run (F1 0.769). That run is
**not comparable** to the manifest's 244-video number — different prevalence,
different F1 floor, ±0.07 at n=50. On the proper held-out set the model scores
**0.613 [0.529, 0.687]**, and the manifest's 0.724 is outside the interval.

So the residual gap is **not** purely an eval-set property. There is a real,
measurable discrepancy between this pipeline and whatever produced the shipped
metrics, and it is **precision-shaped**.

## Also settled

**No contamination.** All 24 videos in the external eval set resolve to
`NOT_IN_SPLIT` — none appear in train, validation or test. The 0.72 → 0.18
comparison is genuinely out-of-sample.

**Two different splits exist.** The original Fitness-AQA `Splits/test_keys.json`
(Nov 2022, 244 entries) and the recovered `user_level_multilabel_splits.json`
(244 entries) **overlap on only 38 ids**. The recovered split is the one whose
sizes match the model manifest and is a *combined* corpus:

| split | Fitness-AQA | Penn Action |
|---|---|---|
| train | 1050 | 87 |
| validation | 227 | 17 |
| test | 224 | 20 |

So Penn Action was ~8% of v1's training data — the external eval set is a
different sample of a partially-seen domain, not a wholly unseen one.

**1739 keypoints vs 1724 videos.** 15 keypoint files have no source video; 0
videos lack keypoints; no `copy`-suffixed duplicates in the directory. The eval
joins on split membership, so no double-counting.

## Open — G-28

Find what produces ~31 fewer false positives in the original evaluation.
Candidates, untested:

- a different checkpoint than `posture_v1.pt`
- a different feature extractor — note `fixed_cells_v3_v8_v10_feature_expand_pooling_noleak.ipynb`
  builds its 87D from **body joints and angles**, not face coordinates
- a different decision threshold or a calibration step applied before thresholding
- keypoints extracted by a different pose pass than the container's

The cheapest discriminator: run the original eval path end-to-end on 5 test
videos and compare `prob_fault` per video against this run.

## Reproduce

```bash
docker compose -f backend/deployment/docker-compose.yml run --rm --no-deps \
  -v "$HOME/Desktop/Squat More/Labeled_Dataset/processed_videos/keypoints:/keypoints:ro" \
  -v "$HOME/FORMIQ Form Analysis Model/data/squat_processed:/splits:ro" \
  -T app python - < bench/eval_v1_test_split.py

docker compose -f backend/deployment/docker-compose.yml exec -T app \
  python - < bench/one_video_diff.py
```
