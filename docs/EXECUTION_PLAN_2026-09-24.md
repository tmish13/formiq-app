# Did the pipeline reach its goals? — and the plan to execute next

**Date:** 2026-09-24 · companion to `docs/NEXT_STEPS.md` (the ranked list) · every "measured" cell
below links to a note under `bench/results/`.

## 0. The goals, step by step

The project's stated pipeline (`CLAUDE.md`, the 10-step process) against what exists, is measured,
and is trusted today:

| # | intended step | state | evidence |
|---|---|---|---|
| 1 | Video upload (presigned S3 + metadata) | **Reached, differently.** Uploads go through the API to a shared volume; presigned S3 exists but dispatches nothing. Bounded at 4 in flight per process, 503 above; 20 simultaneous: 17 + 3, 0 dropped. | `2026-09-24-week2-pipeline.md` §5 |
| 2 | Video processing (30 fps extraction, normalisation) | **Reached.** | day-1 note; every run's `n_frames` in the trail |
| 3 | Pose detection (MediaPipe, 33 keypoints) | **Reached and identified.** Every verdict carries its `pose_pass_id`; two passes disagree on 15 % of verdicts (measured, not assumed). | `2026-09-23-pose-pass-verdict-instability.md`, `2026-09-24-acceptance-bar-verdict.md` |
| 4 | Angle calculation | **Reached** (the 64-D temporal block). | features_151d |
| 5 | Exercise classification (LSTM/CNN/Transformer) | **Not reached.** A stub that raises `NotImplementedError`; squat only, said so in the UI now. | `AUDIT.md` (serving map) |
| 6 | Rule-based validation | **Built, measured, and honestly shadow.** Depth, valgus, knees-forward rules exist; all three refuted as per-video verdicts on this corpus; recorded as advisory, never authoritative. | `2026-09-23-corpus-level-negative.md`, G-40 |
| 7 | Feedback generation (Langflow / OpenAI) | **Not reached.** Langflow is a commented line; the RAG path is behind a flag defaulting off, unevaluated (G-04/G-05). Deliberately parked: feedback on a verdict below the bar is confident noise. | `AUDIT.md` G-04, G-05 |
| 8 | Visual comparison (pose overlay, fault annotation) | **Not reached.** | — |
| 9 | Results storage (PostgreSQL) | **Reached and exceeded.** Every analysis leaves an append-only run and its checker decisions (inputs digest, pose pass, frame count); the trail survived a bug that corrupted 520 form-check rows and is what let the evaluation stand. | `2026-09-23-stage-a-decision-trail.md`, G-48 |
| 10 | Results delivery (REST + WebSocket) | **REST reached; WebSocket not.** The router is never included; clients poll every 2 s and it works. | G-18 |

**The AI feedback loop.** What was wanted was a loop: decisions → labels → metrics → a better model.
The *instrument* is built and closes with zero inference — stored decisions, a content-hashed label
store, one metrics implementation, an evaluation runner that reports n, prevalence, floor and CI, a
cycle turn, a pre-registered retrain protocol with a single logged test read — and it has been turned
four times (two threshold turns, one retrain, one bar verdict). Every turn was a **negative**. The
loop works; the model it feeds has not improved, because the label it learns from is a degree
judgement on a near-universal behaviour (AUROC 0.57 for the predicate itself). So: **the feedback
loop reached its goal as an instrument and has not reached it as an engine.** The relabelling pilot
is the one experiment left that can change that.

**The architecture.** Five services (API, worker, beat, Postgres, Redis) and one codebase. Reached:
a 1,000-video batch with the reaper running, 0 never-run, 0 flips, 0 kills in 1,166 videos, 9.25
videos/min, p50 9.7 s; every number reproducible from the trail. Not reached: the "microservices"
of the plan (G-08 — and `docs/architecture/2026-09-24-speed-and-decomposition.md` shows a split is
not a speed lever), observability (no stage timings, no metrics), one deployment manifest, a green
`alembic check`.

**The accuracy goal.** The only stated one was "95 % for top-5 exercises" for a classifier that does
not exist. The bar that now exists (`docs/ml/ACCEPTANCE_BAR.md`) is not met by the shipped model
(AUROC 0.71 [0.62, 0.78], F1 at the all-positive floor, 15 % verdict flips) or by the retrain.

