#!/usr/bin/env python3
"""Controlled retrain: seeded, val-only selection, one logged test read.

PROTOCOL (ML_AUDIT §11c), each rule enforced in code rather than remembered:
  * seeds     N seeds per (arm, head, model); the DISTRIBUTION is reported. The artifact
              is the seed with median validation AUROC -- a rule fixed here, before any
              number is seen, so "best seed" cannot be chosen after the fact.
  * scaler    fitted on TRAIN only, per arm.
  * threshold chosen on VALIDATION only, per head, maximising F1 over a fixed grid.
  * weights   the artifact written to disk is the object that is evaluated -- a fitted
              sklearn estimator is pickled and RELOADED before --final, so the bug in
              ML_AUDIT §6.4 (evaluating an in-memory object that differs from the saved
              one) cannot recur.
  * test      read exactly once per (arm, model), behind --final, appended to
              TEST_READ_LOG.jsonl with a timestamp; a second attempt is refused.
  * metrics   app.eval.metrics only: AUROC (primary), F1 at the val threshold with a
              bootstrap CI, trivial floor, majority-class accuracy, both coverage views
              are moot (no abstention) and said so.
  * paired    the incumbent is scored on the SAME test videos from the SAME cached
              keypoints (serving pass), in the same single read, so the comparison is of
              models and not of samples or pose passes.
  * verdict   the retrain must beat the incumbent's F1 CI LOWER bound on the posture
              head; otherwise it is a negative and is written up as one.
"""
from __future__ import annotations
import argparse, json, sys, time, pickle, hashlib
from pathlib import Path
import numpy as np

for p in ("/app", str(Path.home() / "formiq-app-3" / "backend")):
    if p not in sys.path: sys.path.insert(0, p)

HEADS = ("posture_fault", "stability_fault", "depth_fault", "any_fault", "posture_collapsed")
POSTURE_HEADS = ("posture_fault", "posture_collapsed")   # both get the paired incumbent comparison
THR_GRID = np.round(np.linspace(0.05, 0.95, 91), 3)


def load(data: Path, arm: str, split: str):
    z = np.load(data / f"{arm}_{split}.npz", allow_pickle=False)
    return z["X"].astype(np.float64), z["y"].astype(int), z["video"], z["hash"]


def make_model(kind: str, seed: int):
    from sklearn.linear_model import LogisticRegression
    from sklearn.ensemble import HistGradientBoostingClassifier
    if kind == "logreg":
        return LogisticRegression(C=1.0, max_iter=5000, class_weight="balanced", random_state=seed)
    if kind == "hgb":
        return HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05, max_iter=300,
                                              l2_regularization=1.0, class_weight="balanced",
                                              random_state=seed, early_stopping=False)
    if kind == "mlp":
        # The only seed-sensitive learner here. logreg (lbfgs) and hgb (no subsampling,
        # no early stopping) are deterministic, so their 5-seed distributions are degenerate
        # by construction. MLP early-stops on a 15% slice of TRAIN (never validation/test).
        from sklearn.neural_network import MLPClassifier
        return MLPClassifier(hidden_layer_sizes=(64,), alpha=1e-3, max_iter=500,
                             early_stopping=True, validation_fraction=0.15, n_iter_no_change=20,
                             random_state=seed)
    raise ValueError(kind)


def fit_scaler(X):
    from sklearn.preprocessing import StandardScaler
    sc = StandardScaler().fit(np.nan_to_num(X)); return sc


def clean(X, sc):
    return sc.transform(np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0))


def val_metrics(y, p):
    from app.eval.metrics import auroc, counts, precision_recall_f1, trivial_floor
    best_t, best_f = 0.5, -1.0
    for t in THR_GRID:
        f = precision_recall_f1(counts(y, (p >= t).astype(int)))[2]
        if f > best_f: best_t, best_f = float(t), f
    return {"auroc": auroc(y, p), "f1_at_best": best_f, "threshold": best_t,
            "floor": trivial_floor(y)}


