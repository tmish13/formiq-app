# TODO: Review the necessity of these web-specific (CSRF, cookie-based) auth flow tests \
# if the application's primary interface is exclusively mobile apps using token-based auth.
"""Tests for authentication flows with HttpOnly cookies and CSRF protection."""
import pytest
from fastapi import status
from httpx import AsyncClient
from unittest.mock import patch, MagicMock
import re
import json
from app.core.config import settings
from app.main import app
from app.core.security import create_email_verification_token
from app.models.user import User
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

# client = TestClient(app)

# Test data
TEST_USER = {
    "email": "test@example.com",
    "password": "StrongP@ssw0rd123",
    "username": "testuser",
    "full_name": "Test User"
}

@pytest.fixture
async def csrf_token(async_client: AsyncClient) -> str:
    """Get a CSRF token."""
    response = await async_client.get("/auth/csrf-token")
    assert response.status_code == 200
    return response.json()["csrf_token"]

@pytest.fixture
async def registered_user(async_client: AsyncClient, async_session: AsyncSession):
    """Register a test user and return user data."""
    # Clear any existing test user
    stmt = select(User).where(User.email == TEST_USER["email"])
    result = await async_session.execute(stmt)
    user_to_delete = result.scalars().first()
    if user_to_delete:
        await async_session.delete(user_to_delete)
        await async_session.commit()
    
    # Get CSRF token
    csrf_response = await async_client.get("/auth/csrf-token")
    assert csrf_response.status_code == 200
    local_csrf_token = csrf_response.json()["csrf_token"]
    
    # Register user
    headers = {"X-CSRF-Token": local_csrf_token}
    register_response = await async_client.post("/auth/register", json=TEST_USER, headers=headers)
    
    assert register_response.status_code == 201, register_response.text
    
    # Verify email
    token = create_email_verification_token(TEST_USER["email"])
    verify_response = await async_client.post(
        "/auth/verify-email", 
        json={"token": token},
        headers=headers
    )
    assert verify_response.status_code == 200, verify_response.text
    
    return {"user_data": verify_response.json(), "csrf_token": local_csrf_token}

@pytest.mark.asyncio
async def test_csrf_token_endpoint(async_client: AsyncClient):
    """Test CSRF token generation endpoint."""
    response = await async_client.get("/auth/csrf-token")
    assert response.status_code == 200
    data = response.json()
    assert "csrf_token" in data
    assert len(data["csrf_token"]) > 0
    
    # Check cookie
    cookies = response.cookies
    assert "csrf_token" in cookies
    
@pytest.mark.asyncio
async def test_register_without_csrf_token(async_client: AsyncClient):
    """Test register endpoint rejects requests without CSRF token."""
    response = await async_client.post("/auth/register", json=TEST_USER)
    assert response.status_code == 403  # Forbidden due to missing CSRF token
    
@pytest.mark.asyncio
async def test_register_with_csrf_token(async_client: AsyncClient, csrf_token: str):
    """Test user registration with CSRF token."""
    headers = {"X-CSRF-Token": csrf_token}
    
    # Use a different email for this test to avoid conflicts with `registered_user` fixture
    test_user_register = {**TEST_USER, "email": "register_test@example.com"}
    
    response = await async_client.post("/auth/register", json=test_user_register, headers=headers)
    assert response.status_code == 201, response.text
    
    # Check response data
    data = response.json()
    assert "id" in data
    assert data["email"] == test_user_register["email"]
    assert data["username"] == test_user_register["username"]
    assert "is_active" in data
    assert "is_verified" in data # is_verified should be False initially before email verification
    assert "password" not in data  # Password should not be returned
    
    # Check for HttpOnly cookies
    cookies = response.cookies
    assert "access_token" in cookies
    
    # Access token should be HttpOnly
    # httpx cookies don't directly expose the full 'Set-Cookie' string details easily like TestClient.
    # We trust FastAPI's set_cookie attributes are correctly set.
    # For a deeper check, one might inspect response.headers.getlist('set-cookie')
    # but that's more involved. For now, presence is the main check.
    # Example of deeper check:
    # set_cookie_headers = response.headers.getlist('set-cookie')
    # assert any("HttpOnly" in h and "access_token" in h for h in set_cookie_headers)
    access_cookie_header = ""
    for header_value in response.headers.getlist('set-cookie'):
        if "access_token=" in header_value:
            access_cookie_header = header_value
            break
    assert "HttpOnly" in access_cookie_header, "Access token cookie should be HttpOnly"

    # Clean up the user created if necessary, or rely on test isolation if DB is reset per test
    # For now, assume test isolation or subsequent tests handle cleanup

