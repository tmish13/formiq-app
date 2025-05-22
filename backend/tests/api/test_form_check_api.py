import pytest
import asyncio
import io
import uuid
import logging
from uuid import UUID
from typing import Dict, Any
from httpx import AsyncClient
from fastapi import status
from unittest.mock import patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.main import app
from app.core.config import settings
from app.core.security import create_access_token
from app.models.user import User
from app.models.exercise_template import ExerciseTemplate
from app.models.exercise import ExerciseTemplate as ExerciseTemplateModel
from app.models.form_check import FormCheck, FeedbackItem
from app.models.video import Video
from app.models.enums import (
    FormCheckStatus, FeedbackType, FeedbackSeverity, ExerciseType, Difficulty, MuscleGroup, VideoStatus
)
from app.schemas.form_check import FormCheckDetailedResponse
from app.db.session import SessionLocal
from tests.utils.factories import UserFactory, FormCheckFactory, ExerciseTemplateFactory

logger = logging.getLogger(__name__)

# --- Shared Fixtures ---

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="module")
async def async_client() -> AsyncClient:
    from app.main import app
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest.fixture(scope="function")
async def db_session() -> AsyncSession:
    async with SessionLocal() as session:
        yield session
        await session.rollback()

@pytest.fixture(scope="function")
async def test_user(db_session: AsyncSession) -> User:
    user = await UserFactory()
    return user

@pytest.fixture(scope="function")
def current_user_headers(test_user: User) -> dict:
    token = create_access_token(subject=str(test_user.id))
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture(scope="function")
async def test_exercise_template(db_session: AsyncSession) -> ExerciseTemplate:
    template = await ExerciseTemplateFactory(
        name="Test Squat",
        description="A test squat exercise",
        difficulty=Difficulty.BEGINNER,
        muscle_group=MuscleGroup.LEGS
    )
    return template

@pytest.fixture(scope="function")
async def test_video_with_angles(db_session: AsyncSession, test_user: User, test_exercise_template: ExerciseTemplate) -> Video:
    video = Video(
        id=uuid.uuid4(),
        user_id=test_user.id,
        exercise_template_id=test_exercise_template.id,
        s3_key_raw="test/raw.mp4",
        s3_key_processed="test/processed.mp4",
        duration_seconds=10.0,
        status=VideoStatus.ANGLES_CALCULATED.value,
        angle_data='[{"frame_num": 0, "timestamp": 0.0, "angles": {"leftKnee": 170}}]'
    )
    db_session.add(video)
    await db_session.commit()
    await db_session.refresh(video)
    return video

@pytest.fixture(scope="function")
async def test_video_no_angles(db_session: AsyncSession, test_user: User, test_exercise_template: ExerciseTemplate) -> Video:
    video = Video(
        id=uuid.uuid4(),
        user_id=test_user.id,
        exercise_template_id=test_exercise_template.id,
        s3_key_raw="test/no_angles.mp4",
        duration_seconds=5.0,
        status=VideoStatus.UPLOADED.value,
        angle_data=None
    )
    db_session.add(video)
    await db_session.commit()
    await db_session.refresh(video)
    return video

@pytest.fixture
def logger_fixture():
    return logger

# --- 1. Form Check Submission Endpoint ---

@pytest.mark.integration
@pytest.mark.asyncio
async def test_submit_form_check_creates_record_and_dispatches_task(
    async_client: AsyncClient, db_session: AsyncSession, current_user_headers: dict, test_user: User
):
    exercise_template_name = "TEST_SQUAT_EXERCISE_API"
    exercise_template = await ExerciseTemplateFactory(name=exercise_template_name, type=ExerciseType.SQUAT)
    db_session.add(exercise_template)
    await db_session.commit()
    await db_session.refresh(exercise_template)

    with patch("app.tasks.analysis_tasks.process_form_check_task.delay") as mock_task_delay:
        mock_task_delay.return_value = MagicMock()
        fake_video_content = b"dummy video content for api test"
        fake_file = io.BytesIO(fake_video_content)
        files = {"video_upload": ("test_video_api.mp4", fake_file, "video/mp4")}
        data = {"exercise_name": exercise_template_name, "notes": "API test submission"}
        response = await async_client.post(
            "/api/v1/form-checks/submit", files=files, data=data, headers=current_user_headers
        )
        assert response.status_code == 202, f"Response content: {response.text}"
        response_data = response.json()
        assert "id" in response_data
        form_check_id_str = response_data["id"]
        mock_task_delay.assert_called_once()
        call_args = mock_task_delay.call_args
        assert call_args is not None
        assert call_args.kwargs.get("form_check_id_str") == form_check_id_str
        form_check_id_uuid = UUID(form_check_id_str)
        stmt = select(FormCheck).where(FormCheck.id == form_check_id_uuid)
        result = await db_session.execute(stmt)
        db_form_check = result.scalars().one_or_none()
        assert db_form_check is not None
        assert db_form_check.user_id == test_user.id
        assert db_form_check.exercise_id == exercise_template.id
        assert db_form_check.status == FormCheckStatus.PENDING
        assert db_form_check.notes == "API test submission"
        assert db_form_check.video_url is not None
        assert response_data["status"] == "PENDING"
        assert response_data["user_id"] == str(test_user.id)
        assert response_data["exercise_id"] == str(exercise_template.id)

