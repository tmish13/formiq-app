"""Test users module."""
from fastapi.testclient import TestClient
import pytest
from tests.utils.factories import UserFactory
from app.models.user import User

from app.core.config import settings


def test_create_user(client: TestClient) -> None:
    """Test create user endpoint."""
    response = client.post(
        f"{settings.API_V1_STR}/users/",
        json={
            "email": "new@example.com",
            "password": "test123",
            "full_name": "New User"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "new@example.com"
    assert data["full_name"] == "New User"
    assert "id" in data


def test_create_user_existing_email(client: TestClient) -> None:
    """Test create user with existing email."""
    response = client.post(
        f"{settings.API_V1_STR}/users/",
        json={
            "email": "test@example.com",
            "password": "test123",
            "full_name": "Test User"
        }
    )
    assert response.status_code == 400


def test_read_users(client: TestClient) -> None:
    """Test read users endpoint."""
    response = client.get(f"{settings.API_V1_STR}/users/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_read_user(client: TestClient) -> None:
    """Test read user endpoint."""
    response = client.get(f"{settings.API_V1_STR}/users/1")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1


def test_read_user_not_found(client: TestClient) -> None:
    """Test read user not found."""
    response = client.get(f"{settings.API_V1_STR}/users/999")
    assert response.status_code == 404


def test_update_user(client: TestClient) -> None:
    """Test update user endpoint."""
    response = client.put(
        f"{settings.API_V1_STR}/users/1",
        json={"full_name": "Updated Name"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == "Updated Name"


def test_update_user_not_found(client: TestClient) -> None:
    """Test update user not found."""
    response = client.put(
        f"{settings.API_V1_STR}/users/999",
        json={"full_name": "Updated Name"}
    )
    assert response.status_code == 404


def test_delete_user(client: TestClient) -> None:
    """Test delete user endpoint."""
    response = client.delete(f"{settings.API_V1_STR}/users/1")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1


def test_delete_user_not_found(client: TestClient) -> None:
    """Test delete user not found."""
    response = client.delete(f"{settings.API_V1_STR}/users/999")
    assert response.status_code == 404


def test_user_creation_from_factory():
    '''Test basic user creation using UserFactory.'''
    user = UserFactory()
    assert user.email.endswith("@example.com") # Default factory behavior
    assert user.is_active is True # Default factory behavior
    assert user.is_superuser is False # Default factory behavior
    assert isinstance(user, User)


def test_superuser_creation_from_factory():
    '''Test superuser creation using UserFactory.'''
    admin_user = UserFactory(is_superuser=True)
    assert admin_user.is_superuser is True
    assert admin_user.is_active is True # Superusers should also be active by default from factory
    assert admin_user.email.endswith("@example.com")
    assert isinstance(admin_user, User) 