**Verdict:** the reliability and measurement goals are reached and defensible; the product goals
(multi-fault verdicts, generated coaching, overlays, real-time delivery, a classifier) are not, and
the model is below the bar. The honest product today is knees-forward localisation and `any_fault`.

## 1. The plan to execute (each item its own branch, merged to main when its gate holds)

| # | branch | change | gate |
|---|---|---|---|
| 1 | `audit/g01-measured-claims` | `docs/CV_CLAIMS.md`: each old claim, its status, the measured replacement, the note | every number links to a note |
| 2 | `docs/evidence-map` | `docs/EVIDENCE_MAP.md`: claim → note → commit → command | one row per claim in the CV doc and the audits' headline findings |
| 3 | `audit/stage-timings` | `_stage()` context manager in `analysis_tasks.py` recording per-stage ms into `analysis_runs.settings_snapshot`; `bench/pipeline_dashboard.sh` prints per-stage p50/p90 | 50-video batch: 0 runs without `stage_ms`; the 45 % explained |
| 4 | `audit/build-hygiene` | `bench/rebuild_images.sh`: free-space assertion (VM fs), prune dangling, build, image check in all three | refuses below the threshold; prints `docker system df` before/after |
| 5 | `audit/g35-red-tests` | fix or correctly scope the two failing tests | suite fully green in the worker image |
| 6 | `audit/g06-g07-retire-demo` | quarantine the 18-sample demo model with a README; track the eval outputs; `EVAL.md` with both numbers | no file named production that is not |
| 7 | `audit/ship-per-bar` | `/ml-analysis` exposes knees-forward localisation and `any_fault`; AnalysisPage shows them, bands the posture score as experimental, drops "AI Analyzed"; Dashboard/Progress left for the user's uncommitted change | UI shows only what §A3 permits; e2e still green |
| 8 | `audit/g38-alembic` | declare the real indexes in the models (incl. the G-10 unique), remove spurious `index=True` on primary keys, one hand-reviewed migration, `alembic check` in CI | `No new upgrade operations detected` |
| 9 | `audit/upload-streaming` | `file.file` streamed to storage in chunks while hashing; gunicorn `--timeout` | 20-upload harness with the bound raised to 8: 0 SIGKILL |
| 10 | `audit/cache-is-the-db` | DB idempotency hit → trail row `pose_source='cache'`, keyed also on `pose_pass_id`; dead Redis cache paths and broken `expire=` callers removed | re-upload 20 files: 20 cache rows, 0 new inference |
| 11 | `audit/manifests-one-truth` | one compose file; k8s probe path fixed; the others deleted or marked | `docker compose config -q` exits 0 |
| — | pilot (humans) | two annotators fill `bench/results/relabel/annotation_sheet_{A,B}.csv` | κ ≥ 0.60; AUROC lower bound ≥ 0.6746 |

Order is by value per hour with the human-dependent item running in parallel. Items 9–11 are
last because the batch already holds without them.

### 1a. Status, 2026-09-24 evening (every item ran; each has a note in `bench/results/`)

| # | branch | commit | outcome |
|---|---|---|---|
| 1 | `audit/g01-measured-claims` | 497c8ca | done — `docs/CV_CLAIMS.md` |
| 2 | `docs/evidence-map` | c13b396 | done — `docs/EVIDENCE_MAP.md` |
| 3 | `audit/stage-timings` + `audit/stage-timings-results` | 30fd788, 8b54bb9 | done — pose extraction is **95.5 %** of the task; the "45 % unexplained" withdrawn (`2026-09-24-stage-timings.md`) |
| 4 | `audit/build-hygiene` | 57d885b | done — `bench/rebuild_images.sh` refuses below 15 GB free |
| 5 | `audit/g35-red-tests` | dcd115e, c4002da | done — suite in the worker image **1,406 passed, 33 skipped, 0 failed** on the final tree |
| 6 | `audit/g06-g07-retire-demo` | 6b95873 | done — demo model quarantined, `EVAL.md` |
| 7 | `audit/ship-per-bar` | 5040caa | done — `/ml-analysis` localisation + `verdict_status`; posture score labelled experimental |
| 8 | `audit/g38-alembic` | 33c950e | done — `alembic check`: **No new upgrade operations detected.**; three UNIQUE indexes the app assumed now exist (`2026-09-24-g38-alembic.md`) |
| 9 | `audit/upload-streaming` → `audit/g54-api-loads-ml` | c76393a, 2142608 | streaming alone was a **negative** (peak 4,656 → 4,322 MiB, kill persisted); the cause was **G-54**: each API worker built MediaPipe/torch on its first request (+407 MiB). Fixed: the same 20-upload burst went **14 accepted / 6 dropped / 1 kill / 4,656 MiB → 20 / 0 / 0 / 972 MiB** (`2026-09-24-g54-api-loads-ml.md`); at the default 4 slots: 14 × 202 + 6 × 503, 0 dropped, 0 kills, 1,072 MiB (`2026-09-24-burst-4-slots.md`) |
| 10 | `audit/cache-is-the-db` | fc1b0c6 | done — G-53: 20 files twice → 20 real runs, 20 `pose_source='cache'` rows, 0 cross-pass, 0 second inference, cache row p50 2.28 ms |
| 11 | `audit/manifests-one-truth` | c6a6f78 | done — one compose file; k8s probes on real routes; dangling terraform scaling removed; `infrastructure/README.md` |
| — | pilot (humans) | — | **waiting on two annotators**; kit and gates ready |