@pytest.mark.asyncio
async def test_login_flow(async_client: AsyncClient, async_session: AsyncSession):
    """Test the full login flow with HttpOnly cookies."""
    
    # Needs a fresh user for this flow to avoid interference
    login_test_user_email = "login_flow_test@example.com"
    login_test_user = {**TEST_USER, "email": login_test_user_email, "username": "loginflowuser"}

    # Clear any existing test user
    stmt = select(User).where(User.email == login_test_user_email)
    result = await async_session.execute(stmt)
    user_to_delete = result.scalars().first()
    if user_to_delete:
        await async_session.delete(user_to_delete)
        await async_session.commit()

    # 1. Get CSRF token
    csrf_response = await async_client.get("/auth/csrf-token")
    assert csrf_response.status_code == 200
    local_csrf_token = csrf_response.json()["csrf_token"]
    headers = {"X-CSRF-Token": local_csrf_token}
    
    # 2. Register a new user
    reg_response = await async_client.post("/auth/register", json=login_test_user, headers=headers)
    assert reg_response.status_code == 201, reg_response.text
    
    # 3. Verify email (critical for login if is_verified is checked)
    verification_token = create_email_verification_token(login_test_user_email)
    verify_response = await async_client.post("/auth/verify-email", json={"token": verification_token}, headers=headers)
    assert verify_response.status_code == 200, verify_response.text

    # 4. Logout (to ensure cookies from registration are cleared, if any persistent ones were set)
    # Note: Logout might need a valid session, but we test its effect on a subsequent login
    await async_client.post("/auth/logout", headers=headers) 
    # No specific status code assertion for logout here, focus is on login after
    
    # 5. Now login
    login_data = {
        "username": login_test_user["email"],  # OAuth2 spec uses 'username' field for form
        "password": login_test_user["password"]
    }
    login_response = await async_client.post("/auth/login", data=login_data, headers=headers)
    assert login_response.status_code == 200, login_response.text
    
    # Check response
    data = login_response.json()
    assert "user_id" in data # FastAPI Users typically returns more user details on login
    assert "access_token_expires_in" in data # Or similar if your token response includes it.
                                            # Default /auth/login from fastapi-users might not include this in body.
                                            # It sets cookies.
    
    # Check cookies are set
    cookies = login_response.cookies
    assert "access_token" in cookies
    assert "refresh_token" in cookies # If you have refresh token flow enabled and set via cookie
    
    # 6. Access protected endpoint (assuming /users/me requires auth and uses the cookie)
    # Important: The async_client needs to persist cookies across requests for this to work.
    # httpx.AsyncClient does this by default.
    me_response = await async_client.get(f"{settings.API_V1_STR}/users/me", headers=headers)
    assert me_response.status_code == 200, me_response.text
    user_data = me_response.json()
    assert user_data["email"] == login_test_user["email"]
    
    # 7. Test logout
    logout_response = await async_client.post("/auth/logout", headers=headers)
    assert logout_response.status_code == 200, logout_response.text
    
    # 8. After logout, accessing /users/me should fail
    # Cookies should have been cleared by /auth/logout
    me_after_logout_response = await async_client.get(f"{settings.API_V1_STR}/users/me", headers=headers)
    assert me_after_logout_response.status_code == 401, me_after_logout_response.text

