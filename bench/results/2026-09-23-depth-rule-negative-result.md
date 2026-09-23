# The definitional parallel criterion does not match this annotation

**Date:** 2026-09-23 · **Branch:** `audit/phase2-depth-rule` · **Status:** NEGATIVE RESULT
**Data:** FULL train selection, 133 per class, live-extracted keypoints (extraction finished: 711 clips, 0 errors, MediaPipe 0.10.18 complexity 2)

This is the outcome that was pre-declared as possible in `bench/depth_rule_calibrate.py`
before any fitting:

> An offset approaching the class separation is NOT a correction. It is a fitted threshold
> wearing a correction's name, and the honest conclusion would be that the definitional
> criterion does not match this annotator -- which is a finding, not a failure.

It is that case, and more strongly than anticipated: the class difference runs **backwards**.

## 1. The result

`AT_DEPTH ⟺ (hip_y − knee_y)/S ≥ 0`, zero fitted parameters, full train selection:

```
precision(SHALLOW)   0.4074
recall(SHALLOW)      0.1068
F1(SHALLOW)          0.1692
precision(AT_DEPTH)  0.4390     <- P_target is 0.85
coverage             71.8%      (191/266, 75 abstained)
```

Median score by class -- the ordering is the finding:

| class | n | median |
|---|---|---|
| posture_fault | 128 | +0.1408 |
| good_form | 115 | +0.1536 |
| **depth_fault** | 120 | **+0.1719** |

Class separation is **+0.0179 torso-lengths in the wrong direction**: clips labelled
`depth_fault` score *deeper* than clips labelled `good_form`.

### The number that settles it

Stop calling the offset a correction and simply fit a threshold — the best it achieves is
**F1 0.686**. The classes are balanced 133/133, so the trivial all-positive classifier
("call every squat shallow") scores **2·0.5/1.5 = 0.667**.

**A fully fitted threshold beats thinking about nothing by 0.019 F1.** The fitted offset is
−0.30 at the grid edge, which is **1678% of the class separation** — there is no threshold
anywhere in the sweep that extracts a usable signal, because the signal is not there.

## 2. It is not a measurement bug

Five independent geometric quantities, computed from different landmark subsets, agree:

| indicator | good_form | depth_fault | deeper = | direction |
|---|---|---|---|---|
| femur incline | −14.23° | **−16.81°** | smaller | backwards |
| hip-knee delta | 0.156 | **0.180** | larger | backwards |
| knee flexion | 47.5° | **42.6°** | smaller | backwards |
| hip drop ratio | 0.950 | **1.019** | larger | backwards |
| hip flexion | 45.6° | 47.2° | smaller | *correct* (and it is the trunk-lean-confounded one) |

Ruled out, each by measurement rather than argument:

- **View confound.** The reversal holds *within* every view bucket — side (+0.072 vs +0.212),
  oblique (+0.160 vs +0.190), front (+0.069 vs +0.160).
- **Filming confound.** Coverage medians identical (0.770 both), bottom-window sizes identical
  (15 frames both), view distributions similar.
- **Bottom detection.** Measuring at the *human-marked* `depth_frames` instead of the detected
  bottom gives +0.1222 median for `depth_fault` — still hip-below-knee, still at depth.
- **Extremum noise.** Switching every aggregate from min/max to median over the bottom window
  leaves it backwards, with a *larger* gap (I2: 0.077 vs 0.124).

## 3. Why: the corpus is deep squats

The geometry is validated against known poses:

| | median | p10 | p90 |
|---|---|---|---|
| knee angle, standing frame | **170.2°** | 158.0° | 176.9° |
| knee angle, bottom frame | **49.6°** | 32.4° | **95.6°** |

180° is a straight leg; parallel is ~90–100°; rock bottom is ~40–60°. Standing reads 170° and
the bottom reads 50°, so the computation is right — and **the corpus consists of squats that go
far past parallel**. Only the top decile even approaches it.

**A criterion that asks "did the femur reach horizontal?" cannot discriminate in a population
where essentially everyone's femur goes well past horizontal.** `P_target = 0.85` on `AT_DEPTH`
is not reachable through parallel here, because by the parallel standard nearly every clip is at
depth — including the ones a human called a depth fault.

## 3b. There is no depth contrast in the corpus -- on any axis

Run on train + validation, 457 clips with a usable bottom (`bench/corpus_axes.py`).
**Test was not opened**: the knee-valgus work uses the same split structure, so looking at test
for a depth question would contaminate the next target too.

**Knee flexion at the bottom, by class:**

| class | n | p10 | p25 | median | p75 | p90 |
|---|---|---|---|---|---|---|
| good_form | 145 | 7.8 | 29.7 | **47.1** | 65.4 | 82.4 |
| depth_fault | 149 | 7.6 | 33.9 | **43.4** | 54.2 | 69.1 |
| posture_fault | 159 | 6.8 | 30.1 | **44.9** | 60.6 | 76.4 |

The distributions overlap almost completely -- medians within 4°, p10s within 1°. And **the 90th
percentile of every class is still below parallel** (69–82° against ~90–100°). There is no
subpopulation of shallow squats in this corpus to find.

**Separability, good_form vs depth_fault, AUROC per axis** (0.5 = indistinguishable):

| axis | AUROC | \|dev\| | good_form | depth_fault |
|---|---|---|---|---|
| knee_ankle_x_max | 0.578 | 0.078 | 0.332 | 0.380 |
| hip_drop_ratio | 0.573 | 0.073 | 0.940 | 1.000 |
| knee_flexion_median | 0.431 | 0.069 | 55.02 | 51.63 |
| trunk_lean_max_deg | 0.450 | 0.050 | 29.27 | 25.93 |
| knee_flexion_min | 0.458 | 0.042 | 47.13 | 43.44 |
| hip_knee_delta_max | 0.531 | 0.031 | 0.159 | 0.161 |
| hip_flexion_min | 0.510 | 0.010 | 44.34 | 47.00 |
| clip_frames | 0.511 | 0.011 | 95 | 95 |

