#!/usr/bin/env python3
"""Evaluate stored decisions against stored labels. Nothing is recomputed.

This is the last link in the pipeline: queue -> checkers -> decision + audit ->
labels -> eval. Everything it reads was written by the live path, so it
measures what the system ACTUALLY DID rather than what a script can reproduce
by running the model again. A number computed by re-running the model tells you
about the model; a number computed from `checker_decisions` tells you about the
deployment, and the 14.9% pose-pass flip rate is why those are different
questions.

The join key is `content_hash`, never `form_check_id` -- a label is a statement
about bytes and must survive re-analysis (app/models/labels.py).

REPORTING RULES, NOT OPTIONS
----------------------------
  * coverage ALWAYS, with both views. A checker that declines whenever it is
    unsure looks excellent on the videos it answered; an unanswered video is an
    unflagged video, so `abstain_as_negative` is what a user experiences.
  * the trivial floor ALWAYS. At this corpus's prevalence an all-positive
    classifier scores F1 0.81 on knees-forward, and F1 quoted without the floor
    is how that gets missed.
  * `fitted=false` checkers are reported SEPARATELY and never mixed into a
    headline. They are advisory by construction (combiner_v1) and their numbers
    are descriptive, not performance.
  * disputed labels are counted and reported. 80 corpus videos are
    byte-identical duplicates carrying conflicting labels; an evaluation that
    silently picks one is reporting its own tie-break.
  * `--splits content` uses the content-level splits (G-44/G-45), where no
    byte-identical file spans a split and contradictory duplicates are withheld
    entirely. `--splits user` reproduces the historical, contaminated basis.
    Whichever is used is printed in the header, because a number quoted without
    saying which split it came from is not a number.

    python backend/scripts/eval_runner.py --target posture
    python backend/scripts/eval_runner.py --target depth --checker depth_parallel_v0
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

CONTENT_SPLITS = BACKEND.parent / "bench" / "results" / "content_level_splits.json"

#: Decision strings that mean "this checker said fault/positive", per target.
POSITIVE_DECISIONS = {
    "posture": {"FAULT"},
    "depth": {"SHALLOW"},              # the fault IS being shallow
    "knees_forward": {"OBSERVED"},
}
#: Which label target a checker's verdict should be scored against.
CHECKER_LABEL_TARGET = {
    "posture": "posture_fault",
    "depth": "depth_fault",
    "knees_forward": "depth_fault",    # no knees_forward label exists; see below
}
ABSTAIN = "UNCERTAIN"


async def _load(target: str, checker: Optional[str], split: Optional[str]) -> Dict:
    import sqlalchemy as sa

    from app.core.database import get_async_session_for_celery
    from app.models.audit import AnalysisRun, CheckerDecision
    from app.models.labels import Label

    async with get_async_session_for_celery() as session:
        q = sa.select(CheckerDecision).where(CheckerDecision.target == target)
        if checker:
            q = q.where(CheckerDecision.checker_name == checker)
        decisions = (await session.execute(q)).scalars().all()

        label_target = CHECKER_LABEL_TARGET.get(target, target)
        lq = sa.select(Label).where(Label.target == label_target)
        if split:
            lq = lq.where(Label.split == split)
        labels = (await session.execute(lq)).scalars().all()

        runs = {r.id: r for r in (await session.execute(
            sa.select(AnalysisRun))).scalars().all()}
    return {"decisions": decisions, "labels": labels, "runs": runs,
            "label_target": label_target}


def main() -> int:
    from app.eval.labels import resolve_all, to_binary_arrays
    from app.eval.metrics import auroc, coverage_metrics, summarize, trivial_floor

    ap = argparse.ArgumentParser()
    ap.add_argument("--target", required=True,
                    choices=sorted(POSITIVE_DECISIONS))
    ap.add_argument("--checker", default=None)
    ap.add_argument("--split", default=None,
                    choices=["train", "validation", "test"])
    ap.add_argument("--splits", default="content", choices=["content", "user"],
                    help="content: leakage-free by hash AND user (G-44/G-45). "
                         "user: the historical, contaminated basis.")
    ap.add_argument("--include-conflicted", action="store_true",
                    help="include videos whose duplicates carry contradictory "
                         "labels; off by default because scoring them reports "
                         "this script's tie-break, not the model")
    ap.add_argument("--json", type=Path, default=None)
    args = ap.parse_args()

    # Content-level basis: restrict to videos the repaired split assigns, and
    # drop the ones it withholds. Applied to the DECISIONS as well as the
    # labels, so a video absent from the repaired split cannot enter by either
    # door.
    allowed = None
    basis = args.splits
    if args.splits == "content":
        if not CONTENT_SPLITS.exists():
            print(f"content-level splits not found at {CONTENT_SPLITS}; "
                  "run bench/build_content_splits.py", file=sys.stderr)
            return 1
        built = json.loads(CONTENT_SPLITS.read_text())
        allowed = set()
        withheld = 0
        for r in built["videos"]:
            if not r["split"]:
                withheld += 1
                continue
            if args.split and r["split"] != args.split:
                continue
            if r["content_hash"]:
                allowed.add(r["content_hash"])
        print(f"basis: CONTENT-LEVEL splits (mode {built.get('mode')}), "
              f"{withheld} videos withheld as contradictory duplicates")
        # Videos with no recorded hash cannot be matched to a decision anyway.
    else:
        print("basis: USER-LEVEL splits -- the historical, CONTAMINATED basis "
              "(G-44). Numbers from this are upper bounds.")

    data = asyncio.run(_load(args.target, args.checker,
                             args.split if args.splits == "user" else None))
    decisions, labels = data["decisions"], data["labels"]
    label_target = data["label_target"]

    print(f"target {args.target!r}  scored against label target "
          f"{label_target!r}" + (f"  split={args.split}" if args.split else ""))
    if args.target == "knees_forward":
        print("  NOTE: this corpus carries no video-level knees_forward label.")
        print("  The predicate's video-level separation was measured at AUROC")
        print("  0.572 against a trivial floor of F1 0.812 and REFUTED; the")
        print("  number below is a cross-tab, not a performance claim.")
    print(f"decisions {len(decisions)}   labels {len(labels)}")

    if not decisions:
        print("\nno stored decisions for this target yet -- run some analyses first.")
        return 0

    if allowed is not None:
        before_d, before_l = len(decisions), len(labels)
        decisions = [d for d in decisions if d.content_hash in allowed]
        labels = [l for l in labels if l.content_hash in allowed]
        print(f"  content-level filter: decisions {before_d} -> {len(decisions)}, "
              f"labels {before_l} -> {len(labels)}")

    resolved = resolve_all(labels, label_target)
    if not args.include_conflicted:
        dropped = [h for h, r in resolved.items() if r.disputed]
        for h in dropped:
            resolved.pop(h)
        if dropped:
            print(f"  excluded {len(dropped)} video(s) whose sources disagree "
                  f"(use --include-conflicted to score them)")

    disputed = [h for h, r in resolved.items() if r.disputed]
    unusable = [h for h, r in resolved.items() if not r.usable]
    print(f"labelled videos {len(resolved)}   disputed {len(disputed)}   "
          f"unusable {len(unusable)}")

    out: Dict[str, Any] = {"target": args.target, "label_target": label_target,
                           "basis": basis,
                           "conflicted_included": args.include_conflicted,
                           "split": args.split, "n_decisions": len(decisions),
                           "n_labelled": len(resolved),
                           "n_disputed": len(disputed), "checkers": {}}

    by_checker: Dict[str, List[Any]] = {}
    for d in decisions:
        by_checker.setdefault(d.checker_name, []).append(d)

    positives = POSITIVE_DECISIONS[args.target]
    for name, rows in sorted(by_checker.items()):
        fitted = bool(rows[0].fitted)
        advisory = bool(rows[0].advisory)
        preds: Dict[str, Any] = {}
        for d in rows:
            if not d.content_hash:
                continue
            preds[d.content_hash] = (
                ABSTAIN if (d.abstained or d.decision == ABSTAIN)
                else (1 if d.decision in positives else 0))

        y, p, hashes = to_binary_arrays(resolved, preds)
        banner = ("FITTED" if fitted else "UNFITTED") + \
                 (" / advisory" if advisory else " / authoritative")
        print()
        print("=" * 72)
        print(f"{name}   [{banner}]   matched {len(y)} labelled videos")
        print("=" * 72)
        if not y:
            print("  no overlap between stored decisions and stored labels.")
            out["checkers"][name] = {"fitted": fitted, "advisory": advisory,
                                     "n": 0}
            continue

        cov = coverage_metrics(y, p, abstain_value=ABSTAIN)
        floor = trivial_floor(y)
        print(f"  coverage            {cov['coverage']:.3f}  "
              f"({cov['n_covered']}/{cov['n']} answered)")
        co = cov["covered_only"]
        if co["n"]:
            print(f"  covered-only        P {co['precision']:.4f}  "
                  f"R {co['recall']:.4f}  F1 {co['f1']:.4f}")
        an = cov["abstain_as_negative"]
        print(f"  abstain-as-negative P {an['precision']:.4f}  "
              f"R {an['recall']:.4f}  F1 {an['f1']:.4f}")
        print(f"  trivial floor       F1 {floor['all_positive_f1']:.4f}   "
              f"prevalence {floor['prevalence']:.3f}")
        if not fitted:
            print("  -> UNFITTED: descriptive only. These constants were never")
            print("     selected against data and the combiner treats this")
            print("     checker as advisory. Not a performance claim.")
        out["checkers"][name] = {"fitted": fitted, "advisory": advisory,
                                 "n": len(y), "coverage": cov,
                                 "trivial_floor": floor}

    if disputed:
        print()
        print(f"NOTE: {len(disputed)} of the labelled videos are DISPUTED -- "
              "more than one")
        print("source answered and they disagree. The resolution is by trust, "
              "then")
        print("timestamp, then source_ref. See bench/results/"
              "2026-09-23-corpus-duplicates.md.")

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(out, indent=2, default=str))
        print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
