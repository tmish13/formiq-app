# Controlled retrain — body-only, multi-label, serving pass, one logged test read

**Date:** 2026-09-23 · **Branch:** `ml/retrain-body-only-multilabel` · **Status:** **NEGATIVE.** The pre-registered primary artifact scores AUROC 0.6802 [0.6067, 0.7526] on the clean content-level test (n=196) against the shipped PostureV1's 0.7306 [0.6616, 0.7995]; paired ΔAUROC −0.0504 [−0.1150, +0.0112]. Eight of nine artifacts sit below the incumbent's point estimate, two of them significantly; the ninth is not distinguishable from it. Test was read once per artifact (`bench/results/retrain/TEST_READ_LOG.jsonl`, nine reads, none forced).

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

## 2. Dataset

`dataset_manifest.json`: pose pass `pp1_f9850424580ae186`, spec_hash_A `f06e2b7a…`, **no clip skipped**.

| split | n | posture_fault | stability_fault | depth_fault | any_fault | posture_collapsed |
|---|---|---|---|---|---|---|
| train | 912 | 0.643 | 0.127 | 0.317 | 0.735 | 0.418 |
| validation | 218 | 0.615 | 0.147 | 0.312 | 0.688 | 0.376 |
| test | 196 | 0.612 | 0.102 | 0.311 | 0.709 | 0.398 |

## 3. Validation, and the selection on record before the read

Nine training reports (`bench/results/retrain/*__train_report.json`), median validation AUROC
over five seeds, `[min, max]` across seeds. Logistic regression and HGB are deterministic
(identical across seeds, as expected — no subsampling, no early stopping); the MLP's spread is
up to 0.09 AUROC on the same data, which is ML_AUDIT cause 3 (run-to-run variance) reproduced
under control.

```
arm              learner   posture_faul  stability_fa   depth_fault     any_fault  posture_coll   (median val AUROC over seeds; [min, max])
A_v2_body        hgb      0.7683[0.77,0.77] 0.7608[0.76,0.76] 0.5973[0.60,0.60] 0.7190[0.72,0.72] 0.7319[0.73,0.73]
A_v2_body        logreg   0.7293[0.73,0.73] 0.7715[0.77,0.77] 0.6081[0.61,0.61] 0.7083[0.71,0.71] 0.7239[0.72,0.72]
A_v2_body        mlp      0.7203[0.69,0.74] 0.6104[0.58,0.68] 0.5818[0.50,0.60] 0.6582[0.58,0.71] 0.7241[0.68,0.73]
B_temporal64     hgb      0.7828[0.78,0.78] 0.7791[0.78,0.78] 0.6329[0.63,0.63] 0.7182[0.72,0.72] 0.7827[0.78,0.78]
B_temporal64     logreg   0.7388[0.74,0.74] 0.7206[0.72,0.72] 0.5701[0.57,0.57] 0.7010[0.70,0.70] 0.7218[0.72,0.72]
B_temporal64     mlp      0.7162[0.70,0.74] 0.6048[0.51,0.68] 0.5428[0.52,0.56] 0.6412[0.58,0.68] 0.7282[0.70,0.75]
C_incumbent151   hgb      0.7717[0.77,0.77] 0.7933[0.79,0.79] 0.6115[0.61,0.61] 0.7201[0.72,0.72] 0.7643[0.76,0.76]
C_incumbent151   logreg   0.7200[0.72,0.72] 0.7216[0.72,0.72] 0.6020[0.60,0.60] 0.6996[0.70,0.70] 0.7317[0.73,0.73]
C_incumbent151   mlp      0.7083[0.65,0.74] 0.5526[0.47,0.63] 0.5509[0.45,0.57] 0.6389[0.57,0.68] 0.7133[0.66,0.76]

PRIMARY    for posture_fault: B_temporal64 / hgb  (median val AUROC 0.7828)

CO_PRIMARY for posture_collapsed: B_temporal64 / hgb  (median val AUROC 0.7827)
wrote bench/results/retrain/primary_selection.json
```

`primary_selection.json` was committed at `56cca6c` **before** any test read. The incumbent on
the same validation split (`incumbent_validation_check.json`): AUROC 0.7488 on `posture_fault`,
0.7638 on `posture_collapsed` — below the primary artifact's 0.7828 / 0.7827. On validation the
retrain looked like a win of +0.03.

## 4. The test read — once per artifact, all nine logged

`bench/retrain/run.sh final`; `TEST_READ_LOG.jsonl` has nine entries, `forced: false`, n=196
each, 04:37–04:42 UTC. Raw output:

