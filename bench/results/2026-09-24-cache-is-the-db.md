# The cache is the DB: a re-upload is a trail row, not silence (plan D3 / execution plan item 10) — 2026-09-24

## Finding

The repo carried a Redis "analysis result cache" (`get_cached_analysis`, `cache_analysis_results`,
two write sites in `form_check_service.py`) that was never written and never read: no caller ever
supplied a video hash, the only hasher hashed the *path*, and `expire=` was not even the client's
keyword (`CacheService.set(..., expires_in=)`). What actually skips inference is the DB idempotency
lookup `_find_duplicate_submission(user_id, content_hash, model_version, spec_hash)`, which returned
the existing row silently, with two consequences:

1. **A cache hit was invisible.** "How many uploads were served from cache" had no answer; the trail
   (`analysis_runs`) showed one run per video whether it was uploaded once or twenty times.
2. **A hit ignored the pose pass.** The key has no pose-pass part, so a verdict computed under an
   earlier MediaPipe pass would be returned after the pass changed. G-39 measured 15.3 % of verdicts
   flipping between passes; a "cached" verdict from another pass is a different measurement.

## Change (`audit/cache-is-the-db`)

- `FormCheckService._reuse_as_cache_hit(existing)`: on a lookup hit, take the existing row's latest
  completed run; if its `pose_pass_id` differs from the pass in service (latest non-cache completed
  run table-wide) fall through to a fresh submission; otherwise `open_run` + `close_run(status=
  'completed', pose_source='cache', ...)` copying `final_decision`, `final_score`, `n_frames`,
  `pose_pass_id`, with `settings_snapshot={"cache_hit_of_run": <source run id>}`. A row never
  judged (still queued) is returned as before with no trail row: nothing to copy.
- Both dead cache blocks and both dead methods deleted; `expire=` → `expires_in=` at the four live
  callers (`analytics_service.py` ×3, `storage_service.py`), which were silently raising into a
  broad `except` before.
- Trail assertions: A2 ("completed runs with no checker decision") skips `pose_source='cache'` in
  `bench/trail_report.sh` and `bench/stage_a_decision_trail.sh`; A10 already excluded cache runs
  from "judged twice".
- Tests: `tests/unit/test_idempotency.py::TestCacheHitIsATrailRow` (4): never-judged row reused
  without a trail row; another pass ⇒ not reused; same pass ⇒ cache run copying the verdict; empty
  trail ⇒ reused. 46 passed with the form-check API/contract/finalize-guard tests in the worker image.

## Command

```bash
bash bench/cache_hit_check.sh          # N=20, parity_20 selection, one user, two passes
```

## Environment

- API container restarted on this branch's code (bind mount); worker unchanged
  (`deployment-worker:latest` 3×2, pose pass `pp1_f9850424580ae186`); host on battery with Low Power
  Mode (see `2026-09-24-stage-timings.md`), which affects pass-1 speed only.
- user `cache_1790282729@example.com`

## Raw output

