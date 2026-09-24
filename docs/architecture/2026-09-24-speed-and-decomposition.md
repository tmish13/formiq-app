# Would splitting the pipeline into services make it faster?

**Short answer: no.** The pipeline is one CPU-bound stage (MediaPipe pose extraction) plus small
things. Decomposing it into upload / pose / inference / feedback services adds serialisation and
hops and removes no CPU from the only stage that matters. What makes it faster is more cores for
pose, a cheaper pose pass, or fewer frames — each of which is measurable without a new service.

## Where the time goes (measured)

From the 600-video validation batch (2026-09-24, worker 3 children × 2 threads, idle VM):

| stage | per video | share | source |
|---|---|---|---|
| whole task (fetch → pose → model → rules → finalize) | **p50 9.7 s**, p90 16.9 s | 100 % | `analysis_runs.latency_ms` |
| PostureV1 inference | **p50 39 ms** (465 ms cold, first call) | **0.4 %** | `results.posture_v1.latency_ms` |
| frames per clip | p50 106 (cap 300) | — | `analysis_runs.n_frames` |
| pose extraction (MediaPipe, complexity 2) | **95.5 % of the task** (p50 23.5 s of 24.6 s on the 50-video stage batch; 97.8 % on the first) | **≈ 95 %** | `analysis_runs.settings_snapshot.stage_ms`, `bench/results/2026-09-24-stage-timings.md` |
| everything else: claim, open_run, video fetch, post-model, decisions | p50 0.37 s | **≈ 1.5 %** | same; measured, no longer by subtraction |

The two bottom rows were first written by subtraction ("pose ≈ 50 %, other ≈ 45 %"); the measured
split replaced them on 2026-09-24. Note the stage batch ran on battery with macOS Low Power Mode on
and was 2.6× slower per frame than the validation above; the split held, the absolute times did not
(details in the results note).

Three children on 8 vCPUs deliver 9.25 videos/min; one child alone does a video in ≈ 7.4 s, so
three could in principle do ≈ 24/min — the gap is CPU contention among MediaPipe threads, not
queueing. The machine is the limit.

## What decomposition would and would not do

| proposal | effect on the 9.7 s | verdict |
|---|---|---|
| **upload service** separate from the API | none — uploads are already the API's job and the worker never touches them; the memory problem (G-36) was solved by a bound, not a service | already separate in effect |
| **pose service** (extract keypoints, return JSON) | the same MediaPipe on the same cores, plus a ~100 KB keypoint payload per clip over the network; **0 % faster**, and every verdict now depends on two deployments agreeing on the pose pass (G-39: 15 % of verdicts flip between passes) | no |
| **inference service** (PostureV1 behind an endpoint) | moves 39 ms of work behind a hop that costs more than 39 ms | no |
| **feedback service** (LLM) | disabled (`COACHING_FEEDBACK_ENABLED=false`); the verdict it would explain is below the bar | not yet, and not for speed |
| **frame-level parallelism inside pose** (split a clip's frames across processes) | MediaPipe's tracker is stateful across frames; splitting changes the keypoints — a new pose pass, a re-baseline of every number | no |

## What actually makes it faster, in order of evidence

1. **More cores for pose** — horizontal scaling of the *existing* worker (`docker compose up --scale
   worker=N` on a bigger host, or more hosts). Throughput is linear in cores until the DB/broker
   notice; the trail already makes that measurable per batch (`bench/pipeline_dashboard` when D6 lands).
2. **Cheaper pose** — complexity 1 is roughly 2× faster per frame, **but** it is a different pose
   pass: 15.3 % of the incumbent's verdicts and 25.5 % of the retrain's flip between complexity 2 and
   1 (`bench/results/2026-09-24-acceptance-bar-verdict.md`). Any speed-up here is a model change and
   goes through the acceptance bar with its own pre-registration, not through ops.
3. **Fewer frames** — the 300-frame cap and 30 fps resampling are what the model was trained on;
   sampling at 15 fps halves pose time and is, again, a new pose pass to measure, not a free knob.
4. **The other 45 %** did not exist. Measured per stage, everything outside pose extraction and the
   model is ≈ 0.4 s of a 10–25 s task (`bench/results/2026-09-24-stage-timings.md`). There is no cheap
   win in decode, DB writes or finalize; the only levers are the three above, all of them pose passes.

## When a split would be right

When a stage needs different hardware or a different scaling law from the rest: a GPU pose model
(MediaPipe's Python pose is CPU-only; a GPU alternative is a model change), or an LLM feedback
step whose latency and cost must be isolated from the verdict path. Neither is true today, and
G-08 stands: this is two processes and one codebase, and calling it microservices earlier did not
make it so.
