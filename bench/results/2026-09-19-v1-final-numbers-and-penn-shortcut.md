# v1 — corrected numbers on all 244 held-out videos, and the Penn-domain shortcut

**Date:** 2026-09-19 · **Bench only** · **Supersedes** the quotable numbers and three claims in
`2026-09-19-g28-closed-manifest-reproduces.md` (corrections listed at the bottom).
**Raw:** `2026-09-19-v1-test-per-video-scores.json`, `2026-09-19-penn-shortcut-test.json`
**Script:** `bench/penn_shortcut_test.py`

Coverage is now **244/244**: the 20 Penn Action test clips' keypoints were found in
`~/FORMIQ Form Analysis Model/data/squat_processed/keypoints/`.

## 1. Three truth definitions, one model, one threshold (0.525)

| population / truth | n | prev | floor | AUROC | F1 [95% CI] | P | R |
|---|---|---|---|---|---|---|---|
| **A.** binary task as trained (good vs posture) | 173 | 0.497 | 0.664 | 0.801* | 0.735 [0.654, 0.805] | 0.763 | 0.709 |
| **B.** all 244, 3-class-collapsed labels | 244 | 0.352 | 0.521 | 0.746* | 0.613 [0.528, 0.686] | 0.540 | 0.709 |
| **C.** all 244, **original multilabel** posture flag | 244 | 0.557 | 0.716 | 0.729* | 0.691 [0.620, 0.753] | 0.761 | 0.632 |

\* AUROC on any population containing the Penn clips is **inflated by the shortcut in §2** —
on A it rises from 0.762 (153, AQA only) to 0.801 purely by adding 20 Penn negatives the
model scores low for the wrong reason. **The clean AUROC is 0.76 (AQA-only binary task).**

**C is the honest population.** The split's labels are a 3-class collapse; each video still
carries `enhanced_labels.original_multi_label`. Of the 71 "depth_fault" test videos,
**50 carry `posture_fault: true`**. Under that truth, F1 0.691 is *below* its trivial
floor of 0.716 — at 56% prevalence, F1 cannot separate v1 from a constant classifier.

## 2. The Penn-domain shortcut — confirmed, with mechanism

All 124 Penn Action clips in the corpus are good_form (87 train / 17 val / 20 test), and
87 of 151 features are raw face coordinates that encode camera framing. So the model had
a perfect domain detector whose every training example said "good".

**Test 1 — held-out good-form clips by source domain:**

| domain | n | mean prob_fault | median | flagged ≥0.525 |
|---|---|---|---|---|
| Penn Action | 20 | **0.239** | 0.263 | **0 / 20** |
| Fitness-AQA | 67 | **0.428** | 0.451 | 19 / 67 (28%) |

**Test 2 — the same 20 Penn clips with only the face block [0:87] frozen at the training mean:**

| | mean | median | flagged |
|---|---|---|---|
| Penn, as served | 0.239 | 0.263 | 0 / 20 |
| Penn, face frozen | **0.416** | 0.461 | **6 / 20 (30%)** |

Freezing the face block shifts Penn scores by **+0.177** and lands them on the AQA
distribution (0.416 vs 0.428; 30% vs 28% flagged). Same keypoints, same temporal
features — only the face block changed. **The face block is the domain detector, and
domain is confounded with label.**

This is the face-feature hypothesis returning through the side door. The in-domain
ablation (−0.052 F1) was the wrong test: the face block barely matters *within* a
domain and matters a great deal *across* domains. It also gives the external set's
recall of 0.111 a mechanism — Penn-looking framing pulls `prob_fault` down by ~0.18
before any biomechanics is considered — beyond "never saw a Penn fault".

Caveat: n=20, one threshold. Test 2 is the control for "Penn clips are just cleaner
squats": it holds the squat fixed and moves only the face block.

## 3. Depth-fault "false positives" were mostly correct

| original multi-label | n | flagged as posture | verdict |
|---|---|---|---|
| posture + depth (incl. 2 with stability) | 50 | 25 | **true positives** — recall 0.50 |
| depth without posture | 21 | 8 | true false positives — rate 0.38 (n=21) |

The real weakness is not precision but **recall 0.50 on posture faults that co-occur
with a depth fault**, versus 0.709 on posture-only videos.

## 4. The manifest: consistent with, not reproduced

Checkpoint byte-identical, threshold 0.525, window 300 — all match. FP = 19 in both
runs is strong evidence the ranking matches. But the manifest scored **162** videos
(78 pos / 84 neg) and the binary test candidates number **173** (86 / 87); the notebook's
`_is_valid_video` rule (entry exists, keypoints exist, 10 ≤ frames ≤ 600) drops **none**
of the 173 today. **11 videos (8 pos, 3 neg) are unaccounted for** and the results JSON
stores no ids. TP 61 vs 55 is therefore not a reproduction. Wording: *consistent with*.

## What to quote

- **v1, task as trained, AQA-only: AUROC 0.76**; F1 0.73 [0.66, 0.80] vs floor 0.72 (n=153)
- **v1, all 244 with original multilabel truth:** P 0.76, R 0.63, F1 0.69 [0.62, 0.75] vs floor 0.72
- Lead with AUROC, and say which population. Never bare 0.724. Never the test-tuned 0.370.
- Never an AUROC computed on a population that includes Penn negatives without the asterisk.

## v2 spec, on solid ground

- Multilabel (or good vs *any* fault) — do not collapse co-occurring faults to one class
- Body-joint, normalised `features.py` — removes the domain detector at the source
- Penn-domain **fault** clips in training before the external 24 are used as a gate
- Threshold picked on **validation**, never test
- Gate: AUROC > 0.76 on AQA-only binary; F1 CI lower bound above the floor; and
  **domain parity** — mean `prob_fault` on good-form clips must not differ by source

## Corrections to `2026-09-19-g28-closed-manifest-reproduces.md`

1. **Floor arithmetic was wrong.** I compared the manifest's 0.7237 to a 0.7197 floor that
   belongs to the 153-video population (56% positive). The manifest's own population is
   78/162 = 48.1% positive → floor **0.650**; the manifest is **+0.074** above it, not +0.004.
   "F1 cannot separate v1 from a constant classifier" holds on the 153 run (+0.015, CI
   lower bound below the floor) and on truth C — but I mixed two populations to say it.
2. **"Reproduces" overstated it.** See §4 — *consistent with*; 11 videos unaccounted for.
3. **"v1 flags 46.5% of depth-fault squats — a production defect" is retracted.** 25 of
   those 33 flags were correct under the original labels. Precision on the honest
   population is **0.76, not 0.54**; the 0.54 is an artifact of the label collapse.
