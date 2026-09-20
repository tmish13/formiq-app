"""Unit tests for the stuck-row reaper.

The reaper is the only safety net on this pipeline that survives a worker dying
without running a single `finally`. Its two riskiest properties are tested
directly, because getting either wrong is worse than not having it:

  1. The staleness threshold must exceed the worst case for legitimately-running
     work, or the reaper eats live tasks.
  2. Every write is guarded on the status that was read, so a worker that claims
     the row mid-sweep wins.
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.models.enums import FormCheckStatus
from app.tasks import maintenance_tasks as mt

pytestmark = pytest.mark.unit


_UNSET = object()


def _row(status=FormCheckStatus.PROCESSING, details=None, age_minutes=45, video_id=_UNSET):
    row = MagicMock()
    row.id = uuid4()
    # `video_id=None` must mean "no video", not "pick one for me".
    row.video_id = uuid4() if video_id is _UNSET else video_id
    row.status = status
    row.details = details
    row.created_at = datetime.now(timezone.utc) - timedelta(minutes=age_minutes)
    row.updated_at = None
    return row


def _session(rows, rowcount=1):
    session = AsyncMock()
    select_result = MagicMock()
    select_result.scalars.return_value.all.return_value = rows
    update_result = MagicMock()
    update_result.rowcount = rowcount
    # First execute is the SELECT; every later one is an UPDATE.
    session.execute = AsyncMock(side_effect=[select_result] + [update_result] * 50)
    return session


def _patch_session(session):
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=None)
    return patch(
        "app.tasks.maintenance_tasks.get_async_session_for_celery", return_value=cm
    )


class TestThresholdInvariant:
    def test_threshold_exceeds_the_worst_case_for_live_work(self):
        """If this ever inverts, the reaper starts killing running tasks.

        Worst case for work that is legitimately still running:
          task_time_limit * (1 + max_retries) + retry backoff
        """
        from app.core.celery_app import celery_app
        from app.tasks.analysis_tasks import process_form_check_task

        hard_limit = celery_app.conf.task_time_limit
        max_retries = process_form_check_task.max_retries
        backoff = sum(2 ** n for n in range(max_retries))  # 1 + 2 + 4
        worst_case = hard_limit * (1 + max_retries) + backoff

        assert mt.STUCK_THRESHOLD.total_seconds() > worst_case, (
            f"threshold {mt.STUCK_THRESHOLD.total_seconds()}s must exceed the "
            f"worst case for live work ({worst_case}s)"
        )

    def test_beat_interval_is_well_below_the_threshold(self):
        from app.core.celery_app import celery_app

        entry = celery_app.conf.beat_schedule["reap-stuck-form-checks"]
        assert entry["task"] == "app.tasks.maintenance_tasks.reap_stuck_form_checks"
        assert entry["schedule"] < mt.STUCK_THRESHOLD.total_seconds()


class TestScan:
    @pytest.mark.asyncio
    async def test_scans_both_pending_and_processing(self):
        """PENDING is the shape the original failure produced.

        The 17 lost tasks raised inside asyncio.run() before ever setting
        PROCESSING, so a reaper that only looked at PROCESSING would have missed
        every one of them.
        """
        session = _session([])
        with _patch_session(session):
            await mt._reap_stuck_form_checks()

        where_clause = str(session.execute.call_args_list[0].args[0])
        assert "status" in where_clause
        # Both non-terminal states must appear in the OR
        compiled = session.execute.call_args_list[0].args[0].compile(
            compile_kwargs={"literal_binds": True}
        )
        sql = str(compiled)
        assert sql.count("form_checks.status") >= 2, sql

    @pytest.mark.asyncio
    async def test_uses_coalesce_so_never_updated_rows_are_visible(self):
        """updated_at has onupdate but no server_default, so it is NULL until the
        row is first updated. A plain `updated_at < cutoff` would skip exactly
        the never-claimed rows this exists to catch."""
        session = _session([])
        with _patch_session(session):
            await mt._reap_stuck_form_checks()

        sql = str(session.execute.call_args_list[0].args[0])
        assert "coalesce" in sql.lower()
        assert "created_at" in sql.lower()

    @pytest.mark.asyncio
    async def test_scan_is_capped(self):
        session = _session([])
        with _patch_session(session):
            await mt._reap_stuck_form_checks()

        sql = str(session.execute.call_args_list[0].args[0].compile(
            compile_kwargs={"literal_binds": True}
        ))
        assert str(mt.MAX_ROWS_PER_RUN) in sql


class TestPolicy:
    @pytest.mark.asyncio
    async def test_first_strike_redispatches(self):
        row = _row(details=None)
        session = _session([row])
        with _patch_session(session), patch(
            "app.tasks.analysis_tasks.process_form_check_task"
        ) as mock_task:
            summary = await mt._reap_stuck_form_checks()

        assert summary == {"scanned": 1, "redispatched": 1, "failed": 0, "errors": 0}
        mock_task.delay.assert_called_once_with(str(row.video_id), str(row.id))

    @pytest.mark.asyncio
    async def test_second_strike_fails_instead_of_looping_forever(self):
        row = _row(details={mt.REDISPATCH_KEY: 1})
        session = _session([row])
        with _patch_session(session), patch(
            "app.tasks.analysis_tasks.process_form_check_task"
        ) as mock_task:
            summary = await mt._reap_stuck_form_checks()

        assert summary["failed"] == 1
        assert summary["redispatched"] == 0
        mock_task.delay.assert_not_called()

        values = session.execute.call_args_list[-1].args[0].compile().params
        assert values["status"] == FormCheckStatus.FAILED

    @pytest.mark.asyncio
    async def test_a_row_with_no_video_is_failed_not_requeued(self):
        """Re-dispatching it would queue a task that cannot possibly work."""
        row = _row(details=None, video_id=None)
        session = _session([row])
        with _patch_session(session), patch(
            "app.tasks.analysis_tasks.process_form_check_task"
        ) as mock_task:
            summary = await mt._reap_stuck_form_checks()

        mock_task.delay.assert_not_called()
        assert summary["redispatched"] == 1  # counted as handled by the first strike
        values = session.execute.call_args_list[-1].args[0].compile().params
        assert values["status"] == FormCheckStatus.FAILED

    @pytest.mark.asyncio
    async def test_a_worker_that_claims_the_row_mid_sweep_wins(self):
        """rowcount == 0 means the guarded UPDATE matched nothing: someone else
        moved the row between the SELECT and the UPDATE. The reaper must not
        re-dispatch work that is now running."""
        row = _row(details=None)
        session = _session([row], rowcount=0)
        with _patch_session(session), patch(
            "app.tasks.analysis_tasks.process_form_check_task"
        ) as mock_task:
            summary = await mt._reap_stuck_form_checks()

        mock_task.delay.assert_not_called()
        session.rollback.assert_awaited()
        assert summary["errors"] == 0

    @pytest.mark.asyncio
    async def test_one_bad_row_does_not_abort_the_sweep(self):
        good, bad = _row(details=None), _row(details=None)
        session = _session([bad, good])
        session.commit = AsyncMock(side_effect=[RuntimeError("boom"), None])

        with _patch_session(session), patch(
            "app.tasks.analysis_tasks.process_form_check_task"
        ) as mock_task:
            summary = await mt._reap_stuck_form_checks()

        assert summary["scanned"] == 2
        assert summary["errors"] == 1
        assert summary["redispatched"] == 1
        mock_task.delay.assert_called_once_with(str(good.video_id), str(good.id))


def test_the_reaper_task_is_not_a_coroutine_function():
    """Same trap that made four tasks in ai_tasks.py no-ops."""
    import inspect

    assert not inspect.iscoroutinefunction(mt.reap_stuck_form_checks_task.run)
