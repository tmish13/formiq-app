# 105 duplicate videos, 45 across splits, 80 with conflicting labels

**Date:** 2026-09-23 · **Branch:** `audit/phase2-depth-rule`
**Script:** `bench/corpus_duplicates.py` · **Raw:** `bench/results/corpus_duplicates.json`
**Method:** sha256 of every corpus `.mp4`, using `app/core/hashing.py` — the same function and
chunk size the upload path uses, so these are the keys `form_checks`, `analysis_runs` and
`labels` actually join on.

## How this was found

Not by looking for it. The `labels` table's unique key
`(content_hash, target, source, source_ref)` **refused an insert** during the first full import:

```
duplicate key value violates unique constraint "uq_labels_hash_target_source_ref"
DETAIL: Key (content_hash, target, source, source_ref)=(e9d05e7e…, good_form, dataset, …)
```

Two different `video_name`s had produced identical bytes. A constraint declared for idempotency
caught a data defect nobody was looking for.

## The numbers

| | |
|---|---|
| videos hashed | **1,487** (138 corpus entries have no file on disk) |
| distinct content | **1,382** |
| hashes appearing under >1 name | **104** |
| extra copies | **105 — 7.1% of the corpus** |
| duplicates spanning **different splits** | **45** |
| duplicates spanning different users | **104** |
| duplicates with **conflicting labels** | **80** |

Group sizes: 103 pairs and one triple.

## Why the earlier "zero leakage" check did not catch it

The splits are user-level and were verified leakage-free **by user id** — 1,625 videos, 1,625
users, no user in two splits. That check is correct. It is also not sufficient, because it
assumes each user's footage is distinct.

**104 byte-identical files are filed under different user ids.** The split is clean by the
identifier and dirty by the content. That is precisely the failure a content hash detects and a
user id cannot:

```
0fc5adb7  38094_2 / train      / u38094 / good_form
          37491_2 / test       / u37491 / depth_fault
60e9448c  38104_1 / train      / u38104 / good_form
          37448_1 / test       / u37448 / depth_fault
f946bf6d  37527_2 / train      / u37527 / depth_fault
          38111_2 / validation / u38111 / good_form
```

**I need to withdraw the unqualified version of an earlier claim.** "Verified zero leakage,
1625 videos = 1625 users" was reported during Phase 2 without this caveat. The user-level
statement is true as stated; the impression it gave — that the split is free of train/test
contamination — is not. **45 hashes appear in more than one split.**

## The part that matters most: 80 conflicting labels

The same bytes, labelled two different things:

| conflicting pair | n |
|---|---|
| `depth_fault` vs `good_form` | **47** |
| `good_form` vs `posture_fault` | **33** |
| any fault vs a *different* fault | **0** |

**Every single conflict involves `good_form`, and none is fault-vs-fault.** That is not scattered
annotation noise — noise would produce some depth-vs-posture disagreements. It is a systematic
boundary: annotators disagree about *whether there is a fault at all*, and never about which one.

```
c39ea921  37044_4 / train / good_form      36836_4 / train / depth_fault
402d3e6f  50824_2 / train / good_form      48298_2 / train / posture_fault
e9d05e7e  48602_1 / train / posture_fault  50859_1 / train / good_form
```

### This is a measured explanation for the Phase 2 depth negative

Phase 2 concluded that no geometric axis separates `depth_fault` in this corpus — best AUROC
0.578 of ten tried, knee-flexion distributions overlapping across all three classes
(`2026-09-23-depth-rule-negative-result.md`).

**47 pairs of byte-identical frames carry both `depth_fault` and `good_form`.** No function of
the pixels can separate classes when the same pixels sit in both. The negative result stands, and
it now has a cause that is not "the rule was badly designed": part of the label is irreducible by
construction.

This does not fully explain the negative — 47 pairs is small against 1,625 videos — but it is
the first evidence that the ceiling is in the labels rather than in the geometry, and it is
measured rather than argued.

## A second, separate disagreement inside the splits file

While importing, the two label fields in `user_level_multilabel_splits.json` turned out to
disagree with each other on **600 of 1,625 videos (36.9%)**:

| `category` (source folder) | assigned class | n |
|---|---|---|
| `posture_faults` | `depth_fault` | 293 |
| `stability_faults` | `posture_fault` | 131 |
| **`good_form`** | **`depth_fault`** | **128** |
| `stability_faults` | `depth_fault` | 48 |

`multilabel_targets` and `enhanced_labels.video_level.class_label` agree **perfectly** (0 of
1,625), so there are two fields, not three. `category` is the folder a clip was *collected*
into; the target is the class it was *assigned*.

`stability_fault` has no class in the three-class scheme, so all 179 stability clips were
reassigned to posture or depth. And **128 clips the collectors filed under good form carry the
`depth_fault` label** — a reassignment, not an observation.

Both fields are imported, under different `source_ref`s. Importing only the winner would have
erased the corpus's best evidence about its own label quality.

## What to do with this

1. **Stop quoting "zero leakage" without the content-hash caveat.** The correct statement is
   "leakage-free at the user level; 45 duplicate files span splits."
2. **De-duplicate by content hash before any future training or evaluation split**, not by
   filename or user id. The tooling now exists — this is one query against `labels`.
3. **The 80 conflicting pairs are the cheapest labelling win available.** They are a
   pre-identified list of clips where a second annotator is known to be needed, and resolving
   them costs 80 reviews rather than a relabelling campaign.
4. **Do not re-run the Phase 2 negatives yet.** Removing 105 duplicates from a 1,487-video
   corpus will not turn AUROC 0.578 into a working rule, and re-running measurements after
   changing the data is how a negative result quietly becomes a positive one.

## Reproduce

```bash
docker run --rm -v $PWD/backend:/app -v $PWD:/repo \
  -v "$HOME/FORMIQ Form Analysis Model/data/squat_processed:/splits:ro" \
  -v "$HOME/Desktop/Squat More/Labeled_Dataset/videos:/videos:ro" \
  -e SECRET_KEY=dev-only-insecure-secret-key-32chars-minimum -w /app \
  deployment-beat:latest python /repo/bench/corpus_duplicates.py
```
