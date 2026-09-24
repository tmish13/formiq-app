"""Seeded PostureV1 trainer (Track B5): the notebook's recipe, the serving code, one logged test read.

    python -m ml_training.posture_v1.train --data DATA --out OUT --seeds 0 1 2 3 4
    python -m ml_training.posture_v1.train --data DATA --out OUT --final            # once, logged

What is reused from serving, so parity is by construction: PostureV1Model (app/ml/posture_v1/model.py)
built from the shipped manifest's model_config; the arrays come from dataset.py, which runs
preprocess_pose_data and compute_151d_features; metrics from app/eval/metrics.py.

The recipe is the notebook's (backend/ml_training/posture_v1/provenance/PROVENANCE.md): Adam(lr 1e-3,
wd 5e-4), ReduceLROnPlateau(max, 0.5, patience 7), grad clip 1.0, batch 4, up to 100 epochs, early
stopping patience 15 on validation F0.5, BCEWithLogits with class weights total/(2*count), threshold
chosen on validation by an F0.5 sweep over linspace(0.2, 0.8, 25). Two things the notebook did not do:
every run is seeded, and the best state is a DEEP copy (the notebook's .copy() was shallow).

The test split is never opened by train(); final() opens it once for the selected seed and appends
to TEST_READ_LOG.jsonl; a second read is refused unless --force-second-read --reason is given.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import random
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np

for p in ("/app", str(Path(__file__).resolve().parents[2])):
    if p not in sys.path:
        sys.path.insert(0, p)

SERVING_MANIFEST = Path(__file__).resolve().parents[2] / "app" / "ml" / "posture_v1" / "artifacts" / "posture_v1_manifest.json"
RECIPE = {"optimizer": "Adam", "lr": 1e-3, "weight_decay": 5e-4, "scheduler": "ReduceLROnPlateau(mode=max, factor=0.5, patience=7)",
          "grad_clip_norm": 1.0, "batch_size": 4, "max_epochs": 100, "early_stopping_patience": 15,
          "loss": "BCEWithLogitsLoss, per-sample class weights total/(2*count)",
          "early_stopping_metric": "validation F0.5 at threshold 0.5",
          "threshold_selection": "validation F0.5 sweep over linspace(0.2, 0.8, 25)"}
THRESHOLDS = np.linspace(0.2, 0.8, 25)


# ----------------------------------------------------------------------------- model / data
def serving_model_config() -> Dict[str, Any]:
    return json.loads(SERVING_MANIFEST.read_text())["model_config"]


def build_model(config: Optional[Dict[str, Any]] = None):
    from app.ml.posture_v1.model import PostureV1Model
    return PostureV1Model(config or serving_model_config())


def seed_everything(seed: int) -> None:
    import torch
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
    try:
        torch.use_deterministic_algorithms(True, warn_only=True)
    except Exception:  # noqa: BLE001 -- older torch
        pass
    os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")


def load_split(data: Path, split: str, subset: Optional[int] = None) -> Dict[str, np.ndarray]:
    z = np.load(data / f"{split}.npz", allow_pickle=False)
    d = {k: z[k] for k in z.files}
    if subset:
        d = {k: v[:subset] for k, v in d.items()}
    return d


def class_weights(y: np.ndarray) -> np.ndarray:
    """The notebook's weights: total / (2 * count) per class, [good_form, posture_fault]."""
    total, fault = float(len(y)), float(np.sum(y == 1)); good = total - fault
    return np.asarray([total / (2.0 * good) if good > 0 else 1.0, total / (2.0 * fault) if fault > 0 else 1.0], np.float32)


def snapshot_state(model) -> Dict[str, Any]:
    """A DEEP copy of the weights. The notebook used state_dict().copy(), which shares storage."""
    return copy.deepcopy({k: v.detach().clone() for k, v in model.state_dict().items()})


def weighted_bce(logits, y_idx, weights):
    """The notebook's posture_only_bce_loss for fully labelled batches: 2 logits, one-hot targets,
    per-sample weight = class weight of the true class, weighted mean."""
    import torch
    import torch.nn.functional as F
    targets = F.one_hot(y_idx, num_classes=2).float()
    per_sample = F.binary_cross_entropy_with_logits(logits, targets, reduction="none").mean(dim=1)
    w = weights[y_idx]
    return (per_sample * w).sum() / w.sum()


def _probs(model, K, X, L, device, batch_size: int = 16) -> np.ndarray:
    import torch
    model.eval(); out = []
    with torch.no_grad():
        for i in range(0, len(K), batch_size):
            k = torch.as_tensor(K[i:i + batch_size], dtype=torch.float32, device=device)
            x = torch.as_tensor(X[i:i + batch_size], dtype=torch.float32, device=device)
            l = torch.as_tensor(L[i:i + batch_size], dtype=torch.long, device=device)
            out.append(torch.sigmoid(model(k, x, l)[:, 1]).cpu().numpy())
    return np.concatenate(out) if out else np.zeros(0)