# --- 2. Form Check Creation (Direct) and CRUD ---

@pytest.fixture
async def test_form_check(db_session: AsyncSession, test_user: User) -> FormCheck:
    form_check_obj = await FormCheckFactory(user_id=test_user.id)
    return form_check_obj

@pytest.mark.integration
class TestFormCheckDirectEndpoints:
    @pytest.mark.asyncio
    async def test_create_form_check(self, async_client: AsyncClient, current_user_headers: dict, db_session: AsyncSession, test_user: User):
        video_file = io.BytesIO(b"test video content for direct form check")
        video_file.name = "test_video_direct.mp4"
        form_data = {"exercise_type": ExerciseType.SQUAT.value}
        files = {"video": (video_file.name, video_file, "video/mp4")}
        response = await async_client.post(
            f"{settings.API_V1_STR}/form-checks/", data=form_data, files=files, headers=current_user_headers
        )
        assert response.status_code == 201, response.text
        data = response.json()
        assert data["video_url"]
        assert data["status"] == FormCheckStatus.PENDING.value
        assert "id" in data
        form_check_id = uuid.UUID(data["id"])
        db_form_check = await db_session.get(FormCheck, form_check_id)
        assert db_form_check is not None
        assert db_form_check.user_id == test_user.id

    @pytest.mark.asyncio
    async def test_get_form_checks(self, async_client: AsyncClient, current_user_headers: dict, test_form_check: FormCheck, test_user: User):
        response = await async_client.get(f"{settings.API_V1_STR}/form-checks/", headers=current_user_headers)
        assert response.status_code == 200, response.text
        data = response.json()
        assert isinstance(data, list)
        found = any(item["id"] == str(test_form_check.id) for item in data)
        assert found, f"Test form check {test_form_check.id} not found in list."

    @pytest.mark.asyncio
    async def test_get_form_check(self, async_client: AsyncClient, current_user_headers: dict, test_form_check: FormCheck):
        response = await async_client.get(f"{settings.API_V1_STR}/form-checks/{test_form_check.id}", headers=current_user_headers)
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["id"] == str(test_form_check.id)
        assert data["video_url"] == test_form_check.video_url

    @pytest.mark.asyncio
    async def test_add_feedback(self, async_client: AsyncClient, current_user_headers: dict, test_form_check: FormCheck, db_session: AsyncSession):
        feedback_data = {
            "feedback_type": FeedbackType.FORM.value,
            "severity": FeedbackSeverity.MEDIUM.value,
            "timestamp": 15.5,
            "description": "Knees caving inward during descent in direct test",
            "suggestions": ["Keep knees pushed outward", "Focus on engaging glutes"]
        }
        response = await async_client.post(
            f"{settings.API_V1_STR}/form-checks/{test_form_check.id}/feedback",
            json=feedback_data,
            headers=current_user_headers
        )
        assert response.status_code == 201, response.text
        data = response.json()
        feedback_id = uuid.UUID(data["id"])
        assert data["form_check_id"] == str(test_form_check.id)
        assert data["feedback_type"] == feedback_data["feedback_type"]
        assert data["description"] == feedback_data["description"]
        db_feedback_item = await db_session.get(FeedbackItem, feedback_id)
        assert db_feedback_item is not None
        assert db_feedback_item.message == feedback_data["description"]

    @pytest.mark.asyncio
    async def test_complete_analysis(self, async_client: AsyncClient, current_user_headers: dict, test_form_check: FormCheck, db_session: AsyncSession):
        complete_data = {
            "summary": "Overall good form with minor issues with knee positioning (direct test)",
            "overall_score": 8.5
        }
        response = await async_client.post(
            f"{settings.API_V1_STR}/form-checks/{test_form_check.id}/complete",
            json=complete_data,
            headers=current_user_headers
        )
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["id"] == str(test_form_check.id)
        assert data["status"] == FormCheckStatus.COMPLETED.value
        assert data["overall_feedback"] == complete_data["summary"]
        assert data["score"] == complete_data["overall_score"]
        await db_session.refresh(test_form_check)
        assert test_form_check.status == FormCheckStatus.COMPLETED
        assert test_form_check.overall_feedback == complete_data["summary"]
        assert test_form_check.score == complete_data["overall_score"]

    @pytest.mark.asyncio
    async def test_delete_form_check(self, async_client: AsyncClient, current_user_headers: dict, test_form_check: FormCheck, db_session: AsyncSession):
        form_check_id_to_delete = test_form_check.id
        response = await async_client.delete(
            f"{settings.API_V1_STR}/form-checks/{form_check_id_to_delete}",
            headers=current_user_headers
        )
        assert response.status_code == 204, response.text
        deleted_db_form_check = await db_session.get(FormCheck, form_check_id_to_delete)
        assert deleted_db_form_check is None

