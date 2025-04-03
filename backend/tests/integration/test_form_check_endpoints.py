"""Integration tests for form check endpoints."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
import io
import uuid
from typing import Dict, Any

from app.core.config import settings
from app.main import app
from app.models.form_check import FormCheck, FeedbackItem
from app.models.user import User
from app.models.enums import FormCheckStatus, FeedbackType, FeedbackSeverity, ExerciseType
from app.core.deps import get_db, get_current_user_sync
from app.db.base import Base
from app.core.auth import create_access_token


@pytest.fixture(scope="module")
def client():
    """Create test client for the app."""
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    # Use a clean database for tests
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    
    # Use in-memory SQLite for tests
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def override_get_db(db_session):
    """Override get_db dependency."""
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = _override_get_db
    yield
    app.dependency_overrides = {}


@pytest.fixture
def user(db_session: Session) -> User:
    """Create a test user."""
    user = User(
        email="test@example.com",
        password="hashed_password",
        full_name="Test User"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(user: User) -> Dict[str, str]:
    """Create authorization headers for the test user."""
    access_token = create_access_token(
        data={"sub": user.email}
    )
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def override_auth(user: User):
    """Override auth dependency to use test user."""
    def _get_current_user_override():
        return user
    
    app.dependency_overrides[get_current_user_sync] = _get_current_user_override
    yield
    del app.dependency_overrides[get_current_user_sync]


@pytest.fixture
def form_check(db_session: Session, user: User) -> FormCheck:
    """Create a test form check."""
    form_check = FormCheck(
        id=uuid.uuid4(),
        video_url="https://example.com/video.mp4",
        exercise_id=uuid.uuid4(),
        user_id=user.id,
        status="pending"
    )
    db_session.add(form_check)
    db_session.commit()
    db_session.refresh(form_check)
    return form_check


class TestFormCheckEndpoints:
    """Tests for form check endpoints."""

    def test_create_form_check(self, client: TestClient, override_get_db, override_auth):
        """Test creating a form check."""
        # Create a mock video file
        video_file = io.BytesIO(b"test video content")
        video_file.name = "test_video.mp4"
        
        # Test data
        form_data = {
            "exercise_type": ExerciseType.SQUAT.value
        }
        
        files = {
            "video": ("test_video.mp4", video_file, "video/mp4")
        }
        
        # Submit form check
        response = client.post(
            f"{settings.API_V1_STR}/form-checks/",
            data=form_data,
            files=files
        )
        
        # Check response
        assert response.status_code == 201
        data = response.json()
        assert data["video_url"]
        assert data["status"] == FormCheckStatus.PENDING.value
        assert "id" in data
    
    def test_get_form_checks(self, client: TestClient, override_get_db, override_auth, form_check):
        """Test getting all form checks for a user."""
        response = client.get(
            f"{settings.API_V1_STR}/form-checks/"
        )
        
        # Check response
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["id"] == str(form_check.id)
    
    def test_get_form_check(self, client: TestClient, override_get_db, override_auth, form_check):
        """Test getting a specific form check."""
        response = client.get(
            f"{settings.API_V1_STR}/form-checks/{form_check.id}"
        )
        
        # Check response
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(form_check.id)
        assert data["video_url"] == form_check.video_url
    
    def test_add_feedback(self, client: TestClient, override_get_db, override_auth, form_check):
        """Test adding feedback to a form check."""
        feedback_data = {
            "feedback_type": FeedbackType.FORM.value,
            "severity": FeedbackSeverity.MEDIUM.value,
            "timestamp": 15.5,
            "description": "Knees caving inward during descent",
            "suggestions": ["Keep knees pushed outward", "Focus on engaging glutes"]
        }
        
        response = client.post(
            f"{settings.API_V1_STR}/form-checks/{form_check.id}/feedback",
            json=feedback_data
        )
        
        # Check response
        assert response.status_code == 201
        data = response.json()
        assert data["form_check_id"] == str(form_check.id)
        assert data["feedback_type"] == feedback_data["feedback_type"]
        assert data["description"] == feedback_data["description"]
    
    def test_complete_analysis(self, client: TestClient, override_get_db, override_auth, form_check):
        """Test completing a form check analysis."""
        complete_data = {
            "summary": "Overall good form with minor issues with knee positioning",
            "overall_score": 8.5
        }
        
        response = client.post(
            f"{settings.API_V1_STR}/form-checks/{form_check.id}/complete",
            json=complete_data
        )
        
        # Check response
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(form_check.id)
        assert data["status"] == FormCheckStatus.COMPLETED.value
        assert data["overall_feedback"] == complete_data["summary"]
        assert data["score"] == complete_data["overall_score"]
    
    def test_delete_form_check(self, client: TestClient, override_get_db, override_auth, form_check):
        """Test deleting a form check."""
        response = client.delete(
            f"{settings.API_V1_STR}/form-checks/{form_check.id}"
        )
        
        # Check response
        assert response.status_code == 204
        
        # Check it was deleted
        get_response = client.get(
            f"{settings.API_V1_STR}/form-checks/{form_check.id}"
        )
        assert get_response.status_code == 404 