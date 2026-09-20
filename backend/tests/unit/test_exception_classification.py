"""The analysis task must tell "the infrastructure blinked" from "this video is bad".

Before this branch every exception was swallowed into FAILED and ``self.retry()``
was never called, so the ``max_retries=3`` declared on the task was dead
configuration: a momentary Postgres disconnect burned the form check permanently,
and the user saw a failure caused by something that had nothing to do with their
video.
"""
import asyncio
from contextlib import contextmanager
from unittest.mock import patch

import pytest
from sqlalchemy import exc as sa_exc

from app.core.exceptions import NotFoundException
from app.tasks.analysis_tasks import (
    TransientTaskError,
    _is_transient,
    process_form_check_task,
)

pytestmark = pytest.mark.unit


def _db_error():
    return sa_exc.OperationalError("SELECT 1", {}, Exception("server closed the connection"))


class TestClassification:
    @pytest.mark.parametrize(
        "exc",
        [
            sa_exc.OperationalError("SELECT 1", {}, Exception("connection lost")),
            sa_exc.InterfaceError("SELECT 1", {}, Exception("connection already closed")),
            ConnectionResetError("peer reset"),
            ConnectionRefusedError("nothing listening"),
            TimeoutError("timed out"),
        ],
    )
    def test_infrastructure_errors_are_transient(self, exc):
        assert _is_transient(exc, retries_so_far=0, max_retries=3) is True

    @pytest.mark.parametrize(
        "exc",
        [
            ValueError("duration gate rejected the video"),
            NotFoundException("FormCheck not found"),
            KeyError("results"),
            IOError("Cannot open video: /tmp/x.mp4"),
            RuntimeError("model failed to load"),
        ],
    )
    def test_task_level_errors_are_permanent(self, exc):
        assert _is_transient(exc, retries_so_far=0, max_retries=3) is False

    def test_ioerror_is_permanent_even_though_it_is_an_oserror(self):
        """The trap this classification was written around.

        _extract_pose_from_video raises IOError("Cannot open video: ...") for a
        corrupt or unreadable file. IOError IS OSError, so classifying on OSError
        would retry a corrupt video three times and still fail.
        """
        assert issubclass(IOError, OSError)
        assert _is_transient(IOError("Cannot open video"), 0, 3) is False
        assert _is_transient(ConnectionError("blip"), 0, 3) is True

    def test_soft_time_limit_is_permanent(self):
        """A clip that blew the soft limit will blow it again."""
        from celery.exceptions import SoftTimeLimitExceeded

        assert _is_transient(SoftTimeLimitExceeded(), 0, 3) is False

    def test_exhausted_retries_make_a_transient_error_permanent(self):
        """Otherwise the row is released to PENDING with nothing left to claim it.

        That is the stuck-PENDING state this whole branch exists to remove, so it
        must not be reachable through the retry path.
        """
        exc = _db_error()
        assert _is_transient(exc, retries_so_far=0, max_retries=3) is True
        assert _is_transient(exc, retries_so_far=2, max_retries=3) is True
        assert _is_transient(exc, retries_so_far=3, max_retries=3) is False
        assert _is_transient(exc, retries_so_far=9, max_retries=3) is False


class TestWrapperRetries:
    """The sync wrapper is what actually turns a classification into a retry.

    Driven through the real bound task object -- process_form_check_task is
    bind=True, so `self` is the task itself and cannot be injected. push_request
    supplies the retry count Celery would have set.
    """

    @contextmanager
    def _task_context(self, retries=0):
        task = process_form_check_task
        task.push_request(retries=retries)
        try:
            with patch.object(
                task, "retry", side_effect=lambda **kw: Exception("Retry")
            ) as mock_retry:
                yield mock_retry
        finally:
            task.pop_request()

    @contextmanager
    def _body_raises(self, exc):
        async def _boom(*a, **kw):
            raise exc

        with patch("app.tasks.analysis_tasks._process_form_check_task_async", _boom):
            yield

    def test_transient_error_calls_retry_with_backoff(self):
        with self._task_context(retries=1) as mock_retry:
            with self._body_raises(TransientTaskError(_db_error())):
                with pytest.raises(Exception, match="Retry"):
                    process_form_check_task.run("vid", "fcid")

        mock_retry.assert_called_once()
        kwargs = mock_retry.call_args.kwargs
        assert kwargs["countdown"] == 2 ** 1
        assert isinstance(kwargs["exc"], sa_exc.OperationalError), (
            "retry must carry the original error, not the TransientTaskError wrapper"
        )

    @pytest.mark.parametrize(
        "retries,expected_countdown", [(0, 1), (1, 2), (2, 4), (3, 8)]
    )
    def test_backoff_doubles(self, retries, expected_countdown):
        with self._task_context(retries=retries) as mock_retry:
            with self._body_raises(TransientTaskError(_db_error())):
                with pytest.raises(Exception, match="Retry"):
                    process_form_check_task.run("vid", "fcid")

        assert mock_retry.call_args.kwargs["countdown"] == expected_countdown

    def test_backoff_is_capped(self):
        """Unbounded 2**n would push a late retry hours out."""
        with self._task_context(retries=20) as mock_retry:
            with self._body_raises(TransientTaskError(_db_error())):
                with pytest.raises(Exception, match="Retry"):
                    process_form_check_task.run("vid", "fcid")

        assert mock_retry.call_args.kwargs["countdown"] == 300

    def test_permanent_error_does_not_retry(self):
        """A permanent failure returns normally -- the body already wrote FAILED."""
        async def _finished(*a, **kw):
            return {"status": "failed", "form_check_id": "fcid"}

        with self._task_context() as mock_retry:
            with patch(
                "app.tasks.analysis_tasks._process_form_check_task_async", _finished
            ):
                result = process_form_check_task.run("vid", "fcid")

        assert result["status"] == "failed"
        mock_retry.assert_not_called()

    def test_the_wrapper_is_not_a_coroutine_function(self):
        """Regression guard shared with tests/unit/test_retired_tasks.py."""
        assert not asyncio.iscoroutinefunction(process_form_check_task.run)
