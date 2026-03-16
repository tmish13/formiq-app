"""
Regression tests for the "countable session" rule.

A session is countable only when it contains at least one set with reps > 0.
Empty sessions must be rejected at POST time and filtered from GET results.
"""
import pytest
from fastapi import HTTPException
from unittest.mock import AsyncMock, MagicMock, patch

from app.api.v1.endpoints.training_sessions import _is_countable


# ---------------------------------------------------------------------------
# Unit tests for the pure helper
# ---------------------------------------------------------------------------

class TestIsCountable:
    def test_empty_list_is_not_countable(self):
        assert _is_countable([]) is False

    def test_none_is_not_countable(self):
        assert _is_countable(None) is False

    def test_set_with_zero_reps_is_not_countable(self):
        assert _is_countable([{"reps": 0, "weightLb": 135}]) is False

    def test_set_with_positive_reps_is_countable(self):
        assert _is_countable([{"reps": 5, "weightLb": 135}]) is True

    def test_bodyweight_set_with_reps_is_countable(self):
        """Bodyweight sets have weightLb=0 — reps alone makes them countable."""
        assert _is_countable([{"reps": 10, "weightLb": 0}]) is True

    def test_mixed_sets_one_valid_is_countable(self):
        """One warm-up (reps=0) and one working set (reps=5) → countable."""
        sets = [{"reps": 0, "setType": "warmup"}, {"reps": 5, "setType": "working"}]
        assert _is_countable(sets) is True

    def test_all_zero_reps_is_not_countable(self):
        sets = [{"reps": 0}, {"reps": 0}]
        assert _is_countable(sets) is False

    def test_malformed_set_dict_missing_reps_is_not_countable(self):
        """Dicts without a 'reps' key default to 0 and don't count."""
        assert _is_countable([{"weightLb": 135}]) is False

    def test_non_dict_entries_are_skipped(self):
        """Corrupt/non-dict entries must not crash the helper."""
        assert _is_countable(["bad", None, 42]) is False


# ---------------------------------------------------------------------------
# Endpoint-level tests (POST rejects empty; GET filters empty)
# ---------------------------------------------------------------------------

def _make_fake_user():
    user = MagicMock()
    user.id = "user-123"
    return user


def _make_fake_session(sets_json, session_id="sess-abc"):
    sess = MagicMock()
    sess.id = session_id
    sess.user_id = "user-123"
    sess.sets_json = sets_json
    return sess


class TestCreateTrainingSessionEndpoint:
    @pytest.mark.asyncio
    async def test_empty_workout_rejected_with_422(self):
        from app.api.v1.endpoints.training_sessions import create_training_session
        from app.schemas.training_session import TrainingSessionCreate

        body = TrainingSessionCreate(
            id="sess-empty",
            started_at="2026-03-01T10:00:00Z",
            goal="strength",
            sets_json=[],
        )
        db = AsyncMock()
        user = _make_fake_user()

        with pytest.raises(HTTPException) as exc_info:
            await create_training_session(body=body, db=db, current_user=user)

        assert exc_info.value.status_code == 422
        assert "reps > 0" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_zero_reps_only_workout_rejected_with_422(self):
        from app.api.v1.endpoints.training_sessions import create_training_session
        from app.schemas.training_session import TrainingSessionCreate

        body = TrainingSessionCreate(
            id="sess-zeros",
            started_at="2026-03-01T10:00:00Z",
            goal="strength",
            sets_json=[{"reps": 0, "weightLb": 0}],
        )
        db = AsyncMock()
        user = _make_fake_user()

        with pytest.raises(HTTPException) as exc_info:
            await create_training_session(body=body, db=db, current_user=user)

        assert exc_info.value.status_code == 422

    @pytest.mark.asyncio
    async def test_valid_workout_accepted(self):
        from app.api.v1.endpoints.training_sessions import create_training_session
        from app.schemas.training_session import TrainingSessionCreate

        body = TrainingSessionCreate(
            id="sess-valid",
            started_at="2026-03-01T10:00:00Z",
            goal="strength",
            sets_json=[{"reps": 5, "weightLb": 135, "setType": "working"}],
        )
        db = AsyncMock()
        db.get = AsyncMock(return_value=None)
        db.add = MagicMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        user = _make_fake_user()

        # Should not raise
        await create_training_session(body=body, db=db, current_user=user)
        db.add.assert_called_once()
        db.commit.assert_awaited_once()


class TestListTrainingSessionsEndpoint:
    @pytest.mark.asyncio
    async def test_empty_sessions_filtered_from_get(self):
        from app.api.v1.endpoints.training_sessions import list_training_sessions

        empty_sess = _make_fake_session(sets_json=[], session_id="sess-empty")
        valid_sess = _make_fake_session(
            sets_json=[{"reps": 5, "weightLb": 100}], session_id="sess-valid"
        )

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [empty_sess, valid_sess]
        execute_result = MagicMock()
        execute_result.scalars.return_value = scalars_mock

        db = AsyncMock()
        db.execute = AsyncMock(return_value=execute_result)
        user = _make_fake_user()

        result = await list_training_sessions(limit=200, db=db, current_user=user)

        assert len(result) == 1
        assert result[0].id == "sess-valid"

    @pytest.mark.asyncio
    async def test_historical_zero_reps_sessions_excluded(self):
        """Historically-synced sessions with only reps=0 are excluded from GET."""
        from app.api.v1.endpoints.training_sessions import list_training_sessions

        bad_hist = _make_fake_session(
            sets_json=[{"reps": 0, "weightLb": 0}], session_id="sess-hist-bad"
        )
        good_hist = _make_fake_session(
            sets_json=[{"reps": 8, "weightLb": 0}], session_id="sess-hist-good"
        )

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [bad_hist, good_hist]
        execute_result = MagicMock()
        execute_result.scalars.return_value = scalars_mock

        db = AsyncMock()
        db.execute = AsyncMock(return_value=execute_result)
        user = _make_fake_user()

        result = await list_training_sessions(limit=200, db=db, current_user=user)

        assert len(result) == 1
        assert result[0].id == "sess-hist-good"
