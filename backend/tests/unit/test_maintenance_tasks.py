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

        This bounds PROCESSING time only. It says nothing about how long a
        healthy row may wait in the queue -- that is unbounded, and the PENDING
        sweep is gated on the broker instead (TestBrokerGate, G-48).

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
    @staticmethod
    def _last_form_check_update(session):
        """The last UPDATE against form_checks.

        Not `call_args_list[-1]`: the sweep also closes unclosed analysis_runs,
        and that statement is issued after this one. A test that means "the
        form check update" must say so, or it silently starts asserting about a
        different table the next time a statement is appended.
        """
        for call in reversed(session.execute.call_args_list):
            stmt = call.args[0]
            if "form_checks" in str(stmt) and "UPDATE" in str(stmt).upper():
                return stmt
        raise AssertionError("no UPDATE against form_checks was issued")

    @pytest.mark.asyncio
    async def test_first_strike_redispatches(self):
        row = _row(details=None)
        session = _session([row])
        with _patch_session(session), patch(
            "app.tasks.analysis_tasks.process_form_check_task"
        ) as mock_task:
            summary = await mt._reap_stuck_form_checks()

        assert summary["scanned"] == 1
        assert summary["redispatched"] == 1
        assert summary["failed"] == 0
        assert summary["errors"] == 0
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

        values = self._last_form_check_update(session).compile().params
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
        values = self._last_form_check_update(session).compile().params
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


class TestUnclosedRunSweep:
    """A SIGKILLed worker runs no `finally`, so its analysis_runs row sits
    `running` with `finished_at` NULL forever. Until it is swept, an unclosed
    run is indistinguishable from one still in flight, so "how many analyses
    died?" has no answer.
    """

    @staticmethod
    def _run_update(session):
        for call in reversed(session.execute.call_args_list):
            stmt = str(call.args[0])
            if "analysis_runs" in stmt and "UPDATE" in stmt.upper():
                return call.args[0]
        raise AssertionError("no UPDATE against analysis_runs was issued")

    @pytest.mark.asyncio
    async def test_the_sweep_runs_even_when_no_form_check_is_stuck(self):
        """A run whose form check completed normally but whose worker died
        between the two is exactly the case a form-check-driven sweep misses."""
        session = _session([])
        with _patch_session(session):
            summary = await mt._reap_stuck_form_checks()
        assert "runs_abandoned" in summary
        self._run_update(session)

    @pytest.mark.asyncio
    async def test_it_only_touches_runs_that_are_running_and_unclosed(self):
        session = _session([])
        with _patch_session(session):
            await mt._reap_stuck_form_checks()
        sql = str(self._run_update(session).compile(
            compile_kwargs={"literal_binds": True})).lower()
        assert "finished_at is null" in sql
        assert "status" in sql and "running" in sql
        assert "started_at <" in sql

    @pytest.mark.asyncio
    async def test_it_sets_a_terminal_status_and_a_finish_time(self):
        session = _session([])
        with _patch_session(session):
            await mt._reap_stuck_form_checks()
        params = self._run_update(session).compile().params
        assert params["status"] == "abandoned"
        assert params["finished_at"] is not None
        assert params["error_type"] == "abandoned"

    @pytest.mark.asyncio
    async def test_it_is_not_keyed_on_the_form_check(self):
        """analysis_runs deliberately has no foreign key, so a run whose form
        check was deleted still exists and still needs closing -- and it is
        precisely the row a per-form-check sweep would never reach."""
        session = _session([])
        with _patch_session(session):
            await mt._reap_stuck_form_checks()
        # The WHERE clause only. The SET clause carries the string
        # "swept by reap_stuck_form_checks", which is prose, not a join.
        sql = str(self._run_update(session).compile(
            compile_kwargs={"literal_binds": True})).lower()
        where = sql.split(" where ", 1)[1]
        assert "form_check" not in where

    def test_the_run_cutoff_is_later_than_the_form_check_cutoff(self):
        """A run is opened BEFORE the work and closed AFTER it, so it is open
        for longer than its form check is stale. Sweeping both at the same
        cutoff would abandon the trail of a task this same sweep has just
        re-dispatched."""
        assert mt.RUN_ABANDON_FACTOR >= 2

    @pytest.mark.asyncio
    async def test_a_failure_in_the_sweep_does_not_abort_the_reaper(self):
        """Form checks matter more than the audit table."""
        session = AsyncMock()
        select_result = MagicMock()
        select_result.scalars.return_value.all.return_value = []
        session.execute = AsyncMock(side_effect=[select_result, RuntimeError("boom")])
        with _patch_session(session):
            summary = await mt._reap_stuck_form_checks()
        assert summary["runs_abandoned"] == 0
        assert summary["errors"] == 0      # not a form-check error


class TestBrokerGate:
    """G-48. A PENDING row whose task is still on the broker is waiting, not
    stranded. On the first batch deeper than the threshold the age-only sweep
    re-dispatched 772 healthy rows and then FAILED 261 of them unrun."""

    @staticmethod
    def _snapshot(*ids):
        # Shaped like the broker text: celery v2 headers carry argsrepr in plaintext.
        return "\n".join(
            '{"headers": {"argsrepr": "(\'vid\', \'%s\')"}}' % i for i in ids
        )

    @pytest.mark.asyncio
    async def test_a_queued_pending_row_is_deferred_not_reaped(self):
        row = _row(status=FormCheckStatus.PENDING, details=None)
        session = _session([row])
        with _patch_session(session), patch(
            "app.tasks.analysis_tasks.process_form_check_task"
        ) as mock_task, patch.object(mt, "_broker_snapshot", return_value=self._snapshot(row.id)):
            summary = await mt._reap_stuck_form_checks()

        assert summary["deferred"] == 1
        assert summary["redispatched"] == 0 and summary["failed"] == 0
        mock_task.delay.assert_not_called()
        # "UPDATE" alone would match the SELECT's `updated_at` column.
        assert not any(
            str(c.args[0]).lstrip().upper().startswith("UPDATE") and "form_checks" in str(c.args[0])
            for c in session.execute.call_args_list
        ), "a deferred row must not be written"

    @pytest.mark.asyncio
    async def test_a_queued_second_strike_row_is_still_not_failed(self):
        """The 261 were exactly this: re-dispatched once, still queued, then FAILED."""
        row = _row(status=FormCheckStatus.PENDING, details={mt.REDISPATCH_KEY: 1})
        session = _session([row])
        with _patch_session(session), patch(
            "app.tasks.analysis_tasks.process_form_check_task"
        ) as mock_task, patch.object(mt, "_broker_snapshot", return_value=self._snapshot(row.id)):
            summary = await mt._reap_stuck_form_checks()

        assert summary["failed"] == 0 and summary["deferred"] == 1
        mock_task.delay.assert_not_called()

    @pytest.mark.asyncio
    async def test_an_unreadable_broker_defers_every_pending_row(self):
        row = _row(status=FormCheckStatus.PENDING, details=None)
        session = _session([row])
        with _patch_session(session), patch(
            "app.tasks.analysis_tasks.process_form_check_task"
        ) as mock_task, patch.object(mt, "_broker_snapshot", return_value=None):
            summary = await mt._reap_stuck_form_checks()

        assert summary["deferred"] == 1 and summary["redispatched"] == 0
        mock_task.delay.assert_not_called()

    @pytest.mark.asyncio
    async def test_a_pending_row_absent_from_an_empty_broker_is_reaped_as_before(self):
        """The original failure: message acked, row never claimed, nothing queued."""
        row = _row(status=FormCheckStatus.PENDING, details=None)
        session = _session([row])
        with _patch_session(session), patch(
            "app.tasks.analysis_tasks.process_form_check_task"
        ) as mock_task, patch.object(mt, "_broker_snapshot", return_value=""):
            summary = await mt._reap_stuck_form_checks()

        assert summary["deferred"] == 0 and summary["redispatched"] == 1
        mock_task.delay.assert_called_once_with(str(row.video_id), str(row.id))

    @pytest.mark.asyncio
    async def test_a_pending_row_absent_from_a_busy_broker_is_reaped(self):
        """Other work on the queue does not shield a row whose own task is gone."""
        row = _row(status=FormCheckStatus.PENDING, details=None)
        session = _session([row])
        with _patch_session(session), patch(
            "app.tasks.analysis_tasks.process_form_check_task"
        ) as mock_task, patch.object(mt, "_broker_snapshot", return_value=self._snapshot(uuid4(), uuid4())):
            summary = await mt._reap_stuck_form_checks()

        assert summary["redispatched"] == 1 and summary["deferred"] == 0

    @pytest.mark.asyncio
    async def test_processing_rows_keep_the_age_policy(self):
        """A claimed row past the processing bound is stuck even if its message
        is still unacked (acks_late): the worker that held it is gone."""
        row = _row(status=FormCheckStatus.PROCESSING, details=None)
        session = _session([row])
        with _patch_session(session), patch(
            "app.tasks.analysis_tasks.process_form_check_task"
        ) as mock_task, patch.object(mt, "_broker_snapshot", return_value=self._snapshot(row.id)) as snap:
            summary = await mt._reap_stuck_form_checks()

        assert summary["redispatched"] == 1 and summary["deferred"] == 0
        snap.assert_not_called()          # no PENDING candidate -> no broker read

    def test_snapshot_returns_none_when_the_broker_is_unreachable(self):
        with patch("app.core.config.get_settings") as gs:
            gs.return_value.CELERY_BROKER_URL = "redis://256.0.0.1:1/0"
            assert mt._broker_snapshot() is None