```
=== FINAL A_v2_body logreg ===
TEST READ #1  A_v2_body__logreg  n=196
  posture_fault    AUROC 0.6945  F1 0.7535 [0.6963, 0.8069] @0.17  P 0.6524 R 0.8917  floor 0.7595  maj-acc 0.6122  acc 0.6429
  incumbent shipped_0.525    AUROC 0.7306  F1 0.7111 [0.6411, 0.7753] @0.525  P 0.7619 R 0.6667   paired ΔF1 +0.0424 [-0.0250, +0.1097]
  incumbent notebook_val_opt_0.475 AUROC 0.7306  F1 0.7311 [0.6667, 0.7918] @0.475  P 0.7373 R 0.7250   paired ΔF1 +0.0224 [-0.0381, +0.0834]
  incumbent content_val_opt_0.27 AUROC 0.7306  F1 0.7465 [0.6866, 0.8000] @0.27  P 0.6463 R 0.8833   paired ΔF1 +0.0070 [-0.0326, +0.0464]
  incumbent AUROC 0.7306 [0.6616, 0.7995]   paired ΔAUROC -0.0361 [-0.1097, +0.0388]
  -> NEGATIVE: retrain AUROC 0.6945 is not above the incumbent's point estimate 0.7306 (paired delta -0.0361 [-0.1097, +0.0388])
     secondary F1 criterion: retrain 0.7535 vs strongest incumbent lower bound 0.6866 -> passes
  stability_fault  AUROC 0.7420  F1 0.3111 [0.1333, 0.4783] @0.78  P 0.2800 R 0.3500  floor 0.1852  maj-acc 0.8980  acc 0.8418
  depth_fault      AUROC 0.5899  F1 0.4953 [0.4082, 0.5740] @0.23  P 0.3464 R 0.8689  floor 0.4747  maj-acc 0.6888  acc 0.4490
  any_fault        AUROC 0.6458  F1 0.8217 [0.7738, 0.8635] @0.19  P 0.7371 R 0.9281  floor 0.8299  maj-acc 0.7092  acc 0.7143
  posture_collapsed AUROC 0.7203  F1 0.6292 [0.5422, 0.7059] @0.47  P 0.5600 R 0.7179  floor 0.5693  maj-acc 0.6020  acc 0.6633
  incumbent shipped_0.525    AUROC 0.7159  F1 0.6120 [0.5301, 0.6911] @0.525  P 0.5333 R 0.7179   paired ΔF1 +0.0172 [-0.0647, +0.0945]
  incumbent notebook_val_opt_0.475 AUROC 0.7159  F1 0.6224 [0.5424, 0.6984] @0.475  P 0.5169 R 0.7821   paired ΔF1 +0.0068 [-0.0690, +0.0825]
  incumbent content_val_opt_0.69 AUROC 0.7159  F1 0.5612 [0.4545, 0.6490] @0.69  P 0.6393 R 0.5000   paired ΔF1 +0.0681 [-0.0301, +0.1702]
  incumbent AUROC 0.7159 [0.6388, 0.7893]   paired ΔAUROC +0.0045 [-0.0728, +0.0791]
  -> POSITIVE per contract, NOT DISTINGUISHABLE: retrain AUROC 0.7203 exceeds the incumbent's lower bound 0.6388 and point estimate 0.7159, but the paired delta +0.0045 [-0.0728, +0.0791] includes zero
     secondary F1 criterion: retrain 0.6292 vs strongest incumbent lower bound 0.5424 -> passes
logged -> /repo/bench/results/retrain/TEST_READ_LOG.jsonl
=== FINAL A_v2_body hgb ===
TEST READ #1  A_v2_body__hgb  n=196
  posture_fault    AUROC 0.7443  F1 0.7790 [0.7190, 0.8278] @0.34  P 0.7075 R 0.8667  floor 0.7595  maj-acc 0.6122  acc 0.6990
  incumbent shipped_0.525    AUROC 0.7306  F1 0.7111 [0.6411, 0.7753] @0.525  P 0.7619 R 0.6667   paired ΔF1 +0.0679 [+0.0068, +0.1311]
  incumbent notebook_val_opt_0.475 AUROC 0.7306  F1 0.7311 [0.6667, 0.7918] @0.475  P 0.7373 R 0.7250   paired ΔF1 +0.0479 [-0.0076, +0.1051]
  incumbent content_val_opt_0.27 AUROC 0.7306  F1 0.7465 [0.6866, 0.8000] @0.27  P 0.6463 R 0.8833   paired ΔF1 +0.0325 [-0.0141, +0.0828]
  incumbent AUROC 0.7306 [0.6616, 0.7995]   paired ΔAUROC +0.0137 [-0.0536, +0.0795]
  -> POSITIVE per contract, NOT DISTINGUISHABLE: retrain AUROC 0.7443 exceeds the incumbent's lower bound 0.6616 and point estimate 0.7306, but the paired delta +0.0137 [-0.0536, +0.0795] includes zero
     secondary F1 criterion: retrain 0.7790 vs strongest incumbent lower bound 0.6866 -> passes
  stability_fault  AUROC 0.6651  F1 0.2000 [0.0476, 0.3529] @0.44  P 0.1667 R 0.2500  floor 0.1852  maj-acc 0.8980  acc 0.7959
  depth_fault      AUROC 0.6463  F1 0.4821 [0.3963, 0.5587] @0.16  P 0.3313 R 0.8852  floor 0.4747  maj-acc 0.6888  acc 0.4082
  any_fault        AUROC 0.6814  F1 0.8339 [0.7867, 0.8738] @0.38  P 0.7619 R 0.9209  floor 0.8299  maj-acc 0.7092  acc 0.7398
  posture_collapsed AUROC 0.7389  F1 0.6729 [0.6000, 0.7429] @0.27  P 0.5294 R 0.9231  floor 0.5693  maj-acc 0.6020  acc 0.6429
  incumbent shipped_0.525    AUROC 0.7159  F1 0.6120 [0.5301, 0.6911] @0.525  P 0.5333 R 0.7179   paired ΔF1 +0.0609 [-0.0076, +0.1275]
  incumbent notebook_val_opt_0.475 AUROC 0.7159  F1 0.6224 [0.5424, 0.6984] @0.475  P 0.5169 R 0.7821   paired ΔF1 +0.0504 [-0.0087, +0.1128]
  incumbent content_val_opt_0.69 AUROC 0.7159  F1 0.5612 [0.4545, 0.6490] @0.69  P 0.6393 R 0.5000   paired ΔF1 +0.1117 [+0.0196, +0.2166]
  incumbent AUROC 0.7159 [0.6388, 0.7893]   paired ΔAUROC +0.0230 [-0.0558, +0.1026]
  -> POSITIVE per contract, NOT DISTINGUISHABLE: retrain AUROC 0.7389 exceeds the incumbent's lower bound 0.6388 and point estimate 0.7159, but the paired delta +0.0230 [-0.0558, +0.1026] includes zero
     secondary F1 criterion: retrain 0.6729 vs strongest incumbent lower bound 0.5424 -> passes
logged -> /repo/bench/results/retrain/TEST_READ_LOG.jsonl
=== FINAL A_v2_body mlp ===
TEST READ #1  A_v2_body__mlp  n=196
  posture_fault    AUROC 0.6883  F1 0.7713 [0.7153, 0.8220] @0.24  P 0.6532 R 0.9417  floor 0.7595  maj-acc 0.6122  acc 0.6582
  incumbent shipped_0.525    AUROC 0.7306  F1 0.7111 [0.6411, 0.7753] @0.525  P 0.7619 R 0.6667   paired ΔF1 +0.0602 [-0.0074, +0.1295]
  incumbent notebook_val_opt_0.475 AUROC 0.7306  F1 0.7311 [0.6667, 0.7918] @0.475  P 0.7373 R 0.7250   paired ΔF1 +0.0402 [-0.0187, +0.1024]
  incumbent content_val_opt_0.27 AUROC 0.7306  F1 0.7465 [0.6866, 0.8000] @0.27  P 0.6463 R 0.8833   paired ΔF1 +0.0249 [-0.0110, +0.0599]
  incumbent AUROC 0.7306 [0.6616, 0.7995]   paired ΔAUROC -0.0423 [-0.1145, +0.0282]
  -> NEGATIVE: retrain AUROC 0.6883 is not above the incumbent's point estimate 0.7306 (paired delta -0.0423 [-0.1145, +0.0282])
     secondary F1 criterion: retrain 0.7713 vs strongest incumbent lower bound 0.6866 -> passes
  stability_fault  AUROC 0.5753  F1 0.1455 [0.0364, 0.2712] @0.22  P 0.1143 R 0.2000  floor 0.1852  maj-acc 0.8980  acc 0.7602
  depth_fault      AUROC 0.5876  F1 0.4296 [0.3248, 0.5270] @0.34  P 0.3919 R 0.4754  floor 0.4747  maj-acc 0.6888  acc 0.6071
  any_fault        AUROC 0.6484  F1 0.8328 [0.7848, 0.8721] @0.23  P 0.7211 R 0.9856  floor 0.8299  maj-acc 0.7092  acc 0.7194
  posture_collapsed AUROC 0.6931  F1 0.6051 [0.5196, 0.6796] @0.31  P 0.5043 R 0.7564  floor 0.5693  maj-acc 0.6020  acc 0.6071
  incumbent shipped_0.525    AUROC 0.7159  F1 0.6120 [0.5301, 0.6911] @0.525  P 0.5333 R 0.7179   paired ΔF1 -0.0069 [-0.0795, +0.0655]
  incumbent notebook_val_opt_0.475 AUROC 0.7159  F1 0.6224 [0.5424, 0.6984] @0.475  P 0.5169 R 0.7821   paired ΔF1 -0.0173 [-0.0820, +0.0445]
  incumbent content_val_opt_0.69 AUROC 0.7159  F1 0.5612 [0.4545, 0.6490] @0.69  P 0.6393 R 0.5000   paired ΔF1 +0.0440 [-0.0516, +0.1472]
  incumbent AUROC 0.7159 [0.6388, 0.7893]   paired ΔAUROC -0.0228 [-0.0932, +0.0461]
  -> NEGATIVE: retrain AUROC 0.6931 is not above the incumbent's point estimate 0.7159 (paired delta -0.0228 [-0.0932, +0.0461])
     secondary F1 criterion: retrain 0.6051 vs strongest incumbent lower bound 0.5424 -> passes
logged -> /repo/bench/results/retrain/TEST_READ_LOG.jsonl
=== FINAL B_temporal64 logreg ===
TEST READ #1  B_temporal64__logreg  n=196
  posture_fault    AUROC 0.6772  F1 0.7273 [0.6667, 0.7841] @0.31  P 0.6452 R 0.8333  floor 0.7595  maj-acc 0.6122  acc 0.6173
  incumbent shipped_0.525    AUROC 0.7306  F1 0.7111 [0.6411, 0.7753] @0.525  P 0.7619 R 0.6667   paired ΔF1 +0.0162 [-0.0431, +0.0781]
  incumbent notebook_val_opt_0.475 AUROC 0.7306  F1 0.7311 [0.6667, 0.7918] @0.475  P 0.7373 R 0.7250   paired ΔF1 -0.0038 [-0.0596, +0.0536]
  incumbent content_val_opt_0.27 AUROC 0.7306  F1 0.7465 [0.6866, 0.8000] @0.27  P 0.6463 R 0.8833   paired ΔF1 -0.0192 [-0.0620, +0.0236]
  incumbent AUROC 0.7306 [0.6616, 0.7995]   paired ΔAUROC -0.0534 [-0.1150, +0.0096]
  -> NEGATIVE: retrain AUROC 0.6772 is not above the incumbent's point estimate 0.7306 (paired delta -0.0534 [-0.1150, +0.0096])
     secondary F1 criterion: retrain 0.7273 vs strongest incumbent lower bound 0.6866 -> passes
  stability_fault  AUROC 0.7236  F1 0.2333 [0.0930, 0.3750] @0.62  P 0.1750 R 0.3500  floor 0.1852  maj-acc 0.8980  acc 0.7653
  depth_fault      AUROC 0.6192  F1 0.5079 [0.4142, 0.5876] @0.4  P 0.3750 R 0.7869  floor 0.4747  maj-acc 0.6888  acc 0.5255
  any_fault        AUROC 0.6384  F1 0.8012 [0.7492, 0.8452] @0.23  P 0.7049 R 0.9281  floor 0.8299  maj-acc 0.7092  acc 0.6735
  posture_collapsed AUROC 0.6889  F1 0.5698 [0.4744, 0.6498] @0.52  P 0.5213 R 0.6282  floor 0.5693  maj-acc 0.6020  acc 0.6224
  incumbent shipped_0.525    AUROC 0.7159  F1 0.6120 [0.5301, 0.6911] @0.525  P 0.5333 R 0.7179   paired ΔF1 -0.0423 [-0.1154, +0.0277]
  incumbent notebook_val_opt_0.475 AUROC 0.7159  F1 0.6224 [0.5424, 0.6984] @0.475  P 0.5169 R 0.7821   paired ΔF1 -0.0527 [-0.1302, +0.0206]
  incumbent content_val_opt_0.69 AUROC 0.7159  F1 0.5612 [0.4545, 0.6490] @0.69  P 0.6393 R 0.5000   paired ΔF1 +0.0086 [-0.0790, +0.0986]
  incumbent AUROC 0.7159 [0.6388, 0.7893]   paired ΔAUROC -0.0269 [-0.0890, +0.0356]
  -> NEGATIVE: retrain AUROC 0.6889 is not above the incumbent's point estimate 0.7159 (paired delta -0.0269 [-0.0890, +0.0356])
     secondary F1 criterion: retrain 0.5698 vs strongest incumbent lower bound 0.5424 -> passes
logged -> /repo/bench/results/retrain/TEST_READ_LOG.jsonl
=== FINAL B_temporal64 hgb ===
TEST READ #1  B_temporal64__hgb  n=196
  posture_fault    AUROC 0.6802  F1 0.7385 [0.6774, 0.7955] @0.35  P 0.6857 R 0.8000  floor 0.7595  maj-acc 0.6122  acc 0.6531
  incumbent shipped_0.525    AUROC 0.7306  F1 0.7111 [0.6411, 0.7753] @0.525  P 0.7619 R 0.6667   paired ΔF1 +0.0274 [-0.0374, +0.0931]
  incumbent notebook_val_opt_0.475 AUROC 0.7306  F1 0.7311 [0.6667, 0.7918] @0.475  P 0.7373 R 0.7250   paired ΔF1 +0.0074 [-0.0501, +0.0646]
  incumbent content_val_opt_0.27 AUROC 0.7306  F1 0.7465 [0.6866, 0.8000] @0.27  P 0.6463 R 0.8833   paired ΔF1 -0.0080 [-0.0581, +0.0396]
  incumbent AUROC 0.7306 [0.6616, 0.7995]   paired ΔAUROC -0.0504 [-0.1150, +0.0112]
  -> NEGATIVE: retrain AUROC 0.6802 is not above the incumbent's point estimate 0.7306 (paired delta -0.0504 [-0.1150, +0.0112])
     secondary F1 criterion: retrain 0.7385 vs strongest incumbent lower bound 0.6866 -> passes
  stability_fault  AUROC 0.7310  F1 0.3529 [0.1739, 0.5091] @0.47  P 0.2903 R 0.4500  floor 0.1852  maj-acc 0.8980  acc 0.8316
  depth_fault      AUROC 0.6023  F1 0.4815 [0.3981, 0.5582] @0.16  P 0.3355 R 0.8525  floor 0.4747  maj-acc 0.6888  acc 0.4286
  any_fault        AUROC 0.6556  F1 0.7811 [0.7297, 0.8323] @0.38  P 0.7342 R 0.8345  floor 0.8299  maj-acc 0.7092  acc 0.6684
  posture_collapsed AUROC 0.6914  F1 0.6243 [0.5385, 0.7041] @0.31  P 0.5315 R 0.7564  floor 0.5693  maj-acc 0.6020  acc 0.6378
  incumbent shipped_0.525    AUROC 0.7159  F1 0.6120 [0.5301, 0.6911] @0.525  P 0.5333 R 0.7179   paired ΔF1 +0.0123 [-0.0653, +0.0861]
  incumbent notebook_val_opt_0.475 AUROC 0.7159  F1 0.6224 [0.5424, 0.6984] @0.475  P 0.5169 R 0.7821   paired ΔF1 +0.0019 [-0.0737, +0.0753]
  incumbent content_val_opt_0.69 AUROC 0.7159  F1 0.5612 [0.4545, 0.6490] @0.69  P 0.6393 R 0.5000   paired ΔF1 +0.0632 [-0.0265, +0.1596]
  incumbent AUROC 0.7159 [0.6388, 0.7893]   paired ΔAUROC -0.0244 [-0.0967, +0.0417]
  -> NEGATIVE: retrain AUROC 0.6914 is not above the incumbent's point estimate 0.7159 (paired delta -0.0244 [-0.0967, +0.0417])
     secondary F1 criterion: retrain 0.6243 vs strongest incumbent lower bound 0.5424 -> passes
logged -> /repo/bench/results/retrain/TEST_READ_LOG.jsonl
=== FINAL B_temporal64 mlp ===
TEST READ #1  B_temporal64__mlp  n=196
  posture_fault    AUROC 0.6529  F1 0.7368 [0.6781, 0.7875] @0.26  P 0.6087 R 0.9333  floor 0.7595  maj-acc 0.6122  acc 0.5918
  incumbent shipped_0.525    AUROC 0.7306  F1 0.7111 [0.6411, 0.7753] @0.525  P 0.7619 R 0.6667   paired ΔF1 +0.0257 [-0.0408, +0.0922]
  incumbent notebook_val_opt_0.475 AUROC 0.7306  F1 0.7311 [0.6667, 0.7918] @0.475  P 0.7373 R 0.7250   paired ΔF1 +0.0057 [-0.0524, +0.0689]
  incumbent content_val_opt_0.27 AUROC 0.7306  F1 0.7465 [0.6866, 0.8000] @0.27  P 0.6463 R 0.8833   paired ΔF1 -0.0096 [-0.0454, +0.0262]
  incumbent AUROC 0.7306 [0.6616, 0.7995]   paired ΔAUROC -0.0777 [-0.1461, -0.0116]
  -> NEGATIVE: retrain AUROC 0.6529 does not exceed the incumbent's AUROC CI lower bound 0.6616
     secondary F1 criterion: retrain 0.7368 vs strongest incumbent lower bound 0.6866 -> passes
  stability_fault  AUROC 0.5830  F1 0.1500 [0.0000, 0.3077] @0.37  P 0.1500 R 0.1500  floor 0.1852  maj-acc 0.8980  acc 0.8265
  depth_fault      AUROC 0.5984  F1 0.4854 [0.4067, 0.5591] @0.18  P 0.3258 R 0.9508  floor 0.4747  maj-acc 0.6888  acc 0.3724
  any_fault        AUROC 0.6009  F1 0.8299 [0.7864, 0.8671] @0.12  P 0.7092 R 1.0000  floor 0.8299  maj-acc 0.7092  acc 0.7092
  posture_collapsed AUROC 0.7183  F1 0.6073 [0.5193, 0.6839] @0.36  P 0.5133 R 0.7436  floor 0.5693  maj-acc 0.6020  acc 0.6173
  incumbent shipped_0.525    AUROC 0.7159  F1 0.6120 [0.5301, 0.6911] @0.525  P 0.5333 R 0.7179   paired ΔF1 -0.0047 [-0.0740, +0.0619]
  incumbent notebook_val_opt_0.475 AUROC 0.7159  F1 0.6224 [0.5424, 0.6984] @0.475  P 0.5169 R 0.7821   paired ΔF1 -0.0151 [-0.0829, +0.0477]
  incumbent content_val_opt_0.69 AUROC 0.7159  F1 0.5612 [0.4545, 0.6490] @0.69  P 0.6393 R 0.5000   paired ΔF1 +0.0462 [-0.0385, +0.1405]
  incumbent AUROC 0.7159 [0.6388, 0.7893]   paired ΔAUROC +0.0024 [-0.0546, +0.0547]
  -> POSITIVE per contract, NOT DISTINGUISHABLE: retrain AUROC 0.7183 exceeds the incumbent's lower bound 0.6388 and point estimate 0.7159, but the paired delta +0.0024 [-0.0546, +0.0547] includes zero
     secondary F1 criterion: retrain 0.6073 vs strongest incumbent lower bound 0.5424 -> passes
logged -> /repo/bench/results/retrain/TEST_READ_LOG.jsonl
=== FINAL C_incumbent151 logreg ===
TEST READ #1  C_incumbent151__logreg  n=196
  posture_fault    AUROC 0.6709  F1 0.7517 [0.6962, 0.8025] @0.17  P 0.6292 R 0.9333  floor 0.7595  maj-acc 0.6122  acc 0.6224
  incumbent shipped_0.525    AUROC 0.7306  F1 0.7111 [0.6411, 0.7753] @0.525  P 0.7619 R 0.6667   paired ΔF1 +0.0406 [-0.0245, +0.1092]
  incumbent notebook_val_opt_0.475 AUROC 0.7306  F1 0.7311 [0.6667, 0.7918] @0.475  P 0.7373 R 0.7250   paired ΔF1 +0.0206 [-0.0375, +0.0810]
  incumbent content_val_opt_0.27 AUROC 0.7306  F1 0.7465 [0.6866, 0.8000] @0.27  P 0.6463 R 0.8833   paired ΔF1 +0.0052 [-0.0299, +0.0402]
  incumbent AUROC 0.7306 [0.6616, 0.7995]   paired ΔAUROC -0.0596 [-0.1252, +0.0051]
  -> NEGATIVE: retrain AUROC 0.6709 is not above the incumbent's point estimate 0.7306 (paired delta -0.0596 [-0.1252, +0.0051])
     secondary F1 criterion: retrain 0.7517 vs strongest incumbent lower bound 0.6866 -> passes
  stability_fault  AUROC 0.7324  F1 0.2703 [0.1356, 0.4045] @0.57  P 0.1852 R 0.5000  floor 0.1852  maj-acc 0.8980  acc 0.7245
  depth_fault      AUROC 0.5633  F1 0.4469 [0.3529, 0.5312] @0.42  P 0.3390 R 0.6557  floor 0.4747  maj-acc 0.6888  acc 0.4949
  any_fault        AUROC 0.6225  F1 0.8228 [0.7750, 0.8638] @0.05  P 0.7062 R 0.9856  floor 0.8299  maj-acc 0.7092  acc 0.6990
  posture_collapsed AUROC 0.7091  F1 0.6023 [0.5095, 0.6842] @0.46  P 0.5408 R 0.6795  floor 0.5693  maj-acc 0.6020  acc 0.6429
  incumbent shipped_0.525    AUROC 0.7159  F1 0.6120 [0.5301, 0.6911] @0.525  P 0.5333 R 0.7179   paired ΔF1 -0.0097 [-0.0832, +0.0633]
  incumbent notebook_val_opt_0.475 AUROC 0.7159  F1 0.6224 [0.5424, 0.6984] @0.475  P 0.5169 R 0.7821   paired ΔF1 -0.0202 [-0.0981, +0.0513]
  incumbent content_val_opt_0.69 AUROC 0.7159  F1 0.5612 [0.4545, 0.6490] @0.69  P 0.6393 R 0.5000   paired ΔF1 +0.0411 [-0.0438, +0.1328]
  incumbent AUROC 0.7159 [0.6388, 0.7893]   paired ΔAUROC -0.0067 [-0.0720, +0.0543]
  -> NEGATIVE: retrain AUROC 0.7091 is not above the incumbent's point estimate 0.7159 (paired delta -0.0067 [-0.0720, +0.0543])
     secondary F1 criterion: retrain 0.6023 vs strongest incumbent lower bound 0.5424 -> passes
logged -> /repo/bench/results/retrain/TEST_READ_LOG.jsonl
=== FINAL C_incumbent151 hgb ===
TEST READ #1  C_incumbent151__hgb  n=196
  posture_fault    AUROC 0.6898  F1 0.7273 [0.6615, 0.7832] @0.3  P 0.6667 R 0.8000  floor 0.7595  maj-acc 0.6122  acc 0.6327
  incumbent shipped_0.525    AUROC 0.7306  F1 0.7111 [0.6411, 0.7753] @0.525  P 0.7619 R 0.6667   paired ΔF1 +0.0162 [-0.0490, +0.0826]
  incumbent notebook_val_opt_0.475 AUROC 0.7306  F1 0.7311 [0.6667, 0.7918] @0.475  P 0.7373 R 0.7250   paired ΔF1 -0.0038 [-0.0617, +0.0531]
  incumbent content_val_opt_0.27 AUROC 0.7306  F1 0.7465 [0.6866, 0.8000] @0.27  P 0.6463 R 0.8833   paired ΔF1 -0.0192 [-0.0658, +0.0275]
  incumbent AUROC 0.7306 [0.6616, 0.7995]   paired ΔAUROC -0.0408 [-0.1040, +0.0182]
  -> NEGATIVE: retrain AUROC 0.6898 is not above the incumbent's point estimate 0.7306 (paired delta -0.0408 [-0.1040, +0.0182])
     secondary F1 criterion: retrain 0.7273 vs strongest incumbent lower bound 0.6866 -> passes
  stability_fault  AUROC 0.6844  F1 0.1600 [0.0392, 0.3078] @0.48  P 0.1333 R 0.2000  floor 0.1852  maj-acc 0.8980  acc 0.7857
  depth_fault      AUROC 0.6130  F1 0.4828 [0.4000, 0.5560] @0.11  P 0.3275 R 0.9180  floor 0.4747  maj-acc 0.6888  acc 0.3878
  any_fault        AUROC 0.6442  F1 0.7973 [0.7437, 0.8442] @0.41  P 0.7632 R 0.8345  floor 0.8299  maj-acc 0.7092  acc 0.6990
  posture_collapsed AUROC 0.6730  F1 0.6040 [0.5200, 0.6816] @0.27  P 0.4919 R 0.7821  floor 0.5693  maj-acc 0.6020  acc 0.5918
  incumbent shipped_0.525    AUROC 0.7159  F1 0.6120 [0.5301, 0.6911] @0.525  P 0.5333 R 0.7179   paired ΔF1 -0.0081 [-0.0802, +0.0647]
  incumbent notebook_val_opt_0.475 AUROC 0.7159  F1 0.6224 [0.5424, 0.6984] @0.475  P 0.5169 R 0.7821   paired ΔF1 -0.0185 [-0.0832, +0.0483]
  incumbent content_val_opt_0.69 AUROC 0.7159  F1 0.5612 [0.4545, 0.6490] @0.69  P 0.6393 R 0.5000   paired ΔF1 +0.0428 [-0.0447, +0.1427]
  incumbent AUROC 0.7159 [0.6388, 0.7893]   paired ΔAUROC -0.0429 [-0.1116, +0.0196]
  -> NEGATIVE: retrain AUROC 0.6730 is not above the incumbent's point estimate 0.7159 (paired delta -0.0429 [-0.1116, +0.0196])
     secondary F1 criterion: retrain 0.6040 vs strongest incumbent lower bound 0.5424 -> passes
logged -> /repo/bench/results/retrain/TEST_READ_LOG.jsonl
=== FINAL C_incumbent151 mlp ===
TEST READ #1  C_incumbent151__mlp  n=196
  posture_fault    AUROC 0.6712  F1 0.7692 [0.7133, 0.8173] @0.06  P 0.6250 R 1.0000  floor 0.7595  maj-acc 0.6122  acc 0.6327
  incumbent shipped_0.525    AUROC 0.7306  F1 0.7111 [0.6411, 0.7753] @0.525  P 0.7619 R 0.6667   paired ΔF1 +0.0581 [-0.0107, +0.1288]
  incumbent notebook_val_opt_0.475 AUROC 0.7306  F1 0.7311 [0.6667, 0.7918] @0.475  P 0.7373 R 0.7250   paired ΔF1 +0.0381 [-0.0244, +0.1025]
  incumbent content_val_opt_0.27 AUROC 0.7306  F1 0.7465 [0.6866, 0.8000] @0.27  P 0.6463 R 0.8833   paired ΔF1 +0.0228 [-0.0128, +0.0598]
  incumbent AUROC 0.7306 [0.6616, 0.7995]   paired ΔAUROC -0.0594 [-0.1169, -0.0075]
  -> NEGATIVE: retrain AUROC 0.6712 is not above the incumbent's point estimate 0.7306 (paired delta -0.0594 [-0.1169, -0.0075])
     secondary F1 criterion: retrain 0.7692 vs strongest incumbent lower bound 0.6866 -> passes
  stability_fault  AUROC 0.5344  F1 0.2000 [0.1127, 0.2875] @0.13  P 0.1154 R 0.7500  floor 0.1852  maj-acc 0.8980  acc 0.3878
  depth_fault      AUROC 0.5824  F1 0.4781 [0.4000, 0.5496] @0.06  P 0.3158 R 0.9836  floor 0.4747  maj-acc 0.6888  acc 0.3316
  any_fault        AUROC 0.5813  F1 0.8263 [0.7788, 0.8671] @0.18  P 0.7077 R 0.9928  floor 0.8299  maj-acc 0.7092  acc 0.7041
  posture_collapsed AUROC 0.6786  F1 0.5683 [0.4790, 0.6529] @0.38  P 0.4952 R 0.6667  floor 0.5693  maj-acc 0.6020  acc 0.5969
  incumbent shipped_0.525    AUROC 0.7159  F1 0.6120 [0.5301, 0.6911] @0.525  P 0.5333 R 0.7179   paired ΔF1 -0.0437 [-0.1257, +0.0319]
  incumbent notebook_val_opt_0.475 AUROC 0.7159  F1 0.6224 [0.5424, 0.6984] @0.475  P 0.5169 R 0.7821   paired ΔF1 -0.0541 [-0.1369, +0.0228]
  incumbent content_val_opt_0.69 AUROC 0.7159  F1 0.5612 [0.4545, 0.6490] @0.69  P 0.6393 R 0.5000   paired ΔF1 +0.0072 [-0.0883, +0.1124]
  incumbent AUROC 0.7159 [0.6388, 0.7893]   paired ΔAUROC -0.0373 [-0.1085, +0.0273]
  -> NEGATIVE: retrain AUROC 0.6786 is not above the incumbent's point estimate 0.7159 (paired delta -0.0373 [-0.1085, +0.0273])
     secondary F1 criterion: retrain 0.5683 vs strongest incumbent lower bound 0.5424 -> passes
logged -> /repo/bench/results/retrain/TEST_READ_LOG.jsonl
```

