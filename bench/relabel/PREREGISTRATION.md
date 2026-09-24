# Relabelling pilot — pre-registration

Written before any clip was annotated (2026-09-24). Gates are fixed here; they are not moved after
the sheets come back.

## What is annotated
- **Test**: all 196 clips of the content-level test split that have serving-pass keypoints
  (`bench/results/retrain/test_clip_names.txt`).
- **Train**: 300 clips from the content-level train split, stratified by the current class
  (`good_form` / `posture_fault` / `depth_fault` in the corpus's proportions), seed 42.
- Two annotators, independent, blind (protocol: `docs/ml/LABELLING_PROTOCOL.md`).
- Sheets: `bench/results/relabel/annotation_sheet_{A,B}.csv`. Import: `backend/scripts/import_pilot_labels.py`
  → label store rows, `source = expert`, `source_ref = pilot:<annotator>`, trust 1.0, targets
  `posture_severity` (0–3) and `posture_fault_v2` (severity ≥ 2). A `usable = no` row writes the
  store's "unusable for every target" marker.

## Gate 1 — is the construct annotatable?
`bench/relabel/agreement.py`: quadratic-weighted Cohen's κ between A and B on severity, over clips
both marked usable; exact agreement and the 2×2 agreement on `severity ≥ 2` alongside.
**Pass: κ ≥ 0.60.** Below that, the degree judgement is not reproducible either, the pilot stops,
and the product claim stays re-scoped (localisation + `any_fault`).

## Gate 2 — does the new label lift the ceiling? (no training)
`bench/relabel/gate.py`: on the test clips, the shipped PostureV1's stored probabilities
(`checker_decisions.prob`, no inference) scored against `posture_fault_v2` resolved from the expert
rows (clips where A and B disagree at the 1/2 boundary are `disputed` and excluded; n is reported).
Baseline on the same population: AUROC lower bound **0.6246** against the current label (n=188).
**Pass: AUROC 95 % CI lower bound ≥ 0.6746** (+0.05) — measured on the same clips, paired.
On a pass the full-corpus relabel is funded; on a fail the label was not the ceiling either, and the
honest product remains localisation.

## What is NOT decided by the pilot
Whether a retrain beats the incumbent. That is `docs/ml/ACCEPTANCE_BAR.md`, after a full relabel,
with its own pre-registration and one test read.

## Not done here
The train clips' annotations are for the future retrain's training set and for κ; they enter no
metric in this pilot.
