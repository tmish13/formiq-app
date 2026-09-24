"""G-54: the API injects an AIService proxy; the real service (MediaPipe, torch, model loaders)
is built once per process on first *use*, never on injection. Measured cost of the eager
singleton: +407 MiB per gunicorn worker on its first request, with no inference run."""
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def fresh_process():
    from app.core import deps

    deps.LazyAIService._instance = None
    yield
    deps.LazyAIService._instance = None


async def test_injection_builds_nothing():
    from app.api import deps as api_deps
    from app.core import deps

    with patch.object(deps, "AIService") as ctor:
        injected = api_deps.get_ai_service()
        assert injected is await deps.get_ai_service()  # both dependency modules hand out the same proxy
        ctor.assert_not_called()


def test_first_use_builds_it_once_and_delegates():
    from app.core import deps

    with patch.object(deps, "AIService") as ctor:
        real = ctor.return_value
        real.detect_pose.return_value = ("landmarks", 0.9)
        svc = deps.lazy_ai_service
        assert svc.detect_pose("frame") == ("landmarks", 0.9)
        real.detect_pose.assert_called_once_with("frame")
        assert svc.reset_pose_tracker is real.reset_pose_tracker
        ctor.assert_called_once_with()


def test_constructing_the_form_check_service_stays_cheap():
    from app.core import deps
    from app.services.form_check_service import FormCheckService

    with patch.object(deps, "AIService") as ctor:
        FormCheckService(db=MagicMock(), settings=MagicMock(), storage_service=MagicMock(),
                         ai_service=deps.lazy_ai_service, cache_service=None)
        ctor.assert_not_called()
