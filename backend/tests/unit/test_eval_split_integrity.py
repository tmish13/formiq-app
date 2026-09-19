"""
Evaluation-set integrity.

Any accuracy number is only meaningful if the data it was measured on was held
out. The v1 split was not originally shipped with the model, which forced the
face-block ablation (bench/results/2026-09-19-face-block-ablation.md) to publish
its headline F1 with a caveat: "these fixtures may overlap the training split".

The split has since been recovered from the training repo into
artifacts/posture_v1_splits.json. These tests assert the caveat stays resolved.
"""
import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_ARTIFACTS = Path(__file__).resolve().parents[2] / "app" / "ml" / "posture_v1" / "artifacts"
_SPLITS_PATH = _ARTIFACTS / "posture_v1_splits.json"
_MANIFEST_PATH = _ARTIFACTS / "posture_v1_manifest.json"
_FIXTURE_MANIFEST = (
    Path(__file__).resolve().parents[1]
    / "fixtures" / "pose_data" / "in_domain_accuracy" / "manifest.json"
)


@pytest.fixture(scope="module")
def splits() -> dict:
    assert _SPLITS_PATH.exists(), (
        f"v1 split manifest missing: {_SPLITS_PATH}. Without it, no evaluation "
        "number can be shown to be held out."
    )
    return json.loads(_SPLITS_PATH.read_text())


def test_split_manifest_is_user_level_and_matches_the_model_manifest(splits):
    """Splits must be subject-level, and sizes must agree with the shipped model."""
    assert splits["user_level_splits"] is True, (
        "splits are not user-level; the same subject could appear in train and test"
    )

    counts = splits["counts"]
    assert counts["train"] + counts["validation"] + counts["test"] == splits["total_videos"]

    model_manifest = json.loads(_MANIFEST_PATH.read_text())
    recorded = model_manifest["split_sizes"]
    # val/test must match exactly; train differs because the training run filtered
    # some rows after splitting (manifest records 809 of the 1137 split rows).
    assert counts["validation"] == recorded["val"], (
        f"validation size {counts['validation']} != model manifest {recorded['val']}"
    )
    assert counts["test"] == recorded["test"], (
        f"test size {counts['test']} != model manifest {recorded['test']}"
    )
    assert counts["train"] >= recorded["train"], (
        "recovered train split is smaller than the model manifest's train size"
    )


def test_every_ablation_fixture_is_held_out(splits):
    """
    The 50 in-domain fixtures used by bench/ablate_face_block.py must all be in
    the TEST split. If any were training data the reported F1 would be inflated.
    """
    assert _FIXTURE_MANIFEST.exists(), f"fixture manifest missing: {_FIXTURE_MANIFEST}"
    fixtures = json.loads(_FIXTURE_MANIFEST.read_text())
    video_split = splits["video_split"]

    leaked, unknown = [], []
    for name, meta in fixtures.items():
        split = video_split.get(meta["video_id"])
        if split is None:
            unknown.append(meta["video_id"])
        elif split != "test":
            leaked.append((meta["video_id"], split))

    assert not unknown, (
        f"{len(unknown)} fixtures are not in the v1 split manifest at all, so their "
        f"held-out status is unknown: {unknown[:10]}"
    )
    assert not leaked, (
        f"{len(leaked)} evaluation fixtures are NOT held out: {leaked[:10]}. "
        "Any F1 measured on this set is inflated."
    )
    assert len(fixtures) == 50, f"expected 50 in-domain fixtures, got {len(fixtures)}"