# --- 3. Form Check History Endpoint ---

@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_form_check_history_filters_by_status(async_client: AsyncClient, db_session: AsyncSession, current_user_headers: dict):
    exercise1 = await ExerciseTemplateFactory(
        name="Squat",
        description="Basic squat exercise",
        difficulty=Difficulty.BEGINNER,
        muscle_group=MuscleGroup.LEGS
    )
    exercise2 = await ExerciseTemplateFactory(
        name="Pushup",
        description="Basic pushup exercise",
        difficulty=Difficulty.BEGINNER,
        muscle_group=MuscleGroup.CHEST
    )
    user_response = await async_client.get("/api/v1/auth/me", headers=current_user_headers)
    assert user_response.status_code == 200
    auth_user_id = user_response.json()["id"]
    completed_check = await FormCheckFactory(
        user_id=auth_user_id,
        status=FormCheckStatus.COMPLETED,
        video_url="http://example.com/video1.mp4",
        exercise_id=exercise1.id
    )
    pending_check = await FormCheckFactory(
        user_id=auth_user_id,
        status=FormCheckStatus.PENDING,
        video_url="http://example.com/video2.mp4",
        exercise_id=exercise2.id
    )
    other_user = await UserFactory(email="otheruser@example.com")
    await FormCheckFactory(
        user_id=other_user.id,
        status=FormCheckStatus.COMPLETED,
        video_url="http://example.com/video_other.mp4",
        exercise_id=exercise1.id
    )
    response = await async_client.get(f"/api/v1/form-checks/history?status=COMPLETED", headers=current_user_headers)
    assert response.status_code == 200, response.text
    response_data = response.json()
    assert len(response_data) == 1
    assert response_data[0]["status"] == "COMPLETED"
    assert response_data[0]["id"] == str(completed_check.id)
    response_pending = await async_client.get(f"/api/v1/form-checks/history?status=PENDING", headers=current_user_headers)
    assert response_pending.status_code == 200, response_pending.text
    response_data_pending = response_pending.json()
    assert len(response_data_pending) == 1
    assert response_data_pending[0]["status"] == "PENDING"
    assert response_data_pending[0]["id"] == str(pending_check.id)
    response_all = await async_client.get(f"/api/v1/form-checks/history", headers=current_user_headers)
    assert response_all.status_code == 200, response_all.text
    response_data_all = response_all.json()
    assert len(response_data_all) == 2
    ids_returned = {item["id"] for item in response_data_all}
    assert str(completed_check.id) in ids_returned
    assert str(pending_check.id) in ids_returned
    response_invalid = await async_client.get(f"/api/v1/form-checks/history?status=INVALID_STATUS_FOO", headers=current_user_headers)
    assert response_invalid.status_code == 422

# --- 4. Form Check Analysis Trigger & Retrieval ---

