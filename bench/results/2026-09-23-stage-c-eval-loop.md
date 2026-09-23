# Stage C: the loop closes, and the safety nets that were not connected

**Date:** 2026-09-23 · **Branch:** `audit/phase2-depth-rule`
**Scripts:** `backend/scripts/import_labels.py`, `backend/scripts/eval_runner.py`,
`bench/corpus_duplicates.py`

The pipeline now runs end to end: **queue → two checkers → decision + audit → labels → eval.**
Every link reads what the previous one actually wrote.

## C.1 — five confusion matrices become one

`app/eval/metrics.py` landed in Stage 1 but nothing was migrated onto it, so every duplicate it
was meant to replace still ran. **Five**, not the four in the plan — the fifth
(`bench/depth_rule_calibrate.py`) was written during Phase 2, *after* the other four had already
been identified as duplicates. That is the argument for deleting them rather than noting them.

They differed in behaviour, not just spelling:

- three zero-denominator conventions across the five
- `eval_posture_v1_fixtures.py` inlined F0.5's `1.25`/`0.25`; `f_beta` derives them from β
- `ablate_face_block.py` divided accuracy by `len(rows)` rather than the counted total
- `eval_v1_test_split.py` fell back to `nan` when sklearn was absent; the module's `auroc` is
  rank-based and tie-corrected, so there is nothing to fall back from

`e2e_posture_v1_smoke.py` got the substantive change: it is an **abstaining** checker and was
reporting the **covered-only view alone**. Videos it declined simply left the denominator, which
flatters a model that abstains whenever it is unsure. It now reports both views and the floor.
Its counting loop is untouched — that loop encodes the script's scope and abstention policy;
only the arithmetic moved.

**The pinned v1 numbers still reproduce bit-for-bit** — F1 **0.6131**, CI **[0.5291, 0.6872]**,
AUROC **0.7184**. That is the check that matters: had the refactor changed the RNG call order the
CI would have moved.

A test per file now asserts the F1 formula is not re-derived anywhere, so a sixth copy cannot
appear quietly.

## C.2 — the label store

`0012_label_store`, keyed on **`content_hash`, never `form_check_id`**. A label is a statement
about bytes and has to survive re-analysis under a new model — which is exactly when the old
ground truth is most wanted.

`app/core/hashing.py` is the single definition of that key, shared with the upload path. If the
two diverged, every join would return nothing, and **that looks identical to "no labels imported
yet"**. A test asserts the chunk sizes match.

The unique key is `(content_hash, target, source, source_ref)`, so an expert review never
overwrites the dataset label it disagrees with. Both are kept; `app/eval/labels.py` resolves by
trust → timestamp → source_ref and reports `disputed` alongside the winner.

**Imported: 8,572 rows over 1,388 videos. Re-run: insert 0, update 0, unchanged 8,572.**

## C.4 — the eval runner

`eval_runner.py` reads stored decisions and stored labels and **recomputes nothing**. A number
from re-running the model tells you about the model; a number from `checker_decisions` tells you
about the deployment, and the measured 14.9% pose-pass flip rate is why those are different
questions.

Live output, joining the 8 Stage A uploads to the imported corpus labels by content hash:

```
target 'posture'  scored against label target 'posture_fault'
labelled videos 1382   disputed 323

posture_v1   [FITTED / authoritative]   matched 8 labelled videos
  coverage            0.875  (7/8 answered)
  covered-only        P 0.5000  R 1.0000  F1 0.6667
  abstain-as-negative P 0.5000  R 1.0000  F1 0.6667
  trivial floor       F1 0.2222   prevalence 0.125

depth_parallel_v0   [UNFITTED / advisory]   matched 8 labelled videos
  coverage            0.625  (5/8 answered)
  -> UNFITTED: descriptive only. Not a performance claim.
```

**n=8 — these numbers mean nothing about model quality and are not quoted as if they did.** What
they demonstrate is that the join works and that the reporting rules hold: coverage in both
views, the trivial floor, and the `UNFITTED` banner are printed always, not optionally.

## What the loop caught on its first run

**105 of 1,487 corpus videos are byte-identical duplicates** under different names — 45 spanning
splits, 80 with conflicting labels. Found because the label table's unique key **refused an
insert**. Full write-up: `2026-09-23-corpus-duplicates.md`, filed as G-44.

The headline consequence is that **47 pairs of byte-identical frames carry both `depth_fault`
and `good_form`**, which gives the Phase 2 depth negative a measured cause rather than a
speculative one: no function of the pixels separates classes when the same pixels sit in both.

## The theme, stated once

Three gaps filed this month are the same shape, and it is worth naming:

| | the safety net | why it was not connected |
|---|---|---|
| **G-38** | `alembic check` — the one command that catches a model change that never reached the database | permanently red at **92 pre-existing drift operations**, so nobody can use it as a gate. It is also why `error_details` and `summary` survived as phantom columns: the tool that would have flagged them was already screaming about 90 other things. |
| **G-43** | `pytest-timeout` in `requirements.txt` — G-32, marked **FIXED** | the `app` and `worker` images were never rebuilt, so `pytest` inside them still aborts before collection. A dependency fix that lives in a requirements file and not in the deployed artifact is not a fix. Found by accident, because adding the `beat` service forced a fresh build. |
| **G-44** | the user-level leakage check | correct as stated and insufficient: it keys on user id, and 104 identical files are filed under different user ids. |

Each one is a mechanism that exists, is believed to be working, and is not connected to anything.
That is the same failure as the **lost 24 decision rows** in Stage A — every form check
COMPLETED, every run opened and closed, health check green, audit trail empty — and the same as
the four earlier silent-loss findings (tracker leak, complexity fallback, both-sides visibility
gate, pose-pass flips).

**The generalisable lesson, now stated six times over: assert on rows written, never on the
absence of errors.** Every one of these passed a green check while losing data.

## Reproduce

```bash
pytest -q backend/tests/unit/test_metrics_parity.py backend/tests/unit/test_label_store.py

docker run --rm --network deployment_default -v $PWD/backend:/app \
  -v "$HOME/FORMIQ Form Analysis Model/data/squat_processed:/splits:ro" \
  -v "$HOME/Desktop/Squat More/Labeled_Dataset/videos:/videos:ro" \
  -e POSTGRES_SERVER=db -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=formiq -e SECRET_KEY=dev-only-insecure-secret-key-32chars-minimum \
  -e REDIS_HOST=redis -e REDIS_PORT=6379 -w /app deployment-beat:latest \
  python scripts/import_labels.py --splits /splits/user_level_multilabel_splits.json \
    --video-root /videos --dry-run

# then, same container args:
#   python scripts/eval_runner.py --target posture
#   python /repo/bench/corpus_duplicates.py
```

**Full suite, in the freshly built image: 1,305 passed, 2 failed** — the two pre-existing G-35
failures, against the Phase 1 baseline of 1,170/2.
