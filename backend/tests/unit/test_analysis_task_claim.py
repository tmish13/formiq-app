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
        result = await at._process_form_check_task_async(MagicMock(), str(uuid4()), str(uuid4()))

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
        await at._process_form_check_task_async(MagicMock(), str(uuid4()), str(uuid4()))

    for u in _updates(session):
        params = u.args[0].compile().params
        assert params.get("status") != FormCheckStatus.FAILED, params


def test_the_claim_flag_is_set_only_after_the_rowcount_check():
    """Source-level guard: `claimed = True` must follow the rowcount branch, not
    precede the claim."""
    import inspect
    src = inspect.getsource(at._process_form_check_task_async)
    assert src.index("claimed = False") < src.index("claim.rowcount == 0") < src.index("claimed = True")
