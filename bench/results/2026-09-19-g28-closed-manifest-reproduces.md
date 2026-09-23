> **CORRECTED 2026-09-19 — read `2026-09-19-v1-final-numbers-and-penn-shortcut.md` first.**
> Three claims below are wrong or overstated: (1) the "+0.004 above the floor" comparison mixes two
> populations — the manifest's own floor is 0.650, so it is +0.074 above; (2) "reproduces" should read
> "consistent with" — 11 of the manifest's videos are unaccounted for; (3) the "46.5% of depth-fault squats
> flagged = production defect" claim is retracted — 25 of those 33 flags were correct under the original
> multilabel truth, and honest precision is 0.76, not 0.54. The provenance table and the FP-by-class
> decomposition stand.

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
>
> **This file's own population: 18 of the 173 reconstructed binary-task videos (10.4%)
> have a byte-identical twin in train.** The manifest records `test_samples: 162`, so
> the overlap is approximate. G-28's conclusion — that the manifest's FP count
> reproduces exactly (19 = 19) — is unaffected: it is a statement about which
> *population* was scored, not about the score's magnitude.

# G-28 closed — the manifest's 0.724 reproduces. It was measured on a different population.

**Date:** 2026-09-19 · **Bench only** · supersedes the "precision-shaped shortfall" reading in
`2026-09-19-v1-held-out-evaluation.md`
**Per-video scores:** `2026-09-19-v1-test-per-video-scores.json`

## Provenance — found, all three settings

Source of every number in `posture_v1_manifest.json`:
`~/FORMIQ Form Analysis Model/runs/cnn_lstm_binary_enhanced_cw_results.json`

| setting | value | matches serving? |
|---|---|---|
| checkpoint | `best_cnn_lstm_binary_enhanced_cw_f0.5_0.736.pt` | **byte-identical** to `posture_v1.pt` (SHA-256 `b7375ca49a93…`) |
| `threshold_used` | 0.525 (25 thresholds tested on val) | yes |
| window | `max_seq=300`, first-300 truncate | yes |
| temperature | none at eval time (scoring.py T=1.5 affects displayed confidence only, not the decision) | n/a |
| **`labeled_samples`** | **162** — not 244 | **NO — this is the whole discrepancy** |

Same weights, same threshold, same window. The difference is WHO was evaluated.

## The cause: depth-fault videos were never part of the binary task

The test split is 87 good_form / 86 posture_fault / **71 depth_fault**. The training
notebook (`verify_no_depth_contamination_binary`, `transform_to_binary_targets`) removes
depth-fault videos entirely: the task is good_form vs posture_fault. That also explains
the manifest's train size of 809 against the split's 1137.

My 224-video run counted the 71 depth-fault videos as negatives. False positives by class:

| true class | n | flagged as posture fault | rate |
|---|---|---|---|
| good_form | 67 | 19 | 0.284 |
| **depth_fault** | 71 | **33** | **0.465** |

Remove them and the manifest reproduces:

| | TP | FP | P | R | F1 |
|---|---|---|---|---|---|
| all 224, depth as negative | 61 | 52 | 0.5398 | 0.7093 | 0.6131 |
| **binary task, n=153** | 61 | **19** | 0.7625 | 0.7093 | **0.7349** [0.658, 0.802] |
| manifest, n=162 | 55 | **19** | 0.7432 | 0.7051 | 0.7237 |

FP = 19 in both. The "31 extra false positives" were 33 depth-fault squats.
Back-solving the manifest confirms its population: 0.7432 = 55/74 and 0.7051 = 55/78
exactly, i.e. 78 positives + 84 negatives = 162.

## It is not calibration

Threshold sweep 0.20–0.80 on the saved scores:

| population | AUROC | floor | F1 @0.525 | F1 @best (tuned on test — optimistic) |
|---|---|---|---|---|
| binary task (153) | 0.7619 | **0.7197** | 0.7349 [0.658, 0.802] | 0.7662 @0.370 |
| all classes (224) | 0.7184 | 0.5548 | 0.6131 [0.531, 0.689] | 0.6190 @0.495 |

On the all-classes population no threshold recovers the manifest's precision
(best F1 0.619). The ranking itself puts depth-fault squats among the faults.

## The finding that matters more than the reproduction

**On its own evaluation population, the manifest's 0.724 sits at the trivial floor.**
That population is 56% positive, so always-predicting-fault scores F1 **0.7197**.
The manifest's 0.7237 is +0.004 above it; this run's 0.7349 is +0.015, with a CI lower
bound (0.658) well below. F1 was never able to distinguish v1 from a constant
classifier on this task. AUROC 0.76 says there is real ranking signal — F1 at this
prevalence just cannot show it. **Quote AUROC, not F1, for v1.**

**And the binary framing hides a production defect:** real users do shallow squats.
v1 flags 46.5% of depth-fault squats as *posture* faults — a class it was never
shown as a negative. Any deployed precision figure must be computed with depth faults
in the population (that is the 0.54), not the 0.76 of the curated task.

## Penn Action: the model never saw a Penn fault

| split | Penn Action clips | labels |
|---|---|---|
| train | 87 | **87 good_form, 0 fault** |
| validation | 17 | 17 good_form |
| test | 20 | 20 good_form |

All 124 Penn clips in the corpus are good_form. The external 24-video set's faults are
Penn Action faults — a (domain, class) combination with **zero training examples**.
Recall 0.111 there is the expected result, not a pipeline failure.

## What to quote

- v1, binary task as trained: **AUROC 0.76; F1 0.73 [0.66, 0.80] against a 0.72 trivial floor** (153 of 173 held-out, Fitness-AQA only)
- v1, realistic population incl. depth faults: **AUROC 0.72; F1 0.61 [0.53, 0.69] against a 0.55 floor; precision 0.54**
- Never the bare "0.724".

## v2 gate, restated on solid ground

AUROC > 0.76 on the binary task AND > 0.72 with depth faults included; F1 CI lower bound
above the floor on both; depth-fault squats in the negative set during training; at least
some Penn-domain faults in training before the external 24 are used as a gate.
