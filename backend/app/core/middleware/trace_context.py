"""Trace context middleware — pure ASGI implementation.

Pure ASGI (not BaseHTTPMiddleware) so it does not add a nested anyio task
group layer.  Starlette 0.36.x has a known edge case where multiple nested
BaseHTTPMiddleware instances can produce RuntimeError("No response returned")
because the memory-stream / task-group pairing in call_next interacts badly
when exceptions propagate through the stack.  Converting this middleware to
pure ASGI removes one layer of nesting and eliminates the bad `raise` path
that was triggering the error.
"""

import uuid
import logging

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.tracing import get_trace_context, is_tracing_enabled

logger = logging.getLogger(__name__)


class TraceContextMiddleware:
    """Pure-ASGI middleware that injects a correlation / trace ID into every
    HTTP request/response pair.

    * Reads ``x-correlation-id`` (or ``correlation-id``) from the incoming
      request headers; generates a short UUID if none is present.
    * Appends ``X-Correlation-ID`` (and OTel trace/span IDs when available)
      to the *response* headers via a ``send`` wrapper (no scope mutation).
    """

    def __init__(self, app: ASGIApp, generate_correlation_id: bool = True) -> None:
        self.app = app
        self.generate_correlation_id = generate_correlation_id

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # ── Extract or generate correlation ID ───────────────────────────
        correlation_id = self._get_correlation_id(scope)

        # ── Optional OTel trace context ───────────────────────────────────
        trace_context: dict = {}
        if is_tracing_enabled():
            trace_context = get_trace_context()
            # An UNSAMPLED request (the default sampler keeps 10 %) carries an
            # all-zero span id, and it was being handed out as the correlation
            # id: nine responses in ten said "0000000000000000", and five
            # concurrent requests in the test suite shared one "unique" id for
            # as long as this middleware existed. All-zero means absent.
            tc_cid = trace_context.get("correlation_id") or ""
            if not correlation_id and tc_cid.strip("0"):
                correlation_id = tc_cid

        if not correlation_id and self.generate_correlation_id:
            correlation_id = str(uuid.uuid4())[:16]

        # ── Wrap send to inject headers into the response ─────────────────
        async def send_with_trace_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                if correlation_id:
                    headers.append("X-Correlation-ID", correlation_id)
                if trace_context.get("trace_id"):
                    headers.append("X-Trace-ID", trace_context["trace_id"])
                if trace_context.get("span_id"):
                    headers.append("X-Span-ID", trace_context["span_id"])
            await send(message)

        await self.app(scope, receive, send_with_trace_headers)

    # ── Helpers ───────────────────────────────────────────────────────────

    def _get_correlation_id(self, scope: Scope) -> str:
        """Return the first correlation-ID header found, or empty string."""
        _wanted = {b"x-correlation-id", b"x-correlation-id", b"correlation-id"}
        for name, value in scope.get("headers", []):
            if name.lower() in _wanted:
                try:
                    return value.decode("latin-1")
                except Exception:
                    pass
        return ""


# ── Module-level helpers (kept for backward compat) ───────────────────────

def get_correlation_id_from_scope(scope: Scope) -> str:
    """Return correlation ID stored on scope state, or empty string."""
    state = scope.get("state")
    if state is None:
        return ""
    try:
        return getattr(state, "correlation_id", "") or ""
    except Exception:
        return state.get("correlation_id", "") if isinstance(state, dict) else ""


def get_correlation_id(request) -> str:
    """Return correlation ID from a Starlette Request object."""
    return getattr(getattr(request, "state", None), "correlation_id", "") or ""


def get_request_trace_context(request) -> dict:
    """Return trace context dict from a Starlette Request object."""
    return getattr(getattr(request, "state", None), "trace_context", {}) or {}
