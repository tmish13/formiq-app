# Acceptance bar — when a FormIQ verdict may ship, and when to stop iterating

**Status:** adopted 2026-09-23 · cited by every pre-registration in `bench/retrain/` · numbers below
are the state on adoption day, from `bench/results/2026-09-23-gate1b-full-corpus.md`,
`2026-09-23-retrain-controlled.md` and `2026-09-23-displayed-score-and-badge.md`.

## Where every number comes from

- **Population:** the clean content-level test split (`bench/results/content_level_splits.json`):
  de-duplicated by content hash first, then split by user; n ≥ 190; conflicted duplicates withheld.
- **Pose pass:** the serving pass (`pose_pass_id` recorded on every run and every artifact).
- **Metrics:** `backend/app/eval/metrics.py` only — AUROC, precision/recall/F1, both coverage views,
  the trivial (all-positive) floor, bootstrap CI n=2000 seed 0. No notebook-local metrics.
- **Reads:** the test split is read once per artifact, behind `--final`, and logged in
  `bench/results/retrain/TEST_READ_LOG.jsonl`; `tests/unit/test_retrain_test_read_log.py` fails CI on
  a second unforced read. A number without n, prevalence, floor and CI is not a number.
- **Comparisons against the incumbent** are paired: same videos, same cached keypoints, the shipped
  weights scored through the serving loader.

## Tier 1 — statistical: is the signal real?

| criterion | rule | posture, 2026-09-23 |
|---|---|---|
| separation | AUROC 95 % CI **lower bound ≥ 0.75** | 0.7057 [0.6246, 0.7808] — **fails** |
| above chance at the shipped threshold | F1 CI lower bound **>** all-positive floor | 0.6036 [0.5135, 0.6854] vs 0.5865 — **fails** |
| replacing the incumbent | paired ΔAUROC CI **excludes zero** and the point estimate is higher | retrain −0.0504 [−0.1150, +0.0112] — **fails** |

## Tier 2 — product: is the verdict usable? (on the label the app shows, `posture_collapsed`)

| criterion | rule | 2026-09-23 |
|---|---|---|
| precision at usable recall | **P ≥ 0.70 at R ≥ 0.60**, threshold chosen on validation, one test read | P 0.5258, R 0.7083 — **fails** |
| abstention honest | coverage ≥ 0.85 **and** abstain-as-negative F1 within 0.05 of covered-only | 0.941; 0.5829 vs 0.6036 — passes |
| reliability | per-item verdict flip rate against a second pose pass **≤ 10 %** | 14.9 % (G-39) — **fails** |

## What ships at each state — the stop rule

| state | what the user gets |
|---|---|
| below Tier 1 **(today)** | no per-video posture verdict. Knees-forward **localisation** ("knees travelled forward at 1.4 s"; 80.2 % within-video agreement) and `any_fault` as the only binary. No accuracy claim anywhere in the UI. |
| Tier 1, not Tier 2 | the verdict, **banded** ("likely / unclear"), abstention on, no accuracy claim. |
| both tiers | the verdict; the UI may state the measured precision and recall with n and CI. |

**Stop iterating** when both tiers hold on the clean test with n ≥ 190 — **or** when two consecutive
pre-registered interventions fail to move the AUROC lower bound by ≥ 0.03. Then re-scope, do not
retune. The threshold is already known not to be the lever (two cycle turns, both negative:
ΔF1 −0.0349 [−0.2172, +0.1135] at n=41, −0.0509 [−0.1349, +0.0272] at n=188).

## Per verdict class

| class | state on 2026-09-23 | bar that applies |
|---|---|---|
| `posture` | below Tier 1 | Tier 1 + Tier 2 above |
| `any_fault` | at its floor (F1 0.80 vs 0.83, AUROC 0.58–0.68) — no verdict | Tier 1 with floor = all-positive F1 at 0.71 prevalence (0.83) |
| `knees_forward` localisation | within-video agreement 0.802 | ≥ 0.80 per pose pass **and** flip rate ≤ 10 % before it is a claim |
| `stability` | never shipped; ~20 test positives; first numbers F1 0.16–0.31, AUROC 0.68–0.74 | not measurable; label ≥ 60 positives or keep the explicit decline (G-42) |
| `depth` | no recoverable signal (G-40); 47 byte-identical pairs labelled both ways | stays NULL |

## What is displayed, and how it is labelled

- The app shows `posture_score = 0.65·model + 0.35·components`. Measured on the same rows, the blend
  separates the label no better and no worse than the model probability (paired ΔAUROC +0.0004
  [−0.015, +0.016] on test). It is decoration, not signal; the components are unvalidated named
  scores and are labelled as such.
- The confidence badge was inverted until G-50 (2026-09-23). Its band thresholds (0.60 / 0.80) were
  never calibrated against correctness; re-derive them from `bench/displayed_score_check.py` once the
  fixed badge has run over a batch.

## Changing this document

A change to a threshold here is itself a pre-registered change: state it, date it, and never after
a test read that it would have flipped.
