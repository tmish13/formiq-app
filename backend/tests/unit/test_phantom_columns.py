"""A write to a field the model does not have must fail loudly, not vanish.

Three fields were lost this way for the life of the project:
  * `error_details` -- six call sites, including every finalized failure, so
    every FAILED form check was reason-less (G-37).
  * `summary` and `analysis_completed_at` -- written on every finalize and read
    back at form_check_service.py:483, against nothing.

Migration 0011 closes the last two instances. The guard closes the class.
"""
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import ServiceError
from app.models.form_check import FormCheck
from app.services.base_service import BaseService, _reject_unknown_fields

pytestmark = pytest.mark.unit


def _bare():
    """A FormCheck instance without running BaseModel's constructor.

    `FormCheck()` calls validate(), which raises on every non-nullable field.
    The guard only inspects type(db_obj), so a bare instance is the honest
    fixture here rather than a fully-populated row that tests nothing extra.
    """
    return FormCheck.__new__(FormCheck)


class TestTheGuard:
    def test_a_known_field_passes_through_untouched(self):
        data = {"status": "COMPLETED", "summary": "ok"}
        assert _reject_unknown_fields(_bare(), data) == data

    def test_an_unknown_field_raises_outside_production(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "test")
        with pytest.raises(ServiceError, match="error_details"):
            _reject_unknown_fields(_bare(), {"error_details": "boom"})

    def test_the_message_says_what_to_do_about_it(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "test")
        with pytest.raises(ServiceError) as exc:
            _reject_unknown_fields(_bare(), {"nope": 1})
        msg = str(exc.value)
        assert "silently discarded" in msg
        assert "Add the column" in msg

    def test_production_drops_the_key_and_keeps_serving(self, monkeypatch):
        """Losing a field is bad. 500ing a user's request over a field name is
        worse, and the error log still names it."""
        monkeypatch.setenv("ENVIRONMENT", "production")
        out = _reject_unknown_fields(_bare(), {"status": "X", "nope": 1})
        assert out == {"status": "X"}

    def test_it_reports_every_offending_key_at_once(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "test")
        with pytest.raises(ServiceError) as exc:
            _reject_unknown_fields(_bare(), {"a_bad": 1, "b_bad": 2})
        assert "a_bad" in str(exc.value) and "b_bad" in str(exc.value)

    @pytest.mark.asyncio
    async def test_update_async_refuses_a_phantom_field(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "test")
        db = AsyncMock()
        db.__class__ = type("FakeAsync", (), {})
        svc = BaseService.__new__(BaseService)
        svc.db, svc.model, svc._is_async = db, FormCheck, True
        with pytest.raises(ServiceError):
            await svc.update_async(db_obj=_bare(), obj_in={"error_details": "x"})


class TestTheColumnsExist:
    @pytest.mark.parametrize("name", ["summary", "analysis_completed_at"])
    def test_the_finalize_writers_now_have_somewhere_to_land(self, name):
        assert name in FormCheck.__table__.c

    def test_error_details_is_still_not_a_column(self):
        """It was never meant to be one. The reason belongs in `details`, a real
        JSON column, which is where the task already writes error_message."""
        assert "error_details" not in FormCheck.__table__.c


class TestPreloadIsGone:
    def test_the_dead_module_was_deleted(self):
        """app/core/preload.py selected fc.overall_score and fc.summary, neither
        of which existed, and had zero callers. Adding `summary` would have made
        it fail LATER -- on overall_score -- instead of sooner, which is worse
        to diagnose. Deleted in the same change as the column."""
        assert not (Path(__file__).resolve().parents[2]
                    / "app" / "core" / "preload.py").exists()
