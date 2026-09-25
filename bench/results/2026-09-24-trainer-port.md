# Trainer port (Track B5): a seeded PostureV1 trainer that reuses the serving code — 2026-09-24

**Not a model candidate.** Nothing here reads the test split; under the acceptance bar's stop rule a
model trained on the current labels would be the second failed intervention. This note records that
the port trains, exports, and round-trips through the serving loader, and what five seeds do on
train/validation with the current labels — the spread the notebook never reported.

## What was built (`ml/trainer-port`, `backend/ml_training/posture_v1/`)

- `dataset.py`: arrays from the **serving pose pass** (`bench/cache/keypoints_live`, `pp1_f9850424580ae186`)
  and the content-level splits (dedup map applied first): `preprocess_pose_data` → K [N,300,33,3],
  `compute_151d_features` (unscaled) → X [N,151], label `posture_collapsed` (the incumbent's own task).
- `train.py`: the notebook's recipe (Adam 1e-3 / wd 5e-4, ReduceLROnPlateau max 0.5 p7, clip 1.0,
  batch 4, ≤ 100 epochs, early stop p15 on val F0.5, class-weighted BCE total/(2·count), validation
  F0.5 sweep over linspace(0.2, 0.8, 25)) with two corrections: every run seeded, the best state a
  **deep** copy. Median-validation-AUROC seed is the artifact. `--final` reads test once per artifact
  and appends to `TEST_READ_LOG.jsonl`; a second read is refused.
- `export.py`: `posture_v1.pt` + scaler + manifest with a full `provenance` block (artifact sha256s,
  data hashes, pose pass, seed, recipe, class weights, code git sha, library versions); refuses the
  live artifacts directory without `--install`.
- `tests/unit/test_trainer_port.py` (6, worker image): **architecture parity** — the trainer's model
  has exactly the shipped checkpoint's state-dict keys and shapes, built from the manifest's
  `model_config`; deep copy; class weights; synthetic smoke train → export → `PostureV1TorchLoader`
  round trip; live-directory refusal; second-read refusal.

## Dataset (command in `backend/ml_training/posture_v1/README.md`)

```
target posture_collapsed   pose_pass_id pp1_f9850424580ae186   skipped {}
n           train 912   validation 218   test 196
prevalence  train 0.418 validation 0.376 test 0.398
```

## Smoke on the real arrays (proves the plumbing, says nothing about accuracy)

`--seeds 0 --subset 40 --max-epochs 2` → export (`posture_v1_smoke`) → the serving loader pointed at
the exported directory scored **20 of 20 parity clips** (`bench/results/parity_20_selection.json`)
from their cached frames; threshold and `model_version` propagated from the exported manifest.
(The 2-epoch/40-clip model is meaningless by construction: val AUROC 0.33 on 20 clips.)

## Five seeds on train/validation, current labels — STOPPED at the owner's request

Started 15:38 PDT at ≈ 2 min per epoch (battery, Low Power Mode, the test suite running alongside).
Stopped at 16:13 PDT during seed 0, epoch 27 (train loss 0.574, validation F0.5 at 0.5 = 0.622 and
still rising; epoch 1 was 0.488). No seed completed, so no `seedN.json`, no artifact and no number
is reported. Re-run with the command in `backend/ml_training/posture_v1/README.md` when the machine
is free; nothing about it reads the test split.

## What this does and does not establish

- Establishes: the recipe is code, seeded, tested, and produces an artifact serving loads; the next
  retrain (after the relabelling pilot's gates) is one command and one read.
- Does not establish: any accuracy claim. The shipped weights remain irreproducible (unseeded
  training; `PROVENANCE.md`), and no number here has touched the test split.
