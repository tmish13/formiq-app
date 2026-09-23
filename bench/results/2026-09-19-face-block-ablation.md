# Face-block ablation — where does PostureV1's signal actually come from?

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
>
> **This file's own population: 7 of its 50 fixtures (14.0%) have a byte-identical
> twin in train.** `test_eval_split_integrity.py::test_every_ablation_fixture_is_held_out`
> passes on all seven, because it checks split membership by *name* rather than by
> content (G-45). The 0.769 baseline was already retracted for a separate reason
> (G-25: an n=50 balanced-fixture run is not comparable to natural prevalence); this
> is a second, independent defect in the same number.

**Date:** 2026-09-19
**Script:** `bench/ablate_face_block.py` (bench only — the serving path was not touched)
**Raw summary:** `2026-09-19-ablation-summary.json`
**Audit refs:** G-24 (resolved here), G-25 (reframed here)

---

## Why this ran

Resolving G-24 established that 87 of PostureV1's 151 features are raw,
unnormalised **face**-landmark coordinates. The hypothesis was that this block is
camera-framing noise, and the leading suspect for the residual eval gap (G-25):
move the camera, and 87 inputs leave the scaler's training distribution while the
features that describe the squat do not.

This ablation tests that hypothesis with a number instead of an argument.

## Feature layout (verified against training source, pinned by tests)

| indices | count | content |
|---|---|---|
| `[0:33]` | 33 | `joint{0..10}_{x,y,z}_mean` — MediaPipe 0–10 = nose, eyes, ears, mouth |
| `[33:66]` | 33 | `joint{0..10}_{x,y,z}_std` — same face joints |
| `[66:87]` | 21 | `joint{0..6}_{x,y,z}_range` — nose + both eyes |
| `[87:147]` | 60 | 4 angles × 15 stats — squat biomechanics |
| `[147:151]` | 4 | derived (trunk wobble, knee asymmetry, forward lean) |

MediaPipe body landmarks start at index **11** (`LEFT_SHOULDER`), so features
0–86 contain **zero body joints**: 57% of the model's tabular input is "where is
the head in the frame".

## Method

- **Data:** `backend/tests/fixtures/pose_data/in_domain_accuracy/` — 50 labelled
  pose fixtures, perfectly balanced (25 `good_form` / 25 `posture_fault`),
  sources `penn_action` and `squat_more`. Precomputed keypoints, so MediaPipe
  variance is eliminated and the run is deterministic.
- **Ablation = freeze the block at the scaler's training mean**, so the value
  after standardisation is exactly `0.0` — the neutral point of the training
  distribution. Zeroing the *raw* value would instead send it to `-mean/scale`,
  far out of distribution, and would measure the wrong thing.
- Threshold 0.525 (the shipped value). Positive class = `posture_fault`.
- The keypoint branch (`[300,33,3]` → CNN-LSTM) is **never** ablated; only the
  151 tabular features fed to the fusion MLP.

## Results (n = 50)

| arm | frozen | F1 | precision | recall | acc | ΔF1 |
|---|---|---|---|---|---|---|
| **baseline** | — | **0.7692** | 0.7407 | 0.8000 | 0.76 | — |
| `face_mean_std` | `[0:66]` | 0.7170 | 0.6786 | 0.7600 | 0.70 | −0.0522 |
| `face_all` | `[0:87]` | 0.7170 | 0.6786 | 0.7600 | 0.70 | −0.0522 |
| `temporal` | `[87:151]` | 0.7273 | 0.6667 | 0.8000 | 0.70 | −0.0419 |
| `all_features` | `[0:151]` | 0.6667 | 0.5000 | 1.0000 | 0.50 | −0.1025 |
| *reference: always-predict-fault* | — | *0.6667* | *0.5000* | *1.0000* | *0.50* | — |

## What this says

**1. The face-block hypothesis for G-25 is NOT supported.**
Freezing all 87 face features costs **0.052 F1**. The model keeps 0.717 on pure
biomechanics. A block worth 0.05 F1 cannot explain a 0.72 → 0.18 collapse. It is
not the cause of the residual gap.

**2. `all_features` reproduces the trivial classifier exactly.**
TP=25, FP=25, TN=0, FN=0 — identical to always-predicting "fault". With all 151
tabular features neutralised, **the keypoint CNN-LSTM branch contributes no
discriminative power at this threshold**. Every bit of separation comes from the
engineered features.

**3. The two feature blocks are largely redundant.**
Removing either leaves ~0.72; removing both collapses to 0.667. They encode
overlapping information rather than complementary information — which is why the
face block looks "useless" in isolation but is not free to delete.

> **SUPERSEDED 2026-09-19** — point 4 below is wrong. The n=50 balanced fixture set is not
> comparable to a 244-video natural-prevalence number. On the recovered held-out split v1
> scores **F1 0.6131 [0.5291, 0.6872]**, and the CI excludes the manifest's 0.7237.
> See `2026-09-19-v1-held-out-evaluation.md`. The ablation's *relative* arm comparisons
> (face vs temporal vs all) are unaffected — only the absolute-baseline claim is retracted.

**4. The most important number here is the baseline.**
In-domain F1 **0.769**, against the manifest's recorded test F1 of **0.724**.
**The serving pipeline reproduces training-time performance.** After the G-21
complexity fix, serving is not degrading the model.

## Consequence for G-25

If serving reproduces the training metric on in-domain data (0.769 vs 0.724), then
the 24-video end-to-end result (F1 **0.182**) is not caused by the pipeline, by
parity, or by feature design. It is a property of **that eval set** — domain shift
(different cameras, framing, cadence) and/or its labels, which the eval report
itself flags (`"user: actually good form — Penn Action mislabel"` on several rows).

G-25 should therefore move off "pipeline investigation" and onto:
- re-examining the 24-video labels, and
- characterising how far those videos sit outside the training distribution.

## Honest caveats

- ~~**These 50 fixtures may overlap the training split.**~~ **RESOLVED 2026-09-19.**
  The v1 split was recovered from the training repo
  (`data/squat_processed/user_level_multilabel_splits.json`) into
  `backend/app/ml/posture_v1/artifacts/posture_v1_splits.json`. **All 50 fixtures
  are in the TEST split**, and the split is `user_level_splits: true` (one video
  per user, 1625 users), so there is no subject leakage. Validation/test sizes
  (244/244) match the model manifest exactly.

  **The 0.769 baseline is therefore a legitimate held-out number**, and it is
  slightly *better* than the manifest's recorded test F1 of 0.724 on the same
  244-video test split. The conclusion strengthens: serving reproduces
  training-time held-out performance. Pinned by
  `backend/tests/unit/test_eval_split_integrity.py`.
- n = 50, one threshold, no confidence intervals. Differences of ±0.05 F1 on 50
  samples are ~2–3 videos and are not individually significant.
- `face_mean_std` and `face_all` scoring identically is expected — the 21 range
  features are a small, highly correlated addition to the same face joints.

## Reproduce

```bash
docker compose -f backend/deployment/docker-compose.yml exec -T app \
  python - < bench/ablate_face_block.py
```

## Recommendation

**Do not retrain to remove the face block on this evidence.** It buys at most
0.05 F1 and the ablation shows the blocks are redundant, so dropping 87 inputs
would likely cost more than it gains. The higher-value work is establishing
whether the 24-video eval set is mislabelled or out-of-distribution — that is
where the 0.72 → 0.18 actually lives.
