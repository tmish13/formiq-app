# The two-checker path, carrying two rules that are not allowed to decide anything

**Date:** 2026-09-23 · **Branch:** `audit/phase2-depth-rule`
**Script:** `bench/two_checker_path.py` · **Raw:** `bench/results/two_checker_path.json`
**Data:** all 719 cached live-extracted clips. No labels are consulted, so no split is spent.

Stage A needs a rules layer to carry through the decision trail. It does not have a working
rule to carry — depth, knee valgus and knees-forward were each measured and refuted at the
video level (`2026-09-23-corpus-level-negative.md`). So the layer carries **two explicitly
unfitted checkers**, and the thing being demonstrated is that neither of them can influence
an answer.

## The two checkers

| checker | target | decisions | `fitted` | what it is |
|---|---|---|---|---|
| `depth_parallel_v0` | `depth` | `AT_DEPTH` / `SHALLOW` / `UNCERTAIN` | **false** | the definitional criterion — femur horizontal, threshold exactly 0, all view offsets 0.0 |
| `knees_forward_v0` | `knees_forward` | `OBSERVED` / `NOT_OBSERVED` / `UNCERTAIN` | **false** | knee-past-toe travel at the bottom, torso-normalised |

`knees_forward_v0` reports a **description, not a judgement**: "the knee travelled this far
past the toes", never "this is a fault". That distinction is the whole module. Its polarity
is confirmed (80.2% within-video on 268 clips, median delta +0.0785 torso-lengths) and its
video-level separation is refuted (AUROC 0.572 against a 68.3% prevalence whose all-positive
trivial floor is **F1 0.812**). Both numbers are in the params file and in
`detail.validated` on **every** decision row, so the limit travels with the evidence rather
than living in a results file nobody opens.

## What the checkers said

Before the combiner — this is the rules layer's own output:

| | answered | breakdown |
|---|---|---|
| **depth** | **507 / 719 = 70.5%** | `AT_DEPTH` 430 (59.8%) · `SHALLOW` 77 (10.7%) · abstain `near_parallel` 143 (19.9%) · `bad_scale` 47 (6.5%) · `no_bottom` 16 (2.2%) · `low_coverage` 6 (0.8%) |
| **knees_forward** | **505 / 719 = 70.2%** | `OBSERVED` 322 (44.8%) · `NOT_OBSERVED` 183 (25.5%) · abstain `low_coverage` 97 (13.5%) · `no_bottom` 70 (9.7%) · `bad_scale` 47 (6.5%) |

Coverage of ~70% on both, from independent abstain reasons, is the headline the plan asked
for. The largest single depth abstention is `near_parallel` (19.9%) — declining calls within
0.08 of parallel, which is exactly where the two pose passes disagreed in the Stage 0b
provenance gate and where a human would also decline.

Knee travel at the bottom: median **+0.0866** torso-lengths, p1 −0.271, p99 +0.472.

## What the combiner did with it

| | |
|---|---|
| checker outcomes | 1438 (2 × 719) |
| advisory outcomes **recorded as evidence** | **1012** |
| outcomes that **set a verdict** | **0** |
| clips given a **combined score** | **0** |
| final verdicts | `depth` UNCERTAIN ×719 · `knees_forward` UNCERTAIN ×719 |

**Every single answer was recorded and none of them counted.** That is the correct outcome
and the script exits non-zero if it ever changes.

The mechanism: `CheckerOutcome.is_authoritative` requires `is_answer AND fitted AND NOT
advisory`. Two independent conditions, so clearing one flag cannot promote a rule. An
advisory outcome lands in `advisory` and `evidence`, and in `exclusions` with the reason
`advisory_unfitted` — distinguishable from `abstained`, `error`, `skipped` and `no_score`,
because "the rule declined" and "the rule is not trusted" are different facts about a run.

## A defect this surfaced, and one it did not fix

**Found and fixed:** three constants shared with `depth_v1.json` — `view_side_max`,
`view_front_min`, `max_window_seconds` — were hand-written rather than copied, despite the
params file's own note claiming they were identical. The wrong cut points classified **59%
of clips as front view** against a measured corpus rate of ~5%, and since the front-view
weight is 0.3 and the coverage floor is 0.35, that abstained the checker on most of the
corpus *by construction*. A test now compares all 15 shared keys, so the note is enforced
rather than asserted. This is why the params note and the test have to be the same object.

**Found, not fixed:** the knee-travel distribution has a physically implausible tail —
20 of 602 clips (3.3%) exceed 0.4 torso-lengths and **4 exceed 1.0**, which would put the
knee a full torso-length past the toes. These pass the coverage gate, so the gate is not
catching whatever is wrong (most likely a degenerate scale reference or a mislocated foot
landmark). Recorded rather than clipped: silently winsorising would hide the defect, and the
value is advisory anyway, so nothing downstream is at risk from it today. It needs its own
look before this checker is ever promoted.

## What this does and does not establish

**Establishes:** a named checker's answer, its evidence, its abstain reason and its fitted
status flow from `app/rules` through `combiner_v1` intact, and the advisory guarantee holds
on 1012 real outcomes rather than on a unit test's fixtures.

**Does not establish:** that either rule is any good. Both are unfitted, one is refuted, and
neither is permitted to affect a user-visible field. `depth_score` stays NULL.

## Reproduce

```bash
python bench/two_checker_path.py     # exits non-zero if an unfitted checker ever counts
pytest -q backend/tests/unit/test_combiner.py backend/tests/unit/test_knees_forward.py
```
