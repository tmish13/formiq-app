"""G-20: the shipped artifacts match the hashes their manifest records -- the model's image_check.

A Git LFS pointer, a re-exported scaler or a swapped checkpoint all fail here with the file named.
"""
import hashlib
import json
import pathlib

import pytest

pytestmark = pytest.mark.unit

ARTIFACTS = pathlib.Path(__file__).resolve().parents[2] / "app" / "ml" / "posture_v1" / "artifacts"


def _sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def manifest():
    return json.loads((ARTIFACTS / "posture_v1_manifest.json").read_text())


def test_every_artifact_matches_the_manifest_hash(manifest):
    recorded = manifest["provenance"]["artifact_sha256"]
    assert set(recorded) == {"posture_v1.pt", "posture_v1_scaler.joblib", "posture_v1_splits.json"}
    for name, expected in recorded.items():
        path = ARTIFACTS / name
        assert path.exists(), f"{name} missing"
        head = path.read_bytes()[:12]
        assert not head.startswith(b"version http"), f"{name} is a Git LFS pointer, not the artifact"
        assert _sha256(path) == expected, f"{name} does not match the manifest (re-exported or swapped?)"


def test_the_checkpoint_is_the_recorded_source_checkpoint(manifest):
    prov = manifest["provenance"]
    assert prov["artifact_sha256"]["posture_v1.pt"] == prov["source_checkpoint_sha256"]
    assert manifest["source_checkpoint"] in prov["source_checkpoint_path"]


def test_the_provenance_says_what_is_unknown(manifest):
    prov = manifest["provenance"]
    assert prov["recipe"]["seed"] is None          # unseeded training is a fact, not an omission
    assert prov["code_git_sha"] is None
    assert len(prov["discrepancies"]) >= 4
    # serving still reads exactly what it read before this block existed
    assert manifest["threshold"] == 0.525 and manifest["version"] == "v1"
