# PostureV1 — provenance of the shipped model (G-20)

The model the API serves (`backend/app/ml/posture_v1/artifacts/`) was trained outside this repository,
in `~/FORMIQ Form Analysis Model/`, a directory under no version control. This folder is that codebase
imported **as it was on 2026-09-24**, unchanged, so that "show me how it was trained" has an answer
that is a file, not a memory. Nothing here is executed by the app or the tests.

## Files imported, with sha256 (first 16 hex) and size

| file | sha256 | bytes | role |
|---|---|---|---|
| `squat_pipeline_posture_stability_goodform_REBUILT.ipynb` | `b7ff1762cc70a601` | 357,290 | the trainer: 34 code cells, kernel Python 3.11.7, executed outputs from the run that produced the shipped checkpoint |
| `export_posture_v1.py` | `9f74a5e0434c546e` | 23,654 | the exporter: copies the checkpoint, refits the scaler on the training split, writes the manifest |
| `cnn_lstm_binary_enhanced_cw_results.json` | `00d287e607baa9ed` | 1,428 | the training run's results (source of the manifest's `training_metrics`) |
| `06_multilabel_CNN_LSTM_refactored.ipynb` | `557896ffcbf48af1` | 97,213 | upstream: produces `user_level_multilabel_splits.json` |
| `05_advanced_performance_optimization_CNN_LSTM_integrated.ipynb` | `75838878e5a73d61` | 191,367 | upstream: produces `balanced_3class_frame_labels.json` |
| `ML_REPO_TRUTH_EXTRACTION.md` | `035d8d4e97681cc0` | 14,525 | the wiring notes the serving code was written from |
| `../../data/user_level_multilabel_splits.json` | `6146992133682d1c` | 1,962,429 | the splits the trainer and exporter read |
| `../../data/balanced_3class_frame_labels.json` | `9f5da0a643a63af8` | 3,566,069 | the per-video labels and keypoint paths they read |

Not imported: the keypoint files and the 1,724 videos (`data/squat_processed/*.json` of 600 MB each,
`~/Desktop/Squat More/Labeled_Dataset/videos/`), and the checkpoint `runs/best_cnn_lstm_binary_enhanced_cw_f0.5_0.736.pt`
(`b7375ca49a932799`, 3,169,130 bytes) — it is byte-identical to the shipped `posture_v1.pt`.

## The shipped artifacts (sha256 first 16)

| file | sha256 |
|---|---|
| `posture_v1.pt` | `b7375ca49a932799` (= the checkpoint above) |
| `posture_v1_scaler.joblib` | `776e986f506f8372` |
| `posture_v1_manifest.json` | `7563b3ad34106916` (before the provenance block was added) |
| `posture_v1_splits.json` | `ee28d014824623b5` |

`tests/unit/test_posture_v1_artifact_integrity.py` recomputes the `.pt`, scaler and splits hashes
against the manifest's `provenance` block on every run.

## The recipe, as the notebook has it (cell numbers are code-cell indices)

- Data: `user_level_multilabel_splits.json` (split by user id, 809 / 244 / 244 before filtering) and
  `balanced_3class_frame_labels.json`; the binary task collapses the three labels to
  `good_form` vs `posture_fault` (cell 1). Input per video: 300 frames × 33 MediaPipe joints × (x, y, z),
  first-300-truncate / zero-pad, plus 151 per-video features (`extract_rep_features_87d` + temporal
  block); `StandardScaler` fitted on the training split only (cells 6, 9).
- Model (cell 23): Conv1d channels [32, 64], kernel 5, `Dropout1d(0.4)` → LSTM hidden 96 → fusion
  `[LSTM 96 + 151 features]` → MLP [256, 128], dropout 0.4 → 2 logits. Same architecture as
  `backend/app/ml/posture_v1/model.py` (`PostureV1Model`), which is how the checkpoint loads.
- Training (cell 24): `Adam(lr=0.001, weight_decay=5e-4)`, `ReduceLROnPlateau(mode='max', factor=0.5,
  patience=7)`, `clip_grad_norm_(max_norm=1.0)`, `BATCH_SIZE = 4`, `max_epochs = 100`, early stopping
  patience 15 on validation F0.5, `BCEWithLogitsLoss` with class weights (`USE_CLASS_WEIGHTS = True`).
  Best-state bookkeeping: `best_model_state = model.state_dict().copy()` — a shallow copy, so the
  in-memory "best" state tracks the live weights (ML_AUDIT.md §"shallow copy"); the checkpoint file
  was written with `torch.save` at the improving epoch and is not affected.
- Threshold: sweep `np.linspace(0.2, 0.8, 25)` on validation F0.5 → 0.525. The results file records
  `validation_f0_5_gain: -0.0187` for that choice.
- **No seed anywhere.** The notebook and `ML_AUDIT.md` §6.2 record 20+ runs spanning validation F0.5
  0.589–0.742; a rerun does not reproduce the shipped weights.

## What the results file says (`cnn_lstm_binary_enhanced_cw_results.json`, 2026-02-11 11:24)

21 epochs, best validation F0.5 0.7363; on the 162 labelled test videos at threshold 0.525:
precision 0.7432, recall 0.7051, F1 0.7237, F0.5 0.7353. These are the numbers in the manifest's
`training_metrics`. Two caveats apply and are written into the manifest too: the evaluation set
was partly in training (G-44, 18 of 173 test videos have a byte-identical twin in train), and the
clean, de-duplicated held-out number is AUROC 0.7057 [0.6246, 0.7808] on n = 188
(`bench/results/2026-09-23-gate1b-full-corpus.md`).

## Discrepancies nobody had written down

1. `ML_REPO_TRUTH_EXTRACTION.md` line 3 names `..._f0.5_0.742.pt` as the best checkpoint; the exporter
   and the manifest ship `..._0.736.pt`. Why 0.736 was chosen over 0.742 is recorded nowhere.
2. The manifest's test metrics and the 0.525 threshold were computed in the notebook on the model's
   final in-memory weights, not on the saved checkpoint; on the shipped weights the validation F0.5
   peak sits at threshold 0.475 (ML_AUDIT.md §7.2). Serving uses 0.525 because the manifest says so.
3. The exporter ran in the ML directory's venv — Python 3.12.1, scikit-learn 1.6.1, numpy 1.26.4,
   torch 2.7.1 — while serving pins scikit-learn 1.4.0 and torch 2.2.0 (`backend/requirements.txt`).
   The two scaler copies differ by exactly the embedded `_sklearn_version` tag; the fitted statistics
   are identical (G-22, `tests/unit/test_train_serve_parity.py`). The notebook's own kernel was 3.11.7.
4. The shipped manifest is the 2026-02-12 export; the ML directory holds a 2026-02-14 re-export.
   Same checkpoint, same numbers.

## What this import does not do

It does not make the model reproducible: no seed, no library pins, no keypoint extraction code for
the training inputs (the keypoints were produced by an earlier pipeline; see `ML_AUDIT.md` §6). A
seeded trainer that reuses the serving code lives next to this folder (`../train.py`, when present)
and is validated on train/validation only — the test split is read once per model, behind `--final`.
