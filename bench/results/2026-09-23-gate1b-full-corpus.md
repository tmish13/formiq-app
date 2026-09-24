# Gate 1b — the full corpus through the live pipeline (and what the reaper did to it)

**Date:** 2026-09-23 · **Branch:** `ml/gate1b-full-corpus` · **Status:** batch complete, recovery batch complete, see §5 for numbers

## 0. Why

ML_AUDIT §11c Step 0: *"make the instrument adequate (no modelling)."* Gate 1 judged 300 videos and
left the content-level **test** split at n=41, where one cycle turn had a ±0.16 F1 interval (G-47).
This gate pushes every remaining usable corpus video through the **live** pipeline so that
evaluation reads stored decisions at n ≈ 190 on test. No model, threshold or rule changed.

## 1. Commands

```bash
# selection: one video per content hash, not yet judged, file on disk (1,021 videos)
python bench/select_eval_batch.py --remaining --judged-hashes <hashes-with-a-posture-decision> \
    --out bench/results/gate1b_selection.json
# submission + poll, reusing the Stage A harness
SEL=bench/results/gate1b_selection.json N=1021 TIMEOUT_S=9000 SUBMIT_STAGGER=2 \
    EMAIL="gate1b_<ts>@example.com" bash bench/stage_a_decision_trail.sh
# recovery batch (see §2): the 263 videos the reaper failed before they ran
python bench/select_eval_batch.py --remaining --judged-hashes <hashes-after-batch-1> \
    --out bench/results/gate1b_recovery_selection.json
SEL=bench/results/gate1b_recovery_selection.json N=263 TIMEOUT_S=5400 SUBMIT_STAGGER=2 \
    EMAIL="gate1b_recovery_<ts>@example.com" bash bench/stage_a_decision_trail.sh
# the trail, decoupled from submission, once everything is terminal
bash bench/trail_report.sh 'gate1b_%'
```

