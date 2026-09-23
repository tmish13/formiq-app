"""The defect every published performance number in this repo carries.

G-44: 105 of the 1,487 corpus videos are byte-identical duplicates filed under
different names, 45 of them spanning splits. Every evaluation set was therefore
partly seen during training, because the split was partitioned by user id and
the duplicates are filed under different user ids.

THE NUMBERS ARE NOT RE-MEASURED, AND WILL NOT BE.
Re-measuring after a data change is how a negative result quietly becomes a
positive one. The published figures stand, with this caveat attached, as upper
bounds rather than estimates.

WHY A CONSTANT AND NOT A SENTENCE IN EACH FILE
-----------------------------------------------
The caveat has to appear in roughly twenty places. Retyping it twenty times is
how twenty slightly different caveats appear, and then how one of them is
dropped. `tests/unit/test_contamination_caveat.py` scans the repo and fails if
any file quotes one of these figures without also naming G-44, which makes
quoting a number clean a build failure rather than an oversight.

Scope is bounded by `bench/contamination_scope.py`, which reads the duplicate
groups and intersects them with each recorded evaluation population.
"""
from __future__ import annotations

from typing import Dict

__all__ = [
    "CONTAMINATION_CAVEAT_ID",
    "CONTAMINATION_CAVEAT",
    "CONTAMINATION_CAVEAT_SHORT",
    "CONTAMINATED_EVALUATIONS",
    "CONTAMINATED_FIGURES",
]

#: The token every file quoting a contaminated figure must also contain.
CONTAMINATION_CAVEAT_ID = "G-44"

CONTAMINATION_CAVEAT = (
    "G-44: measured before 45 cross-split byte-identical duplicates were found. "
    "27 of these 224 videos (12.0%) have a byte-identical twin in the TRAIN "
    "split -- 19 share the posture_fault label (memorisation, optimistic) and 8 "
    "carry a conflicting label (direction unclear), so the bias is "
    "predominantly but not purely optimistic. The duplicate scan covered 1,487 "
    "of 1,625 corpus entries, so 27 is a LOWER bound. Treat this as an upper "
    "bound on true performance, not an estimate. Not re-measured, by choice: "
    "re-measuring after a data change is how a negative becomes a positive. "
    "See bench/results/2026-09-23-corpus-duplicates.md."
)

#: For places with no room for the full paragraph (JSON fields, table cells).
CONTAMINATION_CAVEAT_SHORT = (
    "G-44: upper bound, not an estimate -- 12.0% of this evaluation set has a "
    "byte-identical twin in train. Not re-measured. "
    "See bench/results/2026-09-23-corpus-duplicates.md."
)

#: population key -> what it measures, n, contaminated, rate.
#: Reproduced by `python bench/contamination_scope.py`.
CONTAMINATED_EVALUATIONS: Dict[str, Dict[str, object]] = {
    "pinned_v1_224": {
        "what": "F1 0.6131, CI [0.5291, 0.6872], AUROC 0.7184",
        "where": "bench/results/2026-09-19-v1-held-out-evaluation.md",
        "n": 224, "contaminated": 27, "rate": 0.1205,
        "same_label": 19, "conflicting_label": 8,
    },
    "manifest_binary": {
        "what": "F1 0.7237 (shipped manifest's own test metric)",
        "where": "backend/app/ml/posture_v1/artifacts/posture_v1_manifest.json",
        "n": 173, "contaminated": 18, "rate": 0.1040,
        "note": "the manifest records test_samples 162; 173 is the reconstructed "
                "test-minus-depth_fault population, so the overlap is approximate",
    },
    "ablation_fixtures": {
        "what": "F1 0.7692 baseline (already retracted for a separate reason, G-25)",
        "where": "bench/results/2026-09-19-face-block-ablation.md",
        "n": 50, "contaminated": 7, "rate": 0.1400,
        "note": "test_eval_split_integrity.py::test_every_ablation_fixture_is_"
                "held_out passes on all seven, because it checks split "
                "membership by NAME rather than by content (G-45)",
    },
}

#: Figures that may not appear anywhere without `CONTAMINATION_CAVEAT_ID`
#: alongside them. Enforced by tests/unit/test_contamination_caveat.py.
CONTAMINATED_FIGURES = (
    "0.6131",   # pinned F1
    "0.7184",   # pinned AUROC
    "0.7237",   # shipped manifest test F1
    "0.7692",   # ablation baseline F1
    "0.5548",   # the floor the pinned F1 is read against
    "0.3839",   # the prevalence that floor comes from
)
