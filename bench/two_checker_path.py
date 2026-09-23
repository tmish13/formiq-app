#!/usr/bin/env python3
"""Prove the two-checker path end to end, with both checkers UNFITTED.

Stage A's claim is not that these rules work -- all three fault rules were
measured and refuted at the video level
(bench/results/2026-09-23-corpus-level-negative.md). The claim is that the
PATH works: two named checkers produce evidence, the combiner records it, and
neither of them is allowed to set a verdict or move a score, because neither is
fitted.

The three numbers that matter are the last three printed. If `contributors` or
`scored` is ever non-zero with these params, the advisory guarantee has been
broken and something downstream is treating a hand-set constant as a calibrated
one.

Offline: reads the cached live-extracted keypoints, no container, no DB.

    python bench/two_checker_path.py
"""
from __future__ import annotations

import gzip
import json
import statistics as st
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "backend"))

KP_DIR = REPO / "bench" / "cache" / "keypoints_live"
OUT = REPO / "bench" / "results" / "two_checker_path.json"


def main() -> int:
    from app.rules import (
        evaluate_depth,
        evaluate_knees_forward,
        load_knees_forward_params,
        load_params,
    )
    from app.services.decisions import COMBINER_VERSION, CheckerOutcome, combine

    depth_params = load_params()
    kf_params = load_knees_forward_params()
    assert not depth_params["fitted"], "depth params claim to be fitted"
    assert not kf_params["fitted"], "knees-forward params claim to be fitted"

    files = sorted(KP_DIR.glob("*.json.gz"))
    if not files:
        print(f"no keypoints under {KP_DIR}")
        return 1

    verdicts: Counter = Counter()
    raw: Counter = Counter()
    advisory_n = contrib_n = scored = 0
    kf_scores = []
    rows = []

    for f in files:
        with gzip.open(f, "rt") as fh:
            d = json.load(fh)
        fps = float(d.get("source_fps") or 0.0) or kf_params["fallback_fps"]
        dv = evaluate_depth(d["frames"], fps, depth_params)
        kv = evaluate_knees_forward(d["frames"], fps, kf_params)

        outcomes = [
            CheckerOutcome(
                checker_name="depth_parallel_v0", target="depth",
                decision=dv.verdict, checker_version=dv.params_id,
                fitted=depth_params["fitted"], advisory=True,
                abstained=dv.abstained, abstain_reason=dv.abstain_reason,
                confidence=dv.confidence, coverage=dv.coverage,
                indicators=dv.indicators,
            ),
            CheckerOutcome(
                checker_name="knees_forward_v0", target="knees_forward",
                decision=kv.decision, checker_version=kv.params_id,
                fitted=kv.fitted, advisory=True,
                abstained=kv.abstained, abstain_reason=kv.abstain_reason,
                confidence=kv.confidence, coverage=kv.coverage,
                threshold=kv.threshold, indicators=kv.indicators,
            ),
        ]
        r = combine(outcomes)

        for t, v in r.verdicts.items():
            verdicts[(t, v)] += 1
        raw[("depth", dv.verdict, dv.abstain_reason)] += 1
        raw[("knees_forward", kv.decision, kv.abstain_reason)] += 1
        advisory_n += len(r.advisory)
        contrib_n += len(r.contributors)
        if r.score is not None:
            scored += 1
        if kv.score is not None:
            kf_scores.append(kv.score)
        rows.append({"video": f.name[:-8], "depth": dv.verdict,
                     "knees_forward": kv.decision,
                     "kf_score": kv.score, "view": (kv.view or {}).get("kind")})

    n = len(files)
    print(f"clips {n}   checker outcomes {2 * n}   combiner {COMBINER_VERSION}")
    print()
    print("=" * 70)
    print("WHAT EACH CHECKER SAID (before the combiner)")
    print("=" * 70)
    for target in ("depth", "knees_forward"):
        sub = [(k, c) for k, c in raw.items() if k[0] == target]
        answered = sum(c for (_, dec, _), c in sub if dec != "UNCERTAIN")
        print(f"  {target}   answered {answered}/{n} = {answered / n:.1%}")
        for (_, dec, reason), c in sorted(sub, key=lambda x: -x[1]):
            label = dec if reason is None else f"{dec} ({reason})"
            print(f"      {label:38s} {c:4d}  {c / n:5.1%}")
    if kf_scores:
        print(f"  knees_forward travel, torso-lengths: "
              f"median {st.median(kf_scores):+.4f}  "
              f"min {min(kf_scores):+.4f}  max {max(kf_scores):+.4f}")
    print()
    print("=" * 70)
    print("WHAT THE COMBINER DID WITH IT")
    print("=" * 70)
    for (t, v), c in sorted(verdicts.items()):
        print(f"      {t:16s} {v:14s} {c:4d}")
    print()
    print(f"  advisory outcomes recorded as evidence : {advisory_n}")
    print(f"  outcomes that set a verdict            : {contrib_n}   (must be 0)")
    print(f"  clips given a combined score           : {scored}   (must be 0)")
    print()
    ok = contrib_n == 0 and scored == 0
    print("  => PASS: unfitted checkers produced evidence and nothing else."
          if ok else
          "  => FAIL: an unfitted checker influenced a verdict or a score.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "n": n, "combiner_version": COMBINER_VERSION,
        "advisory": advisory_n, "contributors": contrib_n, "scored": scored,
        "depth_params_id": depth_params["params_id"],
        "knees_forward_params_id": kf_params["params_id"],
        "rows": rows,
    }, indent=2))
    print(f"\nwrote {OUT}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