### 4a. Primary — `posture_fault` (multi-label bit, prevalence 0.612)

| artifact | val AUROC (median) | test AUROC [95 % CI] | paired ΔAUROC vs incumbent [95 % CI] | verdict |
|---|---|---|---|---|
| A_v2_body / hgb | 0.7683 | 0.7443 [0.670, 0.814] | +0.0137 [-0.054, +0.080] | POSITIVE per contract, **not distinguishable** |
| A_v2_body / logreg | 0.7293 | 0.6945 [0.619, 0.765] | -0.0361 [-0.110, +0.039] | **NEGATIVE** |
| A_v2_body / mlp | 0.7203 | 0.6883 [0.612, 0.761] | -0.0423 [-0.115, +0.028] | **NEGATIVE** |
| B_temporal64 / hgb ← **primary** | 0.7828 | 0.6802 [0.607, 0.753] | -0.0504 [-0.115, +0.011] | **NEGATIVE** |
| B_temporal64 / logreg | 0.7388 | 0.6772 [0.602, 0.752] | -0.0534 [-0.115, +0.010] | **NEGATIVE** |
| B_temporal64 / mlp | 0.7162 | 0.6529 [0.576, 0.728] | -0.0777 [-0.146, -0.012] | **NEGATIVE** (below CI lower bound) |
| C_incumbent151 / hgb | 0.7717 | 0.6898 [0.613, 0.762] | -0.0408 [-0.104, +0.018] | **NEGATIVE** |
| C_incumbent151 / logreg | 0.7200 | 0.6709 [0.597, 0.746] | -0.0596 [-0.125, +0.005] | **NEGATIVE** |
| C_incumbent151 / mlp | 0.7083 | 0.6712 [0.598, 0.744] | -0.0594 [-0.117, -0.007] | **NEGATIVE** |
| *incumbent PostureV1 (shipped weights, serving loader, same cached keypoints)* | 0.7488 | 0.7306 [0.662, 0.799] | — | — |

### 4b. Co-primary — `posture_collapsed` (the incumbent's own task, prevalence 0.398)

| artifact | val AUROC (median) | test AUROC [95 % CI] | paired ΔAUROC vs incumbent [95 % CI] | verdict |
|---|---|---|---|---|
| A_v2_body / hgb | 0.7319 | 0.7389 [0.669, 0.806] | +0.0230 [-0.056, +0.103] | POSITIVE per contract, **not distinguishable** |
| A_v2_body / logreg | 0.7239 | 0.7203 [0.643, 0.789] | +0.0045 [-0.073, +0.079] | POSITIVE per contract, **not distinguishable** |
| A_v2_body / mlp | 0.7241 | 0.6931 [0.615, 0.765] | -0.0228 [-0.093, +0.046] | **NEGATIVE** |
| B_temporal64 / hgb ← **co-primary** | 0.7827 | 0.6914 [0.615, 0.763] | -0.0244 [-0.097, +0.042] | **NEGATIVE** |
| B_temporal64 / logreg | 0.7218 | 0.6889 [0.611, 0.760] | -0.0269 [-0.089, +0.036] | **NEGATIVE** |
| B_temporal64 / mlp | 0.7282 | 0.7183 [0.642, 0.788] | +0.0024 [-0.055, +0.055] | POSITIVE per contract, **not distinguishable** |
| C_incumbent151 / hgb | 0.7643 | 0.6730 [0.596, 0.743] | -0.0429 [-0.112, +0.020] | **NEGATIVE** |
| C_incumbent151 / logreg | 0.7317 | 0.7091 [0.634, 0.779] | -0.0067 [-0.072, +0.054] | **NEGATIVE** |
| C_incumbent151 / mlp | 0.7133 | 0.6786 [0.599, 0.753] | -0.0373 [-0.108, +0.027] | **NEGATIVE** |
| *incumbent PostureV1* | 0.7638 | 0.7159 [0.639, 0.789] | — | — |

