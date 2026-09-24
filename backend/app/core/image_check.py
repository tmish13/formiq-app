"""Does the running image contain what requirements.txt says it does?  (G-43)

`pytest-timeout` was added to requirements.txt on 2026-09-20 and the gap it fixed
was marked closed; the app and worker images were never rebuilt, so the fix lived
in a text file and not in the process that needed it, for three days. Nothing
forced a rebuild and nothing said the image was stale.

This compares every pinned `name==version` line against what is importable, at
process start (API lifespan, Celery worker init) and on demand from the CLI:

    python -m app.core.image_check        # exit 1 on any mismatch; for CI and compose healthchecks

Only exact pins are checked. `>=` lines are floors, not statements about the
image, and are skipped -- listed in the result so the gap is visible, never
silently ignored. A mismatch never stops the process: it is logged as an error
and exposed to /health, because a running service with a stale dependency is
still better than no service, as long as someone can see it.
"""
from __future__ import annotations

import logging
import re
import sys
from dataclasses import dataclass, field
from importlib import metadata
from pathlib import Path
from typing import Callable, List, Optional

logger = logging.getLogger(__name__)

_PIN = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)(?:\[[^\]]*\])?\s*==\s*([^\s;#]+)")
_FLOOR = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)(?:\[[^\]]*\])?\s*(>=|~=|>|<|!=)")


def _norm(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


@dataclass
class ImageCheck:
    checked: int = 0
    mismatches: List[str] = field(default_factory=list)   # "name: pinned X, installed Y"
    missing: List[str] = field(default_factory=list)      # pinned but not importable
    unpinned: List[str] = field(default_factory=list)     # floors, not checked

    @property
    def ok(self) -> bool:
        return not self.mismatches and not self.missing

    def summary(self) -> str:
        return (f"image check: {self.checked} pins checked, {len(self.mismatches)} mismatched, "
                f"{len(self.missing)} missing, {len(self.unpinned)} unpinned lines skipped")


def default_requirements_path() -> Path:
    # app/core/image_check.py -> backend/requirements.txt; /app/requirements.txt in the image.
    return Path(__file__).resolve().parents[2] / "requirements.txt"


def check_image(requirements: Optional[Path] = None,
                installed_version: Callable[[str], str] = metadata.version) -> ImageCheck:
    """Pure function over the requirements text and a version lookup (injectable for tests)."""
    path = requirements or default_requirements_path()
    result = ImageCheck()
    try:
        lines = path.read_text().splitlines()
    except OSError as e:
        result.missing.append(f"requirements.txt unreadable: {e}")
        return result
    for line in lines:
        m = _PIN.match(line)
        if not m:
            f = _FLOOR.match(line)
            if f:
                result.unpinned.append(_norm(f.group(1)))
            continue
        name, pinned = _norm(m.group(1)), m.group(2)
        result.checked += 1
        try:
            have = installed_version(name)
        except metadata.PackageNotFoundError:
            result.missing.append(f"{name}: pinned {pinned}, not installed")
            continue
        if _norm(have) != _norm(pinned):
            result.mismatches.append(f"{name}: pinned {pinned}, installed {have}")
    return result


LAST: Optional[ImageCheck] = None   # what the running process saw at start; read by /health


def run_and_log(where: str) -> ImageCheck:
    """Called at API and worker start. Logs; never raises."""
    global LAST
    try:
        LAST = check_image()
    except Exception as e:  # a check that crashes the process would be worse than the drift
        logger.error("image check failed to run in %s: %s", where, e)
        LAST = ImageCheck(missing=[f"check failed: {e}"])
        return LAST
    if LAST.ok:
        logger.info("[%s] %s", where, LAST.summary())
    else:
        logger.error("[%s] %s -- the image is stale (G-43): %s", where, LAST.summary(),
                     "; ".join(LAST.mismatches + LAST.missing))
    return LAST


def main(argv: Optional[List[str]] = None) -> int:
    path = Path(argv[0]) if argv else None
    res = check_image(path)
    print(res.summary())
    for line in res.mismatches + res.missing:
        print("  MISMATCH", line)
    return 0 if res.ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
