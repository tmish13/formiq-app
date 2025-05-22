"""API tests for authenticated user endpoints (/users/me and related)."""
import pytest
from httpx import AsyncClient

# Remove unused imports and fixtures; rely on conftest.py for async_client, test_user, current_user_headers, etc.

@pytest.mark.asyncio
async def test_get_current_user(async_client: AsyncClient, current_user_headers: dict, test_user):
    """Test getting the current user."""
    response = await async_client.get("/api/v1/users/me", headers=current_user_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == test_user.email
    assert data["full_name"] == test_user.full_name
    assert data["id"] == str(test_user.id)

@pytest.mark.asyncio
async def test_update_current_user(async_client: AsyncClient, current_user_headers: dict, test_user):
    """Test updating the current user."""
    response = await async_client.put(
        "/api/v1/users/me",
        headers=current_user_headers,
        json={"full_name": "Updated Current User"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == "Updated Current User"
    assert data["email"] == test_user.email

# If there are admin-level endpoints (e.g., /api/v1/users/ for listing or updating other users),
# move those tests to a new file test_admin_user_api.py. Otherwise, keep only /users/me and self-user logic here. 