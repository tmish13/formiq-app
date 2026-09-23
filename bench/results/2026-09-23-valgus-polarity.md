# Knee valgus: predicate stated, polarity checked, constants NOT fitted

**Date:** 2026-09-23 · **Branch:** `audit/phase2-depth-rule`
**Script:** `bench/valgus_polarity.py` · **Data:** train + validation, 413 labelled clips
**Test was not opened.**

## The predicate, written before any measurement

Valgus is the knee collapsing toward the body midline relative to the foot, so both joints are
measured against the midline rather than against each other:

```
M          = hip-midpoint x                              (body midline in the image)
inward_s   = (|ankle_x − M| − |knee_x − M|) / S          for side s
```

Positive = knee closer to the midline than the ankle = valgus. Normalised by the standing torso
length `S`, side-gated by visibility, averaged over usable sides.

**Why midline-relative rather than the literal `knee_x − ankle_x`:** that quantity's sign flips
between the left and right leg, and flips again if the subject faces the other way. Distance from
the midline is polarity-unambiguous by construction for either leg facing either direction. It is
still a knee-x-versus-ankle-x comparison, just an orientation-safe one.

## 1. Within-video: the polarity is right, and the signal is real but weak

Self-controlled — frames inside a human-marked valgus interval against frames outside it, **same
clip, same subject, same camera**. This removes every between-video confound in one step, which
eyeballing frames cannot.

| | |
|---|---|
| clips with both in/out frames | 51 |
| median delta (in − out) | **+0.0277** torso-lengths |
| clips with delta > 0 | **31/51 (60.8%)** |

**Polarity confirmed** — `inward` is higher inside the marked intervals, so the sign convention
above is correct.

### And the agreement tracks view exactly as the physics demands

| view | n | median delta | agree |
|---|---|---|---|
| front | 4 | **+0.1213** | **4/4 (100%)** |
| oblique | 38 | +0.0220 | 22/38 (58%) |
| side | 9 | +0.0064 | 5/9 (56%) |

Valgus is a frontal-plane fault: it is visible head-on and nearly invisible from the side. The
predicate agrees perfectly where the fault is visible and degrades to chance where it is not.
That ordering is strong evidence the predicate measures the intended thing — it is not the kind
of pattern noise produces.

## 2. Between-video: it does not separate positives from negatives

| formulation | positive median | negative median | AUROC |
|---|---|---|---|
| peak inward over clip | +0.0908 | +0.0842 | **0.533** |
| median inward over clip | −0.1382 | −0.1244 | **0.527** |
| peak inward at the bottom | −0.2876 | −0.2035 | **0.435** |
| **self-referenced** (bottom peak − own standing baseline) | −0.2854 | −0.2511 | **0.448** |

Self-referencing was the obvious fix — baseline knee tracking varies enormously between people
and cameras, so comparing a lifter against themselves should help. **It does not.** 0.448 is no
better than 0.435.

By view, self-referenced: front **0.762** (n_pos = **4**), oblique 0.370, side 0.601.

## 3. A methodology error I made and corrected

The first run reported a between-video AUROC of **0.178**, which would have looked like a strong
backwards signal. It was an artifact: for positive clips I took the peak *inside* the marked
interval (~40 frames), for negative clips the peak over the *whole clip* (~100 frames). A maximum
over more samples is larger by construction, so the comparison measured sample size, not
subjects. Like-for-like whole-clip statistics give **0.533**.

Recording it because the wrong number was the more interesting-looking one.

## 4. Where this leaves a valgus rule

The cross-tab does **not** support fitting constants yet, and the reason is different from depth:

- **Depth failed because the label had no geometric signal** — no axis separated the classes,
  best AUROC 0.578 out of ten tried.
- **Valgus has signal, but only where the fault is visible.** Within-video agreement is 100% in
  front view and chance in side view. The problem is that this corpus is **~5% front view**
  (24 of 457 clips in the axis survey; 4 positive examples in train + validation).

So a valgus rule is plausibly buildable and would be **honest at very low coverage** — it could
only answer for front-facing clips. On this corpus that is a handful of videos, which is not
enough to fit against, let alone validate.

## 5. What would change the answer

- **More front-view data.** The predicate's front-view behaviour (4/4 within-video, 0.762
  between) is the only encouraging cell in this report, and n = 4. That is a reason to collect,
  not a result.
- **`error_knees_forward.json`** instead: 1,109 of 1,623 videos positive (68.3%) against 232
  (14.3%) for inward. Knee-forward travel is a **sagittal**-plane fault, so it is visible from
  exactly the side views this corpus mostly contains — the opposite visibility profile, matched
  to the data we actually have. That is the next thing to check, and it is cheap: the predicate
  is `(knee_x − ankle_x)` in the sagittal direction, same machinery.

## Reproduce

```bash
python bench/valgus_polarity.py
```