**Environment.** Docker Desktop VM 8 vCPU / 7.65 GiB; `deployment-worker-1` prefork ×4 (image
predates G-43's rebuild, as in Gate 1); `deployment-app-1`; Postgres in `formiq_db`; Redis broker.
Batch 1 submitted 17:34–18:08 PDT (2 s stagger), drained 19:16 PDT; throughput 6–8 videos/min,
p50 latency 35.5 s, p90 66 s during the batch (Gate 1a: p50 18 s — the host was also running the
retrain rehearsals). Batch 2 submitted 19:18 PDT with **beat stopped** (§2).

## 2. G-48 — what the batch found before it produced a number

The batch was the first one deeper than the stuck-row reaper's 30-minute threshold, and the
reaper did two things to it.

**(a) It re-dispatched and then failed healthy queued rows.** `STUCK_THRESHOLD = 30 min`
(`app/tasks/maintenance_tasks.py:46`) is justified by an invariant on a single task's
*processing* time — `task_time_limit × (1 + retries) + backoff = 24.1 min` — and
`test_threshold_exceeds_the_worst_case_for_live_work` (`tests/unit/test_maintenance_tasks.py:60`)
asserts exactly that quantity. The PENDING sweep measures *queue wait*, which nothing bounds.
At ~6 videos/min, any batch over ~180 videos puts healthy rows past the threshold. First strike
re-dispatches (a duplicate task; `updated_at` reset), second strike marks FAILED. Every sweep
that touched a row (UTC, from the worker log):

```
2026-09-24 01:15:10  scanned: 95, redispatched: 95, failed: 0, runs_abandoned: 0
2026-09-24 01:19:53  scanned: 100, redispatched: 100, failed: 0, runs_abandoned: 0
2026-09-24 01:23:21  scanned: 100, redispatched: 100, failed: 0, runs_abandoned: 0
2026-09-24 01:27:11  scanned: 100, redispatched: 100, failed: 0, runs_abandoned: 0
2026-09-24 01:30:24  scanned: 100, redispatched: 100, failed: 0, runs_abandoned: 0
2026-09-24 01:33:38  scanned: 100, redispatched: 100, failed: 0, runs_abandoned: 0
2026-09-24 01:37:02  scanned: 100, redispatched: 100, failed: 0, runs_abandoned: 1
2026-09-24 01:45:22  scanned: 77, redispatched: 77, failed: 0, runs_abandoned: 0
2026-09-24 01:50:33  scanned: 1, redispatched: 0, failed: 1, runs_abandoned: 1
2026-09-24 01:57:19  scanned: 37, redispatched: 0, failed: 37, runs_abandoned: 0
2026-09-24 02:03:42  scanned: 100, redispatched: 0, failed: 100, runs_abandoned: 0
2026-09-24 02:03:45  scanned: 48, redispatched: 0, failed: 48, runs_abandoned: 0
2026-09-24 02:07:09  scanned: 69, redispatched: 0, failed: 69, runs_abandoned: 1
2026-09-24 02:15:55  scanned: 6, redispatched: 0, failed: 6, runs_abandoned: 0
```

| reaper action on the 1,021 queued rows | count |
|---|---|
| re-dispatched as duplicate tasks (first strike) | **772** (75.6 %) |
| marked FAILED while still queued (second strike) | **261** |
| of which never ran at all (`reaper_stuck_from_status = pending`, no `analysis_runs` row) | **183** |
| OOM-killed runs correctly abandoned | 3 |

**(b) The duplicates then flipped completed rows to FAILED.** Each duplicate reached the worker
about an hour after its re-dispatch, by which time the original task had completed the row. The
claim (`app/tasks/analysis_tasks.py:697-715`) correctly refused it and returned `skipped` — but
`final_status` is initialised to `FAILED` (line 645), the `finally` (lines 1844-1854) finalizes
the row with it regardless, and `finalize_form_check_analysis_async` carries no status guard and
writes the generic *Analysis failed due to an unknown error.* (`app/services/form_check_service.py:453`).
**520 duplicates hit COMPLETED rows; 520 COMPLETED rows became FAILED**, results columns intact
(520/520 `results`, 520/520 `analysis_completed_at`, 479/520 `posture_score`). One row, end to end:

```
[2026-09-24 01:15:02,112: WARNING/ForkPoolWorker-10] [Reaper] FormCheck 9096ef83-a108-48e5-93b2-554cbcf43e68 was stuck since 2026-09-24 00:41:50.784072+00:00; released to PENDING and re-dispatched.
[2026-09-24 01:15:04,696: INFO/ForkPoolWorker-7] [CeleryTask] FormCheck ID 9096ef83-a108-48e5-93b2-554cbcf43e68 claimed; status updated to PROCESSING.
[2026-09-24 01:15:30,689: INFO/ForkPoolWorker-7] [CeleryTask] Finalizing FormCheck 9096ef83-a108-48e5-93b2-554cbcf43e68 with status completed
[2026-09-24 01:15:30,929: INFO/ForkPoolWorker-7] [CeleryTask] Finished processing FormCheck ID: 9096ef83-a108-48e5-93b2-554cbcf43e68 with status: completed
[2026-09-24 01:15:30,962: INFO/ForkPoolWorker-7] Task app.tasks.analysis_tasks.process_form_check[905cf296-5dc1-43c3-91b1-1786d799f666] succeeded in 26.41733851301251s: {'status': 'completed', 'form_c
[2026-09-24 02:15:57,721: WARNING/ForkPoolWorker-10] [CeleryTask] FormCheck ID 9096ef83-a108-48e5-93b2-554cbcf43e68 could not be claimed (status: completed). Skipping -- another worker has it or it is
[2026-09-24 02:15:57,721: INFO/ForkPoolWorker-10] [CeleryTask] Finalizing FormCheck 9096ef83-a108-48e5-93b2-554cbcf43e68 with status failed
```

The decision trail was untouched — it is append-only: **758 completed runs, every one with its
decisions**, one `posture_v1` decision per judged video. The evaluation reads `checker_decisions`,
not `form_checks.status`, so the numbers in §5 are unaffected; the corruption is fully diagnosable
from the trail, which is what Stage A was for.

**Operational response.** `docker compose stop beat` at 19:04 PDT (no config or manifest was
changed; the scheduler process was stopped and is restarted after the recovery batch). The 263
never-run videos were re-submitted as a fresh batch under a second user so that every row of
batch 1 stays exactly as the reaper left it — the FAILED rows *are* the evidence. Filed as
**G-48** in `AUDIT.md` with the fix (never fail a PENDING row on wall-clock age; make the skip
path return before finalize; guard the finalize UPDATE on `status = PROCESSING`).

Worker OOM kills during batch 1: **8** SIGKILLs (G-46's rate: 0.8 % of 1,021).

## 3. The trail, once everything was terminal

`bash bench/trail_report.sh 'gate1b_%'` at 19:54 PDT, both batches (1,021 + 263 form checks),
before the reaper closed the SIGKILL-orphaned runs:

```
=== decision trail for users LIKE 'gate1b_%' ===
--- form checks by status ---
  COMPLETED : 500
  FAILED : 784
--- runs by status ---
  abandoned : 3
  completed : 1020
  running : 5
--- runs by error_type (failed/abandoned) ---
  abandoned : 3
  (null) : 5
--- decisions by checker ---
  depth_parallel_v0/depth AT_DEPTH  fitted=false advisory=true  n=627
  depth_parallel_v0/depth SHALLOW  fitted=false advisory=true  n=112
  depth_parallel_v0/depth UNCERTAIN  fitted=false advisory=true  n=281
  knees_forward_v0/knees_forward NOT_OBSERVED  fitted=false advisory=true  n=276
  knees_forward_v0/knees_forward OBSERVED  fitted=false advisory=true  n=448
  knees_forward_v0/knees_forward UNCERTAIN  fitted=false advisory=true  n=296
  posture_v1/posture FAULT  fitted=true advisory=false  n=535
  posture_v1/posture GOOD_FORM  fitted=true advisory=false  n=398
  posture_v1/posture UNCERTAIN  fitted=true advisory=false  n=87
--- pose passes observed ---
  pp1_f9850424580ae186  n=1020
  (null)  n=8
--- latency (completed runs, ms) ---
  n=1020  p50=27969  p90=49345  max=140887

=== ASSERTIONS ===
  A1 FAIL  terminal form checks with no run row                 got 258, want 0
  A2 PASS  completed runs with no checker decision              0
  A3 PASS  closed runs missing a pose_pass_id                   0
  A4 FAIL  runs still open                                      got 5, want 0
  A5 PASS  form checks carrying a depth_score                   0
  A6 PASS  rule decisions not marked unfitted+advisory          0
  A7 PASS  answered rule decisions with no score                0
  A8 PASS  decisions with no inputs_digest                      0
  A9 PASS  completed runs with no n_frames                      0

--- determinism: digests with more than one distinct verdict ---
  (empty = deterministic)

=== FAILURES ABOVE ===
```

- **A1 = 258 is G-48's evidence, not a trail defect**: those are batch 1's rows the reaper failed
  before any worker claimed them, so no run was ever opened. Every form check that a worker
  *claimed* has its run (A1 is 0 on batch 2 alone).
- **A4 = 5** were the SIGKILL-orphaned runs (8 OOM kills across both batches; three had already
  been abandoned by the reaper before beat was stopped). The scheduled reaper closed the rest
  once beat was restarted at 19:55 PDT (60-minute run cutoff; `_abandon_unclosed_runs`), the
  last one with an explicit 5-minute-threshold call logged in this note's commit.
- A2, A3, A5–A9 and the determinism check hold across **1,020 completed runs** — every judged
  video has its pose pass, its frame count, its rule scores and digests, and no digest ever
  produced two verdicts.
- Judged in this gate: **1,020 videos** (758 in batch 1, 262 in batch 2; 1 video OOM-killed in
  batch 2 and 3 in batch 1 stay unjudged — `bench/select_eval_batch.py --remaining` will pick
  them up next time). Content-level test coverage went from 41 to **188**.

### 3b. Assertions after the last orphaned run was closed (20:01 PDT)

```
=== ASSERTIONS ===
  A1 FAIL  terminal form checks with no run row                 got 258, want 0
  A2 PASS  completed runs with no checker decision              0
  A3 PASS  closed runs missing a pose_pass_id                   0
  A4 PASS  runs still open                                      0
  A5 PASS  form checks carrying a depth_score                   0
  A6 PASS  rule decisions not marked unfitted+advisory          0
  A7 PASS  answered rule decisions with no score                0
  A8 PASS  decisions with no inputs_digest                      0
  A9 PASS  completed runs with no n_frames                      0

--- determinism: digests with more than one distinct verdict ---
  (empty = deterministic)

=== FAILURES ABOVE ===
```

A1 remains the 258 reaper-failed, never-claimed rows of batch 1 (G-48 evidence); every other
assertion, and the determinism check, passes over 1,020 completed and 8 abandoned runs.

## 4. The evaluation, per content-level split

`python scripts/eval_runner.py --target posture --splits content --split <split> --json ...`
inside `deployment-beat:latest` (the only image with the current test deps, G-43), metrics from
`app/eval/metrics.py`, bootstrap n=2000 seed 0. Full output:

```
=================== test ===================
basis: CONTENT-LEVEL splits (mode minimal), 299 videos withheld as contradictory duplicates
target 'posture'  scored against label target 'posture_fault'  split=test
decisions 1336   labels 2796
  content-level filter: decisions 1336 -> 198, labels 2796 -> 372
labelled videos 188   disputed 0   unusable 0
========================================================================
posture_v1   [FITTED / authoritative]   matched 188 labelled videos
========================================================================
  coverage            0.941  (177/188 answered)
  covered-only        P 0.5258  R 0.7083  F1 0.6036
  abstain-as-negative P 0.5258  R 0.6538  F1 0.5829
  trivial floor       F1 0.5865   prevalence 0.415
  covered-only AUROC  0.7057  95% CI [0.6246, 0.7808]
  covered-only F1 CI  [0.5135, 0.6854]
  abstain-as-neg F1 CI [0.4937, 0.6630]
wrote /repo/bench/results/2026-09-23-gate1b-eval-posture-test.json
=================== validation ===================
basis: CONTENT-LEVEL splits (mode minimal), 299 videos withheld as contradictory duplicates
target 'posture'  scored against label target 'posture_fault'  split=validation
decisions 1336   labels 2796
  content-level filter: decisions 1336 -> 212, labels 2796 -> 404
labelled videos 212   disputed 0   unusable 0
========================================================================
posture_v1   [FITTED / authoritative]   matched 212 labelled videos
========================================================================
  coverage            0.892  (189/212 answered)
  covered-only        P 0.5278  R 0.7917  F1 0.6333
  abstain-as-negative P 0.5278  R 0.6951  F1 0.6000
  trivial floor       F1 0.5578   prevalence 0.387
  covered-only AUROC  0.7783  95% CI [0.7072, 0.8469]
  covered-only F1 CI  [0.5484, 0.7097]
  abstain-as-neg F1 CI [0.5161, 0.6796]
wrote /repo/bench/results/2026-09-23-gate1b-eval-posture-validation.json
=================== train ===================
basis: CONTENT-LEVEL splits (mode minimal), 299 videos withheld as contradictory duplicates
target 'posture'  scored against label target 'posture_fault'  split=train
decisions 1336   labels 2796
  content-level filter: decisions 1336 -> 901, labels 2796 -> 1708
labelled videos 902   disputed 0   unusable 0
========================================================================
posture_v1   [FITTED / authoritative]   matched 901 labelled videos
========================================================================
  coverage            0.913  (823/901 answered)
  covered-only        P 0.5396  R 0.7802  F1 0.6380
  abstain-as-negative P 0.5396  R 0.6632  F1 0.5950
  trivial floor       F1 0.5933   prevalence 0.422
  covered-only AUROC  0.7611  95% CI [0.7266, 0.7954]
  covered-only F1 CI  [0.5974, 0.6762]
  abstain-as-neg F1 CI [0.5534, 0.6341]
wrote /repo/bench/results/2026-09-23-gate1b-eval-posture-train.json
```

| split | n | covered | prevalence | AUROC [95 % CI] | F1 covered-only [95 % CI] | F1 abstain-as-neg [95 % CI] | floor F1 | majority acc |
|---|---|---|---|---|---|---|---|---|
| **test** | **188** | 177 (94.1 %) | 0.415 | **0.7057 [0.6246, 0.7808]** | **0.6036 [0.5135, 0.6854]** | 0.5829 [0.4937, 0.6630] | 0.5865 | 0.585 |
| validation | 212 | 189 (89.2 %) | 0.387 | 0.7783 [0.7072, 0.8469] | 0.6333 [0.5484, 0.7097] | 0.6000 [0.5161, 0.6796] | 0.5578 | 0.613 |
| train | 901 | 823 (91.3 %) | 0.422 | 0.7611 [0.7266, 0.7954] | 0.6380 [0.5974, 0.6762] | 0.5950 [0.5534, 0.6341] | 0.5933 | 0.578 |

What this says, at an n that can finally carry it:

- **The clean held-out number is F1 0.60 [0.51, 0.69] against a 0.59 floor; the interval
  contains the floor.** AUROC 0.71 [0.62, 0.78] does not contain 0.5. Same reading as
  ML_AUDIT §11a — some signal, no usable decision boundary — now with the CI to say so.
- **The contamination caveat (G-44) stands, and its practical effect on this figure was small**:
  the user-level, 12 %-contaminated n=224 number was F1 0.6131 / AUROC 0.7184; the clean n=188
  number is 0.6036 / 0.7057. Within 0.02 on both.
- **Train-to-test gap is modest** (AUROC 0.76 → 0.71): the model is not memorising the content
  basis; it is weak everywhere.
- Coverage 0.94 on test: the `UNCERTAIN` abstention buys almost nothing (abstain-as-negative F1
  0.58 vs covered-only 0.60).

## 5. The cycle, turned again at 4.6× the n

`python bench/cycle_turn.py` — zero inference, stored probabilities only:

```
CYCLE TURN -- no inference is run; every probability is already stored
==========================================================================
  usable decisions by split: {'train': 901, 'validation': 212, 'test': 188}    skipped: {'not_in_content_split': 24}

1. GAP ANALYSIS  (train + validation, test untouched)
--------------------------------------------------------------------------
   n=1113  prevalence 0.415
   at the incumbent 0.525: P 0.5591  R 0.7879  F1 0.6541  acc 0.6541
   counts {'tp': 364, 'fp': 287, 'tn': 364, 'fn': 98}
   floor F1 0.5867   majority-class acc 0.5849
   -> accuracy is above the majority-class baseline
   -> the error is asymmetric: 287 false positives vs 98 false negatives
      the model over-flags, so the lever is a HIGHER threshold

2. THRESHOLD SWEEP  (VALIDATION ONLY -- test is not read here)
--------------------------------------------------------------------------
   n=212  prevalence 0.387
   incumbent 0.525: F1 0.6176  P 0.5164  R 0.7683
   best F1   0.69: F1 0.6541  P 0.6753  R 0.6341
   best F1 at P>=0.60  0.69: F1 0.6541  P 0.6753  R 0.6341
   -> CHOSEN: 0.69  (selected on validation, n=212 -- thin)

3. TEST  (read once, both thresholds on the SAME videos)
--------------------------------------------------------------------------
   n=188  prevalence 0.415  floor F1 0.5865  majority acc 0.5851
   incumbent 0.525  F1 0.6120  P 0.5333  R 0.7179  acc 0.6223  {'tp': 56, 'fp': 49, 'tn': 61, 'fn': 22}
   chosen   0.69   F1 0.5612  P 0.6393  R 0.5000  acc 0.6755  {'tp': 39, 'fp': 22, 'tn': 88, 'fn': 39}

   delta F1 -0.0509   95% CI [-0.1349, +0.0272]   INCLUDES ZERO
   (paired: videos resampled once, both thresholds scored on the same draw)
```

| turn | validation n | test n | chosen thr | test F1 chosen | test F1 incumbent (0.525) | ΔF1 [95 % CI, paired] |
|---|---|---|---|---|---|---|
| Gate 3 (2026-09-23, earlier) | 41 | 41 | 0.65 | 0.4167 | 0.4516 | −0.0349 [−0.2172, +0.1135] |
| **Gate 1b** | **212** | **188** | 0.69 | 0.5612 | 0.6120 | **−0.0509 [−0.1349, +0.0272]** |

The interval halved (±0.16 → ±0.08) and the answer did not change: a threshold chosen on
validation is *worse* on test, and the paired CI still includes zero. **The incumbent's threshold
is not the lever.** G-47's "do not tune until n grows" is now "do not tune, retrain": the
controlled retrain pre-registered in `bench/retrain/PREREGISTRATION.md` is the next step.

## 6. What Gate 1b cost

Batch 1: 1,021 submissions, 102 minutes wall-clock, 8 OOM kills, and one new defect (G-48) that
re-dispatched 772 rows, failed 261 of them unrun and flipped 520 completed rows to FAILED an hour
later. Batch 2: 263 submissions, 36 minutes, 1 OOM kill, zero reaper actions (beat stopped).
The evaluation afterwards was three queries and a bootstrap — no inference.

Files: `bench/results/gate1b_selection.json`, `gate1b_recovery_selection.json`,
`2026-09-23-gate1b-eval-posture-{test,validation,train}.json`, `cycle_turn.json` (overwritten
from the Gate 3 turn; the n=41 numbers are in `2026-09-23-gates-pipeline-as-instrument.md`),
`bench/trail_report.sh` (new), `backend/scripts/eval_runner.py` (now prints AUROC and bootstrap
CIs; `bootstrap_ci` gained `metric="auroc"` in `app/eval/metrics.py` with a parity test).
