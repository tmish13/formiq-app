"""Test exercises module."""
from fastapi.testclient import TestClient

from app.core.config import settings


def test_create_exercise(client: TestClient) -> None:
    """Test create exercise endpoint."""
    response = client.post(
        f"{settings.API_V1_STR}/exercises/",
        json={
            "name": "Squat",
            "description": "A compound exercise",
            "difficulty": "intermediate",
            "muscle_group": "legs",
            "equipment": "barbell"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Squat"
    assert data["description"] == "A compound exercise"
    assert data["difficulty"] == "intermediate"
    assert data["muscle_group"] == "legs"
    assert data["equipment"] == "barbell"
    assert "id" in data


def test_create_exercise_existing_name(client: TestClient) -> None:
    """Test create exercise with existing name."""
    response = client.post(
        f"{settings.API_V1_STR}/exercises/",
        json={
            "name": "Squat",
            "description": "A compound exercise",
            "difficulty": "intermediate",
            "muscle_group": "legs",
            "equipment": "barbell"
        }
    )
    assert response.status_code == 400


def test_read_exercises(client: TestClient) -> None:
    """Test read exercises endpoint."""
    response = client.get(f"{settings.API_V1_STR}/exercises/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_read_exercise(client: TestClient) -> None:
    """Test read exercise endpoint."""
    response = client.get(f"{settings.API_V1_STR}/exercises/1")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1


def test_read_exercise_not_found(client: TestClient) -> None:
    """Test read exercise not found."""
    response = client.get(f"{settings.API_V1_STR}/exercises/999")
    assert response.status_code == 404


def test_update_exercise(client: TestClient) -> None:
    """Test update exercise endpoint."""
    response = client.put(
        f"{settings.API_V1_STR}/exercises/1",
        json={"description": "Updated description"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["description"] == "Updated description"


def test_update_exercise_not_found(client: TestClient) -> None:
    """Test update exercise not found."""
    response = client.put(
        f"{settings.API_V1_STR}/exercises/999",
        json={"description": "Updated description"}
    )
    assert response.status_code == 404


def test_delete_exercise(client: TestClient) -> None:
    """Test delete exercise endpoint."""
    response = client.delete(f"{settings.API_V1_STR}/exercises/1")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1


def test_delete_exercise_not_found(client: TestClient) -> None:
    """Test delete exercise not found."""
    response = client.delete(f"{settings.API_V1_STR}/exercises/999")
    assert response.status_code == 404 