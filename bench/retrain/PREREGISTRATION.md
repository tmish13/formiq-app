# Controlled retrain — pre-registration

Written before any training run on the full dataset and before any test read.
The test split (`content_level_splits.json`, split=test) is read once per artifact,
behind `--final`, and every read is appended to `TEST_READ_LOG.jsonl`.

## Question
Does a body-only, multi-label, serving-pass retrain beat the incumbent PostureV1 on the
posture verdict, on a clean content-level test set of adequate size?

## Fixed in advance
- **Splits**: `bench/results/content_level_splits.json` (`minimal` mode). Dedup map applied
  first; 161 conflicted + 138 no-file videos withheld; Penn absent by construction.
- **Pose pass**: serving pass `pp1_f9850424580ae186` for train, validation and test
  (recorded in `manifest.json` and in every artifact).
- **Targets**: four independent binary heads from `original_multi_label`:
  `posture_fault`, `stability_fault`, `depth_fault`, `any_fault`. No collapse, no undersampling.
- **Arms**: A = v2 body-only 201-D (`spec_hash f06e2b7a…`); B = incumbent's 64-D temporal
  block (151-D[87:151]); C = incumbent's full 151-D including the 87-D face block.
- **Learners**: logistic regression (deterministic), histogram gradient boosting
  (deterministic: no subsampling, no early stopping), MLP (seed-sensitive; early-stops on a
  15% slice of TRAIN). Five seeds each; the artifact is the seed with the median validation
  AUROC; its threshold is the validation F1-optimum on `THR_GRID` (0.05..0.95 step 0.01).
- **Metrics**: `app/eval/metrics.py` only. AUROC primary; F1 with bootstrap CI (n=2000,
  seed 0); trivial floor and majority-class accuracy always reported.

## Primary comparison (decided by rule, not by test)
- **Primary artifact** = the (arm, learner) whose artifact has the highest median validation
  AUROC on `posture_fault`. All other artifacts are secondary and are reported in full.
- **Incumbent** = shipped PostureV1 weights scored through the serving loader on the SAME
  cached test keypoints.
- **Acceptance (primary, threshold-free)**: the primary artifact's posture **AUROC** exceeds
  the incumbent's AUROC bootstrap-CI lower bound on the same test videos. Otherwise the
  result is a NEGATIVE and is written up as one.
- **Secondary**: F1 at the artifact's validation threshold against the incumbent at three
  validation-derived thresholds -- shipped 0.525, notebook-validation-optimal 0.475
  (ML_AUDIT §7.2), and the optimum on THIS experiment's validation split chosen by the same
  rule the retrain uses. Reported as passes/fails against the strongest of the three lower
  bounds; it does not change the verdict.
- Paired bootstraps on ΔAUROC and ΔF1 (same videos) are reported alongside.

*Amendment before any test read (2026-09-23, after a rehearsal with validation aliased as
test):* F1 was the acceptance metric in the first draft. At this corpus's 62 % posture
prevalence the all-positive F1 floor is 0.77, and any threshold at or below 0.3 puts both
models within 0.05 of it, so an F1 acceptance would mostly compare how close each model sits
to all-positive. ML_AUDIT §11c already names AUROC primary; the acceptance now follows it.
No test data was read before this amendment (`TEST_READ_LOG.jsonl` is empty).

## Expected outcome, stated in advance (ML_AUDIT §11b)
Modest gain on `any_fault` and on posture-with-co-occurrence; no gain on `depth_fault`
(the Phase 2 depth negative stands regardless of features). The stability head has no
incumbent (never shipped, G-42) and is reported against its floor only.

*Amendment 2, before any test read (2026-09-23):* the live-pipeline evaluation on the same
content-level test videos (`eval_runner.py --splits content --split test`, interim n=78)
scores the incumbent against the corpus's **collapsed** class label (`posture_fault` as the
single class, prevalence ≈ 0.20), while the four heads above use the **multi-label** posture
bit (prevalence ≈ 0.62). Scoring the incumbent only on the multi-label bit would judge it
on a task it was never trained for. So a fifth head, `posture_collapsed`
(class_label == posture_fault), is added as both a training target and an evaluation label:

- **Primary (unchanged)**: `posture_fault` (multi-label bit), the re-scoped task.
- **Co-primary, reported separately with its own verdict**: `posture_collapsed`, the
  incumbent's own task. Same test videos, same stored probabilities, second label column.
  A retrain that wins on the multi-label bit but loses on the collapsed label is written up
  as exactly that.
- The MLP/logreg/HGB heads trained on `posture_collapsed` with arm C (the incumbent's own
  151-D features) isolate learner-and-protocol from label-definition.

`TEST_READ_LOG.jsonl` is still empty at this amendment.

*Amendment 3, before any test read (2026-09-23, after a rehearsal on validation):* with
n ≈ 93 the incumbent's AUROC interval is ~±0.11 wide, so "exceeds the incumbent's CI lower
bound" alone would have called a retrain POSITIVE while its point estimate sat 0.09 *below*
the incumbent's. That condition is therefore treated as necessary, not sufficient. The
verdict is one of:

- **NEGATIVE** -- retrain AUROC ≤ incumbent CI lower bound, **or** retrain AUROC ≤ incumbent
  point estimate (paired ΔAUROC ≤ 0).
- **POSITIVE** -- retrain AUROC above both, and the paired ΔAUROC 95 % CI excludes zero.
- **POSITIVE per contract, NOT DISTINGUISHABLE** -- above both, but the paired ΔAUROC CI
  includes zero. Reported as such, never as a plain positive.

`TEST_READ_LOG.jsonl` is still empty at this amendment.

## Not done
- Per-item flip rate against a second pose pass (would need a second extraction of test).
