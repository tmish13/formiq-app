# ml_training

Training-side material for the models the API serves. Nothing here is imported by `app/`.

- `posture_v1/provenance/` — the notebook codebase PostureV1 was trained with, imported unchanged on
  2026-09-24, with `PROVENANCE.md` (hashes, recipe, environment, the discrepancies). Read-only history.
- `data/` — the two files that notebook reads: the user-level splits and the per-video labels
  (5.3 MB). Keypoints and videos stay outside the repository; their hashes are in `PROVENANCE.md`.

The trainer that can produce a servable artifact with seeds and a full provenance block is
`posture_v1/train.py` + `export.py` (plan Track B5); until it lands, `bench/retrain/` is the only
in-repo training code and it writes sklearn artifacts the serving loader cannot use.

Rules that apply to anything trained from here: content-level splits with the dedup map applied
first, metrics from `app/eval/metrics.py` with n / prevalence / floor / CI, and one logged read of
the test split per model (`bench/results/retrain/TEST_READ_LOG.jsonl`).