def f05_at(y: np.ndarray, p: np.ndarray, t: float) -> float:
    from app.eval.metrics import counts, f_beta
    return f_beta(counts(y, (p >= t).astype(int)), beta=0.5)


# ----------------------------------------------------------------------------- one seed
def train_one_seed(seed: int, data: Path, out: Path, *, subset: Optional[int] = None, max_epochs: int = 100,
                   patience: int = 15, batch_size: int = 4, lr: float = 1e-3, weight_decay: float = 5e-4,
                   model_config: Optional[Dict[str, Any]] = None, quiet: bool = False) -> Dict[str, Any]:
    import joblib
    import torch
    from sklearn.preprocessing import StandardScaler
    from torch.optim.lr_scheduler import ReduceLROnPlateau
    from app.eval.metrics import auroc, bootstrap_ci

    seed_everything(seed)
    device = torch.device("cpu")
    tr = load_split(data, "train", subset); va = load_split(data, "validation", (subset // 2 if subset else None))
    scaler = StandardScaler().fit(tr["X"])
    Xtr, Xva = scaler.transform(tr["X"]), scaler.transform(va["X"])
    ytr, yva = tr["y"].astype(np.int64), va["y"].astype(np.int64)
    cw = torch.as_tensor(class_weights(ytr), device=device)

    cfg = model_config or serving_model_config()
    model = build_model(cfg).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=weight_decay)
    sched = ReduceLROnPlateau(opt, mode="max", factor=0.5, patience=7)
    gen = torch.Generator().manual_seed(seed)

    best = {"f05": -1.0, "epoch": -1, "state": None}; since_best = 0; history = []
    t0 = time.monotonic()
    for epoch in range(1, max_epochs + 1):
        model.train(); perm = torch.randperm(len(ytr), generator=gen).numpy(); losses = []
        for i in range(0, len(perm), batch_size):
            idx = perm[i:i + batch_size]
            k = torch.as_tensor(tr["K"][idx], dtype=torch.float32, device=device)
            x = torch.as_tensor(Xtr[idx], dtype=torch.float32, device=device)
            l = torch.as_tensor(tr["L"][idx], dtype=torch.long, device=device)
            y = torch.as_tensor(ytr[idx], dtype=torch.long, device=device)
            opt.zero_grad(); loss = weighted_bce(model(k, x, l), y, cw); loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0); opt.step(); losses.append(float(loss))
        pva = _probs(model, va["K"], Xva, va["L"], device)
        f05 = f05_at(yva, pva, 0.5); sched.step(f05)
        history.append({"epoch": epoch, "train_loss": round(float(np.mean(losses)), 4), "val_f05_at_0.5": round(f05, 4),
                        "lr": opt.param_groups[0]["lr"]})
        if not quiet:
            print(f"seed {seed} epoch {epoch:3d} loss {np.mean(losses):.4f} val F0.5@0.5 {f05:.4f}", flush=True)
        if f05 > best["f05"]:
            best = {"f05": f05, "epoch": epoch, "state": snapshot_state(model)}; since_best = 0
        else:
            since_best += 1
            if since_best >= patience:
                break

    model.load_state_dict(best["state"])
    pva = _probs(model, va["K"], Xva, va["L"], device)
    sweep = [(float(t), f05_at(yva, pva, float(t))) for t in THRESHOLDS]
    threshold = max(sweep, key=lambda tf: tf[1])[0]
    val_auroc = auroc(yva, pva); lo, hi = bootstrap_ci(yva, pva, threshold, metric="auroc", n=2000, seed=0)
    report = {"seed": seed, "n_train": int(len(ytr)), "n_val": int(len(yva)),
              "prevalence_train": round(float(ytr.mean()), 4), "prevalence_val": round(float(yva.mean()), 4),
              "class_weights": [round(float(w), 4) for w in class_weights(ytr)],
              "epochs_run": len(history), "best_epoch": best["epoch"], "best_val_f05_at_0.5": round(best["f05"], 4),
              "threshold": round(threshold, 4), "val_f05_at_threshold": round(f05_at(yva, pva, threshold), 4),
              "val_auroc": round(val_auroc, 4), "val_auroc_ci95": [round(lo, 4), round(hi, 4)],
              "recipe": {**RECIPE, "lr": lr, "weight_decay": weight_decay, "batch_size": batch_size,
                         "max_epochs": max_epochs, "early_stopping_patience": patience},
              "model_config": cfg, "wall_s": round(time.monotonic() - t0, 1), "history": history,
              "test_read": None}
    out.mkdir(parents=True, exist_ok=True)
    torch.save({"model_state_dict": best["state"], "model_config": cfg, "seed": seed, "best_epoch": best["epoch"],
                "threshold": threshold, "trainer": "backend/ml_training/posture_v1/train.py"}, out / f"seed{seed}.pt")
    joblib.dump(scaler, out / f"seed{seed}_scaler.joblib")
    (out / f"seed{seed}.json").write_text(json.dumps(report, indent=2))
    return report


