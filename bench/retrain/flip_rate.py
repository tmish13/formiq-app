#!/usr/bin/env python3
"""Per-item verdict flip rate between two pose passes (ACCEPTANCE_BAR §A2, reliability).

The same 196 test clips, byte-identical footage, two MediaPipe passes (the serving pass and a
second pass in its own cache). A verdict that changes when only the pose pass changes is not a
property of the user's squat. Reported for the incumbent (shipped weights, threshold 0.525,
through the serving loader) and for the retrain's primary artifacts (posture_fault and
posture_collapsed heads, at their validation thresholds), with a bootstrap CI over items.

This is NOT a test read: no labels are used. Both passes' feature files are built by
bench/retrain/build_dataset.py from their caches.

    python bench/retrain/flip_rate.py --data-a <dir built from pass A> --data-b <dir built from pass B> \
        --cache-a <cache A> --cache-b <cache B> --artifacts <pickles dir> --arm B_temporal64 --model hgb
"""
import argparse, json, pickle, sys
from pathlib import Path
import numpy as np

for p in ("/app", str(Path(__file__).resolve().parents[2] / "backend")):
    if p not in sys.path: sys.path.insert(0, p)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from train import clean, load, score_incumbent_on, HEADS   # noqa: E402


def _ci(flags, n=2000, seed=0):
    rng = np.random.default_rng(seed); f = np.asarray(flags, dtype=float); out = []
    for _ in range(n):
        idx = rng.integers(0, len(f), len(f)); out.append(f[idx].mean())
    return [round(float(np.percentile(out, 2.5)), 4), round(float(np.percentile(out, 97.5)), 4)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-a", required=True); ap.add_argument("--data-b", required=True)
    ap.add_argument("--cache-a", required=True); ap.add_argument("--cache-b", required=True)
    ap.add_argument("--artifacts", required=True); ap.add_argument("--arm", required=True); ap.add_argument("--model", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    Xa, _, va, ha = load(Path(a.data_a), a.arm, "test"); Xb, _, vb, hb = load(Path(a.data_b), a.arm, "test")
    common = sorted(set(map(str, va)) & set(map(str, vb)))
    ia = {str(v): i for i, v in enumerate(va)}; ib = {str(v): i for i, v in enumerate(vb)}
    res = {"n": len(common), "pass_a": str(a.cache_a), "pass_b": str(a.cache_b),
           "pose_pass_ids": {k: json.loads((Path(c) / "_manifest.json").read_text())["extraction_contract"]["pose_pass_id"]
                             for k, c in (("a", a.cache_a), ("b", a.cache_b))}}
    # retrain heads
    for head in ("posture_fault", "posture_collapsed"):
        art = Path(a.artifacts) / f"{a.arm}__{a.model}__{head}.pkl"
        with open(art, "rb") as fh: m = pickle.load(fh)
        pa = m["model"].predict_proba(clean(Xa[[ia[v] for v in common]], m["scaler"]))[:, 1]
        pb = m["model"].predict_proba(clean(Xb[[ib[v] for v in common]], m["scaler"]))[:, 1]
        t = m["threshold"]; flips = ((pa >= t) != (pb >= t)).astype(int)
        res[f"primary_{head}"] = {"threshold": t, "flips": int(flips.sum()), "flip_rate": round(float(flips.mean()), 4),
                                  "ci95": _ci(flips), "median_abs_prob_move": round(float(np.median(np.abs(pa - pb))), 4)}
        print(f"primary {a.arm}/{a.model} [{head}] @{t}: flips {int(flips.sum())}/{len(common)} = {flips.mean():.4f} {res[f'primary_{head}']['ci95']}")
    # incumbent on both caches
    hashes = {v: (ha[ia[v]] if not isinstance(ha[ia[v]], bytes) else ha[ia[v]].decode()) for v in common}
    pa_i, thr = score_incumbent_on({v: str(hashes[v]) for v in common}, Path(a.cache_a), None)
    pb_i, _ = score_incumbent_on({v: str(hashes[v]) for v in common}, Path(a.cache_b), None)
    xa = np.array([pa_i[v] for v in common]); xb = np.array([pb_i[v] for v in common])
    flips = ((xa >= thr) != (xb >= thr)).astype(int)
    res["incumbent"] = {"threshold": thr, "flips": int(flips.sum()), "flip_rate": round(float(flips.mean()), 4),
                        "ci95": _ci(flips), "median_abs_prob_move": round(float(np.median(np.abs(xa - xb))), 4)}
    res["primary"] = res["primary_posture_fault"]
    print(f"incumbent @{thr}: flips {int(flips.sum())}/{len(common)} = {flips.mean():.4f} {res['incumbent']['ci95']}")
    Path(a.out).write_text(json.dumps(res, indent=2)); print("wrote", a.out)


if __name__ == "__main__":
    main()