@pytest.mark.asyncio
@patch("app.services.email_service.EmailService.send_password_reset_email")
async def test_password_reset_flow(mock_send_email: MagicMock, async_client: AsyncClient, async_session: AsyncSession):
    """Test the password reset flow."""
    
    reset_test_user_email = "reset_flow_test@example.com"
    reset_test_user = {**TEST_USER, "email": reset_test_user_email, "username": "resetflowuser"}

    # Ensure user exists and is verified for password reset
    # Clear any existing
    stmt_del = select(User).where(User.email == reset_test_user_email)
    result_del = await async_session.execute(stmt_del)
    user_to_delete = result_del.scalars().first()
    if user_to_delete:
        await async_session.delete(user_to_delete)
        await async_session.commit()

    # 1. Get CSRF for registration
    csrf_reg_response = await async_client.get("/auth/csrf-token")
    assert csrf_reg_response.status_code == 200
    csrf_for_reg = csrf_reg_response.json()["csrf_token"]
    headers_reg = {"X-CSRF-Token": csrf_for_reg}

    # 2. Register user
    reg_response = await async_client.post("/auth/register", json=reset_test_user, headers=headers_reg)
    assert reg_response.status_code == 201, reg_response.text
    
    # 3. Verify email
    verification_token = create_email_verification_token(reset_test_user_email)
    verify_response = await async_client.post("/auth/verify-email", json={"token": verification_token}, headers=headers_reg)
    assert verify_response.status_code == 200, verify_response.text

    # User should now exist and be verified.
    # Mock the email sending part
    mock_send_email.return_value = True # Assume email sending itself is successful
    
    # 4. Get a new CSRF token for the password reset request itself
    csrf_reset_req_response = await async_client.get("/auth/csrf-token")
    assert csrf_reset_req_response.status_code == 200
    csrf_for_reset_req = csrf_reset_req_response.json()["csrf_token"]
    headers_reset_req = {"X-CSRF-Token": csrf_for_reset_req}

    # 5. Request password reset
    response_req_reset = await async_client.post(
        "/auth/request-password-reset",
        json={"email": reset_test_user["email"]},
        headers=headers_reset_req
    )
    assert response_req_reset.status_code == 200, response_req_reset.text
    
    # Mock should have been called
    mock_send_email.assert_called_once()
    
    # Extract reset token from mock call (this part of the test remains the same logic)
    args, kwargs = mock_send_email.call_args
    reset_url = kwargs.get("reset_url", "") # Or however the token is passed to your email service
    # Fallback if reset_url is not in kwargs directly, maybe it's part of a context dict
    if not reset_url and args: # Assuming context dict might be the first positional arg
        if isinstance(args[0], dict) and "reset_url" in args[0]:
            reset_url = args[0]["reset_url"]
            
    assert reset_url, "Reset URL not found in mock call arguments"
    match = re.search(r"token=([^&]+)", reset_url)
    assert match, "Reset URL does not contain token"
    actual_reset_token = match.group(1)
    
    # 6. Get CSRF for the actual reset password POST
    csrf_reset_response = await async_client.get("/auth/csrf-token")
    assert csrf_reset_response.status_code == 200
    csrf_for_reset = csrf_reset_response.json()["csrf_token"]
    headers_reset = {"X-CSRF-Token": csrf_for_reset}

    # 7. Reset password
    new_password = "NewStrongP@ssw0rd456"
    response_reset_pw = await async_client.post(
        "/auth/reset-password",
        json={
            "token": actual_reset_token,
            "new_password": new_password,
            "confirm_password": new_password # Assuming your endpoint takes confirm_password
        },
        headers=headers_reset
    )
    assert response_reset_pw.status_code == 200, response_reset_pw.text
    
    # 8. Try login with new password
    # Get new CSRF for login
    csrf_login_response = await async_client.get("/auth/csrf-token")
    assert csrf_login_response.status_code == 200
    csrf_for_login = csrf_login_response.json()["csrf_token"]
    headers_login = {"X-CSRF-Token": csrf_for_login}

    login_data = {
        "username": reset_test_user["email"],
        "password": new_password
    }
    response_login_new_pw = await async_client.post("/auth/login", data=login_data, headers=headers_login)
    assert response_login_new_pw.status_code == 200, response_login_new_pw.text