def select_median_seed(reports) -> Dict[str, Any]:
    """The artifact is the median-validation-AUROC seed (the rule bench/retrain used): no picking the
    luckiest seed, no reading test to choose."""
    ordered = sorted(reports, key=lambda r: r["val_auroc"])
    return ordered[len(ordered) // 2]


def train(args) -> int:
    data, out = Path(args.data), Path(args.out)
    reports = [train_one_seed(s, data, out, subset=args.subset, max_epochs=args.max_epochs, patience=args.patience,
                              batch_size=args.batch_size, lr=args.lr, weight_decay=args.weight_decay, quiet=args.quiet)
               for s in args.seeds]
    chosen = select_median_seed(reports)
    summary = {"seeds": [{k: r[k] for k in ("seed", "epochs_run", "best_epoch", "threshold", "val_f05_at_threshold", "val_auroc", "val_auroc_ci95", "wall_s")} for r in reports],
               "selected_seed": chosen["seed"], "selection_rule": "median validation AUROC",
               "val_auroc_min_max": [min(r["val_auroc"] for r in reports), max(r["val_auroc"] for r in reports)],
               "n_train": chosen["n_train"], "n_val": chosen["n_val"], "prevalence_val": chosen["prevalence_val"],
               "subset": args.subset, "test_read": None}
    (out / "SUMMARY.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary["seeds"], indent=1)); print("selected seed:", chosen["seed"])
    return 0


# ----------------------------------------------------------------------------- the one test read
def final_guard(log: Path, key: str, force: bool, reason: Optional[str]) -> bool:
    if log.exists():
        prior = [json.loads(l) for l in log.read_text().splitlines() if l.strip()]
        if any(r.get("key") == key for r in prior):
            if not force or not reason:
                print(f"REFUSED: test already read for {key} (see {log}). --force-second-read with --reason to override; it is logged as a second read.")
                return False
    return True


def final(args) -> int:
    import joblib
    import torch
    from app.eval.metrics import auroc, bootstrap_ci, counts, f_beta, precision_recall_f1, trivial_floor
    data, out = Path(args.data), Path(args.out)
    reports_dir = Path(args.reports) if args.reports else out
    summary = json.loads((out / "SUMMARY.json").read_text())
    seed = summary["selected_seed"]; key = f"trainer_port__seed{seed}__{hashlib.sha256((out / f'seed{seed}.pt').read_bytes()).hexdigest()[:12]}"
    log = reports_dir / "TEST_READ_LOG.jsonl"
    if not final_guard(log, key, args.force_second_read, args.reason):
        return 2
    ckpt = torch.load(out / f"seed{seed}.pt", map_location="cpu", weights_only=False)   # RELOADED from disk
    model = build_model(ckpt["model_config"]); model.load_state_dict(ckpt["model_state_dict"])
    scaler = joblib.load(out / f"seed{seed}_scaler.joblib")
    te = load_split(data, "test"); y = te["y"].astype(np.int64)
    p = _probs(model, te["K"], scaler.transform(te["X"]), te["L"], torch.device("cpu"))
    t = float(ckpt["threshold"]); c = counts(y, (p >= t).astype(int)); P, R, F1 = precision_recall_f1(c)
    alo, ahi = bootstrap_ci(y, p, t, metric="auroc", n=2000, seed=0); flo, fhi = bootstrap_ci(y, p, t, metric="f1", n=2000, seed=0)
    result = {"key": key, "read_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "n_test": int(len(y)), "prevalence": round(float(y.mean()), 4),
              "threshold": t, "auroc": round(auroc(y, p), 4), "auroc_ci95": [round(alo, 4), round(ahi, 4)],
              "precision": round(P, 4), "recall": round(R, 4), "f1": round(F1, 4), "f1_ci95": [round(flo, 4), round(fhi, 4)],
              "f05": round(f_beta(c, 0.5), 4), "floor": trivial_floor(y),
              "forced_second_read": bool(args.force_second_read), "reason": args.reason}
    with open(log, "a") as fh:
        fh.write(json.dumps(result) + "\n")
    summary["test_read"] = result; (out / "SUMMARY.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(result, indent=1))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--reports", default=None, help="where TEST_READ_LOG.jsonl lives (default: --out)")
    ap.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2, 3, 4])
    ap.add_argument("--subset", type=int, default=None, help="first N train / N//2 val rows (smoke runs)")
    ap.add_argument("--max-epochs", type=int, default=RECIPE["max_epochs"]); ap.add_argument("--patience", type=int, default=RECIPE["early_stopping_patience"])
    ap.add_argument("--batch-size", type=int, default=RECIPE["batch_size"]); ap.add_argument("--lr", type=float, default=RECIPE["lr"])
    ap.add_argument("--weight-decay", type=float, default=RECIPE["weight_decay"]); ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--final", action="store_true"); ap.add_argument("--force-second-read", action="store_true"); ap.add_argument("--reason", default=None)
    args = ap.parse_args()
    return final(args) if args.final else train(args)


if __name__ == "__main__":
    sys.exit(main())
