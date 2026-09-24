"""G-48 (3/4): finalize writes the row only while it is still PROCESSING.

The task's claim moves PENDING -> PROCESSING; finalize is the matching release.
Anything that reaches finalize when the row is no longer PROCESSING (a duplicate
dispatch, a retry racing its original, a reaper give-up) does not own the row.
Before this guard, finalize was a plain setattr + commit: 520 COMPLETED rows
were rewritten to FAILED by their own duplicate dispatches, and their feedback
items were deleted unconditionally on the way.
"""
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.models.enums import FormCheckStatus
from app.services.base_service import BaseService
from app.services.form_check_service import FormCheckService

pytestmark = pytest.mark.unit


def _service(rowcount: int, current_status=FormCheckStatus.COMPLETED):
    session = AsyncMock()
    result = MagicMock()
    result.rowcount = rowcount
    session.execute = AsyncMock(return_value=result)
    svc = FormCheckService(db=session, settings=MagicMock(), storage_service=MagicMock(), ai_service=MagicMock())
    svc.response_schema = MagicMock()
    fc = MagicMock()
    fc.id = uuid4()
    fc.status = current_status
    fc.details = {"threshold_mode": "default"}
    fc.feedback_items = []
    return svc, session, fc


def _statements(session):
    return [str(c.args[0]).lstrip().upper() for c in session.execute.call_args_list]


@pytest.mark.asyncio
async def test_a_terminal_row_is_not_rewritten_and_keeps_its_feedback():
    svc, session, fc = _service(rowcount=0, current_status=FormCheckStatus.COMPLETED)
    with patch.object(BaseService, "get_async", AsyncMock(return_value=fc)):
        await svc.finalize_form_check_analysis_async(
            form_check_id=fc.id, analysis_results={"score": None, "feedback": []},
            status=FormCheckStatus.FAILED,
        )

    stmts = _statements(session)
    assert len(stmts) == 1 and stmts[0].startswith("UPDATE"), stmts
    assert not any(s.startswith("DELETE") for s in stmts), "feedback deleted on a refused finalize"
    session.commit.assert_not_awaited()
    session.rollback.assert_awaited()


@pytest.mark.asyncio
async def test_the_update_is_conditional_on_processing():
    svc, session, fc = _service(rowcount=1, current_status=FormCheckStatus.PROCESSING)
    with patch.object(BaseService, "get_async", AsyncMock(return_value=fc)):
        await svc.finalize_form_check_analysis_async(
            form_check_id=fc.id, analysis_results={"score": 42, "feedback": ["ok"]},
            status=FormCheckStatus.COMPLETED,
        )

    update = session.execute.call_args_list[0].args[0]
    sql = str(update).upper()            # no literal binds: the JSON `details` value has no literal renderer
    assert sql.startswith("UPDATE FORM_CHECKS") and "WHERE" in sql, sql
    where = sql.split("WHERE", 1)[1]
    assert "FORM_CHECKS.ID" in where and "FORM_CHECKS.STATUS" in where, where
    assert FormCheckStatus.PROCESSING in update.compile().params.values()


@pytest.mark.asyncio
async def test_a_processing_row_is_finalized_and_its_feedback_replaced():
    svc, session, fc = _service(rowcount=1, current_status=FormCheckStatus.PROCESSING)
    with patch.object(BaseService, "get_async", AsyncMock(return_value=fc)):
        await svc.finalize_form_check_analysis_async(
            form_check_id=fc.id, analysis_results={"score": 42, "feedback": []},
            status=FormCheckStatus.COMPLETED,
        )

    stmts = _statements(session)
    assert stmts[0].startswith("UPDATE") and any(s.startswith("DELETE") for s in stmts), stmts
    assert session.commit.await_count >= 1
