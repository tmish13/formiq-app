# Evidence map — claim → note → command

Every line an interviewer might question, with where its number lives and how to reproduce it.
All commands run from the repo root; container commands assume the compose stack is up.

## Pipeline

| claim | note | reproduce |
|---|---|---|
| 1,000-video batch with the reaper running: 0 never-run, 0 flips, A1–A10 zero | `bench/results/2026-09-23-week1-gate.md` | `SEL=… N=600 bash bench/stage_a_decision_trail.sh; bash bench/trail_report.sh '<email-like>'` |
| Reaper bug (G-48): 772 re-dispatched, 261 failed unrun, 520 completed rows flipped | `bench/results/2026-09-23-gate1b-full-corpus.md` §2 | the worker log excerpt and one row's trace are in the note |
| 0 OOM kills in 1,166 videos after recycling (7 in 900 before); 9.25 videos/min, p50 9.7 s | `bench/results/2026-09-24-week2-pipeline.md` §6; matrix §3 | `bash bench/worker_matrix.sh`; `bench/results/worker_matrix/matrix.tsv` |
| 20 simultaneous uploads: 17 × 202 + 3 × 503, 0 dropped | `2026-09-24-week2-pipeline.md` §5 | `SUBMIT_STAGGER=0 N=20 bash bench/phase1_concurrent_batch.sh` |
| Image matches requirements.txt (G-43) | `AUDIT.md` G-43 | `docker compose exec worker python -m app.core.image_check` |
| End to end against the running stack | `tests/e2e/test_live_pipeline.py` | `pytest -m "e2e or slow" tests/e2e/test_live_pipeline.py` (inside the image) |
| Decision trail: every run explainable | `2026-09-23-stage-a-decision-trail.md` | `bash bench/trail_report.sh '<email-like>'` |

## Model

| claim | note | reproduce |
|---|---|---|
| Clean held-out PostureV1: AUROC 0.7057 [0.6246, 0.7808], F1 0.6036 vs floor 0.5865, n=188 | `2026-09-23-gate1b-full-corpus.md` §4 | `python backend/scripts/eval_runner.py --target posture --splits content --split test` |
| Two threshold turns, both negative | `2026-09-23-gates-pipeline-as-instrument.md`, week-1 note §5 | `python bench/cycle_turn.py` |
| Controlled retrain NEGATIVE, one logged test read | `2026-09-23-retrain-controlled.md`; `bench/results/retrain/TEST_READ_LOG.jsonl` | `bench/retrain/run.sh {build,train,final}` — `final` refuses a second read |
| Acceptance bar: below Tier 1 for both models; flip rates 15.3 % / 25.5 % | `2026-09-24-acceptance-bar-verdict.md` | `python bench/acceptance_bar_verdict.py`; `bench/retrain/flip_rate.py` |
| 105 duplicate videos, 45 cross-split, 80 conflicting pairs (G-44) | `2026-09-23-corpus-duplicates.md` | `python bench/corpus_duplicates.py` |
| Pinned historical numbers are contaminated (≤ 12 %) and caveated | `app/eval/provenance.py`; `tests/unit/test_contamination_caveat.py` | the test fails if a file quotes one without the caveat |
| Depth has no recoverable signal (AUROC 0.578 best of ten axes) | `2026-09-23-depth-rule-negative-result.md`, `2026-09-23-corpus-level-negative.md` | `python bench/depth_rule_calibrate.py` |
| The confidence badge was inverted; "High" right 56 %, "Low" 93 % | `2026-09-23-displayed-score-and-badge.md` | `python bench/displayed_score_check.py` (inside the image) |
| The label is the ceiling; relabelling pilot pre-registered | `ML_AUDIT.md` §10–11; `bench/relabel/PREREGISTRATION.md` | `bench/relabel/agreement.py`, `bench/relabel/gate.py` after annotation |

## Process

| claim | where |
|---|---|
| 51 gaps, each with number, commit and note | `AUDIT.md` |
| Full ML lifecycle audit across two codebases | `ML_AUDIT.md` |
| The bar that decides what ships | `docs/ml/ACCEPTANCE_BAR.md` |
| Every retrain reads test once, guarded by CI | `backend/tests/unit/test_retrain_test_read_log.py` |
| What was NOT reached, stated | `docs/EXECUTION_PLAN_2026-09-24.md` §0 |
