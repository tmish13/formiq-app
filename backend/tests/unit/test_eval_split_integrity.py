"""
Evaluation-set integrity.

Any accuracy number is only meaningful if the data it was measured on was held
out. The v1 split was not originally shipped with the model, which forced the
face-block ablation (bench/results/2026-09-19-face-block-ablation.md) to publish
its headline F1 with a caveat: "these fixtures may overlap the training split".

The split has since been recovered from the training repo into
artifacts/posture_v1_splits.json. These tests assert the caveat stays resolved.

G-45 -- HELD-OUT BY NAME IS NOT HELD OUT BY CONTENT
----------------------------------------------------
Everything below checks split membership by VIDEO NAME. That is necessary and
it is not sufficient, and this file was green throughout while it was wrong:
the corpus holds 105 byte-identical duplicate videos filed under different
names (G-44), 45 of them spanning splits. Seven of the fifty fixtures asserted
"held out" here have a byte-identical twin in the TRAIN split. The model was
fitted on those exact bytes and then scored on them under another filename, and
test_every_ablation_fixture_is_held_out passed on all seven.

The same applies to user_level_splits: partitioning by user id guarantees no
SUBJECT appears in two splits, which is a different claim from no CONTENT
appearing in two splits. 104 identical files are filed under different user
ids, so the second claim is false while the first stays true.

test_no_fixture_has_a_byte_identical_twin_in_train below is the content-level
check. It is expected to fail until the corpus is de-duplicated; it is marked
xfail so the failure is REPORTED rather than hidden or blocking, and it turns
green on its own once the duplicates are removed.
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
    """Splits must be subject-level, and sizes must agree with the shipped model.

    Subject-level is NECESSARY AND NOT SUFFICIENT -- see G-45 in the module
    docstring. This says no subject spans splits. It does not say no CONTENT
    spans splits, and 45 byte-identical files do.
    """
    assert splits["user_level_splits"] is True, (
        "splits are not user-level; the same subject could appear in train and "
        "test. NOTE (G-44/G-45): user-level is not content-level -- this passing "
        "does not mean the evaluation set is uncontaminated; see "
        "test_no_fixture_has_a_byte_identical_twin_in_train"
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

    BY NAME ONLY. Seven of these fifty have byte-identical twins in train and
    this test passes on all seven (G-45). Keep it -- a name-level violation is
    still a real defect -- but read it as "no fixture is LISTED in train", not
    as "no fixture was seen during training".
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
        f"{len(leaked)} evaluation fixtures are NOT held out BY NAME: "
        f"{leaked[:10]}. Any F1 measured on this set is inflated."
    )
    assert len(fixtures) == 50, f"expected 50 in-domain fixtures, got {len(fixtures)}"


# The seven fixtures whose bytes are in train, listed rather than counted: the
# xfail should name its subjects, and a count goes stale silently.
_KNOWN_CONTAMINATED_FIXTURES = {
    "50860_2", "50844_1", "50862_1", "38108_4", "50838_1", "36049_2", "33072_1",
}

_DUP_REPORT = (
    Path(__file__).resolve().parents[3] / "bench" / "results" / "corpus_duplicates.json"
)


def _train_twinned() -> set:
    """Videos with a byte-identical twin in TRAIN, per bench/corpus_duplicates.py."""
    groups = json.loads(_DUP_REPORT.read_text())["groups"]
    return {
        m["video"]
        for members in groups.values()
        for m in members
        if any(o["split"] == "train" for o in members if o["video"] != m["video"])
    }


def _contaminated_fixtures() -> set:
    fixtures = json.loads(_FIXTURE_MANIFEST.read_text())
    twinned = _train_twinned()
    return {meta["video_id"] for meta in fixtures.values()
            if meta["video_id"] in twinned}


@pytest.mark.xfail(
    strict=False,
    reason="G-44: 7 of the 50 fixtures have byte-identical twins in TRAIN. A "
           "STANDING RED FLAG, not a waiver -- it fails until the corpus is "
           "de-duplicated by content hash and turns green on its own when it "
           "is. See bench/results/2026-09-23-corpus-duplicates.md.",
)
def test_no_fixture_has_a_byte_identical_twin_in_train():
    """The content-level check the name-level ones cannot make."""
    if not _DUP_REPORT.exists():
        pytest.skip(f"duplicate report not in this layout: {_DUP_REPORT}")
    hit = sorted(_contaminated_fixtures())
    n = len(json.loads(_FIXTURE_MANIFEST.read_text()))
    assert not hit, (
        f"{len(hit)} of {n} evaluation fixtures have a byte-identical twin in "
        f"TRAIN, so they were never held out: {hit}. The model was fitted on "
        "these exact bytes and is scored on them here."
    )


def test_the_contaminated_fixture_set_has_not_changed():
    """Notices a de-duplication pass, or a regression.

    Pinned separately from the xfail because an xfail that starts failing for a
    NEW reason still just reads as "xfail".
    """
    if not _DUP_REPORT.exists():
        pytest.skip("duplicate report not in this layout")
    hit = _contaminated_fixtures()
    new = sorted(hit - _KNOWN_CONTAMINATED_FIXTURES)
    gone = sorted(_KNOWN_CONTAMINATED_FIXTURES - hit)
    assert not new, f"new contaminated fixtures appeared: {new}"
    assert not gone, (
        "fewer contaminated fixtures than recorded. If the corpus was "
        "de-duplicated, drop the xfail on "
        "test_no_fixture_has_a_byte_identical_twin_in_train and update "
        f"_KNOWN_CONTAMINATED_FIXTURES. Gone: {gone}")
