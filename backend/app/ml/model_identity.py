"""Model identity for the idempotency key — readable without loading PyTorch.

The submit path runs in the API process and must not import torch or the model
just to learn which version it will be scored under, so this reads the manifest
JSON directly and caches it.

PostureV1 predates the ``spec_hash()`` that ``app/ml/posture_v2/features.py``
provides, so its feature spec is identified by the manifest's
``feature_order_version`` ("truth_spec_151d_v1") rather than a real hash. When
v2 lands it supplies a computed hash and this returns that instead; either way
the value's job is the same -- change it and the idempotency key changes, so the
same video is re-analysed under the new spec.
"""
import functools
import json
import logging
from pathlib import Path
from typing import Tuple

logger = logging.getLogger(__name__)

# Lives in app/ml/, NOT app/ml/posture_v1/: that package's __init__ imports the
# loader, which imports torch. Reading a version string must not cost a model
# import, so the path is spelled out from here instead.
_MANIFEST = (
    Path(__file__).resolve().parent
    / "posture_v1" / "artifacts" / "posture_v1_manifest.json"
)

# Used when the manifest cannot be read. Distinct on purpose: rows written during
# an outage must not collide with rows written from a healthy manifest, or a
# broken deploy would poison the cache for real submissions.
_UNKNOWN = "unknown"


@functools.lru_cache(maxsize=1)
def posture_v1_identity() -> Tuple[str, str]:
    """Return ``(model_version, spec_hash)`` for the active PostureV1 model."""
    try:
        manifest = json.loads(_MANIFEST.read_text())
    except Exception as e:
        logger.error(
            "Could not read PostureV1 manifest at %s (%s); idempotency will not "
            "dedupe until this is fixed.", _MANIFEST, e,
        )
        return _UNKNOWN, _UNKNOWN

    model_version = "{}:{}".format(
        manifest.get("model_name", _UNKNOWN), manifest.get("version", _UNKNOWN)
    )
    spec_hash = manifest.get("feature_order_version") or _UNKNOWN
    return model_version, spec_hash


def is_identity_known() -> bool:
    """False when the manifest could not be read, so callers can skip deduping."""
    return posture_v1_identity() != (_UNKNOWN, _UNKNOWN)
