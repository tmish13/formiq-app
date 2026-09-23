#!/usr/bin/env python3
"""Splits that are leakage-free at the CONTENT level, not just by user id.

G-44/G-45: the shipped splits are user-level and were believed leakage-free.
They are leakage-free BY USER ID and not by content -- 105 corpus videos are
byte-identical duplicates filed under different names, 45 of them spanning
splits and 104 filed under different user ids. Partitioning by user id cannot
see that, because the two copies belong to two different users.

THE SPLIT UNIT IS A CONNECTED COMPONENT, NOT A USER
----------------------------------------------------
Two constraints have to hold at once:

  * every video sharing a content hash lands in the same split -- they are the
    same file, so splitting them IS the leak;
  * every video of a user lands in the same split -- the original subject-level
    guarantee, which is still worth having.

Those constraints chain. User A's video is byte-identical to user B's, so A and
B must share a split; B has another video identical to user C's, so C joins
too. The correct unit is therefore a connected component of the graph linking
videos that share a hash OR share a user, found by union-find. Assigning by
user alone re-creates the bug; assigning by hash alone throws away the subject
guarantee.

WHAT HAPPENS TO CONTRADICTORY LABELS
-------------------------------------
80 duplicate groups carry conflicting labels -- the same bytes called
`good_form` under one name and a fault under another. A representative cannot
be chosen without inventing an answer, so those groups are marked
`usable: false` and land in NO split. They are recorded, not deleted: they are
the cheapest labelling work available (80 second opinions), and dropping them
silently would hide that.

TWO MODES, AND `minimal` IS THE DEFAULT FOR A REASON
-----------------------------------------------------
`repartition` rebuilds the split from scratch. It is clean and it moves 46% of
the corpus, which means a before/after comparison against any historical number
is confounded by the population changing, not only by de-duplication.

`minimal` keeps every video where it already was and moves only what MUST move
to satisfy the constraints: each component takes the split held by the plurality
of its members, ties broken toward the smaller split. The population barely
changes, so a delta measured across it is attributable to the repair -- the
same reason the pose-pass comparison was paired rather than sampled twice.

NOTHING IS RE-MEASURED HERE. This builds the instrument. Re-running a model
against these splits is a separate, deliberate act.

    python bench/build_content_splits.py
"""
from __future__ import annotations

import argparse
import json
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List

REPO = Path(__file__).resolve().parent.parent
DUPS = REPO / "bench" / "results" / "corpus_duplicates.json"
SPLITS_CANDIDATES = [
    Path("/splits/user_level_multilabel_splits.json"),
    Path.home() / "FORMIQ Form Analysis Model" / "data" / "squat_processed"
    / "user_level_multilabel_splits.json",
]
CLASSES = ("good_form", "posture_fault", "depth_fault")
RATIOS = {"train": 0.70, "validation": 0.15, "test": 0.15}


class Union:
    """Union-find over video names."""

    def __init__(self):
        self.parent: Dict[str, str] = {}

    def find(self, x: str) -> str:
        self.parent.setdefault(x, x)
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--mode", choices=("minimal", "repartition"),
                    default="minimal",
                    help="minimal: keep videos where they are, move only what "
                         "must move (preserves comparability). repartition: "
                         "rebuild from scratch (clean ratios, ~46%% moves).")
    ap.add_argument("--out", type=Path,
                    default=REPO / "bench" / "results" / "content_level_splits.json")
    args = ap.parse_args()

    splits_path = next((p for p in SPLITS_CANDIDATES if p.exists()), None)
    if splits_path is None:
        print("splits file not found"); return 1

    sp = json.loads(splits_path.read_text())
    groups = json.loads(DUPS.read_text())["groups"] if DUPS.exists() else {}

    # ---- every video, with its user, class and original split ----------------
    videos: Dict[str, dict] = {}
    for split in ("train", "validation", "test"):
        s = sp["splits"][split]
        for tgt, name, uid in zip(s["multilabel_targets"], s["video_names"],
                                  s["user_ids"]):
            cls = CLASSES[list(tgt).index(1)] if sum(tgt) == 1 else None
            videos[name] = {"video": name, "user_id": str(uid), "class": cls,
                            "original_split": split}

    hash_of: Dict[str, str] = {}
    conflicted: set = set()
    for h, members in groups.items():
        classes = {m["class"] for m in members}
        for m in members:
            hash_of[m["video"]] = h
            if len(classes) > 1:
                conflicted.add(m["video"])

    # ---- components: linked by shared hash OR shared user --------------------
    uf = Union()
    for name in videos:
        uf.find(name)
    for bucket in (defaultdict(list), defaultdict(list)):
        pass
    by_hash, by_user = defaultdict(list), defaultdict(list)
    for name, v in videos.items():
        by_user[v["user_id"]].append(name)
        h = hash_of.get(name)
        if h:
            by_hash[h].append(name)
    for members in list(by_hash.values()) + list(by_user.values()):
        for other in members[1:]:
            uf.union(members[0], other)

    comps: Dict[str, List[str]] = defaultdict(list)
    for name in videos:
        comps[uf.find(name)].append(name)

    # ---- drop contradictory groups entirely ----------------------------------
    usable_comps, dropped_comps = {}, {}
    for root, members in comps.items():
        if any(m in conflicted for m in members):
            dropped_comps[root] = members
        else:
            usable_comps[root] = members

    # ---- assign whole components --------------------------------------------
    rng = random.Random(args.seed)
    order = sorted(usable_comps.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    rng.shuffle(order)
    order.sort(key=lambda kv: -len(kv[1]))      # big components placed first

    assigned: Dict[str, str] = {}
    sizes = Counter()
    total = sum(len(m) for _, m in order)

    if args.mode == "minimal":
        # Each component keeps the split its members already had. Only genuine
        # conflicts move, and they move to the plurality choice -- ties broken
        # toward the split that is currently smallest, so the ratios do not
        # drift further than the repair requires.
        for _, members in order:
            votes = Counter(videos[m]["original_split"] for m in members)
            top = max(votes.values())
            candidates = sorted(s for s, v in votes.items() if v == top)
            target = min(candidates, key=lambda s: (sizes[s], s))
            for m in members:
                assigned[m] = target
            sizes[target] += len(members)
    else:
        for _, members in order:
            # the split furthest below its target share takes the component
            target = min(RATIOS,
                         key=lambda s: (sizes[s] / max(total, 1)) - RATIOS[s])
            for m in members:
                assigned[m] = target
            sizes[target] += len(members)

    moved = sum(1 for m, s_ in assigned.items()
                if s_ != videos[m]["original_split"])

    # ---- verification, before anything is written ---------------------------
    errors = []
    for h, members in by_hash.items():
        placed = {assigned[m] for m in members if m in assigned}
        if len(placed) > 1:
            errors.append(f"content hash {h[:12]} spans splits {placed}")
    for uid, members in by_user.items():
        placed = {assigned[m] for m in members if m in assigned}
        if len(placed) > 1:
            errors.append(f"user {uid} spans splits {placed}")

    out_rows = []
    for name, v in videos.items():
        out_rows.append({**v, "content_hash": hash_of.get(name),
                         "split": assigned.get(name),
                         "usable": name in assigned,
                         "reason": None if name in assigned
                                   else "contradictory duplicate labels (G-44)"})

    cls_by_split = defaultdict(Counter)
    for r in out_rows:
        if r["split"]:
            cls_by_split[r["split"]][r["class"]] += 1

    print(f"CONTENT-LEVEL SPLITS  (mode: {args.mode})")
    print("=" * 64)
    print(f"  videos total        : {len(videos)}")
    print(f"  components          : {len(comps)}  "
          f"(usable {len(usable_comps)}, dropped {len(dropped_comps)})")
    print(f"  assigned            : {len(assigned)}")
    print(f"  withheld (conflict) : {len(videos) - len(assigned)}")
    print(f"  moved from original : {moved} ({moved / max(len(assigned),1):.1%})"
          + ("   <- comparability preserved" if args.mode == "minimal" else ""))
    print()
    for s in ("train", "validation", "test"):
        n = sizes[s]
        share = n / max(len(assigned), 1)
        cls = "  ".join(f"{c}={cls_by_split[s][c]}" for c in CLASSES)
        print(f"  {s:11s} {n:5d}  ({share:.1%}, target {RATIOS[s]:.0%})   {cls}")
    print()
    if errors:
        print(f"  !! {len(errors)} LEAKAGE ERROR(S):")
        for e in errors[:10]:
            print(f"     {e}")
        return 1
    print("  VERIFIED: no content hash and no user spans two splits.")

    args.out.write_text(json.dumps({
        "_doc": ("Content-level splits. Leakage-free by CONTENT HASH and by USER "
                 "simultaneously: the split unit is a connected component of the "
                 "graph linking videos that share a hash or a user. Videos in "
                 "duplicate groups with contradictory labels are withheld "
                 "entirely (usable=false) rather than given an invented label. "
                 "Built by bench/build_content_splits.py; supersedes the "
                 "user-level splits for evaluation, which remain unchanged. "
                 "See G-44/G-45 and bench/results/2026-09-23-corpus-duplicates.md."),
        "mode": args.mode, "n_moved": moved,
        "seed": args.seed, "ratios": RATIOS,
        "source_splits": str(splits_path),
        "n_videos": len(videos), "n_assigned": len(assigned),
        "n_withheld": len(videos) - len(assigned),
        "n_components": len(comps),
        "sizes": dict(sizes),
        "class_by_split": {s: dict(c) for s, c in cls_by_split.items()},
        "videos": out_rows,
    }, indent=2))
    print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
