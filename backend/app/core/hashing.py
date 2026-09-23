"""One definition of "the same video".

`content_hash` is the join key between three things that are written at
different times by different processes:

  * `form_checks.content_hash`   -- idempotency (user, bytes, model, spec)
  * `analysis_runs.content_hash` -- which bytes a decision was made about
  * `labels.content_hash`        -- what a human said about those bytes

If the upload path and the label importer disagree about how to hash a file by
so much as a chunk boundary, none of those join and the disagreement is
invisible: every query simply returns nothing, which looks like "no labels yet"
rather than "the key is wrong".

So the chunk size is a constant here, not a parameter with a default in two
places, and `sha256_file` and the upload path's `sha256_stream` are the same
algorithm over the same block size.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Union

#: 1 MiB. Videos are large enough that reading one into memory to hash it would
#: defeat the streaming upload that follows. The VALUE does not affect the
#: digest -- sha256 is a stream cipher over the whole input -- but keeping it in
#: one place keeps the two readers obviously identical.
HASH_CHUNK_BYTES = 1024 * 1024

HASH_ALGORITHM = "sha256"
#: Length of a hex sha256. The `content_hash` columns are varchar(64).
HASH_HEX_LENGTH = 64


def sha256_file(path: Union[str, Path], chunk: int = HASH_CHUNK_BYTES) -> str:
    """Hex sha256 of a file on disk, read in chunks."""
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            block = fh.read(chunk)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def sha256_bytes(data: bytes) -> str:
    """Hex sha256 of a bytes object already in memory."""
    return hashlib.sha256(data).hexdigest()


def is_content_hash(value: object) -> bool:
    """Cheap shape check: 64 lowercase hex characters.

    Used by the label importer, which can otherwise cheerfully write a video
    FILENAME into a content_hash column and produce a table that joins to
    nothing.
    """
    if not isinstance(value, str) or len(value) != HASH_HEX_LENGTH:
        return False
    return all(c in "0123456789abcdef" for c in value)
