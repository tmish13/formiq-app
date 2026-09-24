# Controlled retrain — body-only, multi-label, serving pass, one logged test read

**Date:** 2026-09-23 · **Branch:** `ml/retrain-body-only-multilabel` · **Status:** IN PROGRESS (this header is replaced by the verdict when the single test read has happened)

## 0. Why, and what was fixed before anything ran

ML_AUDIT §11b: *"retrain, but only as a controlled experiment after re-scoping, with a
negative-result contract."* Gate 1b made the instrument adequate (content-level test n=188,
`2026-09-23-gate1b-full-corpus.md`). Everything about this experiment was fixed before the
first full training run and before any test read — see `bench/retrain/PREREGISTRATION.md`
(committed at `2e96d3f`, three dated amendments, all pre-read):

| fixed in advance | value |
|---|---|
| splits | `bench/results/content_level_splits.json` (`minimal`), dedup map first, 161 conflicted + 138 no-file withheld, Penn absent |
| pose pass | serving pass `pp1_f9850424580ae186` for train, validation and test; recorded in the dataset manifest and every artifact |
| targets | `posture_fault`, `stability_fault`, `depth_fault` from `original_multi_label` (no collapse, no undersampling), `any_fault` derived, `posture_collapsed` = the corpus's single-class label (the incumbent's own task; equals the label store's winning `posture_fault` value on 619/619 checked videos) |
| arms | A: v2 body-only 201-D (`spec_hash f06e2b7a…`); B: incumbent 64-D temporal block; C: incumbent full 151-D incl. the 87-D face block |
| learners | logistic regression, histogram gradient boosting (both deterministic), MLP (seed-sensitive; early-stops on 15 % of TRAIN); 5 seeds; artifact = seed with the median validation AUROC; threshold = validation F1 optimum on a 0.05..0.95 grid |
| metrics | `app/eval/metrics.py` only; bootstrap n=2000 seed 0; floor and majority-class accuracy always |
| primary | AUROC on `posture_fault`; the (arm, learner) with the highest median validation AUROC is the primary artifact — chosen by rule, before the read |
| co-primary | AUROC on `posture_collapsed`, same videos, same stored probabilities, reported with its own verdict |
| incumbent | shipped PostureV1 weights, scored through the serving loader on the SAME cached test keypoints; F1 rows at three validation-derived thresholds (0.525 shipped, 0.475 notebook-validation optimum, and this experiment's validation optimum) |
| verdict | NEGATIVE if retrain AUROC ≤ incumbent CI lower bound **or** ≤ incumbent point estimate; POSITIVE if above both and the paired ΔAUROC CI excludes zero; otherwise "POSITIVE per contract, NOT DISTINGUISHABLE" |
| expected (stated in advance) | modest gain on `any_fault` and posture-with-co-occurrence; **no** gain on `depth_fault` |

## 1. Commands

```bash
# all inside deployment-beat:latest, OMP_NUM_THREADS=1 (bench/retrain/run.sh)
bash bench/retrain/run.sh extract    # serving-pass keypoints for every corpus video not cached (768)
bash bench/retrain/run.sh build      # 3 arms x 3 splits -> bench/cache/retrain/data; manifest -> bench/results/retrain/
bash bench/retrain/run.sh valcheck   # incumbent on VALIDATION only (exercises the paired path; no test)
bash bench/retrain/run.sh train      # 3 arms x 3 learners x 5 seeds x 5 heads; selection on validation only
bash bench/retrain/run.sh final      # ONE logged test read per (arm, learner); TEST_READ_LOG.jsonl
```

**Environment.** Docker Desktop VM 8 vCPU / 7.65 GiB; image `deployment-beat:latest`
(python 3.11.16, sklearn 1.4.0, torch 2.2.0, numpy 1.26.3); `-m 3g`, single-threaded BLAS. Extraction ran with 4
MediaPipe workers while the pipeline was idle.
