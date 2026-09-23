# Stage A: every analysis now leaves a trail you can argue with

**Date:** 2026-09-23 · **Branch:** `audit/phase2-depth-rule`
**Script:** `bench/stage_a_decision_trail.sh` · **Env:** Docker Compose dev stack, 7.65 GiB VM,
4 prefork workers, 8 live uploads through the real API.

Phase 1's acceptance was *every dispatched task reaches a terminal state*. This is the next
question: for every task that finished, can we say **what** was decided, **by which checker**,
**from which inputs**, and **under which pose pass**?

Before this branch the only record of a verdict was `posture_v1_inference_logs` — 103 rows,
PostureV1-only, no run id, no content hash, no user, no attempt counter, and nothing recording
when an analysis completed.

## Result: six assertions, all passing

| | assertion | result |
|---|---|---|
| **A1** | terminal form checks with no `analysis_runs` row | **0** |
| **A2** | runs with no `checker_decisions` row | **0** |
| **A3** | closed runs missing a `pose_pass_id` | **0** |
| **A4** | runs still open after the batch drained | **0** |
| **A5** | form checks carrying a `depth_score` | **0** |
| **A6** | rule decisions not marked `fitted=false AND advisory=true` | **0** |

8 form checks, 8 runs, **24 decision rows**, 105s wall clock.

## What the trail actually contains

```
depth_parallel_v0/depth         AT_DEPTH      fitted=false advisory=true   n=4
depth_parallel_v0/depth         SHALLOW       fitted=false advisory=true   n=1
depth_parallel_v0/depth         UNCERTAIN     fitted=false advisory=true   n=3
knees_forward_v0/knees_forward  OBSERVED      fitted=false advisory=true   n=1
knees_forward_v0/knees_forward  NOT_OBSERVED  fitted=false advisory=true   n=2
knees_forward_v0/knees_forward  UNCERTAIN     fitted=false advisory=true   n=5
posture_v1/posture              GOOD_FORM     fitted=true  advisory=false  n=5
posture_v1/posture              FAULT         fitted=true  advisory=false  n=2
posture_v1/posture              UNCERTAIN     fitted=true  advisory=false  n=1
```

**The fitted/advisory distinction is visible in the database, not just in a results file.** One
`SELECT` separates the checker whose constants were selected against data from the two whose
were hand-set. Nothing querying this table can mistake one for the other, which was the point.

## The pose pass is the same one the rules were measured on

Every run: **`pp1_f9850424580ae186`** — byte-identical to the id of the 719-clip live-extraction
corpus that every Phase 2 negative was measured on.

That is the entire justification for G-39 and for the column. Two MediaPipe passes over the same
221 videos moved **33 PostureV1 verdicts (14.9%)** while the paired CI on aggregate F1 spanned
zero (`2026-09-23-pose-pass-verdict-instability.md`). Without the id, one verdict in seven is
unexplainable after the fact. With it, "was this decision produced by the pass I calibrated on?"
has an answer instead of an educated guess.

`pose_pass_id` is resolved at **close**, not at open: the effective MediaPipe complexity is only
settled once the tracker exists, and a run stamped with the *configured* complexity would
misattribute every verdict from a worker that fell back to complexity 1 — the exact case the id
exists to distinguish.

## The kill test

A run is opened immediately after the claim, with its **own commit**. A worker SIGKILLed one
instruction later still leaves a row on disk. Opened inside the task's transaction it would
vanish on rollback, and the run most worth explaining — the one that died — would be the one
with no record.

```
form_check 003a69c2-3504-499d-b7da-730ed437707f
run row appeared after 1s
worker KILLED (SIGKILL -- no finally runs)
  status=running  finished_at=NULL          <- what a dead worker leaves

runs abandoned: 1
  status=abandoned  finished_at=2026-09-23 08:20:21+00  error_type=abandoned
  msg=no worker closed this run; swept by reap_stuck_form_checks
```

The sweep is **unconditional on the form check**. `analysis_runs` deliberately has no foreign
key — an audit row must not change when its subject is deleted — so a run whose form check was
removed is still there and still needs closing, and it is exactly the row a per-form-check sweep
would never reach. It fires at **2×** the form-check threshold, because a run is opened before
the work and closed after it, and sweeping both at the same cutoff would abandon the trail of a
task the same sweep had just re-dispatched.

The `beat` service was added to `docker-compose.yml` in this branch. Verified: it sends
`reap-stuck-form-checks` **within 60s of start**. Without it the Phase 1 reaper was dead
configuration in this environment.

## A defect this found, and how

**The first acceptance run lost all 24 decision rows.** A1, A3, A4, A5 and A6 passed; **A2
failed**. The worker log showed the rules producing real verdicts and then:

```
[Rules] FormCheck 6d572dcd depth=AT_DEPTH(None) knees_forward=UNCERTAIN(low_coverage) in 174.0ms
[Audit] could not write decisions for run 155396f3: Can't match sentinel values in result set
        to parameter sets
```

SQLAlchemy 2.0 batches same-table INSERTs through `insertmanyvalues` and matches the returned
rows back to their parameter sets using the primary key as a *sentinel*. `SQLiteUUID` is a
TypeDecorator that **binds a `str` and returns a `uuid.UUID`**, so the sentinel never matched
and the whole batch failed.

`posture_v1_inference_logs` uses the same type and never hit this, because a task adds exactly
**one** telemetry row. A run adds **three**, which is what crosses the batching threshold. Fixed
with one flush per row — three statements against a 40-second pose pass is not a cost worth
optimising.

**This is the argument for asserting on the rows rather than on the absence of errors.** The
recorder is best-effort by design: it logged a warning and the analyses all completed normally.
Every form check was COMPLETED, every run opened and closed, and the decision trail was empty.
A health check would have been green.

## Two things changed that are worth stating plainly

**`depth_score` stops being a lie.** It received `movement_quality['consistency']` — how steady
the movement was. Nothing depth-related fed it and the word "femur" appears nowhere in this
repo. The value moves to `results["movement_quality"]` and the column stays NULL until a
**fitted** depth checker exists. The unfitted parallel rule records into `results["rules_shadow"]`,
which is labelled as such.

**`stability_score` is now an explicit decline rather than an accident.** Making score writes
presence-based (absent = leave alone, present = write, including an explicit `None`) would have
*started* shipping `stability_score` — a user-visible field fed by the legacy temporal
heuristic, which nothing validates. The PostureV1 path now passes `None` deliberately.
Observable behaviour is unchanged. **It deserves the same measurement `depth_score` got and has
not had it** — that is a decision to make, not one I made.

## Reproduce

```bash
docker compose -f backend/deployment/docker-compose.yml up -d        # brings up beat
docker compose -f backend/deployment/docker-compose.yml exec app alembic upgrade head   # -> 0011
docker compose -f backend/deployment/docker-compose.yml logs beat | grep reap_stuck
N=8 bash bench/stage_a_decision_trail.sh                             # exits non-zero on any failure
```
