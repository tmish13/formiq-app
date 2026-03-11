"""
Auth registration integration test — register → login → /users/me

Exercises the full request path with a real test PostgreSQL database.

To run standalone:
    docker compose -f tests/docker-compose.test.yml up -d
    cd backend
    pytest -q -m integration tests/integration/form_checks/test_auth_registration.py \
        --override-ini="addopts=-q --asyncio-mode=auto"

Also included in the standard integration gate (make test-integration).
"""
import uuid

import pytest
from httpx import AsyncClient, ASGITransport

pytestmark = pytest.mark.integration

_REGISTER = "/api/v1/auth/register"
_LOGIN = "/api/v1/auth/login"
_ME = "/api/v1/users/me"


# ---------------------------------------------------------------------------
# Fixture — unauthenticated client wired to the test Postgres DB
# ---------------------------------------------------------------------------

@pytest.fixture
async def raw_client(pg_factory):
    """
    AsyncClient with the real test-DB injected but NO auth override.
    Suitable for testing the full auth flow (register → login → /users/me).
    """
    from app.main import app
    from app.api import deps

    async def _override_db():
        async with pg_factory() as session:
            yield session

    app.dependency_overrides[deps.get_async_db] = _override_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.pop(deps.get_async_db, None)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestRegisterLoginMe:
    """End-to-end: register a brand-new user, log in, and fetch /users/me."""

    @pytest.mark.integration
    async def test_register_returns_201(self, raw_client: AsyncClient):
        """POST /auth/register with a valid payload must return HTTP 201."""
        suffix = uuid.uuid4().hex[:8]
        resp = await raw_client.post(
            _REGISTER,
            json={
                "email": f"regtest_{suffix}@formiq.com",
                "password": "PvOneShip2026!",
                "confirm_password": "PvOneShip2026!",
                "full_name": "Reg Test User",
                "username": f"regtest{suffix}",
            },
        )
        assert resp.status_code == 201, (
            f"Expected 201 from /register, got {resp.status_code}: {resp.text}"
        )
        data = resp.json()
        assert data["email"] == f"regtest_{suffix}@formiq.com"
        # New users are not onboarded yet
        assert data.get("has_completed_onboarding") is False

    @pytest.mark.integration
    async def test_register_then_login_then_me(self, raw_client: AsyncClient):
        """
        Full happy path:
          1. POST /auth/register     → 201
          2. POST /auth/login        → 200 + access_token
          3. GET  /users/me          → 200, has_completed_onboarding=False
        """
        suffix = uuid.uuid4().hex[:8]
        email = f"flow_{suffix}@formiq.com"
        password = "PvOneShip2026!"
        username = f"flow{suffix}"

        # Step 1 — register
        resp_reg = await raw_client.post(
            _REGISTER,
            json={
                "email": email,
                "password": password,
                "confirm_password": password,
                "full_name": "Flow Test User",
                "username": username,
            },
        )
        assert resp_reg.status_code == 201, (
            f"Register failed ({resp_reg.status_code}): {resp_reg.text}"
        )

        # Step 2 — login with the same credentials
        resp_login = await raw_client.post(
            _LOGIN,
            content=f"username={email}&password={password}",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert resp_login.status_code == 200, (
            f"Login failed ({resp_login.status_code}): {resp_login.text}"
        )
        login_data = resp_login.json()
        assert "access_token" in login_data, (
            f"No access_token in login response: {login_data}"
        )
        token = login_data["access_token"]

        # Step 3 — GET /users/me with the JWT
        resp_me = await raw_client.get(
            _ME,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp_me.status_code == 200, (
            f"/users/me failed ({resp_me.status_code}): {resp_me.text}"
        )
        me = resp_me.json()
        assert me["email"] == email
        assert me["has_completed_onboarding"] is False

    @pytest.mark.integration
    async def test_duplicate_email_returns_400(self, raw_client: AsyncClient):
        """Registering the same email twice must return 400."""
        suffix = uuid.uuid4().hex[:8]
        payload = {
            "email": f"dup_{suffix}@formiq.com",
            "password": "PvOneShip2026!",
            "confirm_password": "PvOneShip2026!",
            "full_name": "Dup User",
            "username": f"dup{suffix}",
        }
        resp1 = await raw_client.post(_REGISTER, json=payload)
        assert resp1.status_code == 201

        # Same email — username is different to isolate the email-unique constraint
        payload2 = dict(payload, username=f"dup2{suffix}")
        resp2 = await raw_client.post(_REGISTER, json=payload2)
        assert resp2.status_code == 400, (
            f"Expected 400 for duplicate email, got {resp2.status_code}: {resp2.text}"
        )
        body = resp2.json()
        # Custom exception handler may use "message" or "detail"
        error_text = body.get("message", body.get("detail", ""))
        assert "already exists" in error_text.lower(), (
            f"Expected 'already exists' in error, got: {body}"
        )

    @pytest.mark.integration
    async def test_weak_password_returns_422(self, raw_client: AsyncClient):
        """
        Backend must reject a password with no special character (422).
        This also validates that the backend rules match the comment in validators.py.
        """
        suffix = uuid.uuid4().hex[:8]
        resp = await raw_client.post(
            _REGISTER,
            json={
                "email": f"weakpw_{suffix}@formiq.com",
                "password": "NoSpecial1",   # digit ✓, special char ✗
                "confirm_password": "NoSpecial1",
                "full_name": "Weak Pw User",
                "username": f"weakpw{suffix}",
            },
        )
        assert resp.status_code == 422, (
            f"Expected 422 for weak password, got {resp.status_code}: {resp.text}"
        )
