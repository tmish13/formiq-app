"""Integration tests for feedback endpoints."""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import uuid
from typing import Dict

from app.core.config import settings
from app.models.form_check import FormCheck, FeedbackItem
from app.models.user import User
from app.models.enums import FeedbackType, FeedbackSeverity
# Removed sync deps: get_db, get_current_user_sync, Base

# Removed sync fixtures: client, db_session, override_get_db, test_user (sync version), override_auth

@pytest.fixture
async def test_form_check(async_session: AsyncSession, test_user: User) -> FormCheck:
    """Create a test form check for async tests."""
    form_check_obj = FormCheck(
        id=uuid.uuid4(),
        video_url="https://example.com/video.mp4",
        exercise_id=uuid.uuid4(),
        user_id=test_user.id,
        status="pending"
    )
    async_session.add(form_check_obj)
    await async_session.commit()
    await async_session.refresh(form_check_obj)
    return form_check_obj

@pytest.fixture
async def test_feedback_item(async_session: AsyncSession, test_form_check: FormCheck) -> FeedbackItem:
    """Create a test feedback item for async tests."""
    feedback = FeedbackItem(
        form_check_id=test_form_check.id,
        type=FeedbackType.FORM,
        message="Your knees are caving inward during the squat",
        timestamp=15.5,
        severity=FeedbackSeverity.MEDIUM,
        joint_angles={"knee": 85, "hip": 95},
        suggestions=["Keep knees pushed outward", "Focus on engaging glutes"]
    )
    async_session.add(feedback)
    await async_session.commit()
    await async_session.refresh(feedback)
    return feedback

