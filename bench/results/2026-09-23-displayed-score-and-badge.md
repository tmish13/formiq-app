# The displayed score and the confidence badge, measured from stored decisions

**Date:** 2026-09-23 · **Branch:** `audit/g50-confidence-badge` · **Script:** `bench/displayed_score_check.py` ·
**Raw:** `bench/results/displayed_score_check.json` · no inference; every number is a query over
`analysis_runs` / `checker_decisions` / `form_checks.results` joined to the label store by content hash,
restricted to the content-level splits. Metrics from `app/eval/metrics.py`, bootstrap n=2000 seed 0.

## 1. The badge was anti-informative (G-50)

`compute_calibrated_confidence` used `boundary_score = 1 − 2·|p − 0.5|`, which is highest at p = 0.5.
The label the user saw is stored per row (`results.posture_v1.calibrated_confidence.label`). Accuracy
of the shipped verdict (threshold 0.525) by badge, among answered rows:

| split | High | Moderate | Low |
|---|---|---|---|
| test | 0.561 (n=98) | 0.646 (n=65) | **0.929** (n=14) |
| validation | 0.542 (n=96) | 0.761 (n=71) | **0.773** (n=22) |
| train | 0.544 (n=401) | 0.728 (n=345) | **0.883** (n=77) |

"High" was right about as often as a coin (54–56 %); "Low" — the badge that tells the user to
re-record — was right 77–93 % of the time. The ordering is exactly inverted, on every split, on
1,300 videos. The fix (`2·|p − 0.5|`) flips the ordering; the band thresholds (0.60 / 0.80) were
never calibrated against correctness and still are not — a follow-up once the fixed badge has run
over a batch is to re-derive them from this same query.

## 2. The displayed score adds nothing to the model, and costs nothing

The app shows `posture_score = 0.65·model_score + 0.35·components` (hand-weighted z-scores). On the
same rows (rows where a score was shown):

| split | n | AUROC displayed score [95 % CI] | AUROC model prob [95 % CI] | paired Δ (displayed − model) [95 % CI] |
|---|---|---|---|---|
| test | 177 | 0.7061 [0.628, 0.784] | 0.7057 [0.625, 0.782] | +0.0004 [-0.015, +0.016] |
| validation | 189 | 0.7727 [0.699, 0.838] | 0.7783 [0.704, 0.847] | -0.0056 [-0.018, +0.008] |
| train | 823 | 0.7562 [0.723, 0.787] | 0.7611 [0.728, 0.793] | -0.0050 [-0.012, +0.002] |

The 35 % component blend neither helps nor hurts separation (every paired interval spans zero and is
narrower than ±0.02). Decision under ACCEPTANCE_BAR §A4: the blend is decoration, not signal; it is
not worse, so it is not changed here — the bar continues to be measured on the model probability,
and the blend's components stay unvalidated named scores, labelled as such.

## Reproduce

```bash
docker run --rm --network deployment_default -v $PWD/backend:/app -v $PWD:/repo <db env> -w /app \
  deployment-beat:latest python /repo/bench/displayed_score_check.py
```
