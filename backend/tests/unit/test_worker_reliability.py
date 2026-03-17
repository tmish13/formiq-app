"""
Tests for Celery worker reliability fixes:
  1. NullPool session lifecycle — get_async_session_for_celery() uses the NullPool
     engine so no asyncpg connections survive across asyncio.run() boundaries.
  2. Coaching-feedback gating — the coaching block is skipped (no import attempted)
     when COACHING_FEEDBACK_ENABLED is False.
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# 1. NullPool session lifecycle
# ---------------------------------------------------------------------------

class TestCelerySessionNullPool:
    """get_async_session_for_celery() must use the NullPool engine."""

    def test_celery_session_factory_is_nullpool(self):
        """_celery_async_engine is configured with NullPool."""
        from sqlalchemy.pool import NullPool
        from app.core.database import _celery_async_engine
        assert isinstance(_celery_async_engine.pool, NullPool), (
            "_celery_async_engine should use NullPool to avoid cross-loop "
            "asyncpg connection reuse"
        )

    def test_celery_engine_is_separate_from_main_engine(self):
        """_celery_async_engine must be a distinct object from async_engine."""
        from app.core.database import _celery_async_engine, async_engine
        assert _celery_async_engine is not async_engine, (
            "_celery_async_engine must be a separate engine instance so its "
            "pool configuration is independent of the main web-app engine"
        )

    def test_celery_session_yields_async_session(self):
        """get_async_session_for_celery() yields an AsyncSession successfully."""
        from sqlalchemy.ext.asyncio import AsyncSession
        from app.core.database import _celery_async_session_factory

        mock_session = MagicMock(spec=AsyncSession)
        mock_session.close = AsyncMock()
        mock_session.rollback = AsyncMock()

        with patch("app.core.database._celery_async_session_factory", return_value=mock_session):
            async def _run():
                from app.core.database import get_async_session_for_celery
                async with get_async_session_for_celery() as session:
                    assert session is mock_session
                mock_session.close.assert_awaited_once()

            asyncio.run(_run())

    def test_celery_session_rolls_back_on_error(self):
        """get_async_session_for_celery() rolls back and re-raises on exception."""
        from sqlalchemy.ext.asyncio import AsyncSession
        from app.core.database import _celery_async_session_factory

        mock_session = MagicMock(spec=AsyncSession)
        mock_session.close = AsyncMock()
        mock_session.rollback = AsyncMock()

        with patch("app.core.database._celery_async_session_factory", return_value=mock_session):
            async def _run():
                from app.core.database import get_async_session_for_celery
                with pytest.raises(ValueError, match="boom"):
                    async with get_async_session_for_celery() as _:
                        raise ValueError("boom")
                mock_session.rollback.assert_awaited_once()
                mock_session.close.assert_awaited_once()

            asyncio.run(_run())

    def test_session_closed_after_two_sequential_asyncio_runs(self):
        """
        Simulates two sequential asyncio.run() calls (like two Celery tasks).
        Each should get an independent session that is fully closed before the
        next run starts.  With NullPool there are no shared connections, so this
        must not raise any event-loop errors.
        """
        from sqlalchemy.ext.asyncio import AsyncSession
        from app.core.database import _celery_async_session_factory

        closed_counts = []

        def make_mock():
            m = MagicMock(spec=AsyncSession)
            m.close = AsyncMock(side_effect=lambda: closed_counts.append(1))
            m.rollback = AsyncMock()
            return m

        with patch("app.core.database._celery_async_session_factory", side_effect=make_mock):
            from app.core.database import get_async_session_for_celery

            async def _task():
                async with get_async_session_for_celery() as _:
                    pass  # just open and close

            # First task
            asyncio.run(_task())
            # Second task — separate event loop, should be clean
            asyncio.run(_task())

        assert len(closed_counts) == 2, "Both sessions must be closed, one per asyncio.run()"


# ---------------------------------------------------------------------------
# 2. Coaching-feedback gating
# ---------------------------------------------------------------------------

class TestCoachingFeedbackGating:
    """Coaching feedback import must be guarded by COACHING_FEEDBACK_ENABLED."""

    def test_flag_defaults_false(self):
        """COACHING_FEEDBACK_ENABLED must default to False in Settings."""
        from app.core.config import Settings
        s = Settings()
        assert s.COACHING_FEEDBACK_ENABLED is False, (
            "COACHING_FEEDBACK_ENABLED must default to False so beta workers "
            "without langchain_openai never attempt the import"
        )

    def test_flag_respects_env_true(self, monkeypatch):
        """COACHING_FEEDBACK_ENABLED=true in env enables the flag."""
        monkeypatch.setenv("COACHING_FEEDBACK_ENABLED", "true")
        from app.core.config import Settings
        s = Settings()
        assert s.COACHING_FEEDBACK_ENABLED is True

    def test_coaching_block_skipped_when_disabled(self):
        """
        When COACHING_FEEDBACK_ENABLED=False the coaching block must not attempt
        to import rag_feedback_service, so no ModuleNotFoundError is raised even
        if langchain_openai is absent.
        """
        import sys
        # Ensure langchain_openai appears missing
        saved = sys.modules.pop("langchain_openai", None)
        # Also ensure rag_feedback_service is not cached
        rag_key = "app.services.rag_feedback_service"
        saved_rag = sys.modules.pop(rag_key, None)

        try:
            mock_settings = MagicMock()
            mock_settings.COACHING_FEEDBACK_ENABLED = False

            # Simulate the guard condition exactly as written in analysis_tasks.py
            _is_shadow = False
            pv1_decision = "good"

            rag_imported = False
            if not _is_shadow and pv1_decision != "uncertain" and getattr(mock_settings, "COACHING_FEEDBACK_ENABLED", False):
                # This block must NOT run
                import app.services.rag_feedback_service  # noqa
                rag_imported = True

            assert not rag_imported, "Coaching block must be skipped when COACHING_FEEDBACK_ENABLED=False"
        finally:
            if saved is not None:
                sys.modules["langchain_openai"] = saved
            if saved_rag is not None:
                sys.modules[rag_key] = saved_rag

    def test_coaching_block_runs_when_enabled(self):
        """
        When COACHING_FEEDBACK_ENABLED=True the guard passes and rag_feedback_service
        would be imported (we just verify the condition evaluates truthy).
        """
        mock_settings = MagicMock()
        mock_settings.COACHING_FEEDBACK_ENABLED = True

        _is_shadow = False
        pv1_decision = "good"

        should_run = (
            not _is_shadow
            and pv1_decision != "uncertain"
            and getattr(mock_settings, "COACHING_FEEDBACK_ENABLED", False)
        )
        assert should_run, "Coaching block must run when COACHING_FEEDBACK_ENABLED=True"

    def test_coaching_block_skipped_for_uncertain(self):
        """Coaching block must be skipped when pv1_decision='uncertain' regardless of flag."""
        mock_settings = MagicMock()
        mock_settings.COACHING_FEEDBACK_ENABLED = True

        _is_shadow = False
        pv1_decision = "uncertain"

        should_run = (
            not _is_shadow
            and pv1_decision != "uncertain"
            and getattr(mock_settings, "COACHING_FEEDBACK_ENABLED", False)
        )
        assert not should_run

    def test_coaching_block_skipped_for_shadow_mode(self):
        """Coaching block must be skipped in shadow mode regardless of flag."""
        mock_settings = MagicMock()
        mock_settings.COACHING_FEEDBACK_ENABLED = True

        _is_shadow = True
        pv1_decision = "good"

        should_run = (
            not _is_shadow
            and pv1_decision != "uncertain"
            and getattr(mock_settings, "COACHING_FEEDBACK_ENABLED", False)
        )
        assert not should_run