### 4c. The secondary F1 rows for the primary artifact, and why they say nothing

| model | threshold (how chosen) | P | R | F1 [95 % CI] | paired ΔF1 (retrain − incumbent) |
|---|---|---|---|---|---|
| retrain B / hgb | 0.35 (validation F1 optimum) | 0.6857 | 0.8000 | 0.7385 [0.6774, 0.7955] | — |
| incumbent | 0.525 (shipped) | 0.7619 | 0.6667 | 0.7111 [0.6411, 0.7753] | +0.0274 [-0.0374, +0.0931] |
| incumbent | 0.475 (notebook-validation optimum) | 0.7373 | 0.7250 | 0.7311 [0.6667, 0.7918] | +0.0074 [-0.0501, +0.0646] |
| incumbent | 0.27 (this experiment's validation optimum) | 0.6463 | 0.8833 | 0.7465 [0.6866, 0.8000] | -0.0080 [-0.0581, +0.0396] |

Every row sits within 0.05 of the all-positive floor of **0.7595**, and the incumbent's
strongest F1 lower bound (0.6866) is itself *below* the floor — the F1 criterion is passed by a
classifier that says "fault" to everything. This is why amendment 1 made AUROC the acceptance
metric; the F1 rows are reported because they were pre-registered, and they are uninformative.

### 4d. The other heads (best-on-validation artifact per head, read on the same test)

| head | test prevalence | floor F1 | artifact (best median val AUROC) | test AUROC [95 % CI] | test F1 [95 % CI] @thr |
|---|---|---|---|---|---|
| stability_fault | 0.102 | 0.1852 | C_incumbent151 / hgb (val 0.7933) | 0.6844 [0.542, 0.810] | 0.1600 [0.039, 0.308] @0.48 |
| depth_fault | 0.311 | 0.4747 | B_temporal64 / hgb (val 0.6329) | 0.6023 [0.514, 0.684] | 0.4815 [0.398, 0.558] @0.16 |
| any_fault | 0.709 | 0.8299 | C_incumbent151 / hgb (val 0.7201) | 0.6442 [0.561, 0.724] | 0.7973 [0.744, 0.844] @0.41 |

- **depth_fault**: no artifact clears the floor (AUROC 0.56–0.65, every F1 CI contains 0.475).
  As pre-registered: the Phase 2 depth negative stands regardless of features.
- **any_fault**: F1 0.78–0.83 against a floor of 0.830 — nothing beats all-positive; AUROC
  0.58–0.68. The pre-registered "modest gain on any_fault" **did not materialise**.
- **stability_fault** (20 positives): the rule-selected artifact (C / hgb, best median validation
  AUROC 0.7933) scores **F1 0.16 [0.04, 0.31] vs a floor of 0.185 — below it** — at AUROC 0.68
  [0.54, 0.81]. Other artifacts score higher on test (A / logreg: F1 0.31, AUROC 0.74), but those
  are test-selected numbers and are not the result; the widest intervals on the page. Never shipped
  (G-42); this is the first measured number for it and it is not a shippable one.
  *(Corrected 2026-09-23: the first version of this bullet quoted the best-on-test artifact.)*

## 5. Verdict — NEGATIVE, and what it does and does not say

**Pre-registered primary:** B / hgb on `posture_fault`, test AUROC **0.6802 [0.6067, 0.7526]**
vs the incumbent's **0.7306 [0.6616, 0.7995]**; paired ΔAUROC **−0.0504 [−0.1150, +0.0112]**.
Below the incumbent's point estimate: NEGATIVE by the rule. **Co-primary** on the collapsed
label: 0.6914 vs 0.7159, Δ −0.0244 [−0.0967, +0.0417]: NEGATIVE.

Across all nine artifacts on the primary label, eight are below the incumbent's point estimate
and two (both MLPs) are below it with a paired CI that excludes zero. The one above it —
A / hgb, +0.0137 [−0.0536, +0.0795] — is a secondary artifact, and calling it the result would
be selecting on test; by the rule it is "not distinguishable". No artifact is distinguishable
from the incumbent on the collapsed label either.

What it says:

1. **Body-only features, multi-label targets, the serving pose pass and a deterministic
   protocol do not move the honest number.** The incumbent's edge is not the face block: its
   own 151-D features with a deterministic learner (C / hgb) score 0.69, below its 0.73. Whatever
   the incumbent learned, it is not recoverable from these features with these learners, and the
   corpus does not contain enough to beat it — consistent with ML_AUDIT cause 1 (the label
   defines a degree judgement on a near-universal behaviour) being the ceiling, not causes 2 or 4.
2. **Validation at n=218 over-promised by 0.05–0.10 AUROC.** The primary went 0.7828 → 0.6802;
   the incumbent went 0.7488 → 0.7306. Selecting the best of nine on 218 videos buys that much
   optimism; this is what the single-read rule protects against, and the number to quote for
   "how much does validation selection inflate" on this corpus is now measured.
3. **Some of the incumbent's margin is contamination, and it does not change the verdict.** The
   incumbent was trained on the user-level split; 12 % of the historical test had byte-identical
   twins in its training set (G-44), and Gate 1b measured that effect at ≤ 0.02 on this label. The
   retrain's test is clean. A ≤ 0.02 bias in the incumbent's favour does not close a −0.05 gap.
4. **The re-scoping in ML_AUDIT §11c stands.** No per-video posture verdict trained here clears
   its floor with a CI that excludes it; the temporal predicate (knees-forward localisation) and
   `any_fault` remain the only claims the data supports, and `any_fault` scored at its floor here.

What it does not say: that a better model cannot exist. It says one was not found by the most
defensible route available, and that the shipped model keeps its place because nothing beat it
on a paired, pre-registered, single-read comparison — which is the outcome the contract named.

## 6. Files

`bench/retrain/` (protocol, committed before any run), `bench/results/retrain/` (dataset
manifest, nine training reports, `primary_selection.json`, `incumbent_validation_check.json`,
nine `*__FINAL.json`, `TEST_READ_LOG.jsonl`), `backend/tests/unit/test_retrain_test_read_log.py`
(a second read of test for the same artifact fails CI unless forced with a reason). Pickled
artifacts and `.npz` datasets are in `bench/cache/retrain/` (gitignored; regenerable from
`run.sh build` + `train` — logreg/HGB deterministically, the MLP per seed).
