# Stage 0b GATE — do the dataset's keypoints match what we serve?

**Date:** 2026-09-22 · **Branch:** `audit/phase2-depth-rule`
**Script:** `bench/keypoint_provenance.py` · **Verdict:** PASSES on correlation, **but do not
calibrate on dataset keypoints**

## Why this gate is central

Under the definitional design the *entire* calibration is a landmark offset. If the dataset's
pose pass differs from the container's MediaPipe, that offset does not transfer and the rule is
mis-calibrated in production by exactly the disagreement. So this measures **bias**, not just
correlation — the verdict is `sign(I2)`, and a bias shifts every call.

40 videos selected stratified by class; 34 produced comparable pairs; **3,401 paired frames**.
Container MediaPipe at **complexity 2**.

## 1. Correlation — PASS, with one marginal

| indicator | n | Pearson r | gate (≥0.90) |
|---|---|---|---|
| `I1` femur incline | 3,401 | **+0.9124** | PASS — *marginal* |
| `I2` hip-knee delta | 3,401 | **+0.9413** | PASS |
| `I3` knee flexion | 3,401 | **+0.9290** | PASS |
| `I4` hip flexion | 3,401 | **+0.9206** | PASS |

⚠️ **`I1` is sample-sensitive and sits on the gate.** At n=30 videos it measured **0.8952 —
a FAIL**; at n=40 it measures 0.9124. An indicator that changes verdict with sample size should
not be load-bearing. `I1` is retained as corroboration only; the verdict rests on `I2`.

## 2. Bland–Altman bias — the number that matters

| indicator | bias (live − dataset) | sd | 95% limits of agreement |
|---|---|---|---|
| `I1` femur incline | −3.97° | 13.58 | [−30.58, +22.64] |
| **`I2` hip-knee delta** | **+0.0108** | **0.0968** | **[−0.1790, +0.2006]** |
| `I3` knee flexion | −5.13° | 15.17 | [−34.87, +24.61] |
| `I4` hip flexion | −6.86° | 15.69 | [−37.60, +23.89] |

The `I2` bias is **+0.0108 torso-lengths — live reads *deeper* than the dataset.**

For scale: the discriminative range of `I2` between shallow bottoms (≈ +0.005) and deep bottoms
(≈ −0.319) is about **0.32 torso-lengths**. So the bias is ~3% of the range — small. But the
**limits of agreement are ±0.19, roughly 60% of the range**, meaning an individual frame can
differ enormously between passes.

## 3. Verdict agreement — 80%, and every flip in the same direction

| | |
|---|---|
| videos compared | 30 |
| definitional verdict agrees | **24/30 (80.0%)** |

All six flips, `I2` at the bottom (dataset → live):

```
-0.0074  ->  +0.1254
-0.0743  ->  +0.1430
-0.0439  ->  +0.0399
-0.0019  ->  +0.0165
-0.0111  ->  +0.0101
-0.0371  ->  +0.0155
```

**Every flip is dataset-shallow → live-at-depth.** Six out of six in one direction is systematic,
not noise, and it matches the sign of the `I2` bias.

### Abstaining absorbs it

Agreement among calls *both* passes make confidently, by deadband `m` on `|I2|`:

| `m` | both confident | coverage | agreement |
|---|---|---|---|
| 0.00 | 30 | 100.0% | 80.0% |
| 0.01 | 26 | 86.7% | 84.6% |
| **0.02** | 24 | **80.0%** | **91.7%** |
| 0.03 | 23 | 76.7% | 91.3% |
| 0.05 | 18 | 60.0% | 94.4% |
| **0.08** | 17 | **56.7%** | **100.0%** |
| 0.10 | 15 | 50.0% | 100.0% |

The pose-pass disagreement lives **entirely near parallel**. Declining to call a squat that is
within `m` of parallel — which is what a human does from an imperfect angle — removes it. This is
independent evidence that the abstain design is load-bearing rather than decorative.

## 4. Rep-bottom agreement

`|bottom frame delta|` median **1**, mean 4.1, max 59. **28 of 34 videos agree within 3 frames.**
Single-rep `argmax(smoothed hip_y)` is stable across pose passes; the tail is a handful of
clips where one pass loses the subject.

## 5. A bug found in this gate, worth recording

The first run required **all eight** core landmarks (11,12,23,24,25,26,27,28) at visibility ≥ 0.4.
That rejected 11 of 30 videos outright.

Inspection showed why: `32991_2` has left-side visibility 0.93–1.00 and **right knee 0.198,
right ankle 0.225**. `33499_1` is the mirror. These are **side views** — one leg occludes the
other. The gate was rejecting precisely the videos where depth is *most* measurable.

Fixed to **per-side gating** (a side is usable when its shoulder/hip/knee/ankle are all visible),
matching what `app/ml/posture_v1/geometry.py:compute_knee_angles` already does. Effect:

| | both-sides gate | per-side gate |
|---|---|---|
| paired frames | 1,269 | **3,401** |
| frames matched | ~50% | **86.9%** |
| verdict comparisons | 8 | **30** |

⚠️ **This invalidates the earlier "53% of frames fail the visibility gate" estimate** from the
Stage 0 probe, which used the same both-sides rule. Real usable-frame coverage is **86.9%**, not
~47%. The coverage risk recorded in the plan was overstated by that bug.

## Gate verdict

**Correlation: PASS** for all four indicators — so none is dropped under the declared rule, with
`I1` flagged as marginal and demoted to corroboration.

**But the actionable conclusion is different from the pass/fail.** A +0.0108 systematic bias with
±0.19 limits of agreement means **an offset fitted on dataset keypoints would be wrong at
serving**, and the 80% raw verdict agreement shows what that costs.

**Recommendation: calibrate on container-extracted keypoints instead.** The source videos are
present (1,724 in `Labeled_Dataset/videos`), so the transfer problem is avoidable rather than
something to be corrected for. Extract with the live path — `_extract_pose_from_video`,
complexity 2, tracker reset per video — and fit the offset on those. Transfer error then becomes
zero by construction, and the dataset keypoints are reduced to what they should be: a
cross-check.

## Reproduce

```bash
docker run --rm -m 4g --network deployment_default \
  -v $PWD/backend:/app -v $PWD:/repo \
  -v "$HOME/Desktop/Squat More/Labeled_Dataset/videos:/videos:ro" \
  -v "$HOME/Desktop/Squat More/Labeled_Dataset/processed_videos/keypoints:/keypoints:ro" \
  -v "$HOME/FORMIQ Form Analysis Model/data/squat_processed:/splits:ro" \
  -e POSTGRES_SERVER=db -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=formiq -e SECRET_KEY=dev-only-insecure-secret-key-32chars-minimum \
  -e REDIS_HOST=redis -e REDIS_PORT=6379 -w /app deployment-worker:latest \
  python /repo/bench/keypoint_provenance.py --n 40
```

Raw: `bench/results/keypoint_provenance.json`
