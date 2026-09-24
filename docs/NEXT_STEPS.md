# Next steps — after the audits, Week 1, Week 2 and the merge (2026-09-24)

State: `main` carries the full audited chain (pushed to origin at `34bd840`). The pipeline holds a
1,000-video batch with the reaper running, loses nothing to OOM, and answers 503 under upload load.
The model is below the acceptance bar and the only lever left is the label. This is the order to
work in, with the gate that lets each step stop.

| # | step | why now | effort | gate / evidence |
|---|---|---|---|---|
| 1 | **Replace the CV claims with the measured numbers (G-01)** | The audit rated "100+ uploads, sub-300 ms, 99.9 %" NOT FOUND. There are now real numbers: 9.25 videos/min, p50 9.7 s, 0 kills / 1,166, 20 concurrent uploads bounded, a 900-video batch with A1–A10 zero, a clean held-out AUROC with its CI. Say those instead. | S | every number on the CV links to a `bench/results/*.md` note |
| 2 | **Evidence map** | One page that maps each claim (pipeline, model, process) to the note, commit and command that reproduces it — the artefact an interviewer can follow. | S | `docs/EVIDENCE_MAP.md`, every row reproducible |
| 3 | **Ship what the bar allows (plan C2, `ACCEPTANCE_BAR` §A3)** | The app still shows a per-video posture score and an "AI Analyzed" badge that the bar says may not ship. Show knees-forward localisation ("knees travelled forward at 1.4 s") and `any_fault`; band or hide the posture verdict; no accuracy language. | M | UI shows only what §A3 permits; localisation's within-video agreement ≥ 0.80 and flip rate measured per pose pass |
| 4 | **Run the relabelling pilot (needs two people)** | The only route to a higher model number. Sheets, importer and both gates are ready (`bench/relabel/`). | ~2 annotator-days | Gate 1 κ ≥ 0.60; Gate 2 incumbent AUROC lower bound ≥ 0.6746 on `posture_fault_v2` — else stop at localisation |
| 5 | **Per-stage timings (plan D6)** | 45 % of each video's 9.7 s is unexplained (fetch/decode/DB/finalize). Timings in `settings_snapshot` cost nothing and say where a cheap second is. | S | 0 completed runs without `stage_ms`; a per-stage p50/p90 table in `bench/pipeline_dashboard.sh` |
| 6 | **Build hygiene (G-51)** | A free-space assertion before `docker compose build`, prune before rebuilding three copies of one image, raise the Docker disk image size. Fifth disk incident this month. | S | the rebuild script refuses below N GB; `docker system df` printed before and after |
| 7 | **Fix the two failing tests (G-35) and retire the fake metadata (G-06, G-07)** | Two red tests on main since before Phase 1 and an 18-sample model named `production_metadata.json` are cheap credibility losses. | S | suite fully green; the file gone or renamed with its n |
| 8 | **Alembic reconciliation (G-38)** | `alembic check` has 92 drift ops; the models do not declare the idempotency unique index the DB relies on. Declare the real indexes in the models, drop the spurious `ix_*_id` on primary keys, one hand-reviewed migration, then `alembic check` in CI. | M | `alembic check`: "No new upgrade operations detected" |
| 9 | **Upload streaming (plan D4a)** | The 503 bound makes upload memory finite (≤ 16 × 100 MB), not small. Pass `file.file` and copy in chunks while hashing. | S–M | 20-upload harness: 0 SIGKILL with the bound raised to 8 |
| 10 | **Cache visibility (plan D3)** | The DB idempotency lookup is the cache; make a hit a trail row (`pose_source = 'cache'`) keyed also on `pose_pass_id`; delete the dead Redis cache paths and the broken `expire=` callers. | S–M | re-upload 20 files: 20 rows with `pose_source = 'cache'`, 0 new inference |
| 11 | **One deployment truth (plan D5b)** | Three manifests describe three different systems; two run no worker. | S | one compose file; k8s probe path fixed; the rest deleted or marked non-deployable |
| 12 | **Reliability before accuracy (only after step 4 passes)** | The retrain artifact flipped 25 % of verdicts between pose passes, the incumbent 15 %. Any future model is measured on flip rate first; temporal smoothing or ensembling over passes is a reliability intervention worth one pre-registered run. | M | flip rate ≤ 10 % on the 196 test clips before an accuracy read |

Not on the list, on purpose: a new training run on the current labels (the bar's stop rule counts
it as the second failed intervention; the retrain already showed what it yields), microservices
(`docs/architecture/2026-09-24-speed-and-decomposition.md` — not a speed lever), LLM feedback on a
verdict below the bar, and WebSocket delivery while polling works and there are no users.

Rules that stay: one gap per branch; evidence in `bench/results/` with command, environment and
raw output; never round up; the test split is read once per artifact; nothing ships that the data
does not support.
