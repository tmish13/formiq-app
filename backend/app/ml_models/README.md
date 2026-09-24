# app/ml_models — what is (not) here

**`_deprecated_demo_squat/`** is an 18-sample RandomForest demo from June 2025
(`production_metadata.json` inside it says `"model_type": "RandomForest_demo", "samples_used": 18,
"training_accuracy": 1.0`). It was never validated on held-out data, and while it sat under the
name `squat/` the legacy temporal path in `services/ai_service.py` loaded it for every squat and
wrote its output into `results.temporal_ml` — a number no evaluation ever looked at (G-06). Moving
the directory makes `EnhancedSquatModelLoader.is_model_available()` return False, which is the
loader's own graceful path: the branch is skipped and nothing is written.

**Production is `app/ml/posture_v1/`** (PostureV1, the CNN-LSTM; manifest, scaler, and threshold
under `artifacts/`). Its honest numbers are in `docs/ml/ACCEPTANCE_BAR.md` and
`bench/results/2026-09-23-gate1b-full-corpus.md`.

Delete `_deprecated_demo_squat/` whenever nobody needs the artefact for the record; nothing imports it.