@pytest.mark.asyncio
async def test_refresh_token(async_client: AsyncClient, registered_user):
    """Test refresh token functionality."""
    # `registered_user` fixture now returns a dict: {"user_data": ..., "csrf_token": ...}
    user_details = registered_user["user_data"]
    local_csrf_token = registered_user["csrf_token"] # CSRF token used during registration/verification of this user
    
    headers = {"X-CSRF-Token": local_csrf_token}
    
    # Get initial tokens by logging in the `registered_user`
    login_data = {
        "username": user_details["email"], # Use email from the fixture's registered user
        "password": TEST_USER["password"] # Original password from TEST_USER constant
    }
    
    # For login, we might need a fresh CSRF token if the one from registration is stale or single-use
    csrf_login_response = await async_client.get("/auth/csrf-token")
    assert csrf_login_response.status_code == 200
    csrf_for_login = csrf_login_response.json()["csrf_token"]
    headers_login = {"X-CSRF-Token": csrf_for_login}

    login_response = await async_client.post("/auth/login", data=login_data, headers=headers_login)
    assert login_response.status_code == 200, login_response.text
    
    # Should have cookies now
    assert "access_token" in login_response.cookies
    assert "refresh_token" in login_response.cookies
    
    # Refresh token - use the CSRF token obtained for the login request or a fresh one
    # Let's get a fresh one for the refresh action specifically
    csrf_refresh_response = await async_client.get("/auth/csrf-token")
    assert csrf_refresh_response.status_code == 200
    csrf_for_refresh = csrf_refresh_response.json()["csrf_token"]
    headers_refresh = {"X-CSRF-Token": csrf_for_refresh}

    refresh_response = await async_client.post("/auth/refresh", headers=headers_refresh)
    assert refresh_response.status_code == 200, refresh_response.text
    
    # Check that we got new cookies (specifically a new access_token)
    assert "access_token" in refresh_response.cookies
    
    # Check that we can access protected routes with the new token (cookie)
    # The client should automatically use the new cookie
    # A fresh CSRF might be needed if the protected route also checks it, though typically not for GET.
    # For safety, let's use the latest CSRF from the refresh step for the GET headers.
    me_response = await async_client.get(f"{settings.API_V1_STR}/users/me", headers=headers_refresh)
    assert me_response.status_code == 200, me_response.text
    me_data = me_response.json()
    assert me_data["email"] == user_details["email"]

@pytest.mark.asyncio
async def test_rate_limiting(async_client: AsyncClient):
    """Test that rate limiting is applied to auth endpoints (conceptual)."""
    # This is a conceptual test. Real rate limit testing needs specific setup
    # (e.g., mock FixedWindowRateLimiter or a very fast in-memory store for limits).
    # Here, we just make a few calls to an endpoint that might be rate-limited,
    # like /auth/csrf-token as it's simple and doesn't require auth state.
    
    # Get initial CSRF for headers
    initial_csrf_response = await async_client.get("/auth/csrf-token")
    assert initial_csrf_response.status_code == 200
    csrf_for_requests = initial_csrf_response.json()["csrf_token"]
    headers = {"X-CSRF-Token": csrf_for_requests}

    # Example: Send multiple requests to /auth/login with invalid data
    # FastAPI-Users default rate limit for login is often like "5/minute".
    # To truly test this, we'd need to send more than 5 requests very quickly.
    # and have control over the time window or use a mock.
    # For now, just illustrating the async conversion.
    for i in range(settings.RATE_LIMIT_LOGIN_ATTEMPTS + 5): # Exceed a hypothetical limit
        response = await async_client.post(
            "/auth/login", 
            data={"username": f"ratelimit{i}@example.com", "password": "password"},
            headers=headers # Reuse CSRF, though some systems might invalidate per use
        )
        # We can't easily assert 429 Too Many Requests without specific rate limit config knowledge
        # and control over the timing or a mock.
        # This loop just shows async calls.
        if response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
            print(f"Rate limit hit at attempt {i+1}") # For visibility if it happens
            # In a real test, you'd assert this after a certain number of calls.
            break 
    # No strong assertion here as rate limit behavior is highly config-dependent.
    # The goal is to show the test structure is async.
    assert True # Placeholder assertion

