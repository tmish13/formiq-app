"""Writing the decision trail, without ever being able to break the pipeline.

EVERY FUNCTION HERE IS BEST-EFFORT. An audit row that fails to write must
produce a log line and nothing else. The failure mode this rules out is the one
that matters: telemetry throwing after a form check has been claimed, leaving a
row that is PROCESSING with no worker behind it. Phase 1 spent real effort
making the claim atomic and the release reliable; an observability table is not
allowed to undo that.

Three moments:

  `open_run`  -- immediately after the claim, with its OWN commit. If the worker
                 is SIGKILLed one instruction later, the row is already on disk
                 saying `running` with `finished_at` NULL, which is precisely
                 what the reaper sweeps. A run opened inside the task's main
                 transaction would vanish on rollback, and the one case where
                 the audit trail is most useful -- the task that died -- would
                 be the one case with no trail.

  `record_decision` -- one row per (run, checker, target). The unique
                 constraint makes a redelivered task idempotent here rather
                 than doubling its rows.

  `close_run` -- at the TOP of the task's `finally`, before the
                 transient/finalize branching, so a retried task closes as
                 `released` rather than being left open. Issues a bare UPDATE
                 after a rollback: by that point the ORM session may be
                 poisoned by whatever put us in the `finally`.
"""
from __future__ import annotations

import logging
import socket
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Sequence

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import (
    RUN_STATUS_ABANDONED,
    RUN_STATUS_COMPLETED,
    RUN_STATUS_FAILED,
    RUN_STATUS_RELEASED,
    RUN_STATUS_RUNNING,
    AnalysisRun,
    CheckerDecision,
)
from app.services.decisions.types import CheckerOutcome

logger = logging.getLogger(__name__)

__all__ = [
    "open_run", "record_decision", "record_decisions", "close_run",
    "RUN_STATUS_ABANDONED", "RUN_STATUS_COMPLETED", "RUN_STATUS_FAILED",
    "RUN_STATUS_RELEASED", "RUN_STATUS_RUNNING",
]


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def open_run(
    db_session: AsyncSession,
    *,
    form_check_id: Any,
    video_id: Any = None,
    user_id: Any = None,
    celery_task_id: Optional[str] = None,
    attempt: int = 0,
    content_hash: Optional[str] = None,
    model_version: Optional[str] = None,
    spec_hash: Optional[str] = None,
    rules_spec_hash: Optional[str] = None,
    pose_pass_id: Optional[str] = None,
    combiner_version: Optional[str] = None,
    settings_snapshot: Optional[Dict[str, Any]] = None,
) -> Optional[uuid.UUID]:
    """Open a run and COMMIT it on its own. Returns the run id, or None.

    Returning None rather than raising is deliberate: the caller continues
    without a decision trail, which is strictly better than failing an analysis
    that would otherwise have succeeded.
    """
    run_id = uuid.uuid4()
    try:
        run = AnalysisRun(
            id=run_id,
            form_check_id=form_check_id,
            video_id=video_id,
            user_id=user_id,
            celery_task_id=celery_task_id,
            attempt=int(attempt or 0),
            worker_hostname=socket.gethostname()[:255],
            status=RUN_STATUS_RUNNING,
            content_hash=content_hash,
            model_version=model_version,
            spec_hash=spec_hash,
            rules_spec_hash=rules_spec_hash,
            pose_pass_id=pose_pass_id,
            combiner_version=combiner_version,
            settings_snapshot=settings_snapshot,
            started_at=_now(),
        )
        db_session.add(run)
        await db_session.commit()
        logger.info("[Audit] run %s opened for FormCheck %s (attempt %d)",
                    run_id, form_check_id, attempt)
        return run_id
    except Exception as exc:
        logger.warning("[Audit] could not open a run for FormCheck %s: %s",
                       form_check_id, exc)
        try:
            await db_session.rollback()
        except Exception:
            pass
        return None


