# The retrain against ACCEPTANCE_BAR.md — verdict

**Date:** 2026-09-24 · **Branch:** `ml/acceptance-bar-verdict` · **Script:** `bench/acceptance_bar_verdict.py` ·
**Raw:** `bench/results/acceptance_bar_verdict.json`, `bench/results/retrain/flip_rate.json`

No new test read. Every Tier-1 and precision/recall number comes from the single logged read of
2026-09-23 (`bench/results/retrain/TEST_READ_LOG.jsonl`, nine entries, none forced); the abstention
row from the live evaluation on stored decisions (n=188); the reliability row from a measurement that
uses **no labels** — the same 196 test clips under two MediaPipe passes.

Primary artifact, by the pre-registered rule: `B_temporal64__hgb` (test n=196).

## Tier 1 — statistical (is the signal real?)

| criterion | model | value | pass |
|---|---|---|---|
| separation | incumbent | 0.7306 [0.6616, 0.7995] | **FAIL** |
| separation | primary B_temporal64__hgb | 0.6802 [0.6067, 0.7526] | **FAIL** |
| above chance | incumbent @0.525 | 0.7111 [0.6411, 0.7753] vs floor 0.7595 | **FAIL** |
| above chance | primary @0.35 | 0.7385 [0.6774, 0.7955] vs floor 0.7595 | **FAIL** |
| replacing the incumbent | primary vs incumbent | -0.0504 [-0.1150, +0.0112] | **FAIL** |

## Tier 2 — product (is the verdict usable?), on the label the app shows

| criterion | model | value | pass |
|---|---|---|---|
| precision at usable recall | incumbent @0.525 | P 0.5333 R 0.7179 | **FAIL** |
| precision at usable recall | primary @0.31 | P 0.5315 R 0.7564 | **FAIL** |
| abstention honest | incumbent (live, n=188) | coverage 0.941, gap 0.0207 | **PASS** |
| abstention honest | primary | n/a: predicts on every clip | — |
| reliability | incumbent | 0.1531 (30/196) [0.1070, 0.2041] | **FAIL** |
| reliability | primary | 0.2551 (50/196) [0.1939, 0.3163] | **FAIL** |

## The new measurement: per-item flip rate between two pose passes

Serving pass `pp1_f9850424580ae186` (MediaPipe complexity 2, the cache every retrain number was
computed on) vs a second pass `pp1_0d1b7d0af7e9509e` (complexity 1, `bench/cache/keypoints_pass_c1`,
extracted 2026-09-24 with `AI_MODEL_COMPLEXITY=1 KEYPOINT_CACHE_DIR=… extract_keypoints.py --only
test_clip_names.txt`, 196 clips, 0 errors). Same footage, same models, same thresholds; only the
keypoints differ.

| model | threshold | flips / n | flip rate [95 % CI] | median \|Δp\| per clip |
|---|---|---|---|---|
| incumbent PostureV1 | 0.525 | 30 / 196 | **0.1531** [0.107, 0.204] | 0.0674 |
| primary B / hgb, `posture_fault` | 0.35 | 50 / 196 | **0.2551** [0.194, 0.316] | 0.1179 |
| primary B / hgb, `posture_collapsed` | 0.31 | 50 / 196 | **0.2551** [0.199, 0.316] | 0.1280 |

The incumbent's 15.3 % reproduces G-39's 14.9 % (33/221, dataset pass vs live pass) on a different
second pass and a different n. The retrain's 64-D temporal-block artifact is **less** stable than the
incumbent under a pose change — one verdict in four moves — which is what a model fitted on angle
statistics with no smoothing should be expected to do, and which no accuracy number would have shown.

## Verdict

**below Tier 1: no per-video posture verdict; localisation + any_fault only.** Neither the shipped PostureV1 nor the retrain's primary artifact meets a
single Tier-1 row; both fail the precision row and the reliability row of Tier 2. Under the bar's
stop rule this is the first of the two consecutive pre-registered interventions that may fail before
re-scoping is mandatory — and the bar itself already says what ships at this state: knees-forward
localisation and `any_fault`, no per-video posture verdict, no accuracy claim.

What would change the verdict, in order of evidence: the graded-severity relabel pilot (plan B2 —
the only lever the audits found), then a model whose per-item reliability is measured *before* its
accuracy (temporal smoothing or ensembling over pose passes is a reliability intervention, not an
accuracy one). A new training run on the current labels is the second intervention the stop rule
counts, and the retrain already showed what that yields.
