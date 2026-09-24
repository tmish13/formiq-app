#!/usr/bin/env python3
"""Name the primary artifact BY RULE from the validation reports (PREREGISTRATION.md).

  primary     = (arm, learner) with the highest median validation AUROC on posture_fault
  co-primary  = same rule on posture_collapsed (the incumbent's own task)

Reads bench/results/retrain/*__train_report.json; touches nothing else. Run before --final
and commit its output alongside the test read, so the selection is on record first.

    python bench/retrain/select_primary.py [--reports bench/results/retrain]
"""
import argparse, glob, json
from pathlib import Path

HEADS = ("posture_fault", "stability_fault", "depth_fault", "any_fault", "posture_collapsed")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reports", type=Path, default=Path(__file__).resolve().parents[1] / "results" / "retrain")
    ap.add_argument("--json", type=Path, default=None)
    a = ap.parse_args()
    reps = [json.loads(Path(f).read_text()) for f in sorted(glob.glob(str(a.reports / "*__train_report.json")))]
    if not reps:
        print("no train reports found"); return 1
    print(f"{'arm':16s} {'learner':8s} " + " ".join(f"{h[:12]:>13s}" for h in HEADS) + "   (median val AUROC over seeds; [min, max])")
    rows = []
    for r in reps:
        cells = []
        for h in HEADS:
            hd = r["heads"].get(h)
            cells.append(f"{hd['val_auroc_median']:.4f}[{hd['val_auroc_min_max'][0]:.2f},{hd['val_auroc_min_max'][1]:.2f}]" if hd else "-")
            rows.append((h, hd["val_auroc_median"] if hd else -1.0, r["arm"], r["model"]))
        print(f"{r['arm']:16s} {r['model']:8s} " + " ".join(f"{c:>13s}" for c in cells))
    out = {"n_reports": len(reps), "rule": "highest median validation AUROC; ties broken by arm then learner name (deterministic)"}
    for head, label in (("posture_fault", "primary"), ("posture_collapsed", "co_primary")):
        best = max((x for x in rows if x[0] == head), key=lambda x: (x[1], -ord(x[2][0]), x[3]))
        out[label] = {"head": head, "arm": best[2], "learner": best[3], "val_auroc_median": best[1]}
        print(f"\n{label.upper():10s} for {head}: {best[2]} / {best[3]}  (median val AUROC {best[1]:.4f})")
    if a.json:
        a.json.write_text(json.dumps(out, indent=2)); print(f"wrote {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
