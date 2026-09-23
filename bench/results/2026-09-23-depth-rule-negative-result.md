# The definitional parallel criterion does not match this annotation

**Date:** 2026-09-23 · **Branch:** `audit/phase2-depth-rule` · **Status:** NEGATIVE RESULT
**Data:** partial train split (133 `good_form`, 61 `depth_fault`), live-extracted keypoints

This is the outcome that was pre-declared as possible in `bench/depth_rule_calibrate.py`
before any fitting:

> An offset approaching the class separation is NOT a correction. It is a fitted threshold
> wearing a correction's name, and the honest conclusion would be that the definitional
> criterion does not match this annotator -- which is a finding, not a failure.

It is that case, and more strongly than anticipated: the class difference runs **backwards**.

## 1. The result

`AT_DEPTH ⟺ (hip_y − knee_y)/S ≥ 0`, zero fitted parameters:

```
precision(SHALLOW)   0.2381
recall(SHALLOW)      0.1020
F1(SHALLOW)          0.1429
precision(AT_DEPTH)  0.6207     <- P_target is 0.85
coverage             70.6%      (137/194, 57 abstained)
```

Class separation is **+0.0417 torso-lengths in the wrong direction**: clips labelled
`depth_fault` score *deeper* than clips labelled `good_form`.

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

## 5. Consequences

**The definitional criterion is not shippable as a depth checker against this label.** It would
be a checker that disagrees with its own ground truth in the wrong direction.

Three honest options, none of which is "fit an offset until it works":

- **Ship it as what it is.** A *parallel* checker, measuring an objective, defensible geometric
  fact, evaluated against a label that does not encode parallel. Report the disagreement as a
  property of the label rather than of the rule. This is intellectually clean but the rule then
  has no validated relationship to the product's notion of a depth fault.
- **Change the target.** If `depth_fault` is relative depth, the rule needs a per-lifter
  reference (e.g. the deepest squat that lifter achieves elsewhere), which this corpus cannot
  supply at one clip per user.
- **Abandon depth as the first rule** and pick a fault whose definition and label agree. The
  corpus also carries `error_knees_forward.json` and `error_knees_inward.json` — interval-level
  knee-valgus annotations over 1,623 videos, a different and possibly better-posed target.

## 6. What stands regardless

- The rule is correct code: 28 tests, validated geometry (170°/50°), deterministic, no numeric
  literals, per-side gating.
- Two real bugs were found and fixed by it (scale-from-one-frame, no-descent clips).
- The metrics module reproduces the pinned v1 numbers bit-for-bit.
- The provenance gate, label-polarity resolution and split verification all hold.

The rule works. The label does not mean what the rule measures, and that was measurable before
anything was fitted to hide it.

## Caveat

These are **partial-train** numbers (194 of 1137 clips); extraction was still running. The
direction is consistent across every cut tried, but the magnitudes will move. Nothing here
touched validation or test.

## Reproduce

```bash
python bench/depth_rule_calibrate.py --split train --smoke
python bench/validate_segmentation.py --split train
```
