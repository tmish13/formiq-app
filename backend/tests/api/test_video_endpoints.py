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
from backend.app.main import app as fastapi_app # Corrected path

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
    API_ENDPOINT = "/api/v1/videos/upload/signed-url"

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
        assert "video_id" in data
        assert "upload_url" in data
        assert "fields" in data
        
        # Retrieve the mock_db_sess instance used by this client
        mock_db_session_instance = authenticated_async_client.mock_db_sess_ref # type: ignore

        mock_video_service_for_api.create_upload_session.assert_awaited_once_with(
            user_id=mock_user_id,
            filename=payload["filename"],
            content_type=payload["content_type"],
            metadata=None, 
            db_session=mock_db_session_instance
        )

    @pytest.mark.asyncio
    async def test_get_presigned_url_invalid_content_type(
        self, authenticated_async_client: httpx.AsyncClient, mock_video_service_for_api: MagicMock
    ):
        payload = {"filename": "test_document.txt", "content_type": "text/plain"}
        response = await authenticated_async_client.post(self.API_ENDPOINT, json=payload)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "Invalid content type" in response.json()["detail"]
        mock_video_service_for_api.create_upload_session.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_presigned_url_service_exception(
        self, authenticated_async_client: httpx.AsyncClient, mock_video_service_for_api: MagicMock
    ):
        mock_video_service_for_api.create_upload_session.side_effect = Exception("Service layer boom!")
        
        payload = {"filename": "test_video.mp4", "content_type": "video/mp4"}
        response = await authenticated_async_client.post(self.API_ENDPOINT, json=payload)
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Error generating presigned URL" in response.json()["detail"]
        
    @pytest.mark.asyncio
    async def test_get_presigned_url_unauthenticated(
        self, unauthenticated_async_client: httpx.AsyncClient, mock_video_service_for_api: MagicMock
    ):
        payload = {"filename": "test_video.mp4", "content_type": "video/mp4"}
        response = await unauthenticated_async_client.post(self.API_ENDPOINT, json=payload)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED # Or 403 depending on default behavior
        # FastAPI typically returns 401 if the auth dependency itself fails before your code runs.
        # If get_current_user raises HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"),
        # then the detail might be "Not authenticated". Otherwise, it might be "Not authenticated"
        # or "Unauthorized" from the security scheme. Let's assume a generic detail for now or check FastAPI's default.
        # For a more specific check, you might need to know how your `deps.get_current_user` fails.
        # A common detail is "Not authenticated" or "Unauthorized".
        assert "Not authenticated" in response.json()["detail"] # Adjust if your auth failure detail is different
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
        assert response.json() == mock_response_data
        
        mock_db_session_instance = authenticated_async_client.mock_db_sess_ref # type: ignore
        mock_video_service_for_api.create_upload_session.assert_awaited_once_with(
            user_id=mock_user_id,
            filename=payload["filename"],
            content_type=payload["content_type"],
            metadata=metadata_payload, 
            db_session=mock_db_session_instance
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
        print(f"DEBUG test_get_presigned_url_missing_required_params data: {data}") # DEBUG
        
        detail_content = data.get("detail")
        detail_list = []
        if isinstance(detail_content, str):
            try:
                # Try ast.literal_eval for strings like "[{...}]"
                detail_list = ast.literal_eval(detail_content)
                if not isinstance(detail_list, list): # Ensure it evaluated to a list
                    detail_list = []
                    print(f"DEBUG: ast.literal_eval did not produce a list: {detail_content}")
            except (ValueError, SyntaxError):
                detail_list = [] 
                print(f"DEBUG: Could not ast.literal_eval detail string: {detail_content}")
        elif isinstance(detail_content, list):
            detail_list = detail_content

        found_error = False
        for err in detail_list:
            if isinstance(err, dict) and err.get("loc") and isinstance(err["loc"], (list, tuple)) and len(err["loc"]) > 0:
                if err["loc"][-1] == missing_field and err.get("type") == "missing":
                    found_error = True
                    break
            else:
                print(f"DEBUG: Unexpected error structure in detail: {err}")
        assert found_error, f"Expected validation error for missing field '{missing_field}' not found or has wrong type/loc."
        mock_video_service_for_api.create_upload_session.assert_not_called()


class TestConfirmUpload:
    API_ENDPOINT = "/api/v1/videos/upload/confirm"

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
        
        payload = {"video_id": str(video_id_to_confirm), "object_key": object_key_val, "size": 1024}
        response = await authenticated_async_client.post(self.API_ENDPOINT, json=payload)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == str(video_id_to_confirm)
        assert data["object_key"] == object_key_val
        assert data["status"] == "PENDING_PROCESSING" # Verify expected status

        # Retrieve the mock_db_sess instance used by this client
        mock_db_session_instance = authenticated_async_client.mock_db_sess_ref # type: ignore

        mock_video_service_for_api.confirm_video_upload.assert_awaited_once_with(
            video_id=video_id_to_confirm,
            current_user_id=sample_auth_user.id,
            is_superuser=sample_auth_user.is_superuser,
            object_key=object_key_val,
            size=1024,
            db_session=mock_db_session_instance
        )

    @pytest.mark.asyncio
    async def test_confirm_upload_video_not_found(
        self, authenticated_async_client: httpx.AsyncClient, mock_video_service_for_api: MagicMock, sample_auth_user: User
    ):
        video_id_not_found = uuid4()
        mock_video_service_for_api.confirm_video_upload.side_effect = NotFoundException("Video not found")
        
        payload = {"video_id": str(video_id_not_found), "object_key": "some/key.mp4"}
        response = await authenticated_async_client.post(self.API_ENDPOINT, json=payload)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Video not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_confirm_upload_permission_denied(
        self, authenticated_async_client: httpx.AsyncClient, mock_video_service_for_api: MagicMock, sample_auth_user: User
    ):
        video_id_perm_denied = uuid4()
        mock_video_service_for_api.confirm_video_upload.side_effect = PermissionDeniedException("Not authorized")
        
        payload = {"video_id": str(video_id_perm_denied), "object_key": "some/key.mp4"}
        response = await authenticated_async_client.post(self.API_ENDPOINT, json=payload)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN # Assuming PermissionDeniedException maps to 403
        assert "Not authorized" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_confirm_upload_service_exception(
        self, authenticated_async_client: httpx.AsyncClient, mock_video_service_for_api: MagicMock
    ):
        mock_video_service_for_api.confirm_video_upload.side_effect = Exception("Service layer confirm boom!")
        
        payload = {"video_id": str(uuid4()), "object_key": "some/key.mp4"}
        response = await authenticated_async_client.post(self.API_ENDPOINT, json=payload)
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Error confirming video upload" in response.json()["detail"]
        
    @pytest.mark.asyncio
    async def test_confirm_upload_unauthenticated(
        self, unauthenticated_async_client: httpx.AsyncClient, mock_video_service_for_api: MagicMock
    ):
        payload = {"video_id": str(uuid4()), "object_key": "some/key.mp4"}
        response = await unauthenticated_async_client.post(self.API_ENDPOINT, json=payload)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Not authenticated" in response.json()["detail"] # Adjust as needed
        mock_video_service_for_api.confirm_video_upload.assert_not_called()

    @pytest.mark.parametrize(
        "missing_field, payload_override",
        [
            ("video_id", {"object_key": "some/key.mp4"}),
            ("object_key", {"video_id": str(uuid4())}),
        ]
    )
    @pytest.mark.asyncio
    async def test_confirm_upload_missing_required_params(
        self, authenticated_async_client: httpx.AsyncClient, mock_video_service_for_api: MagicMock, missing_field: str, payload_override: dict
    ):
        response = await authenticated_async_client.post(self.API_ENDPOINT, json=payload_override)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        print(f"DEBUG test_confirm_upload_missing_required_params data: {data}") # DEBUG

        detail_content = data.get("detail")
        if isinstance(detail_content, str):
            try:
                detail_list = ast.literal_eval(detail_content)
            except (ValueError, SyntaxError):
                detail_list = []
                print(f"DEBUG: Could not ast.literal_eval detail string: {detail_content}")
        elif isinstance(detail_content, list):
            detail_list = detail_content
        else:
            detail_list = []

        found_error = False
        for err in detail_list:
            if isinstance(err, dict) and err.get("loc") and isinstance(err["loc"], (list, tuple)) and len(err["loc"]) > 0:
                if err["loc"][-1] == missing_field and err.get("type") == "missing":
                    found_error = True
                    break
            else:
                print(f"DEBUG: Unexpected error structure in detail: {err}")
        assert found_error, f"Expected validation error for missing field '{missing_field}' not found or has wrong type/loc."
        mock_video_service_for_api.confirm_video_upload.assert_not_called()

    @pytest.mark.asyncio
    async def test_confirm_upload_invalid_video_id_format(
        self, authenticated_async_client: httpx.AsyncClient, mock_video_service_for_api: MagicMock
    ):
        payload = {"video_id": "not-a-uuid", "object_key": "some/key.mp4"}
        response = await authenticated_async_client.post(self.API_ENDPOINT, json=payload)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        print(f"DEBUG test_confirm_upload_invalid_video_id_format data: {data}") # DEBUG

        detail_content = data.get("detail")
        if isinstance(detail_content, str):
            try:
                detail_list = ast.literal_eval(detail_content)
            except (ValueError, SyntaxError):
                detail_list = []
                print(f"DEBUG: Could not ast.literal_eval detail string: {detail_content}")
        elif isinstance(detail_content, list):
            detail_list = detail_content
        else:
            detail_list = []

        found_error = False
        for err in detail_list:
            if isinstance(err, dict) and err.get("loc") and isinstance(err["loc"], (list, tuple)) and len(err["loc"]) > 0:
                if err["loc"][-1] == "video_id" and isinstance(err.get("type"), str) and "uuid" in err["type"]:
                    found_error = True
                    break
            else:
                print(f"DEBUG: Unexpected error structure in detail: {err}")
        assert found_error, "Expected validation error for invalid video_id format not found or has wrong type/loc."
        mock_video_service_for_api.confirm_video_upload.assert_not_called() 