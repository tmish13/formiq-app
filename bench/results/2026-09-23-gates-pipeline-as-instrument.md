# The pipeline measures something now — and the first cycle turn says stop tuning

**Date:** 2026-09-23 · **Branch:** `audit/phase2-depth-rule`
**Scripts:** `bench/select_eval_batch.py`, `bench/build_content_splits.py`,
`backend/scripts/eval_runner.py`, `bench/cycle_turn.py`
**Raw:** `bench/results/eval_posture_content.json`, `bench/results/cycle_turn.json`

Before this, every box in the pipeline was built and **8 videos** had been through the full
width of it. The decision trail existed and had never measured anything.

> **⚠️ G-44 context.** The historical figures (F1 0.6131 etc.) were measured on a contaminated
> basis. Everything below is on the **repaired content-level basis** — no byte-identical file
> spans a split — so these are the first numbers in the project that are not upper bounds.
> They are also small: see *n* everywhere.

## Gate 0 — splits that are leakage-free at both levels at once

The two constraints **chain**: user A's video is byte-identical to user B's, so A and B must
share a split; B has another identical to C's, so C joins. Both obvious implementations are
wrong — group by user and content still leaks, group by hash and the subject guarantee is
gone. The split unit is a connected component under *shares-a-hash OR shares-a-user*.

**`minimal` mode moves 11 videos (0.8%)** and keeps ratios at 68.8/16.4/14.8. A full
re-partition moves 46%, which would confound any before/after with a population change — the
same reason the pose-pass comparison was paired. 299 videos are **withheld**: 161 for
contradictory duplicate labels, 138 with no file on disk. Both reasons recorded per row.

## Gate 1a — 300 videos through the live pipeline

297 of 300 runs completed. Median run **18s**, ~16/min at concurrency 4, ~26 minutes total.
Videos judged by the trail: **8 → 291**.

**3 runs (1.0%) were left open**, with no decisions and no `pose_pass_id`. Cause confirmed in
the worker log: three prefork children **SIGKILLed (signal 9)**, timestamps matching exactly.
That is OOM — four children each holding MediaPipe and PyTorch on a 7.65 GiB host. **G-36's
mechanism applies to the worker, not only the API**, and the measured worker loss rate at
concurrency 4 is **1.0%**.

The designed recovery held at scale: those 3 form checks went to FAILED via Phase 1's
`reject_on_worker_lost`, and the reaper's unclosed-run sweep closed all 3 as `abandoned`.
**Zero silent losses in 300 videos.**

## Gate 2 — the first number measured from the deployment

`posture_v1`, content-level basis, **n = 281**, of which **96 are real posture faults (34.2%)**:

| | tp | fp | tn | fn | P | R | F1 |
|---|---|---|---|---|---|---|---|
| covered-only (256 answered) | 62 | **75** | 98 | 21 | 0.4526 | 0.7470 | **0.5636** |
| abstain-as-negative (all 281) | 62 | **75** | 110 | 34 | 0.4526 | 0.6458 | **0.5322** |

Coverage **91.1%**. Trivial floor F1 **0.5093**, majority-class accuracy **0.6584**.

**Read it precisely:**

- **Precision 0.4526.** Of 137 videos flagged as faults, 62 were and **75 were not**. The model
  is wrong more often than right when it speaks.
- **F1 0.5322 vs floor 0.5093 = +0.023.** Above the all-positive floor, barely.
- **Accuracy 0.6121 vs majority-class 0.6584.** **Below** the baseline that never flags
  anything. The model's only edge is on a metric that rewards catching positives, and it buys
  that recall by over-flagging.
- **Of the 25 abstentions, 13 were real faults** — 52% against a 34% base rate. It declines
  disproportionately on the faults, which is the wrong direction: it abstains exactly where it
  would have been useful.

## Gate 3 — one cycle turn, and it cost zero inference

**That is the headline about the cycle, not the result.** A threshold applies to a stored
`prob`, so changing it and re-measuring is a query. The same turn without a decision trail
means re-running the corpus — ~26 minutes here — and G-39 says that re-run would produce
different keypoints (14.9% of verdicts move between MediaPipe passes), so the comparison would
not have been of thresholds at all.

The turn, with test read once:

| stage | n | result |
|---|---|---|
| gap analysis (train+val) | 240 | 67 FP vs 22 FN — over-flagging, so the lever is a *higher* threshold |
| sweep, **validation only** | 41 | incumbent 0.525 → F1 0.6667; best **0.65** → F1 0.6923 |
| **test, once** | 41 | incumbent F1 **0.4516**; chosen 0.65 → F1 **0.4167** |

**Delta F1 −0.0349, 95% CI [−0.2172, +0.1135] — includes zero.**

**The change made things worse and the turn is a negative.** A threshold selected on 41
validation videos did not transfer to 41 test videos. Prevalence differs across the splits
(dev 0.358, val 0.293, test 0.244), which at this n is enough to move the optimum on its own.

### The useful finding is the width of that interval

**±0.16 F1 at n=41.** No threshold change — and no model change — is measurable on this much
data. The cycle is **mechanically sound and statistically starved**.

That is an answer, not a failure: it says the next action is **more stored decisions, not more
tuning.** Gate 1a covered 300 videos; the corpus has ~1,300 usable ones. Running the rest is
~1.5 hours of compute and would take test from 41 to roughly 190, shrinking the interval by
about half.

It also rules something out cheaply: **had this turn shown a gain, it would have been noise.**
The discipline of fitting on validation and reading test once is what made that legible instead
of shippable.

## Status

| | |
|---|---|
| pipeline built end to end | **yes**, every box |
| exercised at scale | **partly** — 291 of ~1,300 usable videos |
| clean performance number exists | **yes**, first one: F1 0.5322 vs floor 0.5093 |
| model beats trivial baselines | **no** — above the all-positive F1 floor, below majority-class accuracy |
| cycle closes | **yes**, one turn, zero inference |
| cycle can make decisions | **not yet** — ±0.16 F1 at n=41 |

## Reproduce

```bash
python bench/build_content_splits.py            # Gate 0
python bench/select_eval_batch.py --n 300       # Gate 1 batch
SEL=bench/results/eval_batch_selection.json N=300 TIMEOUT_S=7200 SUBMIT_STAGGER=2 \
  bash bench/stage_a_decision_trail.sh          # Gate 1a
# Gate 2, in-container (see the run commands in eval_runner.py's docstring):
#   python scripts/eval_runner.py --target posture --splits content
python bench/cycle_turn.py                      # Gate 3
```
