#!/usr/bin/env python3
"""
Penn-domain shortcut test.

All 124 Penn Action clips in v1's corpus are good_form (87 train / 17 val / 20 test).
87 of v1's 151 features are raw face coordinates, which encode camera framing, so the
model could have learned "Penn-looking framing -> good" as a shortcut. That would
explain recall 0.111 on external Penn faults better than "never saw a Penn fault".

Test 1: prob_fault on the 20 held-out Penn good-form clips vs the AQA good-form clips.
        Penn near 0 with AQA spread out => shortcut signature.
Test 2: freeze the face block [0:87] at the scaler mean on the Penn clips. If Penn
        scores jump toward the AQA distribution, the face block IS the domain detector.

Bench only.
"""
import json, re, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, "/app")

SPLITS = Path("/splits/user_level_multilabel_splits.json")
PENN_KP = Path("/penn_kp")
AQA_SCORES = Path("/app_bench/2026-09-19-v1-test-per-video-scores.json")


def main():
    from app.core.config import get_settings
    from app.ml.posture_v1.loader import PostureV1TorchLoader
    from app.ml.posture_v1.preprocess import preprocess_pose_data
    from app.ml.posture_v1.features_151d import compute_151d_features

    loader = PostureV1TorchLoader(get_settings()); loader._ensure_loaded()
    mean, std = (np.asarray(a, dtype=np.float64) for a in loader.get_scaler_params())
    test = json.loads(SPLITS.read_text())["splits"]["test"]
    penn = [v for v in test["video_names"] if re.fullmatch(r"\d{3,4}", v)]

    rows = []
    for v in penn:
        f = PENN_KP / f"{v}_keypoints.json"
        if not f.exists():
            print("missing", v); continue
        frames = json.loads(f.read_text())
        pose = [fr.get("landmarks") if isinstance(fr, dict) else fr for fr in frames]
        pre = preprocess_pose_data(pose)
        if pre.sequence_length == 0:
            print("no valid frames", v); continue
        raw = compute_151d_features(pre.keypoints, apply_scaler=False,
                                    sequence_length=pre.sequence_length).astype(np.float64)
        def score(feats):
            sc = ((feats - mean) / std).astype(np.float32)
            return float(loader._run_inference(pre.keypoints, sc, pre.sequence_length))
        frozen = raw.copy(); frozen[0:87] = mean[0:87]
        # how far out of distribution is this clip's face block? (mean |z| over [0:87])
        z_face = float(np.mean(np.abs((raw[0:87] - mean[0:87]) / std[0:87])))
        rows.append({"video": v, "prob": score(raw), "prob_face_frozen": score(frozen), "face_abs_z": z_face})

    aqa = [r["prob_fault"] for r in json.loads(AQA_SCORES.read_text())["rows"] if r["class"] == "good_form"]
    p = np.array([r["prob"] for r in rows]); pf = np.array([r["prob_face_frozen"] for r in rows]); a = np.array(aqa)

    def d(x): return f"n={len(x):3d} mean={x.mean():.4f} median={np.median(x):.4f} min={x.min():.4f} max={x.max():.4f} flagged>=0.525: {(x>=0.525).sum()}"
    print("TEST 1 - held-out GOOD-FORM clips, by source domain")
    print("  Penn Action :", d(p))
    print("  Fitness-AQA :", d(a))
    print()
    print("TEST 2 - same Penn clips with the face block frozen at the training mean")
    print("  Penn, face frozen:", d(pf))
    print(f"  mean shift from freezing face: {pf.mean()-p.mean():+.4f}")
    print(f"  Penn face-block mean |z| vs training distribution: {np.mean([r['face_abs_z'] for r in rows]):.3f}")
    print("\n===JSON===")
    print(json.dumps({"penn": rows, "aqa_good_form_probs": aqa}))


if __name__ == "__main__":
    main()