Open, deliberately: G-55 (committed self-signed, expired TLS keys — user's call), the rate-limit
middleware guard (`main_setup.py:58`, enabling it is a behaviour change), `DashboardPage.tsx:220`
copy (the user's own uncommitted edit). Caveat for every timing quoted today after 11:55 PDT: the
laptop was on battery with Low Power Mode on and ran pose extraction 2.6× slower per frame than the
mains-power validation; the stage *split* held, the absolute times did not.

### 1b. The second pass, same evening (plan "what comes after the pipeline", Track C and Track B1–B4)

| item | branch | outcome |
|---|---|---|
| C1 CI that runs | `audit/g17-ci-truth` → `g17-tests-cwd` → `g17-frontend-workflow` → `frontend-typecheck` → `g17-ci-lfs` | **green**: run 36069257793 — image check, alembic check, 1,490 tests on a GitHub runner; seven dead workflows deleted (`2026-09-24-ci-truth.md`) |
| C2 keys | `audit/g55-keys` | removed; README says certificates are issued at deploy time |
| C3 log redaction | `audit/g16-log-redaction` | structlog processor + stdlib filter; the validation handler no longer logs `input`; 0 clear e-mails / passwords / JWTs in the live segment (`2026-09-24-log-redaction.md`) |
| C4 schema owner | `audit/g23-schema-owner` | API image starts through `deployment/entrypoint.sh` (`alembic upgrade head`, then gunicorn); `create_all` only under test; boot from an empty DB verified (`2026-09-24-schema-owner.md`) |
| C5 health routes | `audit/health-routes` | `/health/metrics` is a real exposition, `/health/rate-limits` gone (`2026-09-24-health-routes.md`) |
| C6 burst at 4 slots | `audit/burst-4-slots` | 14 × 202 + 6 × 503, 0 dropped, 0 kills, 1,072 MiB (`2026-09-24-burst-4-slots.md`) |
| C7 frontend recorded | `audit/frontend-tests-recorded`, `audit/frontend-typecheck` | typecheck green after one config line; jest 17/32 suites red — **G-56 filed, not fixed** (`2026-09-24-frontend-tests.md`) |
| C8 dead-code sweep | — | not done (optional) |
| C9 documents | `docs/truth-2026-09-24`, `audit/rate-limit-guard-log` | README, CLAUDE.md, AUDIT rows corrected; the rate-limit log line tells the truth |
| B1 provenance | `ml/provenance` | notebook codebase imported with hashes, recipe, environment, discrepancies (`backend/ml_training/posture_v1/provenance/PROVENANCE.md`) |
| B2 model card | `ml/model-card` | `backend/app/ml/posture_v1/MODEL_CARD.md` |
| B3 manifest provenance | `ml/manifest-provenance` | `provenance` block + `test_posture_v1_artifact_integrity.py` |
| B4 one variable | `ml/ml-dir-env` | `FORMIQ_ML_DIR` replaces 17 hard-coded paths |
| B5 seeded trainer | `ml/trainer-port` | dataset from the serving pose pass (912/218/196), the notebook's recipe seeded with a deep-copied best state, guarded single test read, exporter with provenance; architecture parity with the shipped checkpoint and a loader round trip tested; 5-seed train/val run started (`2026-09-24-trainer-port.md`) |
| A pilot | — | sheets ready, annotators arranged, 0 rows graded yet |
