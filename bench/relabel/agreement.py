#!/usr/bin/env python3
"""Gate 1: inter-annotator agreement on severity (quadratic-weighted Cohen's kappa).

    python bench/relabel/agreement.py bench/results/relabel/annotation_sheet_A.csv bench/results/relabel/annotation_sheet_B.csv
Pass: kappa >= 0.60 (PREREGISTRATION.md). Pure python; no app imports.
"""
import csv, json, sys
from pathlib import Path

GATE = 0.60


def read_sheet(path):
    out = {}
    for r in csv.DictReader(open(path, newline="")):
        if r["video"].startswith("_") or not r["video"]: continue
        usable = (r.get("usable_yes_no") or "").strip().lower() in ("yes", "y", "1", "true")
        sev = (r.get("severity_0_to_3") or "").strip()
        out[r["video"]] = (int(sev) if sev.isdigit() else None, usable)
    return out


def weighted_kappa(a, b, k=4):
    """Quadratic-weighted Cohen's kappa for ordinal grades 0..k-1."""
    n = len(a)
    if n == 0: return float("nan")
    O = [[0] * k for _ in range(k)]
    for x, y in zip(a, b): O[x][y] += 1
    ra = [sum(O[i]) for i in range(k)]; cb = [sum(O[i][j] for i in range(k)) for j in range(k)]
    num = den = 0.0
    for i in range(k):
        for j in range(k):
            w = (i - j) ** 2 / (k - 1) ** 2
            num += w * O[i][j]; den += w * ra[i] * cb[j] / n
    return 1.0 - num / den if den else float("nan")


def summarize(A, B):
    both = [v for v in A if v in B and A[v][1] and B[v][1] and A[v][0] is not None and B[v][0] is not None]
    a = [A[v][0] for v in both]; b = [B[v][0] for v in both]
    kappa = weighted_kappa(a, b)
    exact = sum(x == y for x, y in zip(a, b)) / len(a) if a else float("nan")
    v2 = sum((x >= 2) == (y >= 2) for x, y in zip(a, b)) / len(a) if a else float("nan")
    unusable_a = sum(1 for v in A if not A[v][1]); unusable_b = sum(1 for v in B if not B[v][1])
    return {"n_both_usable": len(a), "kappa_quadratic": round(kappa, 4), "exact_agreement": round(exact, 4),
            "agreement_on_severity_ge_2": round(v2, 4), "unusable_A": unusable_a, "unusable_B": unusable_b,
            "gate_kappa": GATE, "gate_pass": bool(kappa >= GATE)}


def main():
    A, B = read_sheet(sys.argv[1]), read_sheet(sys.argv[2])
    res = summarize(A, B); print(json.dumps(res, indent=1))
    out = Path(sys.argv[1]).parent / "agreement.json"; out.write_text(json.dumps(res, indent=1)); print("wrote", out)
    return 0 if res["gate_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
