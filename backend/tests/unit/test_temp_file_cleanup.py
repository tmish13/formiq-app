"""Unit tests for the analysis task's temp-file registry.

The S3 fallback in ``_resolve_video_local_path`` writes the video to a
``NamedTemporaryFile(delete=False)``.  Three things can go wrong, and each has a
different cleanup mechanism:

  1. normal path              -> the caller's ``finally`` releases it
  2. cancelled mid-await      -> the task-level sweep releases it
  3. worker hard-killed       -> the next worker's startup sweep releases it

These tests cover the registry primitives behind (2) and (3).  The end-to-end
"disk delta after 20 videos" assertion lives in the pipeline integration suite,
because it needs a live worker.
"""
import os
import time

import pytest

from app.tasks import analysis_tasks as at

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def clean_registry():
    at._task_temp_files.clear()
    yield
    at._task_temp_files.clear()


def _make_temp(tmp_path, name="formiq_pose_abc.mp4", age_seconds=0):
    p = tmp_path / name
    p.write_bytes(b"\x00" * 128)
    if age_seconds:
        old = time.time() - age_seconds
        os.utime(p, (old, old))
    return str(p)


def test_release_deletes_and_deregisters(tmp_path):
    path = _make_temp(tmp_path)
    at._register_temp_file(path)

    assert at._release_temp_file(path) is True
    assert not os.path.exists(path)
    assert path not in at._task_temp_files


def test_release_is_idempotent(tmp_path):
    """A second release must not raise — the caller's `finally` and the
    task-level sweep can both reach the same path."""
    path = _make_temp(tmp_path)
    at._register_temp_file(path)

    assert at._release_temp_file(path) is True
    assert at._release_temp_file(path) is False  # already gone, no exception


def test_task_sweep_removes_what_the_caller_never_released(tmp_path):
    """The cancellation case: the file exists and is registered, but no caller
    ever held the path to delete it."""
    leaked = _make_temp(tmp_path, "formiq_pose_leaked.mp4")
    at._register_temp_file(leaked)

    assert at._sweep_task_temp_files() == 1
    assert not os.path.exists(leaked)
    assert at._task_temp_files == set()


def test_task_sweep_is_a_noop_on_the_happy_path(tmp_path):
    path = _make_temp(tmp_path)
    at._register_temp_file(path)
    at._release_temp_file(path)

    assert at._sweep_task_temp_files() == 0


def test_startup_sweep_removes_stale_files_only(tmp_path, monkeypatch):
    """A hard-killed worker leaves files behind with no registry to consult.

    The age cutoff must exceed task_time_limit so a sibling prefork child's
    in-flight download is never deleted out from under it.
    """
    monkeypatch.setattr("tempfile.gettempdir", lambda: str(tmp_path))

    stale = _make_temp(tmp_path, "formiq_pose_stale.mp4",
                       age_seconds=at._TEMP_FILE_STALE_SECONDS + 60)
    in_flight = _make_temp(tmp_path, "formiq_pose_inflight.mp4", age_seconds=10)
    unrelated = _make_temp(tmp_path, "someone_elses_file.mp4",
                           age_seconds=at._TEMP_FILE_STALE_SECONDS + 60)

    assert at._sweep_stale_temp_files() == 1
    assert not os.path.exists(stale)
    assert os.path.exists(in_flight), "deleted a sibling worker's live download"
    assert os.path.exists(unrelated), "deleted a file it does not own"


def test_stale_cutoff_exceeds_the_hard_task_time_limit():
    """Guards the invariant the cutoff depends on.

    If task_time_limit is ever raised above the cutoff, the startup sweep could
    delete a download that another prefork child is still writing.
    """
    from app.core.celery_app import celery_app

    hard_limit = celery_app.conf.task_time_limit
    assert at._TEMP_FILE_STALE_SECONDS > hard_limit, (
        f"stale cutoff {at._TEMP_FILE_STALE_SECONDS}s must exceed "
        f"task_time_limit {hard_limit}s"
    )
