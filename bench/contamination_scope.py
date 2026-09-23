#!/usr/bin/env python3
"""How much of each published evaluation set was actually in training.

G-44 found 105 byte-identical duplicate videos in the corpus, 45 of them
spanning splits (bench/corpus_duplicates.py). This answers the follow-up:
**which published numbers were measured on contaminated data, and how much?**

"Contaminated" here means exactly one thing: the video has a byte-identical
twin in the TRAIN split, so the model was fitted on those bytes and then scored
on them again under a different filename.

NOTHING IS RE-MEASURED. This reads the duplicate groups already computed by
bench/corpus_duplicates.py and intersects them with the evaluation populations
that were already recorded. Re-running the model after a data change is how a
negative result quietly becomes a positive one.

THE DIRECTION OF THE BIAS IS NOT UNIFORM
----------------------------------------
A twin carrying the SAME label is memorisation and inflates the score. A twin
carrying a DIFFERENT label is conflicting supervision and its effect is not
predictable. Both are reported, because "optimistically biased" is only true of
the first kind.

    python bench/contamination_scope.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List, Set

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "backend"))

DUPS = REPO / "bench" / "results" / "corpus_duplicates.json"
PINNED_SCORES = REPO / "bench" / "results" / "2026-09-19-v1-test-per-video-scores.json"
ABLATION_FIXTURES = (REPO / "backend" / "tests" / "fixtures" / "pose_data"
                     / "in_domain_accuracy" / "manifest.json")
SPLITS_CANDIDATES = [
    Path("/splits/user_level_multilabel_splits.json"),
    Path.home() / "FORMIQ Form Analysis Model" / "data" / "squat_processed"
    / "user_level_multilabel_splits.json",
]
OUT = REPO / "bench" / "results" / "contamination_scope.json"

CLASSES = ("good_form", "posture_fault", "depth_fault")
#: Fixture keys are "<video>_<label>"; strip the label to recover the video.
LABEL_SUFFIXES = ("_good_form", "_posture_fault", "_depth_fault", "_fault",
                  "_other_fault", "_messy")


def _twins() -> Dict[str, List[dict]]:
    """video_name -> the other members of its byte-identical group."""
    groups = json.loads(DUPS.read_text())["groups"]
    out: Dict[str, List[dict]] = {}
    for members in groups.values():
        for m in members:
            out[m["video"]] = [x for x in members if x["video"] != m["video"]]
    return out


def _train_twinned(names, twins) -> List[str]:
    return [n for n in names
            if any(t["split"] == "train" for t in twins.get(n, ()))]


def _strip_label(key: str) -> str:
    for s in LABEL_SUFFIXES:
        if key.endswith(s):
            return key[: -len(s)]
    return key


def main() -> int:
    twins = _twins()
    report: Dict[str, dict] = {}

    # ---- 1. the pinned re-measurement, n=224 --------------------------------
    scores = json.loads(PINNED_SCORES.read_text())
    cls_of = {r["video"]: r["class"] for r in scores["rows"]}
    hit = _train_twinned(list(cls_of), twins)
    same = diff = 0
    conflicting = []
    for n in hit:
        mine = cls_of[n] == "posture_fault"        # v1's positive class
        for t in twins[n]:
            if t["split"] != "train":
                continue
            if (t["class"] == "posture_fault") == mine:
                same += 1
            else:
                diff += 1
                conflicting.append({"video": n, "class": cls_of[n],
                                    "train_twin": t["video"],
                                    "twin_class": t["class"]})
    report["pinned_v1_224"] = {
        "what": "F1 0.6131 / AUROC 0.7184, bench/results/2026-09-19-v1-held-out-evaluation.md",
        "n": len(cls_of), "contaminated": len(hit),
        "rate": round(len(hit) / len(cls_of), 4),
        "same_label": same, "conflicting_label": diff,
        "conflicting": conflicting,
    }

    # ---- 2. the shipped manifest's binary task ------------------------------
    splits_path = next((p for p in SPLITS_CANDIDATES if p.exists()), None)
    if splits_path is not None:
        sp = json.loads(splits_path.read_text())
        test = sp["splits"]["test"]
        # The binary task excludes depth_fault videos (G-28).
        binary = [n for n, t in zip(test["video_names"], test["multilabel_targets"])
                  if CLASSES[list(t).index(1)] != "depth_fault"]
        bh = _train_twinned(binary, twins)
        report["manifest_binary"] = {
            "what": "F1 0.7237, backend/app/ml/posture_v1/artifacts/posture_v1_manifest.json",
            "n": len(binary), "contaminated": len(bh),
            "rate": round(len(bh) / len(binary), 4),
            "note": ("the manifest records test_samples 162; this reconstructs the "
                     "population as test-minus-depth_fault and gets "
                     f"{len(binary)}, so the overlap is approximate"),
        }

    # ---- 3. the face-block ablation fixtures --------------------------------
    if ABLATION_FIXTURES.exists():
        keys = list(json.loads(ABLATION_FIXTURES.read_text()))
        names = [_strip_label(k) for k in keys]
        ah = _train_twinned(names, twins)
        report["ablation_fixtures"] = {
            "what": "F1 0.7692 baseline, bench/results/2026-09-19-face-block-ablation.md",
            "n": len(names), "contaminated": len(ah),
            "rate": round(len(ah) / len(names), 4),
            "videos": sorted(ah),
            "note": ("backend/tests/unit/test_eval_split_integrity.py::"
                     "test_every_ablation_fixture_is_held_out passes on all of "
                     "these, because it checks split membership by NAME, not by "
                     "content"),
        }

    print("CONTAMINATION SCOPE -- videos with a byte-identical twin in TRAIN")
    print("=" * 72)
    for key, r in report.items():
        print(f"  {key:22s} n={r['n']:4d}  contaminated {r['contaminated']:3d}"
              f"  ({r['rate']:.1%})")
        print(f"    {r['what']}")
    p = report["pinned_v1_224"]
    print()
    print(f"  direction, pinned set: {p['same_label']} same-label "
          f"(memorisation, optimistic) / {p['conflicting_label']} conflicting "
          f"(direction unclear)")
    print()
    print("  Every count is a LOWER bound: the duplicate scan covered 1487 of")
    print("  1625 corpus entries -- 138 have no file on disk.")

    OUT.write_text(json.dumps({
        "_contamination_note": (
            "G-44: this file MEASURES the contamination rather than claiming a "
            "clean number. Every figure it names is an upper bound, not an "
            "estimate, and none is re-measured. "
            "See bench/results/2026-09-23-corpus-duplicates.md."),
        "source": "bench/results/corpus_duplicates.json",
        "definition": "has a byte-identical twin in the train split",
        "lower_bound_note": ("the duplicate scan covered 1487 of 1625 corpus "
                             "entries; 138 files were absent from disk"),
        "evaluations": report,
    }, indent=2))
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