**Nothing reaches \|dev\| ≥ 0.10.** Not depth, not lean, not tempo, not clip length, not scale.
The strongest signal in the corpus is knee-ankle x displacement at 0.578 -- barely above chance,
and notably that is the *valgus* axis rather than a depth one.

This settles the question raised in §4 below. It is not that the definitional criterion was the
wrong choice of depth measure: **no measure separates these classes**, so the `depth_fault` label
does not encode anything recoverable from these keypoints. A different depth formulation would
not have worked either.

## 4. What `depth_fault` therefore means

Not "failed to reach parallel". The remaining candidates, in order of plausibility:

1. **Depth relative to that lifter's own capacity or to a coaching standard** — the annotator
   judging "shallower than this person should be going", not against a fixed geometric line.
2. **Depth relative to the rest of the set** — but every clip is a single rep, so there is no
   set to compare against within a clip.
3. Something about the marked instant that is not depth at the bottom at all.

Note the annotation provenance established in Stage 0: `labels_shallow_depth.json` and the
splits file's `depth_frames` are the **same annotation surfaced twice** (1552/1552 identical).
There is no second opinion in the corpus to arbitrate this against.

## 4b. Part of this ceiling is in the labels, not the geometry

*Added 2026-09-23, after G-44.*

The corpus contains **105 byte-identical duplicate videos** filed under different names
(`bench/corpus_duplicates.py`). **47 of those pairs carry both `depth_fault` and
`good_form`** — the same file, the same pixels, two opposite labels.

**No function of the pixels can separate classes when the same pixels sit in both.**

That is not a rhetorical point, it is an upper bound on any geometric rule, including a
perfect one. For those 47 pairs the Bayes-optimal classifier is wrong exactly half the
time no matter what it measures, because the label is a coin flip conditioned on the
filename rather than on the content.

So the AUROC 0.578 ceiling in section 3b is **partly irreducible**, and the negative result
gets *stronger*: the rule was not badly designed and the indicators were not badly chosen.
Some of the signal being looked for does not exist in the data at all.

**The honest scope.** 47 pairs is 94 videos against 1,625 — it does not by itself explain a
ceiling of 0.578, and it would be overclaiming to say it does. What changed is the kind of
explanation available: before G-44 the only account of the ceiling was *"the label means
something other than depth"* (section 4), which is an inference. This is a **measured**
mechanism, and the first evidence that any part of the gap is irreducible rather than
unmodelled.

It also sharpens what the 80 conflicting pairs are as annotation signal: **every one involves
`good_form`** (47 `depth_fault` vs `good_form`, 33 `good_form` vs `posture_fault`) and **none
is fault-vs-a-different-fault**. Annotators disagree about *whether there is a fault at all*
and never about which one — which is consistent with section 4's reading that `depth_fault`
encodes a judgement of degree against a standard that is not in the geometry.

**This does not license re-running the measurement.** De-duplicating the corpus and
re-measuring would produce a number that looks better for a reason unrelated to the rule,
which is how a negative result quietly becomes a positive one. The numbers in this file stand
as measured. Full finding: `bench/results/2026-09-23-corpus-duplicates.md`.

## 5. Consequences

**The definitional criterion is not shippable as a depth checker against this label.** It would
be a checker that disagrees with its own ground truth in the wrong direction.

Three honest options, none of which is "fit an offset until it works":

- ~~**Ship it as a parallel checker.**~~ **Rejected.** `depth_score` stays absent rather than
  carrying a verdict the data does not support. A checker that measures a real geometric fact
  but has no validated relationship to the product's notion of a depth fault is worse than no
  checker: it looks authoritative and is unvalidatable.
- ~~**Change the target to relative depth.**~~ **Dead.** It needs a per-lifter reference, and the
  split verification established **one clip per user** — the corpus cannot supply one.
- **Abandon depth and pick a fault whose definition and label agree.** ← taken. The corpus
  carries `error_knees_forward.json` and `error_knees_inward.json`: interval-level knee
  annotations over 1,623 videos. Structurally better posed — temporal intervals rather than a
  single video-level judgement, and "knee travels inside the foot" is geometrically checkable in
  a way "deep enough" demonstrably is not in this population. §3b also shows knee-ankle x
  displacement is the *strongest* axis in the corpus, weak as it is.

## 6. What stands regardless

- The rule is correct code: 28 tests, validated geometry (170°/50°), deterministic, no numeric
  literals, per-side gating.
- Two real bugs were found and fixed by it (scale-from-one-frame, no-descent clips).
- The metrics module reproduces the pinned v1 numbers bit-for-bit.
- The provenance gate, label-polarity resolution and split verification all hold.

The rule works. The label does not mean what the rule measures, and that was measurable before
anything was fitted to hide it.

## Status

These are **final train-split numbers**, 133 per class, from the completed extraction (711
clips, 0 errors). The partial-data run at 194 clips showed the same direction with a larger
separation (+0.0417); the full data narrows it to +0.0179 and leaves it backwards.

**Validation and test were never opened.** There is nothing to look at them for: a rule whose
fitted ceiling is 0.019 F1 above the trivial floor on train does not earn a held-out
measurement.

## Reproduce

```bash
python bench/depth_rule_calibrate.py --split train --smoke
python bench/validate_segmentation.py --split train
```
