# The MediaPipe tracker carries state between videos — confirmed

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

**Date:** 2026-09-19 · **Phase 0** · **Bench only, nothing changed**
**Script:** `bench/mediapipe_state_leak_test.py`
**Explains:** the 17/20 parity failure in `2026-09-19-celery-parity-20.json`

## Result

Same video (`33387_1`), same bytes, same code, same container. Only the video processed
*before* it differs:

| condition | `prob_fault` | shift vs cold |
|---|---|---|
| cold tracker, run 1 | 0.618214 | — |
| cold tracker, run 2 | **0.618214** | **0.000000** |
| after `33348_2` | 0.439524 | **−0.178690** |
| after `36049_2` | 0.652968 | +0.034754 |
| after itself | 0.586389 | −0.031825 |

**Two findings, and the second one is the good news:**

1. **A video's score depends on its predecessor.** Spread 0.439 → 0.653 = **0.214 wide**,
   and it **straddles the 0.525 threshold** — the preceding video can flip the decision.
2. **The pipeline is deterministic when the tracker is cold.** Two cold runs agree to
   `0.000000`. So the nondeterminism is entirely the carried state, not the model, not
   the decode, not threading.

## Mechanism

`AIService` is a per-worker singleton (`app/tasks/analysis_tasks.py:74-87`) holding one
`mp.solutions.pose.Pose(static_image_mode=False, ...)` (`app/services/ai_service.py:81-86`).

`static_image_mode=False` puts MediaPipe in **video/tracking mode**: each frame's detection is
seeded by the previous frame's landmarks. That is correct *within* a video and wrong *across*
videos — nothing resets the tracker between tasks, so video N+1 starts from video N's final
pose.

`_extract_pose_from_video` (`app/tasks/analysis_tasks.py:235-283`) calls `ai_svc.detect_pose`
per frame and never re-initialises.

## Why this produced exactly the parity result we saw

`2026-09-19-celery-parity-20.json`: 3/20 matched within 1e-6, mean |Δ| 0.062, max 0.453.

- The Celery worker and the offline script processed the 20 videos in different orders and
  with different warm-up, so each video inherited a different predecessor.
- The matches are the cases where the carried state happened to coincide.
- Max |Δ| 0.453 is the same order as the 0.214 spread measured here, compounded across a
  longer chain of predecessors.

This is **not** a Celery bug. The offline script has it too — it reuses one `AIService` across
all 20 videos. Both paths are wrong in the same way; they merely disagree about *how*.

## Consequence for the claims already published

`bench/results/2026-09-19-v1-test-split.json` (F1 0.6131) and the ablation and Penn-shortcut
runs all scored fixtures **sequentially through one loader**. Those runs used precomputed
keypoint JSON, not video decode, so **MediaPipe was never invoked** and this leak does not
apply to them. The numbers stand. Only paths that decode video are affected: the Celery
worker, `celery_parity_offline.py`, and `one_video_diff.py`.

## Fix (Phase 2, not done here)

Construct a fresh `Pose` per video inside `_extract_pose_from_video`, or call `.reset()` if the
installed MediaPipe exposes it. The `AIService` singleton should keep the torch model and drop
the tracker. Cost: one `Pose` init per video (~0.1–0.3 s), against a 10–12 s task.

Then `test_parity_20` becomes meaningful — it cannot pass until this is fixed.

## Reproduce

```bash
docker compose -f backend/deployment/docker-compose.yml run --rm --no-deps \
  -v "$HOME/Desktop/Squat More/Labeled_Dataset/videos:/videos:ro" \
  -T app python - < bench/mediapipe_state_leak_test.py
```
