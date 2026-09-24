"""Periodic maintenance: recover form checks that no worker is working on.

Every other safety net on this branch is in-process, so none of them survives the
failure that started it: a worker that dies without running a single `finally`.
That run left 17 of 20 form checks sitting at PENDING forever, with the broker
already acked and nothing left to notice.

Two stuck shapes, both scanned here:

  PENDING for too long, AND absent from the broker
      The task was accepted but never claimed. This is the exact shape of the
      gevent failure -- the task raised inside asyncio.run() before it ever set
      PROCESSING, so the row never moved. Late acks (celery_app.py) fix the
      cause; this catches whatever still slips through.

      G-48: a PENDING row that is merely WAITING ITS TURN looks identical by age.
      The threshold below bounds a task's processing time; nothing bounds queue
      wait, and a 1,021-video batch at ~6/min put 772 healthy rows past it. The
      reaper re-dispatched them as duplicates and, one sweep later, FAILED 261
      of them unrun. So a PENDING row is only stranded if its task is not on the
      broker: the sweep takes one snapshot of the queue and the unacked set per
      tick and DEFERS every PENDING row whose id appears in it -- or every
      PENDING row, when the broker cannot be read. PROCESSING rows keep the
      age-based policy: a claimed row past the processing bound is stuck.

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
from typing import Any, Dict, List, Optional

from sqlalchemy import func, or_, select, update as sa_update

from app.core.celery_app import celery_app
from app.core.database import get_async_session_for_celery
from app.models.enums import FormCheckStatus
from app.models.form_check import FormCheck

logger = logging.getLogger(__name__)

# How long a CLAIMED row may sit in PROCESSING before it is considered stranded,
# and the minimum age at which an UNQUEUED PENDING row is. It bounds processing
# time; it says nothing about queue wait, which is why the PENDING sweep is
# gated on the broker (G-48) and not on this number alone.
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


def _broker_snapshot() -> Optional[str]:
    """Every queued and every delivered-but-unacked message, as one string.

    Two O(queue) reads on the broker, once per tick and only when the sweep has
    PENDING candidates: LRANGE of the default queue (waiting) and HVALS of kombu's
    `unacked` hash (delivered under acks_late, not yet acknowledged). Celery's
    protocol-v2 headers carry `argsrepr` in plaintext, so a row's task is present
    iff the row id appears in the text. Returns None when the broker cannot be
    read -- and None means "do not touch PENDING rows", never "reap them".
    """
    try:
        import redis
        from app.core.config import get_settings

        client = redis.Redis.from_url(get_settings().CELERY_BROKER_URL, socket_timeout=2)
        queue = celery_app.conf.task_default_queue or "celery"
        parts = list(client.lrange(queue, 0, -1)) + list(client.hvals("unacked"))
        return "\n".join(
            p.decode("utf-8", "replace") if isinstance(p, bytes) else str(p) for p in parts
        )
    except Exception as e:  # unreachable broker, auth, timeout -- all mean "unknown"
        logger.warning("[Reaper] broker snapshot unavailable (%s); PENDING rows left alone.", e)
        return None


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
    summary: Dict[str, Any] = {"scanned": 0, "redispatched": 0, "failed": 0,
                               "deferred": 0, "errors": 0, "runs_abandoned": 0}

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
            summary["runs_abandoned"] = await _abandon_unclosed_runs(session, threshold)
            return summary

        # One broker read per tick, only if a PENDING row is in the candidate set.
        snapshot: Optional[str] = ""
        if any(r.status == FormCheckStatus.PENDING for r in rows):
            snapshot = _broker_snapshot()

        for row in rows:
            if row.status == FormCheckStatus.PENDING and (
                snapshot is None or str(row.id) in snapshot
            ):
                # Its task is still on the broker (or we cannot tell). Queue wait
                # is not a fault; leave it for the worker. G-48.
                summary["deferred"] += 1
                continue
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

        summary["runs_abandoned"] = await _abandon_unclosed_runs(session, threshold)

    logger.info(
        "[Reaper] scanned=%(scanned)d redispatched=%(redispatched)d "
        "failed=%(failed)d deferred=%(deferred)d errors=%(errors)d "
        "runs_abandoned=%(runs_abandoned)d",
        summary,
    )
    return summary


#: How long past the stuck threshold a run may stay open before it is declared
#: abandoned. Doubled because a run is opened BEFORE the work and closed AFTER
#: it: a task that is legitimately slow, or has just been re-dispatched by this
#: same sweep, must not have its trail rewritten underneath it.
RUN_ABANDON_FACTOR = 2


async def _abandon_unclosed_runs(session, threshold: timedelta) -> int:
    """Close runs no worker ever closed.

    A SIGKILLed worker runs no `finally`, so its run sits `running` with
    `finished_at` NULL forever. That is not a cosmetic gap: an unclosed run is
    indistinguishable from one still in flight, so "how many analyses died?" has
    no answer without this sweep.

    Unconditional on the form check. The `analysis_runs` table deliberately has
    no foreign key, so a run whose form check was deleted is still here and
    still needs closing -- and it is exactly the row a per-form-check sweep
    would miss.
    """
    from app.models.audit import RUN_STATUS_ABANDONED, RUN_STATUS_RUNNING, AnalysisRun

    cutoff = _stuck_since(threshold * RUN_ABANDON_FACTOR)
    try:
        result = await session.execute(
            sa_update(AnalysisRun)
            .where(AnalysisRun.status == RUN_STATUS_RUNNING)
            .where(AnalysisRun.finished_at.is_(None))
            .where(AnalysisRun.started_at < cutoff)
            .values(
                status=RUN_STATUS_ABANDONED,
                finished_at=datetime.now(timezone.utc),
                error_type="abandoned",
                error_message=(
                    "no worker closed this run; swept by reap_stuck_form_checks"
                ),
            )
        )
        await session.commit()
        n = int(result.rowcount or 0)
        if n:
            logger.warning("[Reaper] abandoned %d unclosed analysis run(s) "
                           "started before %s", n, cutoff.isoformat())
        return n
    except Exception as e:
        # Never abort the sweep over the audit table -- form checks matter more.
        logger.error("[Reaper] could not sweep unclosed runs: %s", e, exc_info=True)
        try:
            await session.rollback()
        except Exception:
            pass
        return 0


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
    status_text = getattr(row.status, "value", row.status)
    explanation = reason or (
        f"Stuck in {status_text} with no worker since {stuck_at}; already "
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
