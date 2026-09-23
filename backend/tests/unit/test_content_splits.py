"""The content-level splits must be leakage-free at BOTH levels, together.

The shipped user-level splits satisfied one of these two constraints and were
believed to satisfy the goal. They did not: 45 byte-identical files span splits
because their copies are filed under different user ids (G-44/G-45).

Satisfying either constraint alone is easy. Satisfying both at once is what
forces the split unit to be a connected component of the graph linking videos
that share a hash OR a user -- and that is the part worth pinning, because the
obvious implementations (group by user, or group by hash) each silently drop
one of the two guarantees.
"""
import json
from collections import Counter, defaultdict
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_SPLITS = (Path(__file__).resolve().parents[3]
           / "bench" / "results" / "content_level_splits.json")


@pytest.fixture(scope="module")
def built():
    if not _SPLITS.exists():
        pytest.skip(f"not built in this layout: {_SPLITS}")
    return json.loads(_SPLITS.read_text())


@pytest.fixture(scope="module")
def assigned(built):
    return [r for r in built["videos"] if r["split"]]


def test_no_content_hash_spans_two_splits(assigned):
    """The bug this exists to prevent. 45 hashes did."""
    by_hash = defaultdict(set)
    for r in assigned:
        if r["content_hash"]:
            by_hash[r["content_hash"]].add(r["split"])
    offenders = {h: s for h, s in by_hash.items() if len(s) > 1}
    assert not offenders, f"{len(offenders)} content hashes span splits"


def test_no_user_spans_two_splits(assigned):
    """The original subject-level guarantee, which must not be lost in fixing
    the content-level one."""
    by_user = defaultdict(set)
    for r in assigned:
        by_user[r["user_id"]].add(r["split"])
    offenders = {u: s for u, s in by_user.items() if len(s) > 1}
    assert not offenders, f"{len(offenders)} users span splits"


def test_every_withheld_video_says_why(built):
    """Two reasons, both legitimate, neither silent:

      * contradictory duplicate labels -- a representative cannot be chosen
        without inventing an answer;
      * no video file on disk -- it can never be joined to a stored decision,
        so assigning it to a split would promise an evaluation that cannot
        happen.
    """
    withheld = [r for r in built["videos"] if not r["split"]]
    assert withheld, "expected some videos to be withheld"
    assert all(r["usable"] is False for r in withheld)
    unexplained = [r["video"] for r in withheld if not r["reason"]]
    assert not unexplained, f"withheld with no reason: {unexplained[:5]}"
    kinds = {("contradictory" in r["reason"]) or ("no video file" in r["reason"])
             for r in withheld}
    assert kinds == {True}, "a withheld video has an unrecognised reason"


def test_contradictory_duplicates_are_withheld_not_guessed(built):
    """80 duplicate groups carry conflicting labels."""
    conflict = [r for r in built["videos"]
                if r["reason"] and "contradictory" in r["reason"]]
    assert len(conflict) == built["n_withheld_label_conflict"] > 0


def test_withheld_videos_are_recorded_not_deleted(built):
    """They are the cheapest labelling work available; dropping them silently
    would hide that."""
    names = {r["video"] for r in built["videos"]}
    assert len(names) == built["n_videos"] == 1625


def test_minimal_mode_preserves_comparability(built):
    """A before/after delta must be attributable to the repair, not to the
    population changing underneath it. Full re-partition moves ~46%."""
    if built.get("mode") != "minimal":
        pytest.skip("built in repartition mode")
    moved_frac = built["n_moved"] / built["n_assigned"]
    assert moved_frac < 0.05, f"{moved_frac:.1%} moved; too much to compare across"


def test_split_ratios_are_close_to_target(built):
    sizes, n = built["sizes"], built["n_assigned"]
    for split, target in built["ratios"].items():
        assert abs(sizes[split] / n - target) < 0.03, (
            f"{split} is {sizes[split]/n:.1%}, target {target:.0%}")


def test_every_class_is_present_in_every_split(built):
    for split, classes in built["class_by_split"].items():
        assert all(classes.get(c, 0) > 0
                   for c in ("good_form", "posture_fault", "depth_fault")), (
            f"{split} is missing a class: {classes}")


def test_the_doc_states_what_this_supersedes_and_what_it_does_not(built):
    doc = built["_doc"]
    assert "G-44" in doc and "G-45" in doc
    assert "user-level splits" in doc and "unchanged" in doc