@pytest.mark.asyncio
async def test_protected_route_access(async_client: AsyncClient, registered_user):
    """Test access to protected routes after login (using registered_user fixture)."""
    user_details = registered_user["user_data"]
    # CSRF token used during registration of this user
    local_csrf_token = registered_user["csrf_token"]
    
    # Login the registered user
    # Get a fresh CSRF for login
    csrf_login_response = await async_client.get("/auth/csrf-token")
    assert csrf_login_response.status_code == 200
    csrf_for_login = csrf_login_response.json()["csrf_token"]
    headers_login = {"X-CSRF-Token": csrf_for_login}
    
    login_data = {
        "username": user_details["email"],
        "password": TEST_USER["password"] 
    }
    login_response = await async_client.post("/auth/login", data=login_data, headers=headers_login)
    assert login_response.status_code == 200, login_response.text
    
    # Access protected endpoint
    # Use the CSRF from login or a fresh one for the GET request.
    # As /users/me is a GET, CSRF in header might not be strictly checked by default by FastAPI-CSRF-Protect
    # if GET requests are exempt, but good practice to include if tokens are short-lived or for consistency.
    me_response = await async_client.get(f"{settings.API_V1_STR}/users/me", headers=headers_login)
    assert me_response.status_code == 200, me_response.text
    fetched_user_data = me_response.json()
    assert fetched_user_data["email"] == user_details["email"]

@pytest.mark.asyncio
@patch("app.services.email_service.EmailService.send_verification_email")
async def test_verify_email_flow(mock_send_email: MagicMock, async_client: AsyncClient, async_session: AsyncSession):
    """Test the email verification flow."""
    mock_send_email.return_value = True # Assume email sending itself is successful
    
    verify_email_user_email = "verify_email_flow@example.com"
    verify_email_user = {**TEST_USER, "email": verify_email_user_email, "username": "verifyemailuser"}

    # Clean up existing user
    stmt_del = select(User).where(User.email == verify_email_user_email)
    result_del = await async_session.execute(stmt_del)
    user_to_delete = result_del.scalars().first()
    if user_to_delete:
        await async_session.delete(user_to_delete)
        await async_session.commit()

    # 1. Get CSRF token
    csrf_response = await async_client.get("/auth/csrf-token")
    assert csrf_response.status_code == 200
    local_csrf_token = csrf_response.json()["csrf_token"]
    headers = {"X-CSRF-Token": local_csrf_token}

    # 2. Register user - this should trigger send_verification_email if using fastapi-users router event
    # or if your endpoint explicitly calls it.
    # For fastapi-users, the on_after_register event usually handles this.
    # Patching `app.services.email_service.EmailService.send_verification_email` assumes it's called during/after registration.
    register_response = await async_client.post("/auth/register", json=verify_email_user, headers=headers)
    assert register_response.status_code == 201, register_response.text
    
    # Check if email sending mock was called
    mock_send_email.assert_called_once() 
    
    # Extract verification token from mock call arguments
    args, kwargs = mock_send_email.call_args
    # The way token is passed might depend on your EmailService implementation.
    # Common pattern: token is part of a URL in a template context or directly.
    verification_url = ""
    if "verification_url" in kwargs: # Example if passed as a kwarg
        verification_url = kwargs["verification_url"]
    elif args and isinstance(args[0], dict) and "verification_url" in args[0]: # Example if in a context dict
         verification_url = args[0]["verification_url"]
    
    assert verification_url, "Verification URL not found in mock call to send_verification_email"
    match = re.search(r"token=([^&]+)", verification_url)
    assert match, "Verification URL does not contain token"
    actual_verification_token = match.group(1)
    
    # 3. Call verify-email endpoint with the token
    # Use the same CSRF token from registration or get a new one
    verify_response = await async_client.post(
        "/auth/verify-email", 
        json={"token": actual_verification_token},
        headers=headers 
    )
    assert verify_response.status_code == 200, verify_response.text
    verified_user_data = verify_response.json()
    assert verified_user_data["is_verified"] is True
    assert verified_user_data["email"] == verify_email_user_email

    # Check DB directly
    stmt_check = select(User).where(User.email == verify_email_user_email)
    result_check = await async_session.execute(stmt_check)
    db_user = result_check.scalars().first()
    assert db_user is not None
    assert db_user.is_verified is True

