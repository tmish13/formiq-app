# Three faults, three failures to separate at the video level

**Date:** 2026-09-23 · **Branch:** `audit/phase2-depth-rule`
**Data:** train + validation, live-extracted keypoints. **Test was never opened.**

Three fault candidates were taken through the same discipline — predicate written first,
polarity checked before any constant was fitted, view-stratified, like-for-like windows. All
three fail at the video level, and **they fail for three different reasons**, which is the
useful part.

## The three results

| fault | within-video agreement | between-video AUROC | prevalence | trivial floor F1 |
|---|---|---|---|---|
| depth | — (no interval labels) | **0.578** best of 10 axes | 32.7% | 0.492 |
| knees inward (valgus) | 31/51 = **60.8%** | 0.533 / 0.448 | 14.3% | 0.250 |
| **knees forward** | **215/268 = 80.2%** | **0.572** | **68.3%** | **0.812** |

### depth — no signal anywhere

Ten axes tried (knee flexion, hip-knee delta, femur incline, hip drop, trunk lean, tempo, clip
length, scale, …). **Nothing reached |AUROC − 0.5| ≥ 0.10.** Knee-flexion distributions overlap
almost completely across all three classes — medians within 4°, p10s within 1° — and the 90th
percentile of every class is still below parallel. The corpus contains no shallow subpopulation,
so the `depth_fault` label does not encode anything recoverable from these keypoints.
Full detail: `2026-09-23-depth-rule-negative-result.md`.

### knees inward — real signal, wrong corpus

Polarity confirmed, and agreement tracked view exactly as the physics demands: **front 4/4
(100%)**, oblique 58%, side 56%. Valgus is a frontal-plane fault and the predicate agreed
perfectly where it is visible, at chance where it is not. That ordering is not what noise
produces.

But this corpus is **~5% front view**, leaving **4 positive front-view clips** in train +
validation. The rule is plausibly right and there is nothing to fit it on.
Full detail: `2026-09-23-valgus-polarity.md`.

### knees forward — strong temporal signal, no video-level separation

The best of the three, and the failure is the most interesting.

**Within-video, self-controlled:** 215/268 clips (**80.2%**) show more knee-past-toe travel
inside the human-marked interval than outside it, median delta **+0.0785** torso-lengths. On
5× the sample of valgus and 20 points higher.

By view: oblique 166/198 (**84%**), front 12/17 (71%), side 37/53 (70%).

> Worth recording: I predicted side view would be best, since knee-forward is a sagittal-plane
> fault. Oblique won. The prediction was wrong in detail — though the practical point held, which
> is that this fault is visible in the views this corpus actually has, unlike valgus.

**Between-video:** AUROC **0.572** (peak) / 0.519 (median). Prevalence is **68.3%**, so a
classifier that calls every squat positive scores **F1 0.812**. A video-level rule at 0.572
cannot beat that in any useful way.

### And part of the depth ceiling is irreducible

*Added 2026-09-23, after G-44.* The corpus holds 105 byte-identical duplicate videos under
different names, and **47 pairs carry both `depth_fault` and `good_form`** — same file, same
pixels, opposite labels. **No function of the pixels can separate classes when the same
pixels sit in both.** For those pairs even a perfect rule is wrong half the time, so the
AUROC 0.578 ceiling above is partly a property of the labels rather than of the geometry.
Scope honestly: 94 videos against 1,625 does not explain the whole ceiling, but it is the
first *measured* evidence that any of it is irreducible rather than merely unmodelled. The
numbers here are **not** re-measured on a de-duplicated corpus — that would improve them for
a reason unrelated to the rule. See `2026-09-23-corpus-duplicates.md`.

## The pattern, stated once

**The predicate knows WHEN the fault happens. It does not know WHICH clips have it.**

That is the same shape in valgus (60.8% within, 0.533 between) and knees-forward (80.2% within,
0.572 between), and it has a physical explanation: nearly every squat contains some knee-forward
travel and some knee deviation. The annotator marks the moments where it becomes *excessive* —
a judgement about degree, against a standard that is not in the geometry. The between-video
difference is small because everyone does it somewhat.

This is why the within/between gap is not a defect to engineer around. A video-level threshold
asks "does this lifter do the thing", and the answer is almost always yes.

## What this does and does not rule out

**Ruled out:** a video-level, geometrically-thresholded checker for any of the three faults,
validated against these labels. Three predicates, three failures, three distinct causes.

**Not ruled out:** temporal localisation. An 80.2% within-video hit rate on knees-forward is a
real capability — "your knees travelled forward at 1.4s" — and it is what the interval labels
actually describe. It cannot be validated against a video-level label because it is not a
video-level claim.

**Not ruled out:** that a different corpus would work. Valgus in particular needs front-view
footage, and the predicate's behaviour on the 4 front-view positives is the one encouraging cell
in this whole exercise. That is a reason to collect data, not a result.

## Consequence

Stop fitting fault rules against this corpus. Move to Stage A — the decision/audit schema — and
carry a **minimal, explicitly unfitted** rules layer through it: two hand-set predicates, labelled
`fitted: false`, whose purpose is to prove the two-checker path end to end (run row → per-checker
decisions → combiner → result row), **not** to produce a verdict anyone relies on.

The value of Phase 2 is not a shipped depth rule. It is that three plausible rules were killed
by measurement in a day, each with a reproducible number and a distinct reason, before any of
them reached a user.

## Reproduce

```bash
python bench/corpus_axes.py
python bench/valgus_polarity.py
python bench/knees_forward_polarity.py
```
