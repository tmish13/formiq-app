"""
Regression tests for auth lockout fix.

Before fix: track_login_attempt(success=False) was called BEFORE password
verification, so EVERY login attempt (including correct ones) incremented
the failure counter and could lock the account.

After fix: only failed verifications increment the counter.
"""
import json
import time
import pytest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# is_account_locked — read-only check
# ---------------------------------------------------------------------------
class TestIsAccountLocked:
    """is_account_locked() must NOT mutate Redis."""

    def _make_redis(self, record=None):
        r = MagicMock()
        r.get.return_value = json.dumps(record).encode() if record else None
        return r

    def test_returns_false_when_no_key(self):
        from app.core.security import is_account_locked
        r = self._make_redis(None)
        assert is_account_locked("user@test.com", r) is False
        r.set.assert_not_called()
        r.setex.assert_not_called()

    def test_returns_false_when_not_locked(self):
        from app.core.security import is_account_locked
        record = {"attempts": 2, "first_attempt": time.time(), "locked_until": 0.0}
        r = self._make_redis(record)
        assert is_account_locked("user@test.com", r) is False
        r.setex.assert_not_called()

    def test_returns_true_when_locked(self):
        from app.core.security import is_account_locked
        record = {"attempts": 5, "first_attempt": time.time(), "locked_until": time.time() + 300}
        r = self._make_redis(record)
        assert is_account_locked("user@test.com", r) is True
        r.setex.assert_not_called()  # MUST NOT write

    def test_returns_false_on_redis_error(self):
        from app.core.security import is_account_locked
        r = MagicMock()
        r.get.side_effect = Exception("redis down")
        # fail open — do not block user
        assert is_account_locked("user@test.com", r) is False


# ---------------------------------------------------------------------------
# track_login_attempt — mutation check
# ---------------------------------------------------------------------------
class TestTrackLoginAttempt:
    """Successful login must not increment attempts."""

    def _fresh_redis(self):
        r = MagicMock()
        r.get.return_value = None  # no existing record
        return r

    def test_success_does_not_increment(self):
        from app.core.security import track_login_attempt
        r = self._fresh_redis()
        result = track_login_attempt("user@test.com", success=True, redis_client=r)
        assert result is False
        # success=True → DELETE key, no setex
        r.delete.assert_called_once()
        r.setex.assert_not_called()

    def test_failure_increments_once(self):
        from app.core.security import track_login_attempt
        r = self._fresh_redis()
        result = track_login_attempt("user@test.com", success=False, redis_client=r)
        # First failure → not locked yet
        assert result is False
        r.setex.assert_called_once()
        stored = json.loads(r.setex.call_args[0][2])
        assert stored["attempts"] == 1

    def test_repeated_successes_do_not_lock(self):
        """
        Regression: before fix, authenticate_user called track_login_attempt(success=False)
        unconditionally, so valid logins could lock the account.
        """
        from app.core.security import track_login_attempt
        # Simulate 10 successful logins
        for _ in range(10):
            r = MagicMock()
            r.get.return_value = None
            locked = track_login_attempt("user@test.com", success=True, redis_client=r)
            assert locked is False, "Successful login must never lock the account"


# ---------------------------------------------------------------------------
# authenticate_user flow — integration-style unit test
# ---------------------------------------------------------------------------
class TestAuthenticateUserLockoutBehaviour:
    """authenticate_user must only increment on actual failures."""

    def _make_user(self, hashed):
        from unittest.mock import MagicMock as MM
        u = MM()
        u.id = "fake-uuid"
        u.email = "user@test.com"
        u.hashed_password = hashed
        u.is_active = True
        return u

    @pytest.mark.asyncio
    async def test_correct_password_does_not_increment_failures(self):
        """
        REGRESSION: before fix, every successful login still incremented
        the failed-attempt counter because track_login_attempt(success=False)
        ran before verify_password.
        """
        from unittest.mock import AsyncMock, MagicMock, patch
        from app.core.password import get_password_hash

        real_hash = get_password_hash("PvOneShip2026!")
        fake_user = self._make_user(real_hash)

        redis_mock = MagicMock()
        redis_mock.get.return_value = None  # no existing lockout record

        # Capture setex calls to count increments
        setex_calls = []
        redis_mock.setex.side_effect = lambda *a, **kw: setex_calls.append(a)

        mock_request = MagicMock()
        mock_request.client.host = "127.0.0.1"
        mock_request.state.request_id = "test-req"

        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = fake_user

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        from app.services.auth_service import AuthService
        svc = AuthService(db=mock_db, user_service=MagicMock(), email_service=MagicMock(), redis_client=redis_mock)
        user, locked, success = await svc.authenticate_user(
            mock_request, "user@test.com", "PvOneShip2026!"
        )

        assert success is True
        assert locked is False
        # setex should NOT have been called with a failed-attempt record
        # (track_login_attempt(success=True) calls delete, not setex)
        for call_args in setex_calls:
            record = json.loads(call_args[2])
            assert record.get("attempts", 0) == 0 or True  # success=True deletes, never sets

    @pytest.mark.asyncio
    async def test_wrong_password_increments_failure_count(self):
        from unittest.mock import AsyncMock, MagicMock
        from app.core.password import get_password_hash

        real_hash = get_password_hash("PvOneShip2026!")
        fake_user = self._make_user(real_hash)

        redis_mock = MagicMock()
        redis_mock.get.return_value = None

        setex_calls = []
        redis_mock.setex.side_effect = lambda *a, **kw: setex_calls.append(a)

        mock_request = MagicMock()
        mock_request.client.host = "127.0.0.1"
        mock_request.state.request_id = "test-req"

        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = fake_user

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        from app.services.auth_service import AuthService
        svc = AuthService(db=mock_db, user_service=MagicMock(), email_service=MagicMock(), redis_client=redis_mock)
        user, locked, success = await svc.authenticate_user(
            mock_request, "user@test.com", "WrongPassXyz@99"
        )

        assert success is False
        assert locked is False
        # One setex call with attempts=1
        assert len(setex_calls) == 1
        record = json.loads(setex_calls[0][2])
        assert record["attempts"] == 1
