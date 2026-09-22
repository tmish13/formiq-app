# Stage 0 GATE — what `labels_shallow_depth.json` actually means

**Date:** 2026-09-22 · **Branch:** `audit/phase2-depth-rule`
**Script:** `bench/label_polarity_probe.py` · **Status:** RESOLVED — and the naive reading was wrong

## The question

`labels_shallow_depth.json` (3,611 frames, 623 videos) reads as `1 = shallow = fault`. A
600-frame probe said the opposite: label-1 frames were geometrically *deeper*. Fitting on either
reading without resolving it produces a rule that is inverted and still scores well.

## Result

**`label 1` = a human-marked depth-fault *instant*, which is the bottom of a rep in a
shallow-squat video.**
**`label 0` = "not a marked instant"** — overwhelmingly frames from *other phases of the rep*.

Three independent routes, and their disagreement is what gave the answer.

### Route A — overlap with `depth_frames` (decisive)

`depth_frames` in the splits file records, per video, the timestamps where a human saw the depth
fault. They are frame indices ÷ 30 (verified: `1.2666… × 30 = 38.0` exactly).

```
videos with overlap : 469
frames matched      : 1552
...carrying label 1 : 1552  (100.0%)
...carrying label 0 :    0  (  0.0%)

base rate of label 1: 43.9%
lift on fault frames: +56.1%
```

**100.0%, not merely enriched.** The label-1 set *is* the `depth_frames` set. These are the same
annotation surfaced twice.

### Route B — per-video rate of label-1 frames, by video class

| video class | videos | mean rate of label-1 frames |
|---|---|---|
| `good_form` | 42 | **0.000** |
| `posture_fault` | 87 | **0.000** |
| `depth_fault` | 469 | 0.570 |

Label-1 frames exist **only** in `depth_fault` videos. 409 of 623 videos (66%) carry mixed
labels, so this is a genuine per-frame annotation, not a video label copied down.

### Route C — geometry on all 1,106 usable labelled train frames

| indicator | label 1 | label 0 | Cohen d | deeper = |
|---|---|---|---|---|
| `(hip_y − knee_y) / torso` | **0.005** | −0.319 | +1.75 | larger |
| knee flexion (deg) | **70.8** | 116.6 | −1.67 | smaller |

Label-1 frames are unambiguously **deeper**. Which contradicts A and B — until you ask *deeper
than what*.

### Resolving the contradiction

Depth-percentile of each labelled frame **within its own video** (1.0 = that video's deepest
frame):

| video class | label | n | mean | median |
|---|---|---|---|---|
| `depth_fault` | **1** | 1513 | **0.924** | **0.964** |
| `depth_fault` | 0 | 1155 | 0.673 | 0.681 |
| `good_form` | 0 | 221 | 0.775 | 0.852 |
| `posture_fault` | 0 | 486 | 0.623 | 0.621 |

Label-1 frames sit at the **bottom of the rep** (median 0.964). Label-0 frames are scattered
through the movement (0.62–0.78).

Visual confirmation, two sampled crops:
- `label1_32903_8_44.jpg` — lifter at the **bottom** of a back squat, hips near knee level.
- `label0_32907_3_75.jpg` — lifter **mid-rep**, hips well above knees.

## Why this matters more than the polarity itself

**A frame classifier trained on `label 1 vs label 0` learns "is this the bottom of a rep",
not "is this rep deep enough."**

Route C's |d| = 1.75 is a *rep-phase* signal, not a depth signal. It would have produced a
confident, well-scoring, completely wrong checker — a phase detector wearing a depth checker's
name. The 0.90-correlation provenance gate would have passed it. The held-out F1 would have
looked good. Nothing downstream would have caught it.

`label 0` does **not** mean "at depth". It means "not a marked instant", and most label-0 frames
are simply not at the bottom.

## Corrected formulation — bottom vs bottom

The positive class is sound; the negative class has to be **constructed**, not taken from
label 0:

- **Positives** — the marked shallow bottoms (label-1 frames).
- **Negatives** — the bottom frames of `good_form` videos, derived by the same rep segmentation
  the rule already needs. These are bottoms that *were* deep enough.

| split | POS: marked shallow bottoms | from videos | NEG pool: `good_form` videos | `posture_fault` (noisy neg) |
|---|---|---|---|---|
| train | 1,115 | 328 | 404 | 405 |
| validation | 215 | 70 | 87 | 87 |
| test | 222 | 71 | 87 | 86 |

`posture_fault` videos are depth-negatives by the disjoint-label scheme, but they were classified
by their *primary* fault and some are certainly also shallow. Use `good_form` as the clean
negative class; treat `posture_fault` as a secondary noisy negative and report it separately.

This is a strictly better target than the original plan: a **bottom-vs-bottom depth contrast**,
which is the question the rule is actually meant to answer.

**Consequence for segmentation:** it moves from a supporting detail to a **load-bearing
dependency** — the negative class does not exist until reps are segmented. The `depth_frames` IoU
check (planned) now validates the mechanism that *generates the training data*, not just the one
that generates the verdict, so it must run before Tier-1 fitting rather than alongside it.

## `P_target` — the class is now nameable

`P_target = 0.85` is a precision floor on **`AT_DEPTH`**: of the reps the rule calls deep enough,
85% must actually be deep enough. In label terms that is precision on the **negative** class of
this dataset (`good_form` bottoms), because the dataset's positives are the *faults*.

⚠️ Worth confirming: at these class sizes `AT_DEPTH` is roughly the minority class among
*bottoms* (1,115 shallow bottoms vs ~404 good_form videos' bottoms in train), so 0.85 precision
on `AT_DEPTH` is a genuinely demanding target, not a freebie. Flagging because the earlier
concern — that 0.85 might be trivially easy on a majority class — does not apply once the class
is named correctly.

## Written into the artifact

`app/rules/params/depth_v1.json` will carry:

```json
"label_semantics": {
  "source": "Shallow_Squat_Error_Dataset/labels_shallow_depth.json",
  "label_1": "human-marked depth-fault instant == bottom frame of a rep that was too shallow",
  "label_0": "not a marked instant; mostly non-bottom frames. NOT a synonym for at-depth",
  "identity_with_depth_frames": "1552/1552 (100.0%)",
  "positive_class": "SHALLOW",
  "negative_class_construction": "bottom frames of good_form videos, via rep segmentation",
  "p_target_class": "AT_DEPTH",
  "resolved_by": "bench/results/2026-09-22-label-polarity.md"
}
```

## Reproduce

```bash
python bench/label_polarity_probe.py --crops-out /tmp/polarity_crops
```
