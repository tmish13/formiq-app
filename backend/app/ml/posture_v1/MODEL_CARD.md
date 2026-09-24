# Model card — PostureV1

**What it is.** A binary classifier for one squat fault, *knees travelling forward / posture fault*,
from a side-view video: MediaPipe Pose (complexity 2) keypoints of the first 300 frames plus 151
per-video features → a CNN-LSTM (`app/ml/posture_v1/model.py`) → a probability, thresholded at 0.525.
Trained 2026-02-11 outside this repository; provenance, recipe and hashes in
`backend/ml_training/posture_v1/provenance/PROVENANCE.md` and in the manifest's `provenance` block.

**Status: experimental. It does not meet the acceptance bar (`docs/ml/ACCEPTANCE_BAR.md`).** The app
shows its score labelled "experimental", ships the knees-forward *localisation* ("your knees went
forward at 1.4 s") and `any_fault` as the only binary, and makes no accuracy claim
(`bench/results/2026-09-24-acceptance-bar-verdict.md`).

## Intended use and non-use

- For: a single squat rep, side view, one person, a phone held still; the output is a hint about
  knee travel, shown with where in the rep it happened.
- Not for: front views (the localisation abstains; the model has no signal), other exercises
  (`classify_exercise_from_keypoints` is a stub; submit rejects non-squat names), depth or stability
  (those scores are NULL by design, G-40/G-42), coaching decisions or anything with consequences.

## Data and label

- Corpus: 1,487 labelled squat videos (after de-duplication, 105 byte-identical duplicates removed,
  G-44), including 124 Penn Action clips that are all `good_form` (a domain shortcut the face-block
  features can learn, G-26/G-30). Splits for evaluation are content-level (by video content hash,
  dedup map applied first, `bench/results/content_level_splits.json`).
- Label: `posture_fault` collapsed from a 3-class frame-level labelling; a degree judgement on a
  near-universal behaviour (the knees-forward predicate alone separates videos at AUROC 0.57,
  `ML_AUDIT.md` §10). A graded 0–3 severity relabelling pilot is the open experiment
  (`bench/relabel/PREREGISTRATION.md`).

## Measured performance (every number from `app/eval/metrics.py`, bootstrap CI, one logged test read)

| set | metric | value |
|---|---|---|
| clean content-level test, live-judged, n = 188 (`2026-09-23-gate1b-full-corpus.md`) | AUROC | **0.7057 [0.6246, 0.7808]** |
| same | F1 at 0.525 vs all-positive floor | 0.6036 [0.5135, 0.6854] vs 0.5865 |
| content-level test, `posture_collapsed`, n = 196 (`acceptance_bar_verdict.json`) | AUROC | 0.7306 [0.6616, 0.7995] |
| same | precision / recall at 0.525 | 0.533 / 0.718 (bar: P ≥ 0.70 at R ≥ 0.60) |
| same | flip rate against a second pose pass (`pp1_0d1b…` vs `pp1_f985…`) | **15.3 %** (30/196) [10.7, 20.4] (bar: ≤ 10 %) |
| live abstention (n = 188) | coverage / F1 gap abstain-as-negative | 0.941 / 0.021 (passes) |

What the trainer reported and why it is not quoted as the number: test F0.5 0.735 on 162 videos, an
evaluation set that was partly in training (G-44: 18 of 173 test videos have a byte-identical twin
in train) — an upper bound, written into the manifest as such.

Two pre-registered attempts to move the number were negative: a controlled retrain (body-only
features, un-collapsed labels, serving pose pass, seeds; `2026-09-23-retrain-controlled.md`, best
AUROC 0.6802 [0.6067, 0.7526]) and threshold retuning (two cycle turns). Under the bar's stop rule
the next intervention is the label, not the trainer.

## Known failure modes

- 87 of the 151 features are raw face-landmark coordinates (G-26); the model can read the recording
  setup instead of the squat.
- A different MediaPipe pass flips 15 % of verdicts (G-39); every stored verdict carries its
  `pose_pass_id`, and a re-upload is only served from cache under the same pass (G-53).
- Videos with more than 10 % interior missing frames were rejected in training but not at serving
  (plan item C1 in the previous cycle; still open).
- Unseeded training: the shipped weights cannot be regenerated; a seeded trainer that reuses the
  serving code is the planned replacement (Track B5).

## Versioning

`model_version = posture_v1`, feature spec `truth_spec_151d_v1`, scaler statistics and artifact
sha256s in the manifest; `tests/unit/test_posture_v1_artifact_integrity.py` fails if any artifact
changes without the manifest.