class TestFeedbackEndpoints:
    """Tests for feedback endpoints (now async)."""

    @pytest.mark.asyncio
    async def test_add_feedback(self, async_client: AsyncClient, current_user_headers: dict, test_form_check: FormCheck):
        """Test adding feedback to a form check."""
        feedback_data = {
            "feedback_type": FeedbackType.FORM.value,
            "severity": FeedbackSeverity.MEDIUM.value,
            "timestamp": 15.5,
            "description": "Knees caving inward during descent",
            "suggestions": ["Keep knees pushed outward", "Focus on engaging glutes"]
        }
        
        response = await async_client.post(
            f"{settings.API_V1_STR}/form-checks/{test_form_check.id}/feedback",
            json=feedback_data,
            headers=current_user_headers
        )
        
        assert response.status_code == 201, response.text
        data = response.json()
        assert data["form_check_id"] == str(test_form_check.id)
        assert data["feedback_type"] == feedback_data["feedback_type"]
        assert data["description"] == feedback_data["description"]
        assert data["timestamp"] == feedback_data["timestamp"]
        assert data["severity"] == feedback_data["severity"]
        assert data["suggestions"] == feedback_data["suggestions"]
    
    @pytest.mark.asyncio
    async def test_add_feedback_validation_errors(self, async_client: AsyncClient, current_user_headers: dict, test_form_check: FormCheck):
        """Test validation errors when adding feedback."""
        # Test invalid timestamp (negative value)
        feedback_data_invalid_ts = {
            "feedback_type": FeedbackType.FORM.value,
            "severity": FeedbackSeverity.MEDIUM.value,
            "timestamp": -5.0,
            "description": "Knees caving inward during descent",
            "suggestions": ["Keep knees pushed outward"]
        }
        
        response_invalid_ts = await async_client.post(
            f"{settings.API_V1_STR}/form-checks/{test_form_check.id}/feedback",
            json=feedback_data_invalid_ts,
            headers=current_user_headers
        )
        assert response_invalid_ts.status_code == 422
        assert any("timestamp" in e.get("loc", []) for e in response_invalid_ts.json().get("detail", [])) or \
               any("timestamp" in str(e) for e in response_invalid_ts.json().get("detail", []))

        # Test invalid severity
        feedback_data_invalid_sev = {
            "feedback_type": FeedbackType.FORM.value,
            "severity": "INVALID_SEVERITY",
            "timestamp": 15.5,
            "description": "Knees caving inward during descent",
            "suggestions": ["Keep knees pushed outward"]
        }
        response_invalid_sev = await async_client.post(
            f"{settings.API_V1_STR}/form-checks/{test_form_check.id}/feedback",
            json=feedback_data_invalid_sev,
            headers=current_user_headers
        )
        assert response_invalid_sev.status_code == 422
        assert any("severity" in e.get("loc", []) for e in response_invalid_sev.json().get("detail", [])) or \
               any("severity" in str(e) for e in response_invalid_sev.json().get("detail", []))

        # Test invalid feedback type
        feedback_data_invalid_type = {
            "feedback_type": "INVALID_TYPE",
            "severity": FeedbackSeverity.MEDIUM.value,
            "timestamp": 15.5,
            "description": "Knees caving inward during descent",
            "suggestions": ["Keep knees pushed outward"]
        }
        response_invalid_type = await async_client.post(
            f"{settings.API_V1_STR}/form-checks/{test_form_check.id}/feedback",
            json=feedback_data_invalid_type,
            headers=current_user_headers
        )
        assert response_invalid_type.status_code == 422
        assert any("feedback_type" in e.get("loc", []) for e in response_invalid_type.json().get("detail", [])) or \
               any("feedback_type" in str(e) for e in response_invalid_type.json().get("detail", []))

        # Test missing required field (timestamp)
        feedback_data_missing_ts = {
            "feedback_type": FeedbackType.FORM.value,
            "severity": FeedbackSeverity.MEDIUM.value,
            "description": "Knees caving inward during descent",
            "suggestions": ["Keep knees pushed outward"]
        }
        response_missing_ts = await async_client.post(
            f"{settings.API_V1_STR}/form-checks/{test_form_check.id}/feedback",
            json=feedback_data_missing_ts,
            headers=current_user_headers
        )
        assert response_missing_ts.status_code == 422
        assert any("timestamp" in e.get("loc", []) for e in response_missing_ts.json().get("detail", [])) or \
               any("timestamp" in str(e) for e in response_missing_ts.json().get("detail", []))
    
    @pytest.mark.asyncio
    async def test_get_feedback_for_form_check(self, async_client: AsyncClient, current_user_headers: dict, test_form_check: FormCheck, test_feedback_item: FeedbackItem):
        """Test getting all feedback items for a form check."""
        response = await async_client.get(
            f"{settings.API_V1_STR}/form-checks/{test_form_check.id}/feedback",
            headers=current_user_headers
        )
        
        assert response.status_code == 200, response.text
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        
        found_item = None
        for item in data:
            if item["id"] == str(test_feedback_item.id):
                found_item = item
                break
        
        assert found_item is not None, "Test feedback item not found in response"
        assert found_item["form_check_id"] == str(test_form_check.id)
        assert found_item["description"] == test_feedback_item.message
    
    @pytest.mark.asyncio
    async def test_update_feedback(self, async_client: AsyncClient, current_user_headers: dict, test_feedback_item: FeedbackItem):
        """Test updating a feedback item."""
        update_data = {
            "description": "Updated feedback description via API",
            "severity": FeedbackSeverity.HIGH.value
        }
        
        response = await async_client.patch(
            f"{settings.API_V1_STR}/feedback/{test_feedback_item.id}",
            json=update_data,
            headers=current_user_headers
        )
        
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["id"] == str(test_feedback_item.id)
        assert data["description"] == update_data["description"]
        assert data["severity"] == update_data["severity"]
        assert data["timestamp"] == test_feedback_item.timestamp
    
    @pytest.mark.asyncio
    async def test_delete_feedback(self, async_client: AsyncClient, async_session: AsyncSession, current_user_headers: dict, test_feedback_item: FeedbackItem):
        """Test deleting a feedback item."""
        feedback_id_to_delete = test_feedback_item.id

        response = await async_client.delete(
            f"{settings.API_V1_STR}/feedback/{feedback_id_to_delete}",
            headers=current_user_headers
        )
        
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["message"] == "Feedback item deleted successfully"
        
        stmt = select(FeedbackItem).where(FeedbackItem.id == feedback_id_to_delete)
        result = await async_session.execute(stmt)
        deleted_item = result.scalars().one_or_none()
        assert deleted_item is None 