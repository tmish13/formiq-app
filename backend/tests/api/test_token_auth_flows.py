import pytest
from httpx import AsyncClient
from typing import Dict, Any

from app.main import app
from app.core.config import settings
from app.models.user import User
from tests.utils.user_utils import random_lower_string


# Test user data (primarily for registration test as login tests will use conftest test_user)
TEST_USER_REGISTER_DEFAULTS = {
    "email": "placeholder@example.com",
    "password": "Password123!",
    "username": "testuser"
}

async def test_login_success(async_client: AsyncClient, test_user: User):
    """Test successful login with correct credentials"""
    response = await async_client.post(
        "/auth/login",
        json={"email": test_user.email, "password": settings.TEST_USER_PASSWORD}
    )
    assert response.status_code == 200
    
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert "token_type" in data
    assert data["token_type"] == "bearer"
    
    assert "user" in data
    assert data["user"]["email"] == test_user.email


async def test_login_wrong_password(async_client: AsyncClient, test_user: User):
    """Test login failure with wrong password"""
    response = await async_client.post(
        "/auth/login",
        json={"email": test_user.email, "password": "wrongpassword"}
    )
    assert response.status_code == 401


async def test_register_user(async_client: AsyncClient):
    """Test user registration"""
    test_user_data = TEST_USER_REGISTER_DEFAULTS.copy()
    test_user_data["email"] = f"register_{random_lower_string(6)}@example.com"
    
    response = await async_client.post("/auth/register", json=test_user_data)
    assert response.status_code == 201
    
    data = response.json()
    assert "id" in data
    assert data["email"] == test_user_data["email"]
    assert data["username"] == test_user_data["username"]
    assert "is_active" in data
    assert "is_verified" in data
    assert "password" not in data


async def test_get_current_user(async_client: AsyncClient, test_user_headers: Dict[str, str], test_user: User):
    """Test getting current user with auth token"""
    response = await async_client.get("/users/me", headers=test_user_headers)
    assert response.status_code == 200
    
    data = response.json()
    assert "id" in data
    assert data["id"] == str(test_user.id)
    assert data["email"] == test_user.email
    assert data["username"] == test_user.username


async def test_refresh_token(async_client: AsyncClient, test_user: User):
    """Test refreshing the access token"""
    login_response = await async_client.post(
        "/auth/login",
        json={"email": test_user.email, "password": settings.TEST_USER_PASSWORD}
    )
    tokens = login_response.json()
    
    response = await async_client.post(
        "/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]}
    )
    assert response.status_code == 200
    
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["access_token"] != tokens["access_token"]


async def test_logout(async_client: AsyncClient, test_user_headers: Dict[str, str]):
    """Test user logout"""
    response = await async_client.post("/auth/logout", headers=test_user_headers)
    assert response.status_code == 200
    assert response.json()["detail"] == "Successfully logged out"


async def test_update_profile(async_client: AsyncClient, test_user_headers: Dict[str, str], test_user: User):
    """Test updating user profile"""
    update_data = {
        "username": "updated_user_" + random_lower_string(4),
        "fitness_goals": ["strength", "endurance"]
    }
    
    response = await async_client.patch(
        "/users/me",
        json=update_data,
        headers=test_user_headers
    )
    assert response.status_code == 200
    
    data = response.json()
    assert data["username"] == update_data["username"]
    assert data["fitness_goals"] == update_data["fitness_goals"]


async def test_rate_limiting(async_client: AsyncClient):
    """Test rate limiting on authentication endpoints"""
    if settings.RATE_LIMIT_ENABLED:
        for _ in range(settings.RATE_LIMIT_REQUESTS + 1):
            await async_client.post(
                "/auth/login",
                json={"email": "rate_limit_test@example.com", "password": "wrongpassword"}
            )
        response = await async_client.post(
            "/auth/login",
            json={"email": "rate_limit_test@example.com", "password": "wrongpassword"}
        )
        assert response.status_code == 429
    else:
        pytest.skip("Rate limiting is not enabled in settings")


async def test_cookie_settings(async_client: AsyncClient, test_user: User):
    """Test that cookies have correct security settings"""
    response = await async_client.post(
        "/auth/login",
        json={"email": test_user.email, "password": settings.TEST_USER_PASSWORD}
    )
    assert response.status_code == 200
    
    set_cookie_header = response.headers.get("set-cookie")
    
    found_relevant_cookie = False
    raw_cookies = response.headers.get_list("set-cookie")
    for cookie_str in raw_cookies:
        if "access_token" in cookie_str or "refresh_token" in cookie_str:
            found_relevant_cookie = True
            assert "HttpOnly" in cookie_str
            assert "Path=/" in cookie_str
            assert "SameSite=Lax" in cookie_str or "SameSite=Strict" in cookie_str
            if settings.COOKIE_SECURE:
                assert "Secure" in cookie_str
            else:
                assert "Secure" not in cookie_str
    
    assert found_relevant_cookie, "No relevant access_token or refresh_token cookie found to check attributes"


# Tests for V1 API endpoints, adapted from test_auth.py
async def test_v1_login_success_form_data(async_client: AsyncClient, test_user: User):
    """Test successful login to V1 endpoint using form data."""
    login_data = {
        "username": test_user.email,  # V1 endpoint uses 'username' field for email
        "password": settings.TEST_USER_PASSWORD
    }
    response = await async_client.post(f"{settings.API_V1_STR}/auth/login", data=login_data)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    # Add more assertions if V1 returns refresh_token or user details

async def test_v1_login_incorrect_password_form_data(async_client: AsyncClient, test_user: User):
    """Test login failure to V1 endpoint with wrong password using form data."""
    login_data = {
        "username": test_user.email,
        "password": "thisisdefinitelythewrongpassword"
    }
    response = await async_client.post(f"{settings.API_V1_STR}/auth/login", data=login_data)
    assert response.status_code == 401 # Or 400 depending on V1 implementation for bad credentials
    # Add assertion for error message if applicable, e.g.:
    # error_data = response.json()
    # assert "detail" in error_data
    # assert "Incorrect username or password" in error_data["detail"] 

async def test_v1_login_inactive_user_form_data(async_client: AsyncClient):
    """Test login to V1 endpoint for a newly registered (potentially inactive or unverified) user."""
    # Register a new user first using the non-V1 registration endpoint
    unique_email = f"inactive_v1_user_{random_lower_string(6)}@example.com"
    unique_username = f"inactive_v1_user_{random_lower_string(6)}"
    password = "ValidPassword123!"
    
    register_payload = {
        "email": unique_email,
        "username": unique_username,
        "password": password
    }
    register_response = await async_client.post("/auth/register", json=register_payload)
    assert register_response.status_code == 201 # Assuming registration itself is successful
    
    # Attempt to login with the new user via V1 endpoint
    login_data = {
        "username": unique_email, # V1 endpoint uses 'username' field for email
        "password": password
    }
    response = await async_client.post(f"{settings.API_V1_STR}/auth/login", data=login_data)
    
    # Expecting failure if newly registered users are treated as inactive/unverified by V1 login
    assert response.status_code == 400 # Or 401, depending on how V1 handles this
    error_data = response.json()
    assert "detail" in error_data
    # Example: Assert a specific message like "User is inactive" or "Email not verified"
    # This assertion depends on the specific error message from the V1 endpoint
    assert "inactive" in error_data["detail"].lower() or "verify" in error_data["detail"].lower() # Make this more specific 

async def test_v1_refresh_token(async_client: AsyncClient, test_user: User):
    """Test successful token refresh via V1 endpoint."""
    # Log in first via V1 endpoint to get tokens
    login_data = {
        "username": test_user.email,
        "password": settings.TEST_USER_PASSWORD
    }
    login_response = await async_client.post(f"{settings.API_V1_STR}/auth/login", data=login_data)
    assert login_response.status_code == 200
    login_tokens = login_response.json()
    assert "refresh_token" in login_tokens
    assert "access_token" in login_tokens
    
    old_access_token = login_tokens["access_token"]
    refresh_token_payload = {"refresh_token": login_tokens["refresh_token"]}
    
    response = await async_client.post(
        f"{settings.API_V1_STR}/auth/refresh-token", 
        json=refresh_token_payload
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["access_token"] != old_access_token
    # Optionally, check if a new refresh token is also returned and is different, if applicable
    # if "refresh_token" in data:
    #     assert data["refresh_token"] != login_tokens["refresh_token"]

async def test_v1_refresh_token_invalid(async_client: AsyncClient):
    """Test V1 refresh token endpoint with an invalid token."""
    response = await async_client.post(
        f"{settings.API_V1_STR}/auth/refresh-token",
        json={"refresh_token": "this.is.an.invalid.refresh.token"}
    )
    assert response.status_code == 401 # Or 400/403 depending on API error handling
    # error_data = response.json()
    # assert "detail" in error_data
    # assert "invalid" in error_data["detail"].lower() 