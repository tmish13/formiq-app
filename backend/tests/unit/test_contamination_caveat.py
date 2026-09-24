"""No file may quote a contaminated performance figure without naming G-44.

Every published number in this repo was measured on an evaluation set that was
partly in training (105 byte-identical duplicate videos, 45 spanning splits).
The numbers are not being re-measured -- doing that after a data change is how
a negative result quietly becomes a positive one -- so they stand as upper
bounds WITH a stated defect.

A pinned number carrying a stated defect is fine. A pinned number quoted clean
is a false claim, and the only thing that reliably stops one reappearing is a
test that fails.

This is the same lesson as the rest of the month, applied to prose: G-38
(`alembic check` permanently red), G-43 (a dependency fix that never reached
the image), G-45 (held-out-ness asserted by filename), and Stage A's 24 lost
decision rows all passed a green check while being wrong. Assert on what is
written, never on the absence of a complaint.
"""
import re
from pathlib import Path

import pytest

from app.eval.provenance import CONTAMINATED_FIGURES, CONTAMINATION_CAVEAT_ID

pytestmark = pytest.mark.unit

_SCANNED_SUFFIXES = (".md", ".py", ".json")
_SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".pytest_cache", ".venv", "venv",
    "cache",          # bench/cache -- extracted keypoints, not claims
    "htmlcov", "dist", "build", ".mypy_cache", ".ruff_cache",
}

#: Files allowed to carry a figure without the caveat, each with a reason.
#: These hold raw per-run measurements that are INPUTS to an analysis rather
#: than claims made to a reader. Keep this list short and justified: every
#: entry is a place the caveat is NOT shown to whoever opens the file.
_ALLOWED = {
    "bench/results/2026-09-19-v1-test-per-video-scores.json":
        "raw per-video probabilities; the input the pinned figures were "
        "computed FROM, not a statement of them",
    "backend/app/eval/provenance.py":
        "defines the caveat and lists the guarded figures",
    "backend/tests/unit/test_contamination_caveat.py":
        "this test -- it names the guarded figures in order to guard them",
}


def _repo_root() -> Path:
    """The directory to scan, from either checkout layout.

    On the host that is the repo root. In the worker image only `backend/` is
    mounted at /app, so `bench/` does not exist -- scan what is there. Same
    layout-awareness as test_metrics_parity.py.
    """
    here = Path(__file__).resolve()
    backend = here.parents[2]
    return backend.parent if (backend.parent / "bench").is_dir() else backend


def _quotes(src: str, figure: str) -> bool:
    """Is `figure` present as a COMPLETE number, not a prefix of a longer one?

    Plain substring matching is too loose: segmentation_validation.json records
    an IoU of 0.7692307692307693 (10/13), which contains "0.7692" and has
    nothing to do with the ablation F1. Guarding it would have meant an
    allow-list entry excusing a file that never made the claim -- and every
    unjustified exemption is how a guard gets widened until it guards nothing.
    """
    return re.search(rf"(?<!\d){re.escape(figure)}(?!\d)", src) is not None


def _iter_files(root: Path):
    for p in root.rglob("*"):
        if p.suffix not in _SCANNED_SUFFIXES or not p.is_file():
            continue
        if any(part in _SKIP_DIRS for part in p.parts):
            continue
        yield p


def _rel(p: Path, root: Path) -> str:
    rel = p.relative_to(root).as_posix()
    # In-container the root IS backend/, so normalise to repo-relative keys.
    return rel if rel.startswith(("backend/", "bench/")) else f"backend/{rel}"


@pytest.fixture(scope="module")
def offenders():
    root = _repo_root()
    out = []
    for p in _iter_files(root):
        try:
            src = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        found = [f for f in CONTAMINATED_FIGURES if _quotes(src, f)]
        if not found:
            continue
        if CONTAMINATION_CAVEAT_ID in src:
            continue
        rel = _rel(p, root)
        if rel in _ALLOWED:
            continue
        out.append((rel, found))
    return out


def test_no_file_quotes_a_contaminated_figure_without_the_caveat(offenders):
    assert not offenders, (
        "These files quote a figure measured on contaminated data without "
        f"naming {CONTAMINATION_CAVEAT_ID}:\n"
        + "\n".join(f"  {rel}  -> {figs}" for rel, figs in offenders)
        + "\n\nAdd app.eval.provenance.CONTAMINATION_CAVEAT (or "
          "CONTAMINATION_CAVEAT_SHORT for a JSON field / table cell). Do NOT "
          "change the numbers and do NOT re-measure."
    )


def test_the_allow_list_entries_still_exist(offenders):
    """An allow-list entry for a file that has moved silently stops guarding it."""
    root = _repo_root()
    missing = []
    for rel in _ALLOWED:
        on_host = root / rel
        in_container = root / rel.removeprefix("backend/")
        if not on_host.exists() and not in_container.exists():
            missing.append(rel)
    # Guard on the results directory, not a bare `bench` dir: an empty
    # `backend/bench` (left behind by a container run) made this fail in the
    # image, where the allow-listed files are legitimately absent.
    if missing and (root / "bench" / "results").is_dir():
        pytest.fail(f"allow-listed paths no longer exist: {missing}")


def test_every_allow_list_entry_has_a_reason():
    assert all(isinstance(v, str) and len(v) > 20 for v in _ALLOWED.values()), (
        "every allow-list entry needs a written reason -- an unexplained "
        "exemption is how the guard gets widened until it guards nothing")


def test_the_guard_actually_matches_something():
    """A scanner that finds nothing anywhere is broken, not clean."""
    root = _repo_root()
    hits = sum(1 for p in _iter_files(root)
               if any(_quotes(p.read_text(encoding="utf-8", errors="ignore"), f)
                      for f in CONTAMINATED_FIGURES))
    assert hits > 0, "no file contains any guarded figure -- the scanner is broken"


def test_a_longer_number_that_merely_starts_with_a_figure_is_not_a_quote():
    """0.7692307692307693 is an IoU of 10/13 in segmentation_validation.json.
    Substring matching flagged it and would have required an allow-list entry
    excusing a file that never made the claim."""
    assert _quotes("f1: 0.7692,", "0.7692")
    assert not _quotes('"iou": 0.7692307692307693,', "0.7692")
    assert not _quotes("0.61312", "0.6131")
