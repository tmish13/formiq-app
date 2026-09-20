"""Periodic maintenance: recover form checks that no worker is working on.

Every other safety net on this branch is in-process, so none of them survives the
failure that started it: a worker that dies without running a single `finally`.
That run left 17 of 20 form checks sitting at PENDING forever, with the broker
already acked and nothing left to notice.

Two stuck shapes, both scanned here:

  PENDING for too long
      The task was accepted but never claimed. This is the exact shape of the
      gevent failure -- the task raised inside asyncio.run() before it ever set
      PROCESSING, so the row never moved. Late acks (celery_app.py) fix the
      cause; this catches whatever still slips through.

  PROCESSING for too long
      The worker claimed the row and then vanished -- SIGKILL, OOM, the hard
      task_time_limit, a container restart. No `finally` ran, so the row was
      never finalized and no retry was scheduled.

Policy: re-dispatch once, then FAIL with a reason. A row that has already been
re-dispatched and is stuck again is not a transient problem, and re-queueing it
forever would hide a real defect behind an infinite loop.
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from sqlalchemy import func, or_, select, update as sa_update

from app.core.celery_app import celery_app
from app.core.database import get_async_session_for_celery
from app.models.enums import FormCheckStatus
from app.models.form_check import FormCheck

logger = logging.getLogger(__name__)

# How long a row may sit in a non-terminal state before it is considered stranded.
#
# This MUST exceed the worst case for legitimately-running work:
#   task_time_limit * (1 + max_retries) + backoff
#   = 360 * 4 + (1 + 2 + 4) = 1447s = 24.1 min
# Otherwise the reaper eats live work. 30 min leaves headroom, and the invariant
# is asserted in tests/unit/test_maintenance_tasks.py rather than left as a note.
STUCK_THRESHOLD = timedelta(minutes=30)

# Cap per run so a large backlog cannot turn one beat tick into a long job.
MAX_ROWS_PER_RUN = 100

# Counter kept in FormCheck.details. There is no column for it and adding one for
# a rare recovery path is not worth a migration.
REDISPATCH_KEY = "reaper_redispatch_count"


@celery_app.task(
    name="app.tasks.maintenance_tasks.reap_stuck_form_checks",
    bind=True,
)
def reap_stuck_form_checks_task(self) -> Dict[str, Any]:
    """Sync wrapper, for the same reason process_form_check_task is sync.

    An `async def` here would be handed to Celery unawaited and would never run
    -- see app/tasks/ai_tasks.py for four tasks that did exactly that, silently.
    """
    return asyncio.run(_reap_stuck_form_checks())


def _stuck_since(threshold: timedelta) -> datetime:
    return datetime.now(timezone.utc) - threshold


async def _reap_stuck_form_checks(threshold: timedelta = STUCK_THRESHOLD) -> Dict[str, Any]:
    cutoff = _stuck_since(threshold)
    summary: Dict[str, Any] = {"scanned": 0, "redispatched": 0, "failed": 0, "errors": 0}

    async with get_async_session_for_celery() as session:
        # updated_at has onupdate but NO server_default (form_check.py:95), so it
        # is NULL until the row is first updated. A plain `updated_at < cutoff`
        # would silently skip every row that was never touched -- which is
        # exactly the never-claimed PENDING case this is meant to catch.
        last_touched = func.coalesce(FormCheck.updated_at, FormCheck.created_at)

        rows: List[FormCheck] = (
            (
                await session.execute(
                    select(FormCheck)
                    .where(
                        or_(
                            FormCheck.status == FormCheckStatus.PENDING,
                            FormCheck.status == FormCheckStatus.PROCESSING,
                        )
                    )
                    .where(last_touched < cutoff)
                    .order_by(last_touched.asc())
                    .limit(MAX_ROWS_PER_RUN)
                )
            )
            .scalars()
            .all()
        )
        summary["scanned"] = len(rows)
        if not rows:
            return summary

        for row in rows:
            details = dict(row.details or {})
            redispatched = int(details.get(REDISPATCH_KEY, 0) or 0)
            stuck_at = row.updated_at or row.created_at
            try:
                if redispatched == 0:
                    await _redispatch(session, row, details, stuck_at)
                    summary["redispatched"] += 1
                else:
                    await _give_up(session, row, details, stuck_at, redispatched)
                    summary["failed"] += 1
            except Exception as e:
                # One bad row must not abort the sweep.
                summary["errors"] += 1
                logger.error(
                    "[Reaper] Failed to recover FormCheck %s: %s", row.id, e,
                    exc_info=True,
                )
                await session.rollback()

    logger.info(
        "[Reaper] scanned=%(scanned)d redispatched=%(redispatched)d "
        "failed=%(failed)d errors=%(errors)d", summary,
    )
    return summary


async def _redispatch(session, row, details, stuck_at) -> None:
    """First strike: put it back to PENDING and queue it again."""
    from app.tasks.analysis_tasks import process_form_check_task

    if row.video_id is None:
        # Nothing to re-run. Fail it now rather than queue a task that cannot work.
        await _give_up(session, row, details, stuck_at, 0, reason="no video_id")
        return

    details[REDISPATCH_KEY] = 1
    details["reaper_stuck_from_status"] = str(
        row.status.value if hasattr(row.status, "value") else row.status
    )
    details["reaper_redispatched_at"] = datetime.now(timezone.utc).isoformat()

    # Guarded on the status we read, so a worker that picks the row up between
    # the SELECT and this UPDATE wins and we do nothing.
    result = await session.execute(
        sa_update(FormCheck)
        .where(FormCheck.id == row.id)
        .where(FormCheck.status == row.status)
        .values(status=FormCheckStatus.PENDING, details=details)
    )
    if result.rowcount == 0:
        await session.rollback()
        logger.info(
            "[Reaper] FormCheck %s changed status while being reaped; left alone.",
            row.id,
        )
        return

    await session.commit()
    process_form_check_task.delay(str(row.video_id), str(row.id))
    logger.warning(
        "[Reaper] FormCheck %s was stuck since %s; released to PENDING and "
        "re-dispatched.", row.id, stuck_at,
    )


async def _give_up(session, row, details, stuck_at, redispatched, reason=None) -> None:
    """Second strike: mark FAILED with a reason a human can act on.

    FormCheckStatus has no TIMED_OUT or STALE member (models/enums.py:31-51) and
    adding one means ALTER TYPE on a live Postgres enum. FAILED plus an explicit
    error_message carries the same information at none of the risk.
    """
    explanation = reason or (
        f"Stuck in {row.status} with no worker since {stuck_at}; already "
        f"re-dispatched {redispatched} time(s). Giving up."
    )
    details["error_message"] = f"Recovered by the stuck-row reaper: {explanation}"
    details["reaper_failed_at"] = datetime.now(timezone.utc).isoformat()

    result = await session.execute(
        sa_update(FormCheck)
        .where(FormCheck.id == row.id)
        .where(FormCheck.status == row.status)
        .values(status=FormCheckStatus.FAILED, details=details)
    )
    if result.rowcount == 0:
        await session.rollback()
        return
    await session.commit()
    logger.error("[Reaper] FormCheck %s marked FAILED: %s", row.id, explanation)