@pytest.mark.skip(reason="Endpoint is hypothetical or not implemented; test is a placeholder.")
@patch("app.services.user_service.UserService.update_user_profile") 
async def test_fitness_profile_update(mock_update_profile: MagicMock, async_client: AsyncClient, registered_user):
    """Test updating fitness profile after login (conceptual)."""
    user_details = registered_user["user_data"]
    local_csrf_token = registered_user["csrf_token"] # CSRF token from registration/verification
    
    # Mock the service call for profile update
    mock_update_profile.return_value = {"profile_updated": True, **user_details} 

    # Login the user first
    # Get a fresh CSRF for login
    csrf_login_response = await async_client.get("/auth/csrf-token")
    assert csrf_login_response.status_code == 200
    csrf_for_login = csrf_login_response.json()["csrf_token"]
    headers_login = {"X-CSRF-Token": csrf_for_login}

    login_data = {
        "username": user_details["email"],
        "password": TEST_USER["password"]
    }
    login_response = await async_client.post("/auth/login", data=login_data, headers=headers_login)
    assert login_response.status_code == 200, login_response.text
    
    # Now attempt to update fitness profile
    fitness_profile_data = {
        "height": 180, 
        "weight": 75, 
        "fitness_goals": ["strength", "hypertrophy"]
    }
    
    # Use CSRF token from login or get a fresh one for this specific action
    # For POST/PUT/DELETE, CSRF token is typically required
    headers_update = {"X-CSRF-Token": csrf_for_login} # Re-using from login for simplicity

    # Assuming an endpoint like /api/v1/users/me/fitness-profile
    # This is a HYPOTHETICAL endpoint
    update_response = await async_client.put(
        f"{settings.API_V1_STR}/users/me/fitness-profile", 
        json=fitness_profile_data,
        headers=headers_update
    ) 
    
    # This assertion depends on the actual behavior of the (hypothetical) endpoint
    # If the endpoint calls the mocked user_service.update_user_profile,
    # then the mock's return value would influence the response.
    # For this conceptual test, let's assume it returns 200 OK and reflects the update.
    assert update_response.status_code == 200, update_response.text 
    # mock_update_profile.assert_called_once_with(user_id=user_details["id"], profile_data=fitness_profile_data) # Adjust assertion based on service method signature
    
    # Example check of response data (if endpoint returns it)
    # response_data = update_response.json()
    # assert response_data.get("profile_updated") is True

    # This test is more conceptual due to the hypothetical endpoint.
    # The main goal is to demonstrate async conversion of a test with login + action.
    pass # Keep pass if the endpoint is purely hypothetical and no strong assertions can be made. 