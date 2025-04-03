"""Integration tests for feedback endpoints."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
import uuid
from typing import Dict

from app.core.config import settings
from app.main import app
from app.models.form_check import FormCheck, FeedbackItem
from app.models.user import User
from app.models.enums import FeedbackType, FeedbackSeverity
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


@pytest.fixture
def feedback_item(db_session: Session, form_check: FormCheck) -> FeedbackItem:
    """Create a test feedback item."""
    feedback = FeedbackItem(
        form_check_id=form_check.id,
        type=FeedbackType.FORM,
        message="Your knees are caving inward during the squat",
        timestamp=15.5,
        severity=FeedbackSeverity.MEDIUM,
        joint_angles={"knee": 85, "hip": 95},
        suggestions=["Keep knees pushed outward", "Focus on engaging glutes"]
    )
    db_session.add(feedback)
    db_session.commit()
    db_session.refresh(feedback)
    return feedback


class TestFeedbackEndpoints:
    """Tests for feedback endpoints."""

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
        assert data["timestamp"] == feedback_data["timestamp"]
        assert data["severity"] == feedback_data["severity"]
        assert data["suggestions"] == feedback_data["suggestions"]
    
    def test_add_feedback_validation_errors(self, client: TestClient, override_get_db, override_auth, form_check):
        """Test validation errors when adding feedback."""
        # Test invalid timestamp (negative value)
        feedback_data = {
            "feedback_type": FeedbackType.FORM.value,
            "severity": FeedbackSeverity.MEDIUM.value,
            "timestamp": -5.0,
            "description": "Knees caving inward during descent",
            "suggestions": ["Keep knees pushed outward"]
        }
        
        response = client.post(
            f"{settings.API_V1_STR}/form-checks/{form_check.id}/feedback",
            json=feedback_data
        )
        
        assert response.status_code == 422
        assert "timestamp" in response.json()["detail"]
        
        # Test invalid severity
        feedback_data = {
            "feedback_type": FeedbackType.FORM.value,
            "severity": "INVALID_SEVERITY",
            "timestamp": 15.5,
            "description": "Knees caving inward during descent",
            "suggestions": ["Keep knees pushed outward"]
        }
        
        response = client.post(
            f"{settings.API_V1_STR}/form-checks/{form_check.id}/feedback",
            json=feedback_data
        )
        
        assert response.status_code == 422
        assert "severity" in response.json()["detail"]
        
        # Test invalid feedback type
        feedback_data = {
            "feedback_type": "INVALID_TYPE",
            "severity": FeedbackSeverity.MEDIUM.value,
            "timestamp": 15.5,
            "description": "Knees caving inward during descent",
            "suggestions": ["Keep knees pushed outward"]
        }
        
        response = client.post(
            f"{settings.API_V1_STR}/form-checks/{form_check.id}/feedback",
            json=feedback_data
        )
        
        assert response.status_code == 422
        assert "feedback_type" in response.json()["detail"]
        
        # Test missing required field
        feedback_data = {
            "feedback_type": FeedbackType.FORM.value,
            "severity": FeedbackSeverity.MEDIUM.value,
            # Missing timestamp
            "description": "Knees caving inward during descent",
            "suggestions": ["Keep knees pushed outward"]
        }
        
        response = client.post(
            f"{settings.API_V1_STR}/form-checks/{form_check.id}/feedback",
            json=feedback_data
        )
        
        assert response.status_code == 422
        assert "timestamp" in response.json()["detail"]
    
    def test_get_feedback_for_form_check(self, client: TestClient, override_get_db, override_auth, form_check, feedback_item):
        """Test getting all feedback items for a form check."""
        response = client.get(
            f"{settings.API_V1_STR}/form-checks/{form_check.id}/feedback"
        )
        
        # Check response
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["form_check_id"] == str(form_check.id)
        assert data[0]["message"] == feedback_item.message
    
    def test_update_feedback(self, client: TestClient, override_get_db, override_auth, feedback_item):
        """Test updating a feedback item."""
        update_data = {
            "message": "Updated feedback message",
            "severity": FeedbackSeverity.HIGH.value
        }
        
        response = client.patch(
            f"{settings.API_V1_STR}/feedback/{feedback_item.id}",
            json=update_data
        )
        
        # Check response
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == feedback_item.id
        assert data["message"] == update_data["message"]
        assert data["severity"] == update_data["severity"]
        
        # Original values should be preserved if not updated
        assert data["timestamp"] == feedback_item.timestamp
        assert data["type"] == feedback_item.type.value
    
    def test_delete_feedback(self, client: TestClient, override_get_db, override_auth, feedback_item):
        """Test deleting a feedback item."""
        response = client.delete(
            f"{settings.API_V1_STR}/feedback/{feedback_item.id}"
        )
        
        # Check response
        assert response.status_code == 204
        
        # Check it was deleted
        get_response = client.get(
            f"{settings.API_V1_STR}/form-checks/{feedback_item.form_check_id}/feedback"
        )
        assert get_response.status_code == 200
        assert len(get_response.json()) == 0 