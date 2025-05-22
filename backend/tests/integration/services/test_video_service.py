import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from uuid import uuid4, UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.video_service import VideoService
from app.services.storage_service import StorageService
from app.models.video import Video
from app.models.enums import VideoStatus, ExerciseType
from app.schemas.video import VideoUpdate
from app.core.config import Settings # Assuming VideoService and StorageService need settings

@pytest.fixture
def mock_app_settings() -> Settings:
    return Settings(
        S3_BUCKET_NAME="test-bucket",
        # Add other relevant settings if VideoService or StorageService depend on them
    )

@pytest.fixture
def mock_storage_service(mock_app_settings: Settings) -> MagicMock:
    mock = MagicMock(spec=StorageService)
    mock.generate_presigned_upload_url = AsyncMock(return_value={"url": "http://s3-upload-url.com", "fields": {}})
    mock.get_public_url = AsyncMock(return_value="http://s3-public-url.com/video.mp4")
    return mock

@pytest.fixture
async def pending_upload_video(db_session: AsyncSession) -> Video:
    video = Video(
        id=uuid4(),
        user_id=uuid4(),
        filename="test_video.mp4",
        object_key="videos/user_id_placeholder/timestamp_placeholder_test_video.mp4",
        status=VideoStatus.PENDING_UPLOAD,
        mime_type="video/mp4",
        exercise_type=ExerciseType.SQUAT.value # Store as string value
    )
    db_session.add(video)
    await db_session.commit()
    await db_session.refresh(video)
    return video

@pytest.mark.asyncio
@patch('app.tasks.video_tasks.process_video_celery_task.delay')
async def test_confirm_video_upload_enqueues_processing_task(
    mock_process_video_task_delay: MagicMock,
    db_session: AsyncSession,
    mock_storage_service: MagicMock,
    mock_app_settings: Settings,
    pending_upload_video: Video
):
    """
    Test that VideoService.confirm_video_upload successfully updates video status
    and enqueues the process_video_celery_task.
    """
    video_service = VideoService(db=db_session, storage_service=mock_storage_service, app_settings=mock_app_settings)

    current_user_id = pending_upload_video.user_id
    is_superuser = False
    object_key_from_upload = pending_upload_video.object_key
    uploaded_file_size = 1024 * 1024 # 1MB

    # ACT
    updated_video_response = await video_service.confirm_video_upload(
        video_id=pending_upload_video.id,
        current_user_id=current_user_id,
        is_superuser=is_superuser,
        object_key=object_key_from_upload,
        size=uploaded_file_size
    )

    # ASSERT
    # 1. Check video status and details in DB
    await db_session.refresh(pending_upload_video) # Refresh from DB

    assert updated_video_response.id == pending_upload_video.id
    assert updated_video_response.status == VideoStatus.UPLOADED # Status updated by confirm_video_upload
    
    # Verify DB state directly
    assert pending_upload_video.status == VideoStatus.UPLOADED
    assert pending_upload_video.size == uploaded_file_size
    assert pending_upload_video.url == "http://s3-public-url.com/video.mp4" # From mock_storage_service

    # 2. Check that the Celery task was called (enqueued)
    mock_process_video_task_delay.assert_called_once_with(
        video_id_str=str(pending_upload_video.id),
        original_video_path=pending_upload_video.object_key,
        exercise_type_value=pending_upload_video.exercise_type # Should be the string value
    )
    
    # Additional check: Ensure that the status in the response matches the DB
    assert updated_video_response.status == pending_upload_video.status

@pytest.mark.asyncio
@patch('app.tasks.video_tasks.process_video_celery_task.delay')
async def test_confirm_video_upload_object_key_mismatch(
    mock_process_video_task_delay: MagicMock,
    db_session: AsyncSession,
    mock_storage_service: MagicMock,
    mock_app_settings: Settings,
    pending_upload_video: Video
):
    """
    Test that confirm_video_upload handles an object key mismatch
    by updating status to UPLOAD_FAILED and raising an HTTPException.
    """
    video_service = VideoService(db=db_session, storage_service=mock_storage_service, app_settings=mock_app_settings)

    current_user_id = pending_upload_video.user_id
    is_superuser = False
    mismatched_object_key = "wrong/path/to/video.mp4"
    uploaded_file_size = 1024 * 1024

    from fastapi import HTTPException # Import locally for the test

    with pytest.raises(HTTPException) as exc_info:
        await video_service.confirm_video_upload(
            video_id=pending_upload_video.id,
            current_user_id=current_user_id,
            is_superuser=is_superuser,
            object_key=mismatched_object_key, # Mismatched key
            size=uploaded_file_size
        )

    assert exc_info.value.status_code == 400
    assert "Object key mismatch" in exc_info.value.detail

    await db_session.refresh(pending_upload_video)
    assert pending_upload_video.status == VideoStatus.UPLOAD_FAILED
    assert "Object key mismatch" in pending_upload_video.error_message

    mock_process_video_task_delay.assert_not_called()


@pytest.mark.asyncio
@patch('app.tasks.video_tasks.process_video_celery_task.delay')
async def test_confirm_video_upload_task_dispatch_failure(
    mock_process_video_task_delay: MagicMock,
    db_session: AsyncSession,
    mock_storage_service: MagicMock,
    mock_app_settings: Settings,
    pending_upload_video: Video
):
    """
    Test that if Celery task dispatch fails, video status is updated to PROCESSING_FAILED.
    """
    video_service = VideoService(db=db_session, storage_service=mock_storage_service, app_settings=mock_app_settings)

    current_user_id = pending_upload_video.user_id
    object_key_from_upload = pending_upload_video.object_key
    uploaded_file_size = 1024 * 1024

    # Simulate Celery task dispatch failure
    dispatch_error_message = "Celery broker not available"
    mock_process_video_task_delay.side_effect = Exception(dispatch_error_message)

    # ACT
    # We don't expect an HTTP exception to be raised to the client here,
    # the error is handled internally by updating status.
    updated_video_response = await video_service.confirm_video_upload(
        video_id=pending_upload_video.id,
        current_user_id=current_user_id,
        is_superuser=False,
        object_key=object_key_from_upload,
        size=uploaded_file_size
    )

    # ASSERT
    await db_session.refresh(pending_upload_video)

    assert pending_upload_video.status == VideoStatus.PROCESSING_FAILED
    assert dispatch_error_message in pending_upload_video.error_message
    assert updated_video_response.status == VideoStatus.PROCESSING_FAILED

    # Verify that the mock was called
    mock_process_video_task_delay.assert_called_once_with(
        video_id_str=str(pending_upload_video.id),
        original_video_path=pending_upload_video.object_key,
        exercise_type_value=pending_upload_video.exercise_type
    ) 