#!/usr/bin/env python3
"""Pick a stratified batch to push through the LIVE pipeline.

Gate 1: the decision trail has only ever judged 8 videos, so `eval_runner.py`
has never produced a number that means anything. This selects the batch that
turns n=8 into n~300.

THREE SELECTION RULES, EACH FOR A REASON
-----------------------------------------
1. **One representative per content hash.** 105 corpus videos are byte-identical
   duplicates (G-44). Submitting both members wastes a slot: the pipeline's
   content-hash idempotency would return the first row rather than analysing
   again, so the second submission yields no new decision.

2. **Conflicting-label groups are included but FLAGGED, not dropped.** 80
   duplicate pairs carry contradictory labels. They are legitimate input to the
   pipeline -- the rules do not read labels -- but they must not silently enter
   an accuracy calculation, so the manifest marks them and Gate 2 filters.

3. **Stratified by class, deterministic seed.** An unstratified sample of 300
   from a 36%/32%/32% corpus would still be roughly balanced, but "roughly" is
   not reproducible. seed 42, matching the original splits.

Videos with no file on disk are skipped and counted, never substituted.

    python bench/select_eval_batch.py --n 300
"""
from __future__ import annotations

import argparse
import json
import random
from collections import Counter, defaultdict
from pathlib import Path
import os
# The notebook codebase that produced PostureV1 (backend/ml_training/README.md); override with FORMIQ_ML_DIR.
FORMIQ_ML_DIR = Path(os.environ.get("FORMIQ_ML_DIR", str(Path.home() / "FORMIQ Form Analysis Model")))

REPO = Path(__file__).resolve().parent.parent
DUPS = REPO / "bench" / "results" / "corpus_duplicates.json"
SPLITS_CANDIDATES = [
    Path("/splits/user_level_multilabel_splits.json"),
    FORMIQ_ML_DIR / "data" / "squat_processed"
    / "user_level_multilabel_splits.json",
]
VIDEO_ROOTS = [
    Path("/videos"),
    Path.home() / "Desktop" / "Squat More" / "Labeled_Dataset" / "videos",
]
CLASSES = ("good_form", "posture_fault", "depth_fault")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=300)
    ap.add_argument("--remaining", action="store_true",
                    help="Gate 1b: every content-level-assigned video whose content "
                         "hash has no stored decision yet, one per hash, file on disk. "
                         "Ignores --n and stratification -- the point is coverage.")
    ap.add_argument("--judged-hashes", type=Path, default=None,
                    help="newline-separated content hashes already in checker_decisions "
                         "(exported from the DB); required with --remaining")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", type=Path,
                    default=REPO / "bench" / "results" / "eval_batch_selection.json")
    args = ap.parse_args()

    splits_path = next((p for p in SPLITS_CANDIDATES if p.exists()), None)
    if splits_path is None:
        print("splits file not found"); return 1
    video_root = next((p for p in VIDEO_ROOTS if p.exists()), None)
    if video_root is None:
        print("video directory not found"); return 1

    # --- duplicate topology ---------------------------------------------------
    groups = json.loads(DUPS.read_text())["groups"] if DUPS.exists() else {}
    hash_of, conflicting = {}, set()
    for h, members in groups.items():
        classes = {m["class"] for m in members}
        for m in members:
            hash_of[m["video"]] = h
            if len(classes) > 1:
                conflicting.add(m["video"])

    sp = json.loads(splits_path.read_text())
    by_class = defaultdict(list)
    skipped = Counter()
    seen_hash = set()
    for split in ("train", "validation", "test"):
        s = sp["splits"][split]
        for vd, tgt, name, uid in zip(s["video_data"], s["multilabel_targets"],
                                      s["video_names"], s["user_ids"]):
            if not (video_root / f"{name}.mp4").exists():
                skipped["no_file"] += 1
                continue
            h = hash_of.get(name)
            if h is not None:
                if h in seen_hash:
                    skipped["duplicate_content"] += 1
                    continue
                seen_hash.add(h)
            cls = CLASSES[list(tgt).index(1)] if sum(tgt) == 1 else None
            if cls is None:
                skipped["multi_label"] += 1
                continue
            by_class[cls].append({
                "video": name, "class": cls, "split": split,
                "user_id": str(uid),
                "label_conflict": name in conflicting,
            })

    if args.remaining:
        # Coverage, not sampling: the content-level split decides membership and
        # the decision table decides what is still missing. Duplicates collapse
        # to one representative because idempotency would return the first
        # row for the second submission anyway.
        cl = json.loads((REPO / "bench" / "results" / "content_level_splits.json").read_text())
        judged = set(args.judged_hashes.read_text().split()) if args.judged_hashes else set()
        assigned = {r["video"]: r for r in cl["videos"] if r["split"] and r["content_hash"]}
        seen_hash, picked = set(), []
        for cls in CLASSES:
            for r in by_class[cls]:
                a = assigned.get(r["video"])
                if a is None: continue
                if a["content_hash"] in judged or a["content_hash"] in seen_hash: continue
                seen_hash.add(a["content_hash"])
                picked.append({**r, "content_split": a["split"], "content_hash": a["content_hash"]})
        picked.sort(key=lambda r: r["video"])
        counts = Counter(r["class"] for r in picked); by_split = Counter(r["content_split"] for r in picked)
        print(f"REMAINING (Gate 1b): {len(picked)} videos not yet judged, one per content hash")
        for c in CLASSES: print(f"   {c:16s} {counts[c]:4d}")
        print(f"   by content-level split: {dict(by_split)}")
        print(f"   already judged (excluded): {len(judged)} hashes")
        args.out.write_text(json.dumps(picked, indent=2)); print(f"\nwrote {args.out}"); return 0

    rng = random.Random(args.seed)
    per = max(1, args.n // len(CLASSES))
    picked = []
    for cls in CLASSES:
        pool = sorted(by_class[cls], key=lambda r: r["video"])
        rng.shuffle(pool)
        picked += pool[:per]
    picked.sort(key=lambda r: r["video"])

    counts = Counter(r["class"] for r in picked)
    conflicts = sum(1 for r in picked if r["label_conflict"])
    print(f"selected {len(picked)} videos (target {args.n}, seed {args.seed})")
    for c in CLASSES:
        print(f"   {c:16s} {counts[c]:4d}   (pool {len(by_class[c])})")
    print(f"   flagged label_conflict: {conflicts}  <- excluded from Gate 2 accuracy")
    print(f"   skipped: {dict(skipped)}")

    args.out.write_text(json.dumps(picked, indent=2))
    print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
