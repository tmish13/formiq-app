#!/usr/bin/env python3
"""Score the incumbent and the retrain's primary artifact against docs/ml/ACCEPTANCE_BAR.md.

No inference and NO new test read: every number is taken from the single logged read
(bench/results/retrain/*__FINAL.json), the live-pipeline evaluation on stored decisions
(bench/results/2026-09-23-gate1b-eval-posture-test.json) and, when present, the flip-rate
measurement (bench/results/retrain/flip_rate.json). Prints the bar's two tables with a
pass/fail per row and writes bench/results/acceptance_bar_verdict.json.

    python bench/acceptance_bar_verdict.py
"""
import json
from pathlib import Path

R = Path(__file__).resolve().parents[1]
RES = R / "bench/results"
BAR = {"auroc_lb": 0.75, "precision": 0.70, "recall": 0.60, "coverage": 0.85, "abstain_gap": 0.05, "flip_rate": 0.10}


def main():
    sel = json.loads((RES / "retrain/primary_selection.json").read_text())
    prim = sel["primary"]; key = f"{prim['arm']}__{prim['learner']}"
    fin = json.loads((RES / f"retrain/{key}__FINAL.json").read_text())
    head = fin["heads"]["posture_fault"]; inc = fin["incumbent"]["posture_fault"]
    coll = fin["heads"]["posture_collapsed"]; inc_c = fin["incumbent"]["posture_collapsed"]
    live = json.loads((RES / "2026-09-23-gate1b-eval-posture-test.json").read_text())["checkers"]["posture_v1"]
    flips = json.loads((RES / "retrain/flip_rate.json").read_text()) if (RES / "retrain/flip_rate.json").exists() else None

    rows = []
    def row(tier, crit, rule, who, value, ok):
        rows.append({"tier": tier, "criterion": crit, "rule": rule, "model": who, "value": value, "pass": bool(ok) if ok is not None else None})

    # ---- Tier 1: incumbent (n=196 multi-label bit, from the paired read) and primary ----
    ia = inc["auroc"]; pa_lb = head["auroc_ci95"][0]
    row(1, "separation", f"AUROC CI lower bound >= {BAR['auroc_lb']}", "incumbent", f"{ia['auroc']:.4f} [{ia['auroc_ci95'][0]:.4f}, {ia['auroc_ci95'][1]:.4f}]", ia["auroc_ci95"][0] >= BAR["auroc_lb"])
    row(1, "separation", f"AUROC CI lower bound >= {BAR['auroc_lb']}", f"primary {key}", f"{head['auroc']:.4f} [{head['auroc_ci95'][0]:.4f}, {head['auroc_ci95'][1]:.4f}]", pa_lb >= BAR["auroc_lb"])
    # F1 lower bound above the floor (incumbent at its shipped threshold; primary at its validation threshold)
    ish = inc["by_threshold"]["shipped_0.525"]
    row(1, "above chance", "F1 CI lower bound > all-positive floor", "incumbent @0.525", f"{ish['f1']:.4f} [{ish['f1_ci95'][0]:.4f}, {ish['f1_ci95'][1]:.4f}] vs floor {head['floor_f1']:.4f}", ish["f1_ci95"][0] > head["floor_f1"])
    row(1, "above chance", "F1 CI lower bound > all-positive floor", f"primary @{head['threshold']}", f"{head['f1']:.4f} [{head['f1_ci95'][0]:.4f}, {head['f1_ci95'][1]:.4f}] vs floor {head['floor_f1']:.4f}", head["f1_ci95"][0] > head["floor_f1"])
    d = ia["paired_delta_auroc"]
    row(1, "replacing the incumbent", "paired dAUROC CI excludes zero and delta > 0", f"primary vs incumbent", f"{d['delta']:+.4f} [{d['ci95'][0]:+.4f}, {d['ci95'][1]:+.4f}]", (d["ci95"][0] > 0))

    # ---- Tier 2: on the collapsed label (what the app shows) ----
    for who, thr_key in (("incumbent", "shipped_0.525"),):
        r = inc_c["by_threshold"][thr_key]
        row(2, "precision at usable recall", f"P >= {BAR['precision']} at R >= {BAR['recall']}", f"{who} @{r['threshold']}", f"P {r['precision']:.4f} R {r['recall']:.4f}", r["precision"] >= BAR["precision"] and r["recall"] >= BAR["recall"])
    row(2, "precision at usable recall", f"P >= {BAR['precision']} at R >= {BAR['recall']}", f"primary @{coll['threshold']}", f"P {coll['precision']:.4f} R {coll['recall']:.4f}", coll["precision"] >= BAR["precision"] and coll["recall"] >= BAR["recall"])
    cov = live["coverage"]; gap = abs(cov["covered_only"]["f1"] - cov["abstain_as_negative"]["f1"])
    row(2, "abstention honest", f"coverage >= {BAR['coverage']} and |F1 covered - F1 abstain-as-neg| <= {BAR['abstain_gap']}", "incumbent (live, n=188)", f"coverage {cov['coverage']:.3f}, gap {gap:.4f}", cov["coverage"] >= BAR["coverage"] and gap <= BAR["abstain_gap"])
    row(2, "abstention honest", "(the retrain has no abstention gate)", f"primary", "n/a: predicts on every clip", None)
    if flips:
        for who in ("incumbent", "primary"):
            if who in flips:
                f = flips[who]
                row(2, "reliability", f"flip rate vs a second pose pass <= {BAR['flip_rate']} (passes {flips['pose_pass_ids']['a']} vs {flips['pose_pass_ids']['b']})",
                    who, f"{f['flip_rate']:.4f} ({f['flips']}/{flips['n']}) [{f['ci95'][0]:.4f}, {f['ci95'][1]:.4f}]", f["flip_rate"] <= BAR["flip_rate"])
    else:
        row(2, "reliability", f"flip rate vs a second pose pass <= {BAR['flip_rate']}", "incumbent", "0.149 (33/221, G-39; bench/results/2026-09-23-pose-pass-verdict-instability.md)", 0.149 <= BAR["flip_rate"])
        row(2, "reliability", f"flip rate vs a second pose pass <= {BAR['flip_rate']}", "primary", "not measured", None)

    print(f"primary artifact (by rule): {key}   test n={fin['n_test']}")
    for t in (1, 2):
        print(f"\n== Tier {t} ==")
        for r in rows:
            if r["tier"] != t: continue
            mark = "PASS" if r["pass"] else ("FAIL" if r["pass"] is False else " -- ")
            print(f"  [{mark}] {r['criterion']:26s} {r['model']:32s} {r['value']}")
    t1_inc = all(r["pass"] for r in rows if r["tier"] == 1 and r["model"].startswith("incumbent"))
    t1_pri = all(r["pass"] for r in rows if r["tier"] == 1 and r["model"].startswith("primary"))
    verdict = {"primary_key": key, "n_test": fin["n_test"], "rows": rows,
               "tier1_incumbent": t1_inc, "tier1_primary": t1_pri,
               "ships_per_A3": "below Tier 1: no per-video posture verdict; localisation + any_fault only" if not (t1_inc or t1_pri) else "Tier 1 met by at least one model; see Tier 2"}
    print(f"\nA3 state: {verdict['ships_per_A3']}")
    (RES / "acceptance_bar_verdict.json").write_text(json.dumps(verdict, indent=2))
    print("wrote", RES / "acceptance_bar_verdict.json")


if __name__ == "__main__":
    main()
