import pytest
import pytest_asyncio # For async fixtures
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4
from datetime import datetime, timezone
import json
import ast

import httpx
from fastapi import status, FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

# Assuming your main app is accessible for client creation.
# Adjust the import path if your app instance is located elsewhere.
# from app.main import app as fastapi_app # This might be backend.app.main
from app.main import app as fastapi_app

from app.api import deps
from app.models.user import User
from app.models.video import Video
from app.models.enums import VideoStatus, SubscriptionTier
from app.schemas.video import VideoResponse, VideoUploadResponse
from app.services.video_service import VideoService
from app.core.exceptions import NotFoundException, PermissionDeniedException, ServerErrorException

# --- Fixtures ---

@pytest.fixture
def mock_user_id() -> UUID:
    return uuid4()

@pytest.fixture
def sample_auth_user(mock_user_id: UUID) -> User:
    return User(
        id=mock_user_id,
        email="testuser@example.com",
        username="testuser",
        full_name="Test User",
        is_active=True,
        is_superuser=False,
        hashed_password="supersecret",
        subscription_tier=SubscriptionTier.FREE,
        is_email_verified=True,
        is_verified=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

@pytest.fixture
def mock_video_service_for_api() -> MagicMock:
    service = MagicMock(spec=VideoService)
    # Setup common return values or side effects if needed globally for API tests
    # For example, if create_upload_session is always async:
    service.create_upload_session = AsyncMock()
    service.confirm_video_upload = AsyncMock()
    service.get_video_details = AsyncMock()
    service.list_videos_for_user = AsyncMock()
    service.delete_video_by_id = AsyncMock()
    service.request_video_processing = AsyncMock()
    return service

@pytest_asyncio.fixture
async def authenticated_async_client(
    sample_auth_user: User, 
    mock_video_service_for_api: MagicMock,
    # mock_db_session_for_api: AsyncMock # We'll add this if needed for direct db access in tests
) -> httpx.AsyncClient:
    """
    Provides an AsyncClient with authenticated user and mocked services.
    """
    
    # Mock for database session dependency if VideoService methods truly need it passed from API layer
    # (often services create their own sessions or get them from a pool)
    # For now, assuming VideoService mock handles its own DB interactions or doesn't need one from API layer.
    mock_db_sess = AsyncMock(spec=AsyncSession)

    def override_get_current_user():
        return sample_auth_user

    def override_get_video_service():
        return mock_video_service_for_api
    
    def override_get_async_db():
        return mock_db_sess

    fastapi_app.dependency_overrides[deps.get_current_user] = override_get_current_user
    fastapi_app.dependency_overrides[deps.get_video_service] = override_get_video_service
    fastapi_app.dependency_overrides[deps.get_async_db] = override_get_async_db
    
    # Using a context manager for the client ensures lifespan management
    async with httpx.AsyncClient(app=fastapi_app, base_url="http://test") as client:
        # Store mock_db_sess on the client or in a way it can be retrieved by tests if needed
        client.mock_db_sess_ref = mock_db_sess # type: ignore 
        yield client
    
    # Clear overrides after tests
    fastapi_app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def unauthenticated_async_client(
    # We still want to mock the service and db to prevent real calls
    mock_video_service_for_api: MagicMock,
) -> httpx.AsyncClient:
    """
    Provides an AsyncClient WITHOUT an authenticated user, for testing public access and auth errors.
    Service dependencies are still mocked.
    """
    mock_db_sess = AsyncMock(spec=AsyncSession)

    def override_get_video_service():
        return mock_video_service_for_api 
    
    def override_get_async_db(): # Mock DB for service calls even if unauth
        return mock_db_sess

    # Ensure no lingering auth override
    if deps.get_current_user in fastapi_app.dependency_overrides:
        del fastapi_app.dependency_overrides[deps.get_current_user]
        
    fastapi_app.dependency_overrides[deps.get_video_service] = override_get_video_service
    fastapi_app.dependency_overrides[deps.get_async_db] = override_get_async_db
    
    async with httpx.AsyncClient(app=fastapi_app, base_url="http://test") as client:
        client.mock_db_sess_ref = mock_db_sess # type: ignore
        yield client
    
    fastapi_app.dependency_overrides.clear()


# --- Test Classes ---

class TestGetPresignedUploadUrl:
    API_ENDPOINT = "/api/v1/videos/upload-url"

    @pytest.mark.asyncio
    async def test_get_presigned_url_success(
        self, authenticated_async_client: httpx.AsyncClient, mock_video_service_for_api: MagicMock, mock_user_id: UUID
    ):
        mock_video_service_for_api.create_upload_session.return_value = {
            "video_id": str(uuid4()),
            "upload_url": "https://s3.example.com/presigned-url",
            "fields": {"key": "value"}
        }
        
        payload = {"filename": "test_video.mp4", "content_type": "video/mp4"}
        response = await authenticated_async_client.post(self.API_ENDPOINT, json=payload)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "videoId" in data
        assert "uploadUrl" in data
        assert "fields" in data

        mock_video_service_for_api.create_upload_session.assert_awaited_once_with(
            user_id=mock_user_id,
            filename=payload["filename"],
            content_type=payload["content_type"],
            metadata={},
        )

    @pytest.mark.asyncio
    async def test_get_presigned_url_invalid_content_type(
        self, authenticated_async_client: httpx.AsyncClient, mock_video_service_for_api: MagicMock
    ):
        payload = {"filename": "test_document.txt", "content_type": "text/plain"}
        response = await authenticated_async_client.post(self.API_ENDPOINT, json=payload)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "Invalid content type" in response.json()["message"]
        mock_video_service_for_api.create_upload_session.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_presigned_url_service_exception(
        self, authenticated_async_client: httpx.AsyncClient, mock_video_service_for_api: MagicMock
    ):
        mock_video_service_for_api.create_upload_session.side_effect = Exception("Service layer boom!")
        
        payload = {"filename": "test_video.mp4", "content_type": "video/mp4"}
        response = await authenticated_async_client.post(self.API_ENDPOINT, json=payload)
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Error generating presigned URL" in response.json()["message"]
        
    @pytest.mark.asyncio
    async def test_get_presigned_url_unauthenticated(
        self, unauthenticated_async_client: httpx.AsyncClient, mock_video_service_for_api: MagicMock
    ):
        payload = {"filename": "test_video.mp4", "content_type": "video/mp4"}
        response = await unauthenticated_async_client.post(self.API_ENDPOINT, json=payload)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Not authenticated" in response.json()["message"]
        mock_video_service_for_api.create_upload_session.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_presigned_url_with_metadata(
        self, authenticated_async_client: httpx.AsyncClient, mock_video_service_for_api: MagicMock, mock_user_id: UUID
    ):
        mock_response_data = {
            "video_id": str(uuid4()),
            "upload_url": "https://s3.example.com/presigned-url-meta",
            "fields": {"key": "value-meta"}
        }
        mock_video_service_for_api.create_upload_session.return_value = mock_response_data
        
        metadata_payload = {"exercise_type": "SQUAT", "angle": "FRONT"}
        payload = {"filename": "test_video_meta.mp4", "content_type": "video/mp4", "metadata": metadata_payload}
        response = await authenticated_async_client.post(self.API_ENDPOINT, json=payload)
        
        assert response.status_code == status.HTTP_200_OK
        resp = response.json()
        assert resp["uploadUrl"] == mock_response_data["upload_url"]
        assert resp["videoId"] == mock_response_data["video_id"]
        assert resp["fields"] == mock_response_data["fields"]

        mock_video_service_for_api.create_upload_session.assert_awaited_once_with(
            user_id=mock_user_id,
            filename=payload["filename"],
            content_type=payload["content_type"],
            metadata=metadata_payload,
        )

    @pytest.mark.parametrize(
        "missing_field, payload_override",
        [
            ("filename", {"content_type": "video/mp4"}),
            ("content_type", {"filename": "test.mp4"}),
        ]
    )
    @pytest.mark.asyncio
    async def test_get_presigned_url_missing_required_params(
        self, authenticated_async_client: httpx.AsyncClient, mock_video_service_for_api: MagicMock, missing_field: str, payload_override: dict
    ):
        # Construct payload ensuring the specified field is missing
        base_payload = {"filename": "test.mp4", "content_type": "video/mp4"}
        del base_payload[missing_field] # This is not quite right, payload_override should be the full payload
        
        # Corrected approach: The payload_override IS the payload with the missing field
        response = await authenticated_async_client.post(self.API_ENDPOINT, json=payload_override)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        assert data["code"] == "VALIDATION_ERROR"
        assert missing_field in data["details"]["field_errors"]
        mock_video_service_for_api.create_upload_session.assert_not_called()


class TestConfirmUpload:
    API_ENDPOINT = "/api/v1/videos/upload-complete"

    @pytest.mark.asyncio
    async def test_confirm_upload_success(
        self, authenticated_async_client: httpx.AsyncClient, mock_video_service_for_api: MagicMock, sample_auth_user: User
    ):
        video_id_to_confirm = uuid4()
        object_key_val = f"videos/{sample_auth_user.id}/12345_test.mp4"
        
        # Mock the VideoResponse schema that the service layer would return
        mock_service_response_video = VideoResponse(
            id=video_id_to_confirm,
            user_id=sample_auth_user.id,
            filename="test.mp4",
            mime_type="video/mp4",
            object_key=object_key_val,
            status="PENDING_PROCESSING", # or whatever the next status is
            created_at= MagicMock(), # datetime.datetime.now(),
            updated_at= MagicMock(), # datetime.datetime.now(),
            # Add other fields as per VideoResponse schema
            title=None,
            description=None,
            duration=None,
            width=None,
            height=None,
            fps=None,
            size=1024, # example size
            processed_object_key=None,
            raw_keypoints_s3_key=None,
            angle_data_s3_key=None,
            thumbnail_url=None,
            public_url=None,
            # exercise_type=None,
            # exercise_config_id=None,
            error_message=None,
            celery_task_id=None,
            processed_frame_count=None
        )
        mock_video_service_for_api.confirm_video_upload.return_value = mock_service_response_video
        
        payload = {"videoId": str(video_id_to_confirm), "object_key": object_key_val, "size": 1024}
        response = await authenticated_async_client.post(self.API_ENDPOINT, json=payload)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == str(video_id_to_confirm)
        assert data["object_key"] == object_key_val
        assert data["status"] == "PENDING_PROCESSING" # Verify expected status

        mock_video_service_for_api.confirm_video_upload.assert_awaited_once_with(
            video_id=video_id_to_confirm,
            current_user_id=sample_auth_user.id,
            is_superuser=sample_auth_user.is_superuser,
            object_key=object_key_val,
            size=1024,
        )

    @pytest.mark.asyncio
    async def test_confirm_upload_video_not_found(
        self, authenticated_async_client: httpx.AsyncClient, mock_video_service_for_api: MagicMock, sample_auth_user: User
    ):
        video_id_not_found = uuid4()
        mock_video_service_for_api.confirm_video_upload.side_effect = NotFoundException("Video not found")
        
        payload = {"videoId": str(video_id_not_found), "object_key": "some/key.mp4"}
        response = await authenticated_async_client.post(self.API_ENDPOINT, json=payload)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Video not found" in response.json()["message"]

    @pytest.mark.asyncio
    async def test_confirm_upload_permission_denied(
        self, authenticated_async_client: httpx.AsyncClient, mock_video_service_for_api: MagicMock, sample_auth_user: User
    ):
        video_id_perm_denied = uuid4()
        mock_video_service_for_api.confirm_video_upload.side_effect = PermissionDeniedException("Not authorized")
        
        payload = {"videoId": str(video_id_perm_denied), "object_key": "some/key.mp4"}
        response = await authenticated_async_client.post(self.API_ENDPOINT, json=payload)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "Not authorized" in response.json()["message"]

    @pytest.mark.asyncio
    async def test_confirm_upload_service_exception(
        self, authenticated_async_client: httpx.AsyncClient, mock_video_service_for_api: MagicMock
    ):
        mock_video_service_for_api.confirm_video_upload.side_effect = Exception("Service layer confirm boom!")
        
        payload = {"videoId": str(uuid4()), "object_key": "some/key.mp4"}
        response = await authenticated_async_client.post(self.API_ENDPOINT, json=payload)

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Error confirming video upload" in response.json()["message"]
        
    @pytest.mark.asyncio
    async def test_confirm_upload_unauthenticated(
        self, unauthenticated_async_client: httpx.AsyncClient, mock_video_service_for_api: MagicMock
    ):
        payload = {"videoId": str(uuid4()), "object_key": "some/key.mp4"}
        response = await unauthenticated_async_client.post(self.API_ENDPOINT, json=payload)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Not authenticated" in response.json()["message"]
        mock_video_service_for_api.confirm_video_upload.assert_not_called()

    @pytest.mark.asyncio
    async def test_confirm_upload_missing_required_params(
        self, authenticated_async_client: httpx.AsyncClient, mock_video_service_for_api: MagicMock
    ):
        # videoId is required; object_key is Optional so only videoId produces a 422
        response = await authenticated_async_client.post(self.API_ENDPOINT, json={"object_key": "some/key.mp4"})

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        assert data["code"] == "VALIDATION_ERROR"
        assert "videoId" in data["details"]["field_errors"]
        mock_video_service_for_api.confirm_video_upload.assert_not_called()

    @pytest.mark.asyncio
    async def test_confirm_upload_invalid_video_id_format(
        self, authenticated_async_client: httpx.AsyncClient, mock_video_service_for_api: MagicMock
    ):
        # Endpoint alias is "videoId"; sending an invalid UUID value triggers 422
        payload = {"videoId": "not-a-uuid", "object_key": "some/key.mp4"}
        response = await authenticated_async_client.post(self.API_ENDPOINT, json=payload)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        assert data["code"] == "VALIDATION_ERROR"
        assert "videoId" in data["details"]["field_errors"]
        mock_video_service_for_api.confirm_video_upload.assert_not_called() 