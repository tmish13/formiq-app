#!/usr/bin/env python3
"""Gate 2: does the graded label lift the incumbent's ceiling?  No training, no inference.

    python /repo/bench/relabel/gate.py            (inside the image, DB reachable)

Resolves posture_fault_v2 from the expert rows for the content-level TEST clips (both annotators
imported; a 1/2-boundary disagreement is `disputed` and excluded), joins the shipped PostureV1's
stored probabilities (checker_decisions.prob) and reports AUROC with a bootstrap CI, next to the
current corpus label on the SAME clips, paired. Pass: lower bound >= 0.6746 (PREREGISTRATION.md).
"""
import asyncio, json, sys
from pathlib import Path
import numpy as np

for p in ("/app", str(Path(__file__).resolve().parents[2] / "backend")):
    if p not in sys.path: sys.path.insert(0, p)
from app.eval.metrics import auroc, bootstrap_ci, trivial_floor

GATE_LB = 0.6746
SPLITS = next(c for c in (Path("/repo/bench/results/content_level_splits.json"),
                          Path(__file__).resolve().parents[2] / "bench/results/content_level_splits.json") if c.exists())


async def load():
    from sqlalchemy import text
    from app.core.database import get_async_session_for_celery
    async with get_async_session_for_celery() as s:
        probs = (await s.execute(text("""SELECT r.content_hash, d.prob FROM analysis_runs r
            JOIN checker_decisions d ON d.run_id = r.id AND d.checker_name = 'posture_v1'
            WHERE r.status = 'completed' AND d.prob IS NOT NULL ORDER BY r.finished_at"""))).all()
        expert = (await s.execute(text("""SELECT content_hash, source_ref, value, usable FROM labels
            WHERE source = 'expert' AND source_ref LIKE 'pilot:%' AND target IN ('posture_fault_v2', '*')"""))).all()
        current = (await s.execute(text("""SELECT content_hash, value FROM labels
            WHERE target = 'posture_fault' AND source = 'dataset' AND trust = 0.6 AND usable AND value IS NOT NULL"""))).all()
    return probs, expert, current


def main():
    probs, expert, current = asyncio.run(load())
    test = {r["content_hash"] for r in json.loads(SPLITS.read_text())["videos"] if r["split"] == "test" and r["content_hash"]}
    prob = {}
    for h, p in probs: prob[h] = float(p)
    cur = {h: int(v) for h, v in current}
    votes, unusable = {}, set()
    for h, ref, v, usable in expert:
        if not usable: unusable.add(h); continue
        if v is not None: votes.setdefault(h, set()).add(int(v))
    y2, yc, pp, disputed = [], [], [], 0
    for h in sorted(test):
        if h not in prob or h in unusable or h not in votes or h not in cur: continue
        if len(votes[h]) > 1: disputed += 1; continue
        y2.append(next(iter(votes[h]))); yc.append(cur[h]); pp.append(prob[h])
    y2, yc, pp = np.array(y2), np.array(yc), np.array(pp)
    if len(y2) < 30:
        print(f"only {len(y2)} test clips carry an undisputed expert v2 label; import both sheets first"); return 2
    a2 = auroc(y2, pp); lo2, hi2 = bootstrap_ci(y2, pp, 0.5, metric="auroc", n=2000, seed=0)
    ac = auroc(yc, pp); loc, hic = bootstrap_ci(yc, pp, 0.5, metric="auroc", n=2000, seed=0)
    rng = np.random.default_rng(0); d = []
    for _ in range(2000):
        i = rng.integers(0, len(y2), len(y2)); d.append(auroc(y2[i], pp[i]) - auroc(yc[i], pp[i]))
    res = {"n": int(len(y2)), "disputed_excluded": disputed, "unusable_excluded": len(unusable & test),
           "prevalence_v2": round(float(y2.mean()), 4), "prevalence_current": round(float(yc.mean()), 4),
           "auroc_v2": round(a2, 4), "auroc_v2_ci95": [round(lo2, 4), round(hi2, 4)],
           "auroc_current_same_clips": round(ac, 4), "auroc_current_ci95": [round(loc, 4), round(hic, 4)],
           "paired_delta": round(a2 - ac, 4), "paired_delta_ci95": [round(float(np.percentile(d, 2.5)), 4), round(float(np.percentile(d, 97.5)), 4)],
           "floor_v2": trivial_floor(y2), "gate_lower_bound": GATE_LB, "gate_pass": bool(lo2 >= GATE_LB)}
    print(json.dumps(res, indent=1))
    out = Path("/repo/bench/results/relabel/gate2.json") if Path("/repo").exists() else Path(__file__).resolve().parents[2] / "bench/results/relabel/gate2.json"
    out.write_text(json.dumps(res, indent=1)); print("wrote", out)
    return 0 if res["gate_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
