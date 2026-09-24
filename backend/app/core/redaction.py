"""Log redaction (G-16): tokens, passwords and e-mail addresses do not reach a log line.

Two hooks over one rule set:

- ``redact_event`` is a structlog processor placed just before the JSON renderer, so every key and
  value the app logs through structlog (nested ``extra`` dicts included) is scrubbed;
- ``RedactingFilter`` is a stdlib ``logging.Filter`` attached to every handler, so plain
  ``logging.getLogger(...)`` messages, args already applied, are scrubbed too.

Rules: a key named like a credential has its value replaced whole; inside any string, JWT-shaped
tokens, ``Bearer <token>`` credentials, ``password=<value>``-style fragments and the local part of
e-mail addresses are masked. The e-mail domain is kept: it is what you need to debug delivery; the
local part identifies a person and is not.
"""
from __future__ import annotations

import logging
import re
from typing import Any

MASK = "***"

SENSITIVE_KEYS = re.compile(
    r"(?i)^(authorization|password|passwd|password_hash|hashed_password|secret|client_secret|"
    r"token|access_token|refresh_token|id_token|api_key|apikey|x-api-key|private_key|cookie|set-cookie)$"
)
_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+\.[A-Za-z]{2,})\b")
_JWT = re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b")
_BEARER = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{8,}")
# `password=hunter2`, `token: abc`; a value starting with % is a logging placeholder, left alone.
_KV = re.compile(r"(?i)\b(password|passwd|secret|token|api_key|access_token|refresh_token)(\s*[=:]\s*)((?!%)[^\s,;&\"']+)")
_MAX_DEPTH = 8


def redact_text(s: str) -> str:
    s = _JWT.sub(MASK, s)
    s = _BEARER.sub("Bearer " + MASK, s)
    s = _KV.sub(lambda m: m.group(1) + m.group(2) + MASK, s)
    s = _EMAIL.sub(lambda m: MASK + "@" + m.group(1), s)
    return s


def redact_obj(o: Any, key: Any = None, _depth: int = 0) -> Any:
    if key is not None and isinstance(key, str) and SENSITIVE_KEYS.match(key):
        return MASK
    if _depth > _MAX_DEPTH:
        return o
    if isinstance(o, str):
        return redact_text(o)
    if isinstance(o, dict):
        return {k: redact_obj(v, k, _depth + 1) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return type(o)(redact_obj(v, None, _depth + 1) for v in o)
    return o


def redact_event(logger, method_name, event_dict):  # structlog processor signature
    return redact_obj(event_dict)


class RedactingFilter(logging.Filter):
    """Scrub the fully formatted message so templates and args are covered alike."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            message = record.getMessage()
        except Exception:
            return True
        scrubbed = redact_text(message)
        if scrubbed != message:
            record.msg = scrubbed
            record.args = ()
        return True
