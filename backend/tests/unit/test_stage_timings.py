"""Plan D6: per-stage wall time rides into analysis_runs.settings_snapshot at close."""
import inspect
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.services.decisions import recorder
from app.tasks import analysis_tasks as at

pytestmark = pytest.mark.unit

ORDER = ['_mark("claim")', '_mark("open_run")', '_mark("resolve_video")', '_mark("pose_extract")',
         '_mark("posture_v1")', '_mark("after_model")', '_mark("record_decisions")']


def test_the_marks_exist_in_pipeline_order_and_reach_close_run():
    src = inspect.getsource(at._process_form_check_task_async)
    pos = [src.index(m) for m in ORDER]
    assert pos == sorted(pos), "stage marks out of pipeline order"
    assert 'settings_snapshot=({"stage_ms": dict(_stage_ms)} if _stage_ms else None)' in src
    assert src.index("_stage_ms: Dict[str, float] = {}") < pos[0]


@pytest.mark.asyncio
async def test_close_run_writes_the_snapshot_when_given():
    session = AsyncMock()
    session.execute = AsyncMock(return_value=MagicMock(rowcount=1))
    ok = await recorder.close_run(session, run_id=uuid4(), status="completed",
                                  settings_snapshot={"stage_ms": {"claim": 3.2, "pose_extract": 4100.0}})
    assert ok is True
    stmt = session.execute.call_args_list[0].args[0]
    params = stmt.compile().params
    assert params.get("settings_snapshot") == {"stage_ms": {"claim": 3.2, "pose_extract": 4100.0}}


@pytest.mark.asyncio
async def test_close_run_leaves_the_snapshot_alone_when_not_given():
    session = AsyncMock()
    session.execute = AsyncMock(return_value=MagicMock(rowcount=1))
    await recorder.close_run(session, run_id=uuid4(), status="completed")
    stmt = session.execute.call_args_list[0].args[0]
    assert "settings_snapshot" not in stmt.compile().params
