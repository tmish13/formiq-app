# CV claims — old, status, and the measured replacement

G-01: four claims on the CV came from a doc that measured 50 health-endpoint requests and a
*simulated* frame-time distribution on SQLite, and disclaimed itself. Every replacement below was
measured on the real stack (Docker Desktop VM, 8 vCPU / 7.65 GiB, Postgres + Redis + Celery prefork)
with real corpus videos, and links to the note that holds the command, environment and raw output.

| old claim | status | say this instead | measured where |
|---|---|---|---|
| "100+ concurrent uploads" | not reproducible; 20 simultaneous uploads OOM-killed the API and lost 2–7 requests with no log (G-36) | **Uploads are bounded per API process and refused with 503 + Retry-After above the bound: 20 simultaneous uploads → 17 accepted, 3 refused, 0 dropped, 0 worker kills, 17/17 completed.** | `bench/results/2026-09-24-week2-pipeline.md` §5 |
| "sub-300 ms frame processing" | simulated; never measured on the pipeline | **Per video, end to end: p50 9.7 s, p90 16.9 s (pose extraction ≈ 46 ms/frame, model inference 39 ms); 9.25 videos/min sustained over 600 videos on 8 vCPUs.** | `2026-09-24-week2-pipeline.md` §6; `docs/architecture/2026-09-24-speed-and-decomposition.md` |
| "99.9 % success rate" | not measured; the first 1,000-video batch lost 183 rows to a reaper bug (G-48) | **1,586 videos through the live pipeline with the scheduler running after the fix: 100 % terminal, 0 never-run, 0 corrupted rows, 0 out-of-memory losses in the last 1,166 (7 in 900 before worker recycling); every batch closed by ten trail assertions, all zero.** | `2026-09-23-week1-gate.md`, `2026-09-24-week2-pipeline.md` |
| "25 % query latency improvement" | no baseline, no measurement | drop it | — |

## Claims that are now true and were never on the CV

| claim | number | where |
|---|---|---|
| Every verdict is explainable after the fact | each analysis leaves an append-only run + per-checker decisions with the keypoint digest, pose pass id, frame count and score; the trail is what let the evaluation survive a bug that rewrote 520 form-check rows | `2026-09-23-stage-a-decision-trail.md`, G-48 |
| The model's real number, stated honestly | PostureV1 on a clean, de-duplicated, held-out set of 188 videos: AUROC 0.71 [0.62, 0.78]; F1 0.60 [0.51, 0.69] against an all-positive floor of 0.59; 15 % of verdicts flip between two pose passes | `2026-09-23-gate1b-full-corpus.md`, `2026-09-24-acceptance-bar-verdict.md` |
| A pre-registered retrain, written up as a negative | body-only features, un-collapsed labels, serving pose pass, 5 seeds, one logged test read: primary artifact AUROC 0.68 vs incumbent 0.73, paired Δ −0.05 [−0.12, +0.01] | `2026-09-23-retrain-controlled.md` |
| The evaluation loop costs a query, not a re-run | one cycle turn over 1,113 stored decisions with zero inference; threshold changes are queries | `2026-09-23-gates-pipeline-as-instrument.md`, `bench/cycle_turn.py` |
| Fifty-one gaps found, most closed, all with evidence | `AUDIT.md`, one row per gap, each with its number, its commit, and its note | `AUDIT.md`, `ML_AUDIT.md` |

## How to phrase it

Say what was measured and on what. "Sustains 9 videos a minute on an 8-core box with zero lost
work over 1,500 videos" is checkable; "99.9 %" was not. If a number moves, this file moves with it.
