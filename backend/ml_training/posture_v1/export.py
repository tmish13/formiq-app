"""Export a trained seed into the artifact triple the serving loader accepts, with full provenance.

    python -m ml_training.posture_v1.export --run OUT --seed 3 --data-manifest DATA/manifest.json --out ARTIFACTS

Writes posture_v1.pt (the seed checkpoint: model_state_dict + model_config, as the loader wants),
posture_v1_scaler.joblib, posture_v1_manifest.json (the shipped manifest's schema, threshold from
validation, training_metrics = validation only unless a logged test read exists, and a `provenance`
block with every artifact's sha256, the data hashes, the pose pass, the seed, the recipe, the code's
git sha and the library versions). Refuses to write into the live artifacts directory unless
--install is passed: a candidate is not the incumbent.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

for p in ("/app", str(Path(__file__).resolve().parents[2])):
    if p not in sys.path:
        sys.path.insert(0, p)

LIVE_ARTIFACTS = Path(__file__).resolve().parents[2] / "app" / "ml" / "posture_v1" / "artifacts"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_sha() -> str | None:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=Path(__file__).resolve().parents[3], text=True).strip()
    except Exception:  # noqa: BLE001
        return None


def library_versions() -> dict:
    out = {"python": platform.python_version()}
    for mod in ("torch", "sklearn", "numpy", "joblib"):
        try:
            out[mod] = __import__(mod).__version__
        except Exception:  # noqa: BLE001
            out[mod] = None
    return out


def export(run: Path, seed: int, data_manifest: Path, out: Path, *, version: str = "posture_v1_candidate",
           install: bool = False, label_definition: str | None = None) -> dict:
    import joblib
    import numpy as np
    if out.resolve() == LIVE_ARTIFACTS.resolve() and not install:
        raise SystemExit("refusing to overwrite the live artifacts without --install")
    out.mkdir(parents=True, exist_ok=True)
    report = json.loads((run / f"seed{seed}.json").read_text())
    dm = json.loads(data_manifest.read_text())
    shipped = json.loads((LIVE_ARTIFACTS / "posture_v1_manifest.json").read_text())

    shutil.copy2(run / f"seed{seed}.pt", out / "posture_v1.pt")
    shutil.copy2(run / f"seed{seed}_scaler.joblib", out / "posture_v1_scaler.joblib")
    scaler = joblib.load(out / "posture_v1_scaler.joblib")

    manifest = {
        "model_name": "posture_v1", "version": version, "threshold": report["threshold"],
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime()),
        "source_checkpoint": f"seed{seed}.pt",
        "input_spec": shipped["input_spec"], "feature_order_version": shipped["feature_order_version"],
        "feature_order": shipped["feature_order"], "model_config": report["model_config"],
        "training_metrics": {"val_auroc": report["val_auroc"], "val_auroc_ci95": report["val_auroc_ci95"],
                             "val_f05_at_threshold": report["val_f05_at_threshold"], "best_epoch": report["best_epoch"],
                             "epochs_run": report["epochs_run"], "n_train": report["n_train"], "n_val": report["n_val"],
                             "test": report.get("test_read") or "not read (one logged read per model, behind --final)"},
        "split_sizes": dm.get("n", {}), "prevalence": dm.get("prevalence", {}),
        "scaler_file": "posture_v1_scaler.joblib",
        "scaler_stats": {"n_training_videos_used": int(getattr(scaler, "n_samples_seen_", report["n_train"])),
                         "mean_range": [float(np.min(scaler.mean_)), float(np.max(scaler.mean_))],
                         "std_range": [float(np.min(scaler.scale_)), float(np.max(scaler.scale_))]},
        "provenance": {
            "artifact_sha256": {"posture_v1.pt": sha256_file(out / "posture_v1.pt"),
                                "posture_v1_scaler.joblib": sha256_file(out / "posture_v1_scaler.joblib")},
            "source_checkpoint_path": str(run / f"seed{seed}.pt"), "source_checkpoint_sha256": sha256_file(out / "posture_v1.pt"),
            "trainer": {"module": "backend/ml_training/posture_v1/train.py", "dataset": "backend/ml_training/posture_v1/dataset.py"},
            "data": {"target": dm.get("target"), "splits_file": dm.get("splits_file"), "splits_sha256": dm.get("splits_sha256"),
                     "ml_splits_file": dm.get("ml_splits_file"), "ml_splits_sha256": dm.get("ml_splits_sha256"),
                     "keypoint_cache": dm.get("cache"), "label_definition": label_definition or f"{dm.get('target')} as built by dataset.py"},
            "pose_pass_id_at_training": dm.get("pose_pass_id"),
            "recipe": report["recipe"], "seed": seed, "class_weights": report["class_weights"],
            "code_git_sha": git_sha(), "export_environment": library_versions(),
            "selection_rule": "median validation AUROC across seeds; threshold from the validation F0.5 sweep",
        },
    }
    (out / "posture_v1_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", type=Path, required=True); ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--data-manifest", type=Path, required=True); ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--version", default="posture_v1_candidate"); ap.add_argument("--install", action="store_true")
    ap.add_argument("--label-definition", default=None)
    a = ap.parse_args()
    m = export(a.run, a.seed, a.data_manifest, a.out, version=a.version, install=a.install, label_definition=a.label_definition)
    print(json.dumps({k: m[k] for k in ("version", "threshold", "training_metrics")}, indent=1)); print("wrote", a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