def train(args):
    data, out = Path(args.data), Path(args.out)
    reports = Path(args.reports) if args.reports else out
    out.mkdir(parents=True, exist_ok=True); reports.mkdir(parents=True, exist_ok=True)
    out.mkdir(parents=True, exist_ok=True)
    Xtr, ytr, _, _ = load(data, args.arm, "train")
    Xva, yva, _, _ = load(data, args.arm, "validation")
    manifest = json.loads((data / "manifest.json").read_text())
    sc = fit_scaler(Xtr); Xtr_s, Xva_s = clean(Xtr, sc), clean(Xva, sc)
    report = {"arm": args.arm, "model": args.model, "seeds": list(args.seeds),
              "n_train": int(len(ytr)), "n_val": int(len(yva)),
              "pose_pass_id": manifest["pose_pass_id"], "spec_hash_A": manifest["spec_hash_A"],
              "feature_dim": int(Xtr.shape[1]), "heads": {}}
    for hi, head in enumerate(HEADS):
        y_tr, y_va = ytr[:, hi], yva[:, hi]
        if y_tr.sum() == 0 or y_tr.sum() == len(y_tr):
            report["heads"][head] = {"skipped": "single-class train"}; continue
        per_seed = []
        for seed in args.seeds:
            m = make_model(args.model, seed).fit(Xtr_s, y_tr)
            pv = m.predict_proba(Xva_s)[:, 1]
            vm = val_metrics(y_va, pv); vm["seed"] = seed
            per_seed.append((vm, m))
        aurocs = np.array([v["auroc"] for v, _ in per_seed])
        # Deterministic artifact rule: the seed whose val AUROC is the median.
        order = np.argsort(aurocs); chosen = int(order[len(order) // 2])
        vm, m = per_seed[chosen]
        art = out / f"{args.arm}__{args.model}__{head}.pkl"
        with open(art, "wb") as fh:
            pickle.dump({"model": m, "scaler": sc, "threshold": vm["threshold"], "head": head,
                         "arm": args.arm, "model_kind": args.model, "seed": vm["seed"],
                         "pose_pass_id": manifest["pose_pass_id"],
                         "spec_hash_A": manifest["spec_hash_A"], "feature_dim": int(Xtr.shape[1])}, fh)
        report["heads"][head] = {
            "val_auroc_per_seed": [round(float(v["auroc"]), 4) for v, _ in per_seed],
            "val_auroc_median": round(float(np.median(aurocs)), 4),
            "val_auroc_min_max": [round(float(aurocs.min()), 4), round(float(aurocs.max()), 4)],
            "val_f1_at_val_threshold_per_seed": [round(float(v["f1_at_best"]), 4) for v, _ in per_seed],
            "chosen_seed": vm["seed"], "chosen_threshold": vm["threshold"],
            "val_floor_f1": round(float(vm["floor"]["all_positive_f1"]), 4),
            "val_prevalence": round(float(vm["floor"]["prevalence"]), 4),
            "artifact": art.name, "artifact_sha256": hashlib.sha256(art.read_bytes()).hexdigest()[:16],
        }
        print(f"  [{args.arm} {args.model} {head:16s}] val AUROC per seed {report['heads'][head]['val_auroc_per_seed']}"
              f"  median {report['heads'][head]['val_auroc_median']}  thr {vm['threshold']}  "
              f"F1@thr {report['heads'][head]['val_f1_at_val_threshold_per_seed']}  floor {report['heads'][head]['val_floor_f1']}")
    (reports / f"{args.arm}__{args.model}__train_report.json").write_text(json.dumps(report, indent=2))
    return 0


def score_incumbent_on(hashes_by_video: dict, cache: Path, artifacts: Path):
    """PostureV1 posture probability on the SAME cached keypoints, via the serving loader."""
    import gzip
    from app.core.config import get_settings
    from app.ml.posture_v1.loader import PostureV1TorchLoader
    from app.ml.posture_v1.preprocess import preprocess_pose_data
    from app.ml.posture_v1.features_151d import compute_151d_features
    loader = PostureV1TorchLoader(get_settings()); loader._ensure_loaded()
    mean, std = (np.asarray(a, dtype=np.float64) for a in loader.get_scaler_params())
    probs = {}
    for video in hashes_by_video:
        with gzip.open(cache / f"{video}.json.gz", "rt") as fh: d = json.load(fh)
        pre = preprocess_pose_data(d["frames"])
        raw = compute_151d_features(pre.keypoints, apply_scaler=False, sequence_length=pre.sequence_length).astype(np.float64)
        probs[video] = float(loader._run_inference(pre.keypoints, ((raw - mean) / std).astype(np.float32), pre.sequence_length))
    return probs, float(loader._fault_threshold)


def final(args):
    """THE single test read for (arm, model). Refused if already logged."""
    from app.eval.metrics import auroc, bootstrap_ci, counts, precision_recall_f1, trivial_floor
    data, out = Path(args.data), Path(args.out)
    reports = Path(args.reports) if args.reports else out
    out.mkdir(parents=True, exist_ok=True); reports.mkdir(parents=True, exist_ok=True)
    log = reports / "TEST_READ_LOG.jsonl"
    key = f"{args.arm}__{args.model}"
    if log.exists():
        prior = [json.loads(l) for l in log.read_text().splitlines() if l.strip()]
        if any(r["key"] == key for r in prior) and not args.force_second_read:
            print(f"REFUSED: test already read for {key} (see {log}). Pass --force-second-read "
                  f"with --reason to override; the second read will be logged as such.")
            return 2
    Xte, yte, vte, hte = load(data, args.arm, "test")
    result = {"key": key, "read_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "n_test": int(len(yte)),
              "forced_second_read": bool(args.force_second_read), "reason": args.reason, "heads": {}}
    print(f"TEST READ #{1 if not args.force_second_read else 'N'}  {key}  n={len(yte)}")
    for hi, head in enumerate(HEADS):
        art = out / f"{args.arm}__{args.model}__{head}.pkl"
        if not art.exists(): continue
        with open(art, "rb") as fh: a = pickle.load(fh)          # RELOADED, not in-memory
        p = a["model"].predict_proba(clean(Xte, a["scaler"]))[:, 1]
        y = yte[:, hi]; t = a["threshold"]
        c = counts(y, (p >= t).astype(int)); P, R, F = precision_recall_f1(c)
        lo, hi_ = bootstrap_ci(y, p, t, metric="f1", n=2000, seed=0)
        alo, ahi = bootstrap_ci(y, p, t, metric="auroc", n=2000, seed=0)
        fl = trivial_floor(y)
        result["heads"][head] = {"auroc": round(auroc(y, p), 4), "auroc_ci95": [round(alo, 4), round(ahi, 4)], "threshold": t,
                                 "precision": round(P, 4), "recall": round(R, 4), "f1": round(F, 4),
                                 "f1_ci95": [round(lo, 4), round(hi_, 4)], "counts": c.as_dict(),
                                 "floor_f1": round(fl["all_positive_f1"], 4),
                                 "majority_acc": round(fl["majority_class_accuracy"], 4),
                                 "prevalence": round(fl["prevalence"], 4),
                                 "accuracy": round((c.tp + c.tn) / c.n, 4),
                                 "artifact_sha256": hashlib.sha256(art.read_bytes()).hexdigest()[:16]}
        r = result["heads"][head]
        print(f"  {head:16s} AUROC {r['auroc']:.4f}  F1 {r['f1']:.4f} [{lo:.4f}, {hi_:.4f}] @{t}  "
              f"P {P:.4f} R {R:.4f}  floor {r['floor_f1']:.4f}  maj-acc {r['majority_acc']:.4f}  acc {r['accuracy']:.4f}")
        # paired incumbent on the same videos, posture head only, same single read
        if head in POSTURE_HEADS and args.incumbent_cache:
            inc = result.setdefault("incumbent", {}).setdefault(head, {})
            ip, ithr_shipped = score_incumbent_on({v: h for v, h in zip(vte, hte)}, Path(args.incumbent_cache), None)
            pi = np.array([ip[v] for v in vte])
            # Two incumbent rows, both with validation-derived thresholds:
            #   shipped   0.525 -- the deployment as it is (chosen on the wrong weights, ML_AUDIT §6.4)
            #   val-opt   0.475 -- this artifact's own validation optimum (ML_AUDIT §7.2)
            # The acceptance test is against the STRONGER of the two lower bounds, so the
            # retrain cannot pass by beating a mis-thresholded incumbent.
            inc["by_threshold"] = {}
            rows = []
            # Third row: the incumbent's threshold chosen on THIS experiment's validation split by
            # the same rule (val_metrics / THR_GRID) the retrain used, so the incumbent is not
            # handicapped by a threshold tuned elsewhere. Test is still read once; all three
            # thresholds are applied to the same stored test probabilities.
            _, yva_i, vva, hva = load(data, args.arm, "validation")
            ipv, _ = score_incumbent_on({v: h for v, h in zip(vva, hva)}, Path(args.incumbent_cache), None)
            ithr_cv = val_metrics(yva_i[:, HEADS.index(head)], np.array([ipv[v] for v in vva]))["threshold"]
            for label, ithr in (("shipped_0.525", float(ithr_shipped)), ("notebook_val_opt_0.475", 0.475),
                                (f"content_val_opt_{ithr_cv}", float(ithr_cv))):
                ci_ = counts(y, (pi >= ithr).astype(int)); Pi, Ri, Fi = precision_recall_f1(ci_)
                ilo, ihi = bootstrap_ci(y, pi, ithr, metric="f1", n=2000, seed=0)
                rng = np.random.default_rng(0); deltas = []
                for _ in range(2000):
                    idx = rng.integers(0, len(y), len(y))
                    fa = precision_recall_f1(counts(y[idx], (p[idx] >= t).astype(int)))[2]
                    fb = precision_recall_f1(counts(y[idx], (pi[idx] >= ithr).astype(int)))[2]
                    deltas.append(fa - fb)
                dlo, dhi = float(np.percentile(deltas, 2.5)), float(np.percentile(deltas, 97.5))
                inc["by_threshold"][label] = {
                    "auroc": round(auroc(y, pi), 4), "threshold": ithr,
                    "precision": round(Pi, 4), "recall": round(Ri, 4), "f1": round(Fi, 4),
                    "f1_ci95": [round(ilo, 4), round(ihi, 4)], "counts": ci_.as_dict(),
                    "paired_delta_f1": {"delta": round(F - Fi, 4), "ci95": [round(dlo, 4), round(dhi, 4)],
                                        "includes_zero": dlo <= 0 <= dhi}}
                rows.append((label, Fi, ilo, ihi, ithr, Pi, Ri, dlo, dhi))
                print(f"  {'incumbent '+label:26s} AUROC {auroc(y, pi):.4f}  F1 {Fi:.4f} [{ilo:.4f}, {ihi:.4f}] @{ithr}  "
                      f"P {Pi:.4f} R {Ri:.4f}   paired ΔF1 {F - Fi:+.4f} [{dlo:+.4f}, {dhi:+.4f}]")
            # PRIMARY (pre-registered): AUROC, threshold-free. The incumbent has one AUROC.
            i_auroc = auroc(y, pi); ialo, iahi = bootstrap_ci(y, pi, 0.5, metric="auroc", n=2000, seed=0)
            rng = np.random.default_rng(0); dA = []
            for _ in range(2000):
                idx = rng.integers(0, len(y), len(y)); dA.append(auroc(y[idx], p[idx]) - auroc(y[idx], pi[idx]))
            dAlo, dAhi = float(np.percentile(dA, 2.5)), float(np.percentile(dA, 97.5))
            inc["auroc"] = {"auroc": round(i_auroc, 4), "auroc_ci95": [round(ialo, 4), round(iahi, 4)],
                                         "paired_delta_auroc": {"delta": round(auroc(y, p) - i_auroc, 4),
                                                                "ci95": [round(dAlo, 4), round(dAhi, 4)],
                                                                "includes_zero": dAlo <= 0 <= dAhi}}
            # Verdict. Beating the incumbent's CI lower bound is the contract's NECESSARY
            # condition; it is not sufficient -- a retrain whose point estimate sits below the
            # incumbent's cannot be called positive because the incumbent's interval is wide.
            r_auroc = auroc(y, p); d_auroc = r_auroc - i_auroc
            inc["label"] = head
            if r_auroc <= ialo:
                inc["verdict"] = (f"NEGATIVE: retrain AUROC {r_auroc:.4f} does not exceed the incumbent's "
                                  f"AUROC CI lower bound {ialo:.4f}")
            elif d_auroc <= 0:
                inc["verdict"] = (f"NEGATIVE: retrain AUROC {r_auroc:.4f} is not above the incumbent's point "
                                  f"estimate {i_auroc:.4f} (paired delta {d_auroc:+.4f} [{dAlo:+.4f}, {dAhi:+.4f}])")
            elif dAlo > 0:
                inc["verdict"] = (f"POSITIVE: retrain AUROC {r_auroc:.4f} vs incumbent {i_auroc:.4f} "
                                  f"[{ialo:.4f}, {iahi:.4f}]; paired delta {d_auroc:+.4f} [{dAlo:+.4f}, {dAhi:+.4f}] excludes zero")
            else:
                inc["verdict"] = (f"POSITIVE per contract, NOT DISTINGUISHABLE: retrain AUROC {r_auroc:.4f} exceeds the "
                                  f"incumbent's lower bound {ialo:.4f} and point estimate {i_auroc:.4f}, but the paired "
                                  f"delta {d_auroc:+.4f} [{dAlo:+.4f}, {dAhi:+.4f}] includes zero")
            # SECONDARY: F1 against the strongest of the three incumbent thresholds
            strongest_lower = max(r[2] for r in rows)
            inc["secondary_f1_criterion"] = {"retrain_f1": round(F, 4), "incumbent_strongest_f1_lower_bound": round(strongest_lower, 4),
                                                "passes": bool(F > strongest_lower)}
            print(f"  incumbent AUROC {i_auroc:.4f} [{ialo:.4f}, {iahi:.4f}]   paired ΔAUROC {auroc(y, p) - i_auroc:+.4f} [{dAlo:+.4f}, {dAhi:+.4f}]")
            print(f"  -> {inc['verdict']}")
            print(f"     secondary F1 criterion: retrain {F:.4f} vs strongest incumbent lower bound {strongest_lower:.4f} -> "
                  f"{'passes' if F > strongest_lower else 'fails'}")
    (reports / f"{key}__FINAL.json").write_text(json.dumps(result, indent=2))
    with open(log, "a") as fh: fh.write(json.dumps({"key": key, "read_at": result["read_at"], "n": result["n_test"],
                                                     "forced": bool(args.force_second_read), "reason": args.reason}) + "\n")
    print(f"logged -> {log}")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--reports", default=None, help="JSON reports + TEST_READ_LOG (default: --out)")
    ap.add_argument("--arm", required=True); ap.add_argument("--model", default="logreg", choices=["logreg", "hgb", "mlp"])
    ap.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2, 3, 4])
    ap.add_argument("--final", action="store_true"); ap.add_argument("--incumbent-cache", default=None)
    ap.add_argument("--force-second-read", action="store_true"); ap.add_argument("--reason", default=None)
    args = ap.parse_args()
    return final(args) if args.final else train(args)


if __name__ == "__main__":
    raise SystemExit(main())