async def record_decision(
    db_session: AsyncSession,
    *,
    run_id: Optional[uuid.UUID],
    outcome: CheckerOutcome,
    form_check_id: Any = None,
    content_hash: Optional[str] = None,
) -> bool:
    """Write one checker decision. No commit -- the caller's transaction owns it.

    Not committing here is the point: a decision row belongs to the same unit of
    work as the results it explains, so the two cannot disagree about whether
    the analysis happened.
    """
    if run_id is None:
        return False
    try:
        row = CheckerDecision(
            id=uuid.uuid4(),
            run_id=run_id,
            form_check_id=form_check_id,
            content_hash=content_hash,
            **outcome.as_row(),
        )
        db_session.add(row)
        # Flush THIS row on its own, rather than letting several accumulate.
        #
        # SQLAlchemy 2.0 batches same-table INSERTs through insertmanyvalues and
        # matches the returned rows back to their parameter sets using the
        # primary key as a "sentinel". `SQLiteUUID` is a TypeDecorator that
        # BINDS a str and RETURNS a uuid.UUID, so the sentinel never matches and
        # the whole batch fails with:
        #
        #   Can't match sentinel values in result set to parameter sets
        #
        # `posture_v1_inference_logs` uses the same type and never hit this,
        # because a task adds exactly one telemetry row. A run adds three or
        # more decisions at once, which is what crosses the batching threshold.
        #
        # One flush per row is a single INSERT and sidesteps it entirely. Three
        # statements per analysis is not a cost worth optimising against a
        # 40-second pose pass.
        await db_session.flush()
        return True
    except Exception as exc:
        logger.warning("[Audit] could not record %s/%s for run %s: %s",
                       outcome.checker_name, outcome.target, run_id, exc)
        return False


async def record_decisions(
    db_session: AsyncSession,
    *,
    run_id: Optional[uuid.UUID],
    outcomes: Sequence[CheckerOutcome],
    form_check_id: Any = None,
    content_hash: Optional[str] = None,
) -> int:
    written = 0
    for o in outcomes:
        if await record_decision(db_session, run_id=run_id, outcome=o,
                                 form_check_id=form_check_id,
                                 content_hash=content_hash):
            written += 1
    return written


async def close_run(
    db_session: AsyncSession,
    *,
    run_id: Optional[uuid.UUID],
    status: str,
    outcome_status: Optional[str] = None,
    final_decision: Optional[str] = None,
    final_score: Optional[float] = None,
    error_type: Optional[str] = None,
    error_message: Optional[str] = None,
    latency_ms: Optional[float] = None,
    n_frames: Optional[int] = None,
    fps: Optional[float] = None,
    duration_sec: Optional[float] = None,
    pose_source: Optional[str] = None,
    pose_pass_id: Optional[str] = None,
    rules_spec_hash: Optional[str] = None,
    settings_snapshot: Optional[Dict[str, Any]] = None,
) -> bool:
    """Close a run with a bare UPDATE, rolling back first.

    This runs in the task's `finally`, where the session may be poisoned by the
    exception that brought us here. The ORM would try to flush whatever half
    state it is holding; a rollback followed by one statement will not.

    Only sets the columns it was given: a caller that does not know the frame
    count must not blank one that was already recorded.
    """
    if run_id is None:
        return False
    values: Dict[str, Any] = {"status": status, "finished_at": _now()}
    for key, val in (
        ("outcome_status", outcome_status),
        ("final_decision", final_decision),
        ("final_score", final_score),
        ("error_type", error_type),
        ("error_message", error_message),
        ("latency_ms", latency_ms),
        ("n_frames", n_frames),
        ("fps", fps),
        ("duration_sec", duration_sec),
        ("pose_source", pose_source),
        ("pose_pass_id", pose_pass_id),
        ("rules_spec_hash", rules_spec_hash),
        ("settings_snapshot", settings_snapshot),   # per-stage ms live here; no migration (D6)
    ):
        if val is not None:
            values[key] = val
    try:
        await db_session.rollback()
        await db_session.execute(
            sa.update(AnalysisRun)
            .where(AnalysisRun.id == run_id)
            .where(AnalysisRun.finished_at.is_(None))   # never reopen a closed run
            .values(**values)
        )
        await db_session.commit()
        logger.info("[Audit] run %s closed as %s", run_id, status)
        return True
    except Exception as exc:
        # The database is very likely what just failed. The reaper's unclosed-run
        # sweep is the backstop for exactly this.
        logger.warning("[Audit] could not close run %s as %s: %s. "
                       "The reaper will abandon it.", run_id, status, exc)
        return False
