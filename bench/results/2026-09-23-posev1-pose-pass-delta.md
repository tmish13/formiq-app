# PostureV1 re-scored on live keypoints: the aggregate holds, 1 in 7 verdicts does not

**Date:** 2026-09-23 · **Branch:** `audit/phase2-depth-rule`
**Question:** how much of the train/serve gap is the pose pass alone?

The pinned v1 numbers were computed on **dataset** keypoints — a different MediaPipe run from the
one the container serves. This re-scores the identical model on **live-extracted** keypoints
(`_extract_pose_from_video`, complexity 2, fresh tracker per video) so the difference is
attributable to the pose pass and nothing else.

**The pinned numbers are not replaced.** They stand as the published result on the data they were
computed from.

## Paired comparison, same 221 videos

Both runs restricted to the videos they share, so this is not a comparison across different `n`:

| | F1 | AUROC | precision | recall |
|---|---|---|---|---|
| dataset keypoints | 0.6154 | 0.7227 | 0.5405 | 0.7143 |
| live keypoints | **0.5905** | **0.6952** | 0.4921 | 0.7381 |
| delta | **−0.0249** | **−0.0275** | −0.0485 | +0.0238 |

**Paired bootstrap** (2000 resamples, seed 0, same videos both arms):

| | delta | 95% CI |
|---|---|---|
| F1 | −0.0246 | **[−0.0786, +0.0296]** |
| AUROC | −0.0279 | **[−0.0697, +0.0142]** |

**Both CIs include zero.** On aggregate the pose pass is not measurably costing anything. The
honest statement is: *the pose-pass contribution to the train/serve gap is around −0.025 F1 and
is not distinguishable from zero at this sample size.*

The pinned figures for reference (n=224, dataset keypoints): F1 0.6131 CI [0.5291, 0.6872],
AUROC 0.7184.

## The number that matters more

| | |
|---|---|
| per-video \|prob_fault delta\| | median **0.0621**, p90 **0.2183**, max **0.6080** |
| **decisions that flipped** | **33 / 221 = 14.9%** |

**The aggregate is stable. The individual answers are not.**

One in seven users would receive a different verdict depending on which MediaPipe pass ran, on
byte-identical input, from the same model at the same threshold. The population-level metric
conceals that completely, because the flips go both ways and cancel.

This is the same failure mode as the Phase 1 tracker leak — same bytes, different verdict — from a
different cause. There the predecessor video moved the score by up to 0.214; here the pose pass
moves it by up to 0.608. Both are invisible in an F1.

## Secondary finding: on live keypoints, v1 is not separable from the trivial floor

On the live pass, F1 **0.5905** against an all-positive trivial floor of **0.5508** — ahead by
0.04 — and the 95% CI is **[0.5096, 0.6696]**, whose lower bound sits **below the floor**.

The same was already true of the pinned run (F1 0.6131, floor 0.5548, CI lower bound 0.5291),
and is pinned as a test in `tests/unit/test_metrics_parity.py`. The live pass does not change
that conclusion; it makes it slightly starker.

## What to do with this

1. **Quote the pose-pass delta as −0.025 F1, CI including zero.** Not "the pose pass costs
   nothing" and not "the pose pass explains the gap". Neither is supported.
2. **Quote the 14.9% flip rate whenever per-user reliability is the subject.** It is the number
   that describes what a user experiences, and it is 6× larger than the aggregate effect.
3. **Do not re-baseline the published numbers.** The delta is within noise; churning the
   headline to chase it would be movement without information.

## Reproduce

```bash
docker run --rm -m 6g --network deployment_default \
  -v $PWD/backend:/app -v $PWD:/repo \
  -v "$HOME/FORMIQ Form Analysis Model/data/squat_processed:/splits:ro" \
  -e POSTGRES_SERVER=db -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=formiq -e SECRET_KEY=dev-only-insecure-secret-key-32chars-minimum \
  -e REDIS_HOST=redis -e REDIS_PORT=6379 -w /app deployment-worker:latest \
  python /repo/bench/depth_rule_eval.py --split test --final
```

Raw: `bench/results/depth_rule_eval_test.json`

## Note on the test split

This is the one look at test, spent on **evaluating an already-trained model**, not on selecting
or tuning anything. No rule was fitted against it, and the three fault rules were all killed on
train before this ran.
