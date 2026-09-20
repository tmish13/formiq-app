"""The retired Celery tasks never executed, and must not be dispatchable again.

app/tasks/video_tasks.py and app/tasks/ai_tasks.py declared every task as
``async def`` under a plain ``@app.task``. Celery has no await step: it calls the
function, gets a coroutine object back, and returns that object as the task's
result. The body never runs -- under any pool, with or without the gevent
problem that broke the live path.

Measured before the move:

    app.tasks.video_tasks.process_video_celery_task    -> coroutine
    app.tasks.ai_tasks.detect_pose_celery_task         -> coroutine
    app.tasks.ai_tasks.calculate_angles_celery_task    -> coroutine
    ai.perform_form_analysis                           -> coroutine
    app.tasks.analysis_tasks.process_form_check        -> dict   (the live one)

``perform_form_analysis_celery_task`` is worth calling out: it carried
``autoretry_for=(Exception,)``, which wraps the function in a sync shim, so
``inspect.iscoroutinefunction`` reports False. Calling it still returns a
coroutine. Structure is checked here rather than trusted.

The archived sources are parsed with ast rather than imported, because importing
them would re-register the task names over the live stubs.
"""
import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

ARCHIVE = Path(__file__).resolve().parents[2] / "archive" / "tasks_old"

RETIRED = {
    "video_tasks.py": ["process_video_celery_task"],
    "ai_tasks.py": [
        "detect_pose_celery_task",
        "calculate_angles_celery_task",
        "perform_form_analysis_celery_task",
    ],
}


def _decorated_tasks(path: Path):
    """Yield (name, node) for every function in `path` decorated with a Celery task."""
    tree = ast.parse(path.read_text())
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for dec in node.decorator_list:
            call = dec.func if isinstance(dec, ast.Call) else dec
            if isinstance(call, ast.Attribute) and call.attr == "task":
                yield node.name, node
                break


@pytest.mark.parametrize(
    "filename,expected", [(f, names) for f, names in RETIRED.items()]
)
def test_every_archived_task_was_an_unawaited_coroutine(filename, expected):
    """The reason these were retired, pinned to the archived source."""
    path = ARCHIVE / filename
    assert path.exists(), f"archived source missing: {path}"

    found = dict(_decorated_tasks(path))
    assert sorted(found) == sorted(expected), (
        f"{filename} defines {sorted(found)}, expected {sorted(expected)}"
    )
    for name, node in found.items():
        assert isinstance(node, ast.AsyncFunctionDef), (
            f"{name} is not an async def -- if this became a real sync task, the "
            f"reason for retiring it no longer holds and this should be revisited"
        )


def test_retired_modules_are_not_registered_with_any_worker():
    """They must not be in celery_app.include, or a worker would accept them."""
    from app.core.celery_app import celery_app

    include = list(celery_app.conf.include or [])
    assert "app.tasks.video_tasks" not in include
    assert "app.tasks.ai_tasks" not in include
    assert "app.tasks.analysis_tasks" in include, "the live task must still be included"


def test_the_worker_registers_exactly_one_task():
    """Guards against a dead module creeping back into `include`.

    Run in a clean subprocess: in a shared pytest session other test modules
    import the retired stubs directly, which registers those names in
    celery_app.tasks even though no worker would ever load them. A fresh
    interpreter shows what a worker actually starts with.
    """
    import json
    import subprocess
    import sys

    probe = (
        "import warnings; warnings.filterwarnings('ignore'); import json; "
        "from app.core.celery_app import celery_app; "
        "celery_app.loader.import_default_modules(); "
        "print('RESULT' + json.dumps(sorted("
        "n for n in celery_app.tasks if not n.startswith('celery.'))))"
    )
    out = subprocess.run(
        [sys.executable, "-c", probe], capture_output=True, text=True, cwd="/app"
    )
    marker = [ln for ln in out.stdout.splitlines() if ln.startswith("RESULT")]
    assert marker, f"probe produced no result. stderr={out.stderr[-800:]!r}"
    registered = json.loads(marker[-1][len("RESULT"):])
    assert registered == ["app.tasks.analysis_tasks.process_form_check"], registered


def test_the_live_task_is_a_sync_function():
    """process_form_check_task must stay a sync wrapper around asyncio.run().

    If it is ever changed to `async def`, it joins the retired tasks: Celery
    would return an un-awaited coroutine and every form check would silently
    do nothing.
    """
    import inspect
    from app.tasks.analysis_tasks import process_form_check_task

    assert not inspect.iscoroutinefunction(process_form_check_task.run), (
        "process_form_check_task became a coroutine function; Celery will not "
        "await it and the analysis body will never execute"
    )


@pytest.mark.parametrize(
    "module,name",
    [
        ("app.tasks.video_tasks", "process_video_celery_task"),
        ("app.tasks.ai_tasks", "detect_pose_celery_task"),
        ("app.tasks.ai_tasks", "calculate_angles_celery_task"),
        ("app.tasks.ai_tasks", "perform_form_analysis_celery_task"),
    ],
)
def test_retired_stubs_raise_instead_of_pretending_to_work(module, name):
    """The stub names still resolve, but running one is an error, not a no-op."""
    import importlib

    task = getattr(importlib.import_module(module), name)
    with pytest.raises(NotImplementedError, match="retired"):
        task.run()
