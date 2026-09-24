#!/usr/bin/env python3
"""Two measurements on stored decisions, no inference (ACCEPTANCE_BAR §A4).

1. The DISPLAYED score. The app shows `posture_score` = 0.65 * model + 0.35 * hand-weighted
   components (scoring.py). The bar is measured on the model's probability. Which separates the
   label better on the clean content-level test?  AUROC of (100 - posture_score) vs AUROC of prob,
   on the same rows, paired bootstrap on the difference.

2. The confidence badge as the user saw it. `results.posture_v1.calibrated_confidence.label` is
   stored per row. Was a "High" badge more often right than a "Low" one?  (G-50: the formula was
   inverted; this is the measured consequence.)

Runs inside the image with DB access (see bench/retrain/run.sh for the docker invocation):
    python /repo/bench/displayed_score_check.py
"""
import asyncio, json, sys
from pathlib import Path
import numpy as np

for p in ("/app", str(Path(__file__).resolve().parents[1] / "backend")):
    if p not in sys.path: sys.path.insert(0, p)
from app.eval.metrics import auroc, bootstrap_ci

SPLITS = next(c for c in (Path("/repo/bench/results/content_level_splits.json"),
                          Path(__file__).resolve().parents[1] / "bench/results/content_level_splits.json") if c.exists())


async def load():
    from sqlalchemy import text
    from app.core.database import get_async_session_for_celery
    async with get_async_session_for_celery() as s:
        rows = (await s.execute(text("""
            SELECT r.content_hash, f.posture_score, d.prob, d.decision,
                   f.results->'posture_v1'->'calibrated_confidence'->>'label' AS badge
            FROM analysis_runs r
            JOIN form_checks f ON f.id = r.form_check_id
            JOIN checker_decisions d ON d.run_id = r.id AND d.checker_name = 'posture_v1'
            WHERE r.status = 'completed' AND r.content_hash IS NOT NULL AND d.prob IS NOT NULL
            ORDER BY r.finished_at"""))).all()
        labels = (await s.execute(text("""
            SELECT content_hash, value FROM labels
            WHERE target = 'posture_fault' AND source = 'dataset' AND trust = 0.6 AND usable AND value IS NOT NULL"""))).all()
    return rows, labels


def main():
    rows, labels = asyncio.run(load())
    lab = {h: int(v) for h, v in labels}
    split = {r["content_hash"]: r["split"] for r in json.loads(SPLITS.read_text())["videos"] if r["content_hash"] and r["split"]}
    latest = {}
    for h, ps, prob, dec, badge in rows:
        latest[h] = (ps, float(prob), dec, badge)          # ordered by finished_at -> last wins
    out = {"n_decisions": len(rows), "n_distinct_hashes": len(latest), "splits": {}}
    for sp in ("test", "validation", "train"):
        items = [(h, *v) for h, v in latest.items() if split.get(h) == sp and h in lab]
        y = np.array([lab[h] for h, *_ in items]); prob = np.array([v[1] for _, *v in items])
        have_ps = np.array([v[0] is not None for _, *v in items])
        ps = np.array([100.0 - float(v[0]) if v[0] is not None else np.nan for _, *v in items])
        res = {"n": int(len(y)), "prevalence": round(float(y.mean()), 4) if len(y) else None,
               "n_with_displayed_score": int(have_ps.sum())}
        if len(y) > 10:
            res["auroc_model_prob_all"] = round(auroc(y, prob), 4)
            if have_ps.sum() > 10:
                yd, sd, pd_ = y[have_ps], ps[have_ps], prob[have_ps]
                res["same_rows_n"] = int(len(yd))
                res["auroc_displayed_score"] = round(auroc(yd, sd), 4)
                res["auroc_displayed_score_ci95"] = [round(x, 4) for x in bootstrap_ci(yd, sd, 0.5, metric="auroc", n=2000, seed=0)]
                res["auroc_model_prob"] = round(auroc(yd, pd_), 4)
                res["auroc_model_prob_ci95"] = [round(x, 4) for x in bootstrap_ci(yd, pd_, 0.5, metric="auroc", n=2000, seed=0)]
                rng = np.random.default_rng(0); d = []
                for _ in range(2000):
                    idx = rng.integers(0, len(yd), len(yd)); d.append(auroc(yd[idx], sd[idx]) - auroc(yd[idx], pd_[idx]))
                res["paired_delta_displayed_minus_model"] = round(float(np.mean(sd is not None) * 0 + (auroc(yd, sd) - auroc(yd, pd_))), 4)
                res["paired_delta_ci95"] = [round(float(np.percentile(d, 2.5)), 4), round(float(np.percentile(d, 97.5)), 4)]
        bands = {}
        for h, ps_, p_, dec, badge in items:
            if dec not in ("FAULT", "GOOD_FORM") or badge is None: continue
            correct = int((dec == "FAULT") == bool(lab[h]))
            b = bands.setdefault(badge, [0, 0]); b[0] += correct; b[1] += 1
        res["badge_accuracy_at_shipped_threshold"] = {k: {"n": v[1], "accuracy": round(v[0] / v[1], 4)} for k, v in sorted(bands.items())}
        out["splits"][sp] = res
        print(sp, json.dumps(res))
    dest = Path("/repo/bench/results/displayed_score_check.json") if Path("/repo").exists() else Path(__file__).resolve().parents[1] / "bench/results/displayed_score_check.json"
    dest.write_text(json.dumps(out, indent=2)); print("wrote", dest)


if __name__ == "__main__":
    main()
