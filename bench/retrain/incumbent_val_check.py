"""Exercise the incumbent-scoring path on the VALIDATION split only (never test).

Validates score_incumbent_on() -- the same function --final will use for the paired
comparison -- and records the incumbent's validation AUROC/F1 on the serving-pass cache.
"""
import json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
for p in ("/app",):
    if p not in sys.path: sys.path.insert(0, p)
from train import score_incumbent_on, HEADS
from app.eval.metrics import auroc, bootstrap_ci, counts, precision_recall_f1, trivial_floor

data = Path(sys.argv[1]); cache = Path(sys.argv[2])
z = np.load(data / "C_incumbent151_validation.npz", allow_pickle=True)
videos = [str(v) for v in z["video"]]; hashes = [str(h) for h in z["hash"]]
from train import POSTURE_HEADS
probs, thr_shipped = score_incumbent_on(dict(zip(videos, hashes)), cache, None)
p = np.array([probs[v] for v in videos])
out = {"split": "validation", "n": int(len(videos)), "heads": {}}
for head in POSTURE_HEADS:
    y = z["y"][:, HEADS.index(head)].astype(int)
    h = {"prevalence": round(float(y.mean()), 4), "auroc": round(auroc(y, p), 4), "floor": trivial_floor(y), "rows": {}}
    h["floor_f1"] = round(h["floor"]["all_positive_f1"], 4)
    for label, thr in (("shipped", float(thr_shipped)), ("notebook_val_opt_0.475", 0.475)):
        c = counts(y, (p >= thr).astype(int)); P, R, F = precision_recall_f1(c)
        lo, hi = bootstrap_ci(y, p, thr, metric="f1", n=2000, seed=0)
        h["rows"][label] = {"threshold": thr, "precision": round(P, 4), "recall": round(R, 4),
                            "f1": round(F, 4), "f1_ci95": [round(lo, 4), round(hi, 4)], "counts": c.as_dict()}
        print(f"incumbent on validation [{head}] n={len(y)} prev {y.mean():.3f}  @{thr}: AUROC {h['auroc']:.4f}  F1 {F:.4f} [{lo:.4f},{hi:.4f}]  P {P:.4f} R {R:.4f}  floor {h['floor_f1']:.4f}")
    out["heads"][head] = h
dest = Path(sys.argv[3]) if len(sys.argv) > 3 else data / "incumbent_validation_check.json"
dest.parent.mkdir(parents=True, exist_ok=True); dest.write_text(json.dumps(out, indent=1))
print("wrote", dest)
