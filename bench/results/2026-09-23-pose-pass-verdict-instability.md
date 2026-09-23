# One in seven verdicts changes with the pose pass, and no aggregate metric shows it

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

**Date:** 2026-09-23 · **Branch:** `audit/phase2-depth-rule`
**Script:** `bench/posepass_flip.py` · **Raw:** `bench/results/posepass_flip.json`
**Data:** 221 test videos scored twice by the same PostureV1 weights at the same threshold.

The only thing that differs between the two runs is which MediaPipe pass produced the
keypoints — the **dataset** pass that every pinned v1 number was computed on, versus the
**live** pass `_extract_pose_from_video` performs inside the worker (complexity 2, fresh
tracker per video). Same model, same threshold 0.525, same videos, byte-identical footage.

**Headline: 33 of 221 verdicts flip — 14.9% — while the paired CI on aggregate F1 spans zero.**

This is the Phase 2 result worth carrying forward, more than the depth rule's negative.

## The aggregate says nothing happened

| | F1 | AUROC | precision | recall | tp / fp / tn / fn |
|---|---|---|---|---|---|
| dataset keypoints | 0.6154 | 0.7227 | 0.5405 | 0.7143 | 60 / 51 / 86 / 24 |
| live keypoints | 0.5905 | 0.6952 | 0.4921 | 0.7381 | 62 / 64 / 73 / 22 |

**Paired bootstrap** — 2000 resamples, seed 0, videos resampled *once* and both arms scored
on the same resample, so between-video variance does not leak into the interval:

| delta | point | 95% CI | |
|---|---|---|---|
| F1 | **−0.0249** | **[−0.0786, +0.0296]** | includes zero |
| AUROC | **−0.0275** | **[−0.0697, +0.0142]** | includes zero |

The defensible statement is: *the pose pass costs about 0.025 F1, not distinguishable from
zero at n=221.* Neither "the pose pass is free" nor "the pose pass explains the gap" is
supported.

## The per-video picture is not the same picture

| | |
|---|---|
| \|prob_fault delta\| | median **0.0621** · p75 0.1318 · p90 **0.2183** · p95 0.2884 · max **0.6080** |
| **verdicts flipped** | **33 / 221 = 14.9%** |
| direction | **24 negative→positive**, 9 positive→negative |
| accuracy of the flips | 11/33 toward the label, **22/33 away** |

The flip rate is **6× the aggregate effect**, and it is not concentrated in one class:
depth_fault 10/71 (14.1%), good_form 11/66 (16.7%), posture_fault 12/84 (14.3%).

**The flips do not cancel — they are asymmetric.** The live pass produces 13 more false
positives (51 → 64) against 2 more true positives. It is measurably more fault-prone. The
reason F1 barely moves is that precision and recall absorb the asymmetry in opposite
directions (P −0.048, R +0.024), not that the two passes agree.

## Section 4: they are not threshold jitter

The obvious deflation is that these are all borderline cases sitting on 0.525, where any
perturbation flips the sign and nothing is really wrong. Measured against the margin
`|dataset probability − threshold|`:

| flips originating within | count |
|---|---|
| margin ≤ 0.02 | 6 / 33 (18%) |
| margin ≤ 0.05 | 13 / 33 (39%) |
| margin ≤ 0.10 | 22 / 33 (67%) |
| **margin > 0.10** | **11 / 33 (33%)** |

**A third of the flips start well outside any plausible jitter band.** The five furthest:

| video | class | dataset → live | delta | margin |
|---|---|---|---|---|
| `50462_7` | good_form | 0.102 → 0.549 | +0.447 | 0.423 |
| `49295_2` | good_form | 0.275 → 0.770 | +0.495 | 0.250 |
| `50838_1` | good_form | 0.321 → 0.730 | +0.409 | 0.204 |
| `50264_2` | posture_fault | 0.715 → 0.486 | −0.230 | 0.190 |
| `48621_2` | posture_fault | 0.711 → 0.103 | **−0.608** | 0.186 |

`48621_2` goes from a confident fault to a confident pass. `50462_7` goes from a confident
pass to a fault. These are not ties being broken differently; the model's mind is changed by
the pose pass alone.

## Why this is the headline and the F1 delta is not

An F1 is an average over users. A verdict is what one user receives. When the errors
introduced by a change are roughly balanced in sign, the average is preserved exactly while
the individual answers are scrambled — and the aggregate metric will report success
throughout. Here the balance is not even perfect (24 vs 9) and F1 still moves less than its
own noise floor.

This is the **same failure mode as the Phase 1 MediaPipe tracker leak, from a different
cause**. There, the predecessor video shifted a score by up to 0.214 and the fix drove the
spread to 0.000000. Here the pose pass shifts it by up to 0.608, and there is no fix — the
dataset pass is not reproducible and never will be. Both are invisible in any population
metric.

## Consequences

1. **A verdict is only reproducible against a named pose pass.** `spec_hash` alone does not
   identify the computation that produced a decision; the extraction contract — MediaPipe
   version, model complexity, `static_image_mode`, detection/tracking confidences, target
   fps — is a co-equal input. Stage A therefore records **`pose_pass_id`** on `analysis_runs`
   beside `spec_hash`. This measurement is the justification for that column: without it the
   column is bookkeeping, with it the column is the difference between 14.9% of verdicts
   being explicable and being mysterious.
2. **Do not re-baseline the pinned numbers.** The delta is inside its own CI; chasing it
   would be movement without information. The pinned figures stand as the published result
   on the data they were computed on
   (n=224, F1 0.6131 CI [0.5291, 0.6872], AUROC 0.7184).
3. **Quote 14.9% whenever per-user reliability is the subject**, and the F1 delta whenever
   population performance is. They are answers to different questions and neither
   substitutes for the other.
4. **Any future model comparison reports per-item flip rate alongside the aggregate.** This
   run is the argument that the aggregate alone can be stable while the product is not.

## Secondary: on live keypoints v1 is not separable from the trivial floor

F1 **0.5905** against an all-positive floor of **0.5508** on this split, and the pinned run's
95% CI lower bound (0.5291) already sat below its own floor (0.5548). The live pass does not
change that conclusion, it makes it slightly starker. Pinned as a test in
`tests/unit/test_metrics_parity.py`.

## Reproduce

Offline — joins two stored score files, no container, no torch, no DB:

```bash
python bench/posepass_flip.py
```

Inputs: `bench/results/2026-09-19-v1-test-per-video-scores.json` (dataset pass, frozen) and
`bench/results/depth_rule_eval_test.json` (live pass). The latter was produced by the single
`--final` run against test described in `2026-09-23-posev1-pose-pass-delta.md`.

## Note on the test split

Test was opened once, to **evaluate an already-trained model**. Nothing was selected or tuned
against it; all three fault rules were killed on train before this ran.
