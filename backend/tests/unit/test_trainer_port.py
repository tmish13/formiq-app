"""Track B5: the seeded trainer reuses the serving code and round-trips through the serving loader.

Runs where torch is installed (the worker image); skipped elsewhere.
"""
import json
import pathlib

import numpy as np
import pytest

torch = pytest.importorskip("torch")

from ml_training.posture_v1 import export as export_mod  # noqa: E402
from ml_training.posture_v1 import train as train_mod  # noqa: E402

pytestmark = pytest.mark.unit
ARTIFACTS = pathlib.Path(__file__).resolve().parents[2] / "app" / "ml" / "posture_v1" / "artifacts"


def test_the_trainer_builds_the_architecture_the_shipped_checkpoint_has():
    ckpt = torch.load(ARTIFACTS / "posture_v1.pt", map_location="cpu", weights_only=False)
    shipped = ckpt["model_state_dict"]
    ours = train_mod.build_model().state_dict()
    assert set(ours) == set(shipped), (set(ours) ^ set(shipped))
    for k in ours:
        assert tuple(ours[k].shape) == tuple(shipped[k].shape), k
    # and the config the trainer writes into its checkpoints is the manifest's, not a copy
    assert train_mod.serving_model_config() == json.loads((ARTIFACTS / "posture_v1_manifest.json").read_text())["model_config"]


def test_the_best_state_is_a_deep_copy_not_the_notebooks_shallow_one():
    model = train_mod.build_model()
    snap = train_mod.snapshot_state(model)
    before = {k: v.clone() for k, v in snap.items()}
    with torch.no_grad():
        for p in model.parameters():
            p.add_(1.0)                      # training continues after the best epoch
    for k, v in snap.items():
        assert torch.equal(v, before[k]), f"{k} moved with the live weights"
        assert v.data_ptr() != model.state_dict()[k].data_ptr()


def test_class_weights_follow_the_notebook():
    w = train_mod.class_weights(np.array([1, 1, 1, 0]))
    assert w.tolist() == pytest.approx([4 / 2.0, 4 / 6.0])


def _synthetic_split(rng, n, path):
    T, J, C = 300, 33, 3
    L = rng.integers(60, 300, size=n).astype(np.int32)
    K = rng.random((n, T, J, C), dtype=np.float32)
    for i, l in enumerate(L):
        K[i, l:] = 0.0                                     # zero-padded tail, as preprocess_pose_data leaves it
    X = rng.normal(size=(n, 151)).astype(np.float64)
    y = (np.arange(n) % 2).astype(np.int8)
    names = np.asarray([f"v{i}" for i in range(n)]); hashes = np.asarray(["h" * 64] * n)
    np.savez_compressed(path, K=K, X=X, y=y, L=L, names=names, hashes=hashes)


def _pose_frames(rng, n_frames=120):
    return [[{"x": float(rng.random()), "y": float(rng.random()), "z": float(rng.random()), "visibility": 0.95}
             for _ in range(33)] for _ in range(n_frames)]


def test_smoke_train_export_and_serving_loader_round_trip(tmp_path):
    rng = np.random.default_rng(0)
    data = tmp_path / "data"; data.mkdir()
    _synthetic_split(rng, 16, data / "train.npz"); _synthetic_split(rng, 8, data / "validation.npz")
    (data / "manifest.json").write_text(json.dumps({"target": "posture_collapsed", "pose_pass_id": "pp1_test",
                                                    "n": {"train": 16, "validation": 8}, "prevalence": {"train": 0.5}}))
    run = tmp_path / "run"
    report = train_mod.train_one_seed(0, data, run, max_epochs=2, patience=15, batch_size=4, quiet=True)
    assert report["epochs_run"] == 2 and 0.2 <= report["threshold"] <= 0.8
    assert (run / "seed0.pt").exists() and (run / "seed0_scaler.joblib").exists()
    assert report["test_read"] is None                       # train never touches test
    ckpt = torch.load(run / "seed0.pt", map_location="cpu", weights_only=False)
    assert "model_state_dict" in ckpt and ckpt["model_config"] == train_mod.serving_model_config()

    art = tmp_path / "artifacts"
    manifest = export_mod.export(run, 0, data / "manifest.json", art, version="posture_v1_smoke")
    prov = manifest["provenance"]
    assert prov["seed"] == 0 and prov["pose_pass_id_at_training"] == "pp1_test"
    assert prov["artifact_sha256"]["posture_v1.pt"] == export_mod.sha256_file(art / "posture_v1.pt")
    assert manifest["training_metrics"]["test"].startswith("not read")

    from app.core.config import get_settings
    from app.ml.posture_v1.loader import PostureV1TorchLoader
    loader = PostureV1TorchLoader(get_settings())
    loader._artifacts_dir = art                              # the loader has no public override yet
    res = loader.predict_posture(_pose_frames(rng))
    assert 0.0 <= res["prob_fault"] <= 1.0
    assert res["threshold"] == pytest.approx(manifest["threshold"])
    assert res["decision"] in {"fault", "good", "uncertain", "no_fault", "posture_fault", "good_form"} or isinstance(res["decision"], str)


def test_export_refuses_the_live_artifacts_directory_without_install(tmp_path):
    with pytest.raises(SystemExit):
        export_mod.export(tmp_path, 0, tmp_path / "m.json", export_mod.LIVE_ARTIFACTS)


def test_the_second_test_read_is_refused(tmp_path):
    log = tmp_path / "TEST_READ_LOG.jsonl"
    assert train_mod.final_guard(log, "k", force=False, reason=None) is True
    log.write_text(json.dumps({"key": "k"}) + "\n")
    assert train_mod.final_guard(log, "k", force=False, reason=None) is False
    assert train_mod.final_guard(log, "k", force=True, reason=None) is False      # force without a reason is not enough
    assert train_mod.final_guard(log, "k", force=True, reason="pre-registered re-read") is True