```
=== pass 2: the same bytes, the same user ===
=== Stage A decision trail ===
user   : cache_1790282729@example.com
videos : 20
submitted 20/20
--- polling for terminal status ---
=== THE TRAIL ===
--- runs by status ---
  completed : 40
--- decisions by checker ---
  depth_parallel_v0/depth AT_DEPTH  fitted=false advisory=true  n=8
  depth_parallel_v0/depth SHALLOW  fitted=false advisory=true  n=3
  depth_parallel_v0/depth UNCERTAIN  fitted=false advisory=true  n=9
  knees_forward_v0/knees_forward NOT_OBSERVED  fitted=false advisory=true  n=5
  knees_forward_v0/knees_forward OBSERVED  fitted=false advisory=true  n=5
  knees_forward_v0/knees_forward UNCERTAIN  fitted=false advisory=true  n=10
  posture_v1/posture FAULT  fitted=true advisory=false  n=11
  posture_v1/posture GOOD_FORM  fitted=true advisory=false  n=7
  posture_v1/posture UNCERTAIN  fitted=true advisory=false  n=2
--- pose passes observed ---
  pp1_f9850424580ae186  n=40
=== ASSERTIONS ===
  A1 PASS  terminal form checks with no run row                 0
  A2 FAIL  runs with no checker decision                        got 20, want 0
  A3 PASS  closed runs missing a pose_pass_id                   0
  A4 PASS  runs still open                                      0
  A5 PASS  form checks carrying a depth_score                   0
  A6 PASS  rule decisions not marked unfitted+advisory          0
  A7 PASS  answered rule decisions with no score                0
  A8 PASS  decisions with no inputs_digest                      0
  A9 PASS  completed runs with no n_frames                      0
--- determinism: same inputs_digest => same decision? ---
  (more than 1 distinct verdict for one digest = nondeterminism)
=== FAILURES ABOVE ===
ids: /var/folders/2_/837jvk4j7tn3zv9_s24fmbxm0000gn/T/tmp.7RQ9uQKgHy/pairs.txt
pass 2 wall time: 43.2 s
=== cache accounting for cache_1790282729@example.com ===
form_checks (want 20)             : 20
real completed runs (want 20)     : 20
cache runs (want 20)              : 20
cache runs on another pass (want 0): 0
verdict copied exactly (want 20)  : 20
cache latency ms p50 / max         : 2.28 / 9.80
=== decision trail for users LIKE 'cache_1790282729@example.com' ===
--- form checks by status ---
  COMPLETED : 20
--- runs by status ---
  completed : 40
--- runs by error_type (failed/abandoned) ---
--- decisions by checker ---
  depth_parallel_v0/depth AT_DEPTH  fitted=false advisory=true  n=8
  depth_parallel_v0/depth SHALLOW  fitted=false advisory=true  n=3
  depth_parallel_v0/depth UNCERTAIN  fitted=false advisory=true  n=9
  knees_forward_v0/knees_forward NOT_OBSERVED  fitted=false advisory=true  n=5
  knees_forward_v0/knees_forward OBSERVED  fitted=false advisory=true  n=5
  knees_forward_v0/knees_forward UNCERTAIN  fitted=false advisory=true  n=10
  posture_v1/posture FAULT  fitted=true advisory=false  n=11
  posture_v1/posture GOOD_FORM  fitted=true advisory=false  n=7
  posture_v1/posture UNCERTAIN  fitted=true advisory=false  n=2
--- pose passes observed ---
  pp1_f9850424580ae186  n=40
--- latency (completed runs, ms) ---
  n=40  p50=5474  p90=19843  max=39673
=== ASSERTIONS ===
  A1 PASS  terminal form checks with no run row                 0
  A2 PASS  completed runs with no checker decision              0
  A3 PASS  closed runs missing a pose_pass_id                   0
  A4 PASS  runs still open                                      0
  A5 PASS  form checks carrying a depth_score                   0
  A6 PASS  rule decisions not marked unfitted+advisory          0
  A7 PASS  answered rule decisions with no score                0
  A8 PASS  decisions with no inputs_digest                      0
  A9 PASS  completed runs with no n_frames                      0
  A10 PASS  terminal rows disagreeing with their latest closed run, or judged twice 0
--- determinism: digests with more than one distinct verdict ---
  (empty = deterministic)
=== ALL ASSERTIONS PASS ===
```

(The `A2 FAIL got 20` inside pass 2 is the batch script's own copy of A2 before this commit's
exclusion: the 20 cache rows carry no decisions of their own, by design. The report run after it,
with the exclusion, is the acceptance: A1–A10 pass. The query was re-run by hand after the fix: 0.)

## Numbers

| quantity | want | got |
|---|---|---|
| form checks for the user after two passes of 20 | 20 | 20 |
| real completed runs (inference) | 20 | 20 |
| cache runs (`pose_source='cache'`) | 20 | 20 |
| cache runs whose source ran under another pose pass | 0 | 0 |
| cache runs copying decision, score and n_frames exactly | 20 | 20 |
| cache run latency (open_run + close_run), p50 / max | — | 2.28 ms / 9.80 ms |
| pass-2 wall time for 20 re-uploads (2 s submit stagger) | — | 43.2 s |

Second inference runs for the same bytes: **0**. The plan's acceptance ("submit 20 files twice →
20 rows with `pose_source='cache'`, 0 new inference runs") holds.

## Flagged, not done

- `app/core/middleware/main_setup.py:58` guards the rate-limit middleware behind a cache
  `is_available()` call that does not exist, so the middleware has never been installed. Changing
  that line would switch rate limiting on for the first time; it is a behaviour change to the API's
  limits, left for a decision.