@pytest.mark.integration
@pytest.mark.asyncio
async def test_trigger_analysis_success(async_client: AsyncClient, test_video_with_angles: Video, current_user_headers: dict):
    video_id = test_video_with_angles.id
    headers = current_user_headers
    mock_task = MagicMock()
    mock_task.id = str(uuid.uuid4())
    with patch("app.api.v1.endpoints.analysis.perform_form_analysis_celery_task.delay", return_value=mock_task) as mock_delay:
        response = await async_client.post(f"/api/v1/analysis/analyze-form/{video_id}", headers=headers)
    assert response.status_code == status.HTTP_202_ACCEPTED
    json_response = response.json()
    assert json_response["message"] == "Form analysis accepted and queued."
    assert UUID(json_response["video_id"]) == video_id
    assert json_response["task_id"] == mock_task.id
    mock_delay.assert_called_once_with(str(video_id))

@pytest.mark.integration
@pytest.mark.asyncio
async def test_trigger_analysis_video_not_found(async_client: AsyncClient, current_user_headers: dict):
    non_existent_video_id = uuid.uuid4()
    headers = current_user_headers
    response = await async_client.post(f"/api/v1/analysis/analyze-form/{non_existent_video_id}", headers=headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Video not found"

@pytest.mark.integration
@pytest.mark.asyncio
async def test_trigger_analysis_no_angle_data(async_client: AsyncClient, test_video_no_angles: Video, current_user_headers: dict):
    video_id = test_video_no_angles.id
    headers = current_user_headers
    response = await async_client.post(f"/api/v1/analysis/analyze-form/{video_id}", headers=headers)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "Video has no angle data to analyze."

@pytest.mark.integration
@pytest.mark.asyncio
async def test_trigger_analysis_unauthenticated(async_client: AsyncClient, test_video_with_angles: Video):
    video_id = test_video_with_angles.id
    response = await async_client.post(f"/api/v1/analysis/analyze-form/{video_id}")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_form_check_success(async_client: AsyncClient, test_video_with_angles: Video, current_user_headers: dict, db_session: AsyncSession, test_exercise_template: ExerciseTemplate):
    video_id = test_video_with_angles.id
    user_id = test_video_with_angles.user_id
    headers = current_user_headers
    form_check_id = uuid.uuid4()
    form_check = FormCheck(
        id=form_check_id,
        video_id=video_id,
        user_id=user_id,
        exercise_id=test_exercise_template.id,
        status="analysis_complete",
        overall_score=85.5,
        overall_feedback="Good job! Minor improvements needed.",
        reps_detected=10,
        reps_per_minute=60.0,
    )
    db_session.add(form_check)
    await db_session.commit()
    await db_session.refresh(form_check)
    response = await async_client.get(f"/api/v1/form-checks/{video_id}", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    json_response = response.json()
    parsed_response = FormCheckDetailedResponse(**json_response)
    assert parsed_response.id == str(form_check.id)
    assert parsed_response.video_id == str(video_id)
    assert parsed_response.overall_score == 85.5
    assert parsed_response.reps_detected == 10
    assert parsed_response.status == "analysis_complete"
    assert parsed_response.feedback_items is not None

@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_form_check_video_not_found(async_client: AsyncClient, current_user_headers: dict):
    non_existent_video_id = uuid.uuid4()
    headers = current_user_headers
    response = await async_client.get(f"/api/v1/form-checks/{non_existent_video_id}", headers=headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Video not found"

@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_form_check_no_form_check_exists(async_client: AsyncClient, test_video_with_angles: Video, current_user_headers: dict):
    video_id = test_video_with_angles.id
    headers = current_user_headers
    response = await async_client.get(f"/api/v1/form-checks/{video_id}", headers=headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Form check not found for this video"

@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_form_check_unauthorized_different_user(async_client: AsyncClient, test_video_with_angles: Video, db_session: AsyncSession):
    other_user = await UserFactory(email="otheruser@example.com")
    other_user_token = create_access_token(subject=str(other_user.id))
    headers = {"Authorization": f"Bearer {other_user_token}"}
    video_id = test_video_with_angles.id
    response = await async_client.get(f"/api/v1/form-checks/{video_id}", headers=headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["detail"] == "Not authorized to access this video's form check"

@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_form_check_unauthenticated(async_client: AsyncClient, test_video_with_angles: Video):
    video_id = test_video_with_angles.id
    response = await async_client.get(f"/api/v1/form-checks/{video_id}")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED 