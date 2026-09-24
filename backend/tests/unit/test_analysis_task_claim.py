"""G-48 (2/4): a task that does not win the claim must not write to the row.

The claim is a conditional UPDATE (PENDING -> PROCESSING) and its rowcount says
whether this task owns the row. Before this test existed the early `return`
after a lost claim still ran the `finally`, which finalized the row with
`final_status` -- FAILED by default -- and 520 completed form checks were
flipped to FAILED by their own duplicate dispatches, an hour after completing.

The coroutine is driven with every collaborator mocked; only the claim's
rowcount is real input.
"""
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.models.enums import FormCheckStatus
from app.tasks import analysis_tasks as at

pytestmark = pytest.mark.unit


def _updates(session):
    return [c for c in session.execute.call_args_list
            if str(c.args[0]).lstrip().upper().startswith("UPDATE")]


def _task_self(redelivered=False, task_id="task-1"):
    task_self = MagicMock()
    task_self.request.delivery_info = {"redelivered": redelivered}
    task_self.request.id = task_id
    return task_self


def _drive(rowcount: int, status=FormCheckStatus.COMPLETED):
    fc = MagicMock()
    fc.status = status
    session = AsyncMock()
    claim = MagicMock()
    claim.rowcount = rowcount
    session.execute = AsyncMock(return_value=claim)
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=None)
    fcs = MagicMock()
    fcs.get_async = AsyncMock(return_value=fc)
    fcs.finalize_form_check_analysis_async = AsyncMock()
    services = (fcs, MagicMock(), MagicMock(), MagicMock(), MagicMock(), MagicMock())
    return session, fcs, cm, services


@pytest.mark.asyncio
async def test_a_lost_claim_finalizes_nothing_and_issues_no_further_update():
    session, fcs, cm, services = _drive(rowcount=0)
    with patch.object(at, "get_task_db_session", return_value=cm), \
         patch.object(at, "get_services_for_task", AsyncMock(return_value=services)), \
         patch.object(at, "get_settings", return_value=MagicMock()):
        result = await at._process_form_check_task_async(_task_self(), str(uuid4()), str(uuid4()))

    assert result["status"] == "skipped", result
    fcs.finalize_form_check_analysis_async.assert_not_awaited()
    updates = _updates(session)
    assert len(updates) == 1, [str(u.args[0])[:80] for u in updates]   # the claim, nothing after it
    assert "form_checks" in str(updates[0].args[0])


@pytest.mark.asyncio
async def test_a_completed_row_is_not_flipped_by_a_duplicate_dispatch():
    """The exact G-48 shape: the original finished; the duplicate arrives an hour later."""
    session, fcs, cm, services = _drive(rowcount=0, status=FormCheckStatus.COMPLETED)
    with patch.object(at, "get_task_db_session", return_value=cm), \
         patch.object(at, "get_services_for_task", AsyncMock(return_value=services)), \
         patch.object(at, "get_settings", return_value=MagicMock()):
        await at._process_form_check_task_async(_task_self(), str(uuid4()), str(uuid4()))

    for u in _updates(session):
        params = u.args[0].compile().params
        assert params.get("status") != FormCheckStatus.FAILED, params


def test_the_claim_flag_is_set_only_after_the_rowcount_check():
    """Source-level guard: `claimed = True` must follow the rowcount branch, not
    precede the claim."""
    import inspect
    src = inspect.getsource(at._process_form_check_task_async)
    assert src.index("claimed = False") < src.index("claim.rowcount == 0") < src.index("claimed = True")


# ---- G-46: reclaim on redelivery ------------------------------------------------------

@pytest.mark.asyncio
async def test_a_redelivered_message_for_a_processing_row_tries_to_reclaim_it():
    session, fcs, cm, services = _drive(rowcount=0, status=FormCheckStatus.PROCESSING)
    reclaim = AsyncMock(return_value=False)
    with patch.object(at, "get_task_db_session", return_value=cm), \
         patch.object(at, "get_services_for_task", AsyncMock(return_value=services)), \
         patch.object(at, "get_settings", return_value=MagicMock()), \
         patch.object(at, "_reclaim_after_worker_lost", reclaim):
        result = await at._process_form_check_task_async(_task_self(redelivered=True), str(uuid4()), str(uuid4()))
    reclaim.assert_awaited_once()
    assert reclaim.await_args.args[2] == "task-1"
    assert result["status"] == "skipped"          # the helper said no -> still not ours


@pytest.mark.asyncio
async def test_a_first_delivery_never_reclaims_and_a_completed_row_never_reclaims():
    for status, redelivered in ((FormCheckStatus.PROCESSING, False), (FormCheckStatus.COMPLETED, True)):
        session, fcs, cm, services = _drive(rowcount=0, status=status)
        reclaim = AsyncMock(return_value=True)
        with patch.object(at, "get_task_db_session", return_value=cm), \
             patch.object(at, "get_services_for_task", AsyncMock(return_value=services)), \
             patch.object(at, "get_settings", return_value=MagicMock()), \
             patch.object(at, "_reclaim_after_worker_lost", reclaim):
            result = await at._process_form_check_task_async(_task_self(redelivered=redelivered), str(uuid4()), str(uuid4()))
        reclaim.assert_not_awaited()
        assert result["status"] == "skipped"


@pytest.mark.asyncio
async def test_reclaim_closes_the_dead_run_and_retakes_the_row():
    dead_run = uuid4()
    session = AsyncMock()
    sel = MagicMock(); sel.scalar_one_or_none.return_value = dead_run
    upd = MagicMock(); upd.rowcount = 1
    session.execute = AsyncMock(side_effect=[sel, upd])
    with patch("app.services.decisions.recorder.close_run", AsyncMock(return_value=True)) as close:
        ok = await at._reclaim_after_worker_lost(session, uuid4(), "task-1")
    assert ok is True
    close.assert_awaited_once()
    kw = close.await_args.kwargs
    assert kw["run_id"] == dead_run and kw["status"] == "abandoned" and kw["error_type"] == "worker_lost"
    reclaim_sql = str(session.execute.call_args_list[1].args[0]).upper()
    assert reclaim_sql.startswith("UPDATE FORM_CHECKS") and "STATUS" in reclaim_sql.split("WHERE", 1)[1]
    session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_reclaim_refuses_when_no_open_run_bears_this_task_id():
    """A PROCESSING row with someone else's live run is not ours, redelivered or not."""
    session = AsyncMock()
    sel = MagicMock(); sel.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(side_effect=[sel])
    with patch("app.services.decisions.recorder.close_run", AsyncMock()) as close:
        ok = await at._reclaim_after_worker_lost(session, uuid4(), "task-1")
    assert ok is False
    close.assert_not_awaited()
    assert session.execute.await_count == 1                      # the SELECT only; no UPDATE
