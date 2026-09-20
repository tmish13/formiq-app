# Cross-video MediaPipe state leak — fixed

**Date:** 2026-09-20
**Branch:** `audit/phase1-worker-model`
**Closes:** the Phase 0 finding in `2026-09-19-mediapipe-state-leak.md`

## The defect

`AIService` is a per-worker singleton (`app/tasks/analysis_tasks.py:74-87`) holding one
`mp.solutions.pose.Pose(static_image_mode=False)` (`app/services/ai_service.py:81-86`).
`static_image_mode=False` is tracking mode: each frame is seeded by the previous frame's
landmarks. Correct *within* one video, wrong *across* videos. Nothing reset it between tasks,
so the same bytes scored differently depending on which video ran before them.

## The change

`AIService.reset_pose_tracker()` (`app/services/ai_service.py:154`) closes the tracker and
rebuilds it at `self._pose_complexity_used` — the *used* complexity, not the configured one,
so a worker that fell back to complexity=1 at startup (G-21) stays on 1 rather than silently
switching models mid-run.

Called once per video, before the first frame, at every whole-video loop:

| call site | path |
|---|---|
| `app/tasks/analysis_tasks.py:261` | `_extract_pose_from_video` — **the live Celery path** |
| `app/services/ai_service.py:1325` | `process_frames_for_pose` |
| `app/services/ai_service.py:1706` | `_synchronous_frame_processing` |
| `app/services/form_check_service.py:65` | `_process_video_frames_cv2` |

## Before / after

Same target video (`33387_1`), one long-lived `AIService`, varying predecessor.

| condition | before (Phase 0) | after | shift vs cold, after |
|---|---|---|---|
| cold tracker, run 1 | 0.618214 | 0.618214 | — |
| cold tracker, run 2 | 0.618214 | 0.618214 | +0.000000 |
| after `33348_2` | 0.439524 | **0.618214** | +0.000000 |
| after `36049_2` | 0.652968 | **0.618214** | +0.000000 |
| after itself | 0.586389 | **0.618214** | +0.000000 |
| **spread** | **0.214** | **0.000000** | |

The decision threshold is 0.525. Before the fix the spread straddled it, so the predecessor
could flip the verdict. After, every run equals the cold-start value — the fix did not move
the answer, it made every run agree with the answer a fresh process already gave.

### Precision caveat

`loader.py:604` applies `round(prob_fault, 6)`, so "+0.000000" means **identical at 1e-6
resolution**, which is the resolution the pipeline reports and stores. This run does not
establish bit-equality below that. The Phase 0 numbers were rounded by the same line, so the
before/after comparison is like for like.

## Commands

```bash
# regression test (3 tests)
docker run --rm --network deployment_default \
  -v $PWD/backend:/app \
  -v "$HOME/Desktop/Squat More/Labeled_Dataset/videos:/videos:ro" \
  -e POSTGRES_SERVER=db -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=formiq -e SECRET_KEY=dev-only-insecure-secret-key-32chars-minimum \
  -e REDIS_HOST=redis -e REDIS_PORT=6379 -w /app deployment-worker:latest \
  bash -lc 'pip install -q pytest-timeout==2.2.0; pytest -p no:randomly \
    --import-mode=importlib --override-ini="addopts=" --timeout=0 -q \
    tests/integration/pipeline/test_pose_tracker_reset.py'

# the before/after table
docker run --rm --network deployment_default \
  -v $PWD/backend:/app -v $PWD:/repo \
  -v "$HOME/Desktop/Squat More/Labeled_Dataset/videos:/videos:ro" \
  -e POSTGRES_SERVER=db -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=formiq -e SECRET_KEY=dev-only-insecure-secret-key-32chars-minimum \
  -e REDIS_HOST=redis -e REDIS_PORT=6379 -w /app deployment-worker:latest \
  python /repo/bench/tracker_reset_verify.py
```

## Raw output

```
3 passed, 23 warnings in 173.08s (0:02:53)

cold tracker, run 1            : 0.618214
cold tracker, run 2            : 0.618214   (deterministic when cold: True)
same video after 33348_2       : 0.618214   shift vs cold +0.000000
same video after 36049_2       : 0.618214   shift vs cold +0.000000
same video after ITSELF        : 0.618214   shift vs cold +0.000000

max |shift| vs cold            : 0.000000
```

## Environment

- Host: Darwin 25.4.0, 8 cores, Docker Desktop
- Image: `deployment-worker:latest`, python 3.11, mediapipe complexity 2, CPU only
- Backend source bind-mounted (`..:/app`), so no rebuild was required
- Disk at run time: 21 GB free (96% used)

## Two findings recorded on the way

1. **`pytest` cannot run inside the built image.** `pytest.ini:58` lists `pytest-timeout` under
   `required_plugins`, but `requirements.txt` never installed it, so every in-container pytest
   invocation aborts before collection with `ERROR: Missing required plugins: pytest-timeout`.
   Added to `requirements.txt:67`; the runs above installed it inline because a rebuild is
   3.2 GB and disk is tight.
2. **`_process_frame_batch_parallel` / `_process_gpu_batch` share one tracker across threads**
   (`ai_service.py:1876`, `:1924`). That is a *concurrent* misuse of the same stateful object,
   a different defect from this one, and it is not on the live path. Not fixed here — filed
   rather than patched in passing.

## Scope

Unaffected: the published F1 / ablation / Penn-shortcut numbers. Those scored precomputed
keypoint JSON, so MediaPipe was never invoked. Only video-decode paths carried the leak.
