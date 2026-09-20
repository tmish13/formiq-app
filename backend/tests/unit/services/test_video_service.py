import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import uuid
from typing import Optional, Dict, Any
from fastapi import HTTPException, status
import os
from datetime import datetime, timezone

from app.services.video_service import VideoService
from app.services.storage_service import StorageService
from app.core.config import Settings
from app.models.video import Video
from app.models.enums import VideoStatus, ExerciseType
from app.schemas.video import VideoCreate, VideoUpdate
from app.core.exceptions import NotFoundException, PermissionDeniedException, ServerErrorException
from app.services.base_service import BaseService

# --- Fixtures ---

@pytest.fixture
def mock_db_session() -> AsyncMock:
    return AsyncMock()

@pytest.fixture
def mock_storage_service() -> MagicMock:
    service = MagicMock(spec=StorageService)
    service.generate_presigned_upload_url = AsyncMock()
    service.get_public_url = AsyncMock()
    return service

@pytest.fixture
def mock_app_settings() -> MagicMock:
    settings = MagicMock(spec=Settings)
    # Add any specific settings VideoService might use, e.g.
    # settings.SOME_VIDEO_SERVICE_SETTING = "value"
    return settings

@pytest.fixture
def video_service(mock_db_session: AsyncMock, mock_storage_service: MagicMock, mock_app_settings: MagicMock) -> VideoService:
    service = VideoService(db=mock_db_session, storage_service=mock_storage_service, app_settings=mock_app_settings)
    return service

@pytest.fixture
def sample_user_id() -> uuid.UUID:
    return uuid.uuid4()

@pytest.fixture
def sample_video_id() -> uuid.UUID:
    return uuid.uuid4()

@pytest.fixture
def sample_video_record(sample_user_id: uuid.UUID, sample_video_id: uuid.UUID) -> Video:
    now = datetime.now(timezone.utc)
    return Video(
        id=sample_video_id,
        user_id=sample_user_id,
        filename="test_video.mp4",
        mime_type="video/mp4",
        status=VideoStatus.PENDING_UPLOAD,
        object_key=f"videos/{sample_user_id}/12345_test_video.mp4",
        exercise_type=ExerciseType.SQUAT.value,
        created_at=now,
        updated_at=now
    )

# --- Test Class ---

@pytest.mark.asyncio
class TestVideoService:

    # --- Tests for create_upload_session ---

    @patch("time.time", return_value=1234567890)
    async def test_create_upload_session_success(
        self, mock_time: MagicMock, video_service: VideoService, mock_storage_service: MagicMock, sample_user_id: uuid.UUID
    ):
        """Test successful creation of an upload session and video record."""
        filename = "new_video.mp4"
        full_input_filename = "user_uploads/new_video.mp4"
        safe_filename = "new_video.mp4"

        content_type = "video/mp4"
        metadata = {"exercise_type": "SQUAT", "custom_field": "custom_value"}
        
        mocked_timestamp = 1234567890
        expected_object_key = f"videos/{sample_user_id}/{mocked_timestamp}_{safe_filename}"

        # Mock dependent calls
        mock_created_video_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        created_video_instance = Video(
            id=mock_created_video_id,
            user_id=sample_user_id,
            filename=safe_filename,
            mime_type=content_type,
            status=VideoStatus.PENDING_UPLOAD,
            object_key=expected_object_key,
            exercise_type=ExerciseType[metadata["exercise_type"]].value if metadata and "exercise_type" in metadata and metadata["exercise_type"] in ExerciseType.__members__ else None,
            created_at=now,
            updated_at=now
        )
        
        mock_storage_service.generate_presigned_upload_url.return_value = {
            "url": "http://s3.presigned.url/upload",
            "fields": {"key": "value"}
        }

        with patch.object(BaseService, 'create_async', return_value=created_video_instance) as mock_super_create_method:
            response = await video_service.create_upload_session(sample_user_id, full_input_filename, content_type, metadata)
            mock_super_create_method.assert_awaited_once()

        assert response["video_id"] == str(mock_created_video_id)
        assert response["upload_url"] == "http://s3.presigned.url/upload"
        assert response["fields"] == {"key": "value"}
        assert response["object_key"] == expected_object_key

        mock_storage_service.generate_presigned_upload_url.assert_called_once()
        storage_call_kwargs = mock_storage_service.generate_presigned_upload_url.call_args.kwargs
        assert storage_call_kwargs["object_key"] == expected_object_key
        assert storage_call_kwargs["content_type"] == content_type
        
        s3_metadata = storage_call_kwargs["metadata"]
        assert s3_metadata["user_id"] == str(sample_user_id)
        assert s3_metadata["original_filename"] == full_input_filename
        assert s3_metadata["upload_timestamp"] == str(mocked_timestamp)
        assert s3_metadata["exercise_type"] == "SQUAT"
        assert s3_metadata["custom_field"] == "custom_value"

    async def test_create_upload_session_invalid_content_type(
        self, video_service: VideoService, mock_storage_service: MagicMock, sample_user_id: uuid.UUID
    ):
        """Test create_upload_session with an invalid (non-video) content type."""
        with pytest.raises(HTTPException) as exc_info:
            await video_service.create_upload_session(sample_user_id, "test.txt", "text/plain", {})
        assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "Invalid content type" in exc_info.value.detail

    async def test_create_upload_session_db_error_on_create(
        self, video_service: VideoService, mock_storage_service: MagicMock, sample_user_id: uuid.UUID
    ):
        """Test handling of a database error when creating the video record."""
        with patch.object(BaseService, 'create_async', side_effect=ServerErrorException("DB unique constraint failed")):
            with pytest.raises(ServerErrorException) as exc_info:
                await video_service.create_upload_session(sample_user_id, "test.mp4", "video/mp4", {})
        assert "Could not create video record" in exc_info.value.message
        mock_storage_service.generate_presigned_upload_url.assert_not_called()

    @patch.object(VideoService, 'update_video_metadata_and_status', new_callable=AsyncMock)
    async def test_create_upload_session_storage_error_on_presigned_url(
        self, mock_update_status: AsyncMock, video_service: VideoService, mock_storage_service: MagicMock, sample_user_id: uuid.UUID
    ):
        """Test handling of a storage service error when generating presigned URL."""
        now = datetime.now(timezone.utc)
        created_video_instance_for_storage_error = Video(
            id=uuid.uuid4(), 
            user_id=sample_user_id, 
            status=VideoStatus.PENDING_UPLOAD,
            filename="dummy_on_error.mp4", 
            mime_type="video/mp4",        
            object_key=f"videos/{sample_user_id}/error_path.mp4", 
            created_at=now,               
            updated_at=now                 
        )
        with patch.object(BaseService, 'create_async', return_value=created_video_instance_for_storage_error):
            storage_error_message = "S3 unavailable"
            mock_storage_service.generate_presigned_upload_url.side_effect = Exception(storage_error_message)
        
            with pytest.raises(HTTPException) as exc_info:
                await video_service.create_upload_session(sample_user_id, "test.mp4", "video/mp4", {})
        
            assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert "Could not generate upload URL" in exc_info.value.detail 
            mock_update_status.assert_awaited_once_with(
                video_id=created_video_instance_for_storage_error.id, 
                status=VideoStatus.PROCESSING_FAILED,
                error_message=f"Storage error: {storage_error_message}"
            )

    # --- Tests for confirm_video_upload ---

    @patch("app.tasks.video_tasks.process_video_celery_task.delay")
    @patch.object(VideoService, 'update_video_metadata_and_status', new_callable=AsyncMock)
    async def test_confirm_video_upload_does_not_dispatch_and_leaves_video_uploaded(
        self,
        mock_update_meta_status: AsyncMock,
        mock_celery_delay: MagicMock,
        video_service: VideoService,
        sample_video_record: Video,
        sample_user_id: uuid.UUID,
        mock_storage_service: MagicMock
    ):
        """Confirming an upload must not enqueue process_video_celery_task.

        This test previously asserted the opposite. The task it dispatched was an
        async def under a plain @app.task, so Celery returned an un-awaited
        coroutine and the body never ran -- every video confirmed through this
        path was set to PROCESSING, given a celery_task_id pointing at nothing,
        and left there forever. Confirmation now reports the truth: UPLOADED.
        """
        video_id = sample_video_record.id
        object_key = sample_video_record.object_key
        video_size = 1024 * 1024  # 1MB

        mock_db = video_service.db
        execute_result_mock = MagicMock()
        execute_result_mock.scalars.return_value.first.return_value = sample_video_record
        mock_db.execute = AsyncMock(return_value=execute_result_mock)

        now_uploaded = datetime.now(timezone.utc)
        mock_uploaded_video_obj = Video(**{
            "id": sample_video_record.id, "user_id": sample_video_record.user_id,
            "filename": sample_video_record.filename, "mime_type": sample_video_record.mime_type,
            "object_key": sample_video_record.object_key,
            "exercise_type": sample_video_record.exercise_type,
            "created_at": sample_video_record.created_at, "updated_at": now_uploaded,
            "status": VideoStatus.UPLOADED, "size": video_size,
            "url": "http://s3.public.url/video.mp4",
        })

        with patch.object(BaseService, 'update_async', new_callable=AsyncMock) as mock_super_update:
            mock_super_update.return_value = mock_uploaded_video_obj
            mock_storage_service.get_public_url.return_value = "http://s3.public.url/video.mp4"

            result = await video_service.confirm_video_upload(
                video_id, sample_user_id, False, object_key, video_size
            )

        mock_celery_delay.assert_not_called()
        mock_update_meta_status.assert_not_called()

        assert result.id == video_id
        assert result.status == VideoStatus.UPLOADED
        assert result.celery_task_id is None

    async def test_confirm_video_upload_video_not_found(
        self, video_service: VideoService, mock_storage_service: MagicMock, sample_user_id: uuid.UUID
    ):
        """Test confirm_video_upload when the video record does not exist."""
        mock_db = video_service.db
        execute_result_mock = MagicMock()
        execute_result_mock.scalars.return_value.first.return_value = None # Simulate video not found
        mock_db.execute = AsyncMock(return_value=execute_result_mock)
        
        non_existent_video_id = uuid.uuid4()

        with pytest.raises(NotFoundException, match="Video not found"):
            await video_service.confirm_video_upload(
                non_existent_video_id, sample_user_id, False, "some_key", 100
            )
        
        # Ensure no further operations were attempted
        mock_storage_service.get_public_url.assert_not_called()

    async def test_confirm_video_upload_permission_denied(
        self, video_service: VideoService, mock_storage_service: MagicMock, sample_video_record: Video
    ):
        """Test confirm_video_upload when user is not authorized."""
        mock_db = video_service.db
        execute_result_mock = MagicMock()
        execute_result_mock.scalars.return_value.first.return_value = sample_video_record
        mock_db.execute = AsyncMock(return_value=execute_result_mock)
        
        different_user_id = uuid.uuid4()

        with pytest.raises(PermissionDeniedException, match="Not authorized to confirm this video upload"):
            await video_service.confirm_video_upload(
                sample_video_record.id, 
                different_user_id,       
                False,                   
                sample_video_record.object_key, 
                100
            )
        
        mock_storage_service.get_public_url.assert_not_called()
        # If celery was patched at this level: mock_celery_delay.assert_not_called()
    
    @patch.object(VideoService, 'update_video_metadata_and_status', new_callable=AsyncMock)
    async def test_confirm_video_upload_object_key_mismatch(
        self, mock_update_meta_status: AsyncMock, video_service: VideoService, sample_video_record: Video, sample_user_id: uuid.UUID
    ):
        """Test confirm_video_upload with an object key mismatch."""
        mock_db = video_service.db
        execute_result_mock = MagicMock()
        execute_result_mock.scalars.return_value.first.return_value = sample_video_record
        mock_db.execute = AsyncMock(return_value=execute_result_mock)
        
        # Configure the mock for update_video_metadata_and_status
        now_failed = datetime.now(timezone.utc)
        # Ensure all required fields for Video model are present
        failed_video_attrs = {
            "id": sample_video_record.id, 
            "user_id": sample_video_record.user_id,
            "filename": sample_video_record.filename, 
            "mime_type": sample_video_record.mime_type,
            "object_key": sample_video_record.object_key, 
            "exercise_type": sample_video_record.exercise_type,
            "created_at": sample_video_record.created_at, 
            "updated_at": now_failed, # New timestamp
            "status": VideoStatus.PROCESSING_FAILED, 
            "error_message": "Object key mismatch during confirmation.",
            # Add any other non-nullable fields from Video model if not in sample_video_record
            "url": sample_video_record.url,
            "processed_url": sample_video_record.processed_url,
            "size": sample_video_record.size,
            "duration": sample_video_record.duration,
            "resolution": sample_video_record.resolution,
            "fps": sample_video_record.fps,
            "processing_errors": sample_video_record.processing_errors,
            "processed_object_key": sample_video_record.processed_object_key,
            "frame_s3_keys": sample_video_record.frame_s3_keys,
            "processed_frame_count": sample_video_record.processed_frame_count,
            "thumbnail_s3_key": sample_video_record.thumbnail_s3_key,
            "thumbnail_url": sample_video_record.thumbnail_url,
            "additional_metadata": sample_video_record.additional_metadata,
            "pose_data": sample_video_record.pose_data,
            "pose_visualizations": sample_video_record.pose_visualizations,
            "analysis_results": sample_video_record.analysis_results,
            "stats": sample_video_record.stats,
            "score": sample_video_record.score,
            "rep_count": sample_video_record.rep_count,
            "raw_pose_data": sample_video_record.raw_pose_data,
            "calculated_angles": sample_video_record.calculated_angles,
            "celery_task_id": sample_video_record.celery_task_id
        }
        failed_video_obj = Video(**failed_video_attrs)
        mock_update_meta_status.return_value = video_service.response_schema.from_orm(failed_video_obj)

        with pytest.raises(HTTPException) as exc_info:
            await video_service.confirm_video_upload(
                sample_video_record.id, 
                sample_user_id, 
                False, 
                "mismatched_object_key", 
                100
            )
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "Object key mismatch" in exc_info.value.detail
        
        mock_update_meta_status.assert_called_once_with(
            video_id=sample_video_record.id,
            status=VideoStatus.PROCESSING_FAILED, 
            error_message="Object key mismatch during confirmation."
        )

    @pytest.mark.parametrize("terminal_status", [
        VideoStatus.FRAMES_EXTRACTED,
        VideoStatus.PROCESSED,
        VideoStatus.ANALYSIS_COMPLETE,
        VideoStatus.ERROR,
        VideoStatus.PROCESSING_FAILED, 
        VideoStatus.PROCESSING, # Already processing
    ])
    @patch("app.tasks.video_tasks.process_video_celery_task.delay") # Patch Celery to assert not called
    async def test_confirm_video_upload_already_in_terminal_or_processing_state(
        self, mock_celery_delay: MagicMock, video_service: VideoService, sample_video_record: Video, sample_user_id: uuid.UUID, terminal_status: VideoStatus
    ):
        """Test confirm_video_upload when video is already processed, failed, or processing."""
        sample_video_record.status = terminal_status
        mock_db = video_service.db
        execute_result_mock = MagicMock()
        execute_result_mock.scalars.return_value.first.return_value = sample_video_record
        mock_db.execute = AsyncMock(return_value=execute_result_mock)

        result = await video_service.confirm_video_upload(
            sample_video_record.id, sample_user_id, False, sample_video_record.object_key, 100
        )
        assert isinstance(result, video_service.response_schema) # Changed here
        assert result.status == terminal_status 

    @patch("app.tasks.video_tasks.process_video_celery_task.delay") # To check it's not called
    async def test_confirm_video_upload_invalid_initial_state_for_confirmation(
        self, mock_celery_delay: MagicMock, video_service: VideoService, sample_video_record: Video, sample_user_id: uuid.UUID
    ):
        """Test confirm_video_upload when video status is not PENDING_UPLOAD or UPLOADED (and not a terminal/processing state from the first check)."""
        # Use a status that is not PENDING_UPLOAD/UPLOADED and also not in the first list of terminal/processing states.
        # VideoStatus.FRAMES_EXTRACTED is a good candidate.
        sample_video_record.status = VideoStatus.FRAMES_EXTRACTED 
        mock_db = video_service.db
        execute_result_mock = MagicMock()
        execute_result_mock.scalars.return_value.first.return_value = sample_video_record
        mock_db.execute = AsyncMock(return_value=execute_result_mock)
        
        result = await video_service.confirm_video_upload(
            sample_video_record.id, sample_user_id, False, sample_video_record.object_key, 100
        )
        assert isinstance(result, video_service.response_schema) # Changed here
        assert result.status == VideoStatus.FRAMES_EXTRACTED
        # mock_update_meta_status.assert_not_called() # mock_update_meta_status is not in this test's scope

    @patch("app.tasks.video_tasks.process_video_celery_task.delay")
    async def test_confirm_video_upload_has_no_dispatch_failure_path_left(
        self,
        mock_celery_delay: MagicMock,
        video_service: VideoService,
        sample_video_record: Video,
        sample_user_id: uuid.UUID,
        mock_storage_service: MagicMock
    ):
        """Replaces test_confirm_video_upload_celery_import_error and
        test_confirm_video_upload_celery_dispatch_general_error.

        Both covered error handling around a Celery dispatch that no longer
        happens: an ImportError or a general exception from .delay() used to set
        the video to PROCESSING_FAILED. With no dispatch there is no dispatch
        failure, and confirmation cannot be knocked into a failed state by the
        task queue being unavailable. That is the property worth keeping.
        """
        mock_celery_delay.side_effect = AssertionError("dispatch must not be attempted")

        mock_db = video_service.db
        execute_result_mock = MagicMock()
        execute_result_mock.scalars.return_value.first.return_value = sample_video_record
        mock_db.execute = AsyncMock(return_value=execute_result_mock)
        mock_storage_service.get_public_url = AsyncMock(return_value="http://s3.public.url/v.mp4")

        uploaded_obj = Video(**{
            "id": sample_video_record.id, "user_id": sample_video_record.user_id,
            "filename": sample_video_record.filename, "mime_type": sample_video_record.mime_type,
            "object_key": sample_video_record.object_key,
            "exercise_type": sample_video_record.exercise_type,
            "created_at": sample_video_record.created_at,
            "updated_at": datetime.now(timezone.utc),
            "status": VideoStatus.UPLOADED, "size": 2048,
            "url": "http://s3.public.url/v.mp4",
        })

        with patch.object(BaseService, 'update_async', new_callable=AsyncMock) as mock_super_update:
            mock_super_update.return_value = uploaded_obj
            result = await video_service.confirm_video_upload(
                sample_video_record.id, sample_user_id, False,
                sample_video_record.object_key, 2048,
            )

        assert result.status == VideoStatus.UPLOADED
        assert result.status is not VideoStatus.PROCESSING_FAILED

    @patch("app.tasks.video_tasks.process_video_celery_task.delay")
    @patch.object(VideoService, 'update_video_metadata_and_status', new_callable=AsyncMock)
    async def test_confirm_video_upload_missing_object_key_before_dispatch(
        self, mock_update_meta_status: AsyncMock, mock_celery_delay: MagicMock, video_service: VideoService, sample_video_record: Video, sample_user_id: uuid.UUID, mock_storage_service: MagicMock
    ):
        """Test confirm_video_upload when object_key is missing on the record before dispatch."""
        mock_db = video_service.db
        execute_result_mock_get = MagicMock()
        execute_result_mock_get.scalars.return_value.first.return_value = sample_video_record
        mock_db.execute = AsyncMock(return_value=execute_result_mock_get)
        
        # The refactored version already manually creates video_after_update_to_uploaded_obj.

        original_object_key_for_test = sample_video_record.object_key 
        sample_video_record.object_key = None # Setup: Record in DB has no object key

        # Mock for the super().update_async call to set status to UPLOADED
        now_missing_key = datetime.now(timezone.utc)
        video_after_update_to_uploaded_attrs = {
            "id": sample_video_record.id, 
            "user_id": sample_video_record.user_id,
            "filename": sample_video_record.filename, 
            "mime_type": sample_video_record.mime_type,
            "object_key": None, # Explicitly None after update
            "exercise_type": sample_video_record.exercise_type,
            "created_at": sample_video_record.created_at, 
            "updated_at": now_missing_key,
            "status": VideoStatus.UPLOADED, 
            "size": 100,
            "url": None, # No public URL if object key is None
            # Fill other required non-nullable fields
            "processed_url": sample_video_record.processed_url,
            "duration": sample_video_record.duration,
            "resolution": sample_video_record.resolution,
            "fps": sample_video_record.fps,
            "processing_errors": sample_video_record.processing_errors,
            "processed_object_key": sample_video_record.processed_object_key,
            "frame_s3_keys": sample_video_record.frame_s3_keys,
            "processed_frame_count": sample_video_record.processed_frame_count,
            "thumbnail_s3_key": sample_video_record.thumbnail_s3_key,
            "thumbnail_url": sample_video_record.thumbnail_url,
            "additional_metadata": sample_video_record.additional_metadata,
            "pose_data": sample_video_record.pose_data,
            "pose_visualizations": sample_video_record.pose_visualizations,
            "analysis_results": sample_video_record.analysis_results,
            "stats": sample_video_record.stats,
            "score": sample_video_record.score,
            "rep_count": sample_video_record.rep_count,
            "raw_pose_data": sample_video_record.raw_pose_data,
            "calculated_angles": sample_video_record.calculated_angles,
            "celery_task_id": None # No celery task should be dispatched
        }
        video_after_update_to_uploaded_obj = Video(**video_after_update_to_uploaded_attrs)

        with patch("app.tasks.video_tasks.process_video_celery_task.delay") as mock_celery_delay_final, \
             patch.object(BaseService, 'update_async', return_value=video_after_update_to_uploaded_obj) as mock_super_update_to_uploaded_call:

            result = await video_service.confirm_video_upload(
                sample_video_record.id, 
                sample_user_id, 
                False, 
                None, # Confirming with object_key=None
                100
            )
        
        assert result.status == VideoStatus.UPLOADED 
        assert result.object_key is None
        mock_super_update_to_uploaded_call.assert_called_once() 
        
        update_call_args = mock_super_update_to_uploaded_call.call_args.kwargs
        assert isinstance(update_call_args['obj_in'], VideoUpdate)
        assert update_call_args['obj_in'].status == VideoStatus.UPLOADED
        # VideoUpdate schema doesn't have object_key, so we can't assert it here directly on obj_in
        # but the resulting video_after_update_to_uploaded_obj has it as None.

        mock_celery_delay_final.assert_not_called()
        mock_update_meta_status.assert_not_called() 

        sample_video_record.object_key = original_object_key_for_test # Restore

    @patch("app.tasks.video_tasks.process_video_celery_task.delay")
    @patch.object(VideoService, 'update_video_metadata_and_status', new_callable=AsyncMock)
    async def test_confirm_video_upload_permission_allowed_for_superuser(
        self, 
        mock_update_meta_status: AsyncMock, 
        mock_celery_delay: MagicMock, 
        video_service: VideoService, 
        sample_video_record: Video, # Video owned by sample_user_id
        mock_storage_service: MagicMock
    ):
        """Test superuser can confirm upload for a video not owned by them."""
        video_id = sample_video_record.id
        object_key = sample_video_record.object_key
        video_size = 1024 * 1024
        exercise_type_value = sample_video_record.exercise_type
        
        # current_user_id is different from sample_video_record.user_id
        superuser_confirming_id = uuid.uuid4() 
        assert superuser_confirming_id != sample_video_record.user_id

        mock_db = video_service.db
        execute_result_mock_get = MagicMock()
        execute_result_mock_get.scalars.return_value.first.return_value = sample_video_record
        mock_db.execute = AsyncMock(return_value=execute_result_mock_get)
        
        # Manually construct mock_uploaded_video instead of using .dict()
        now_superuser_uploaded = datetime.now(timezone.utc)
        mock_uploaded_video_attrs_superuser = {
            "id": sample_video_record.id, 
            "user_id": sample_video_record.user_id, 
            "filename": sample_video_record.filename,
            "mime_type": sample_video_record.mime_type, 
            "object_key": sample_video_record.object_key, 
            "exercise_type": sample_video_record.exercise_type,
            "created_at": sample_video_record.created_at, 
            "updated_at": now_superuser_uploaded, 
            "status": VideoStatus.UPLOADED,
            "size": video_size, 
            "url": "http://s3.public.url/video.mp4",
            # Ensure all other non-nullable fields from Video model are present
            "processed_url": sample_video_record.processed_url,
            "duration": sample_video_record.duration,
            "resolution": sample_video_record.resolution,
            "fps": sample_video_record.fps,
            "processing_errors": sample_video_record.processing_errors,
            "processed_object_key": sample_video_record.processed_object_key,
            "frame_s3_keys": sample_video_record.frame_s3_keys,
            "processed_frame_count": sample_video_record.processed_frame_count,
            "thumbnail_s3_key": sample_video_record.thumbnail_s3_key,
            "thumbnail_url": sample_video_record.thumbnail_url,
            "additional_metadata": sample_video_record.additional_metadata,
            "pose_data": sample_video_record.pose_data,
            "pose_visualizations": sample_video_record.pose_visualizations,
            "analysis_results": sample_video_record.analysis_results,
            "stats": sample_video_record.stats,
            "score": sample_video_record.score,
            "rep_count": sample_video_record.rep_count,
            "raw_pose_data": sample_video_record.raw_pose_data,
            "calculated_angles": sample_video_record.calculated_angles,
            "celery_task_id": None # sample_video_record likely has this as None initially
        }
        mock_uploaded_video_obj_superuser = Video(**mock_uploaded_video_attrs_superuser)
                
        mock_storage_service.get_public_url.return_value = "http://s3.public.url/video.mp4"

        with patch.object(BaseService, 'update_async', new_callable=AsyncMock) as mock_super_update_first_call_superuser:
            mock_super_update_first_call_superuser.return_value = mock_uploaded_video_obj_superuser

            result = await video_service.confirm_video_upload(
                video_id, 
                superuser_confirming_id, # User doing the confirmation
                True,                    # is_superuser = True
                object_key, 
                video_size
            )

        # The permission check is what this test is about; the dispatch that used
        # to follow it is retired, so the superuser gets the same honest UPLOADED
        # result any other caller gets.
        mock_celery_delay.assert_not_called()
        mock_update_meta_status.assert_not_called()

        assert result.id == video_id
        assert result.status == VideoStatus.UPLOADED
        assert result.celery_task_id is None

    # Add more tests for other methods in VideoService like get_video_details, update_video_metadata_and_status etc.
    # For example, test update_video_metadata_and_status directly:
    @patch("time.time", return_value=1234567890)
    async def test_update_video_metadata_and_status_success(
        self, mock_time: MagicMock, video_service: VideoService, sample_video_record: Video
    ):
        video_id = sample_video_record.id
        new_status = VideoStatus.PROCESSED
        error_msg = None # Explicitly None for a typical success/non-error update
        celery_id = "celery_123"
        processed_frame_count_val = 150

        mock_db = video_service.db
        execute_result_mock_get = MagicMock() # For the get_async in update_video_metadata_and_status
        execute_result_mock_get.scalars.return_value.first.return_value = sample_video_record
        mock_db.execute = AsyncMock(return_value=execute_result_mock_get)
        
        now = datetime.now(timezone.utc)
        updated_video_mock = Video(
            id=sample_video_record.id,
            user_id=sample_video_record.user_id,
            filename=sample_video_record.filename,
            mime_type=sample_video_record.mime_type,
            object_key=sample_video_record.object_key,
            status=new_status,
            error_message=error_msg,
            celery_task_id=celery_id,
            processed_frame_count=processed_frame_count_val,
            exercise_type=sample_video_record.exercise_type,
            created_at=sample_video_record.created_at,
            updated_at=now
        )
        with patch.object(BaseService, 'update_async', return_value=updated_video_mock) as mock_super_update_method:
            result = await video_service.update_video_metadata_and_status(
                video_id=video_id,
                status=new_status,
                error_message=error_msg,
                celery_task_id=celery_id,
                processed_frame_count=processed_frame_count_val
            )
            mock_super_update_method.assert_awaited_once()
            
            update_call_args_obj_in = mock_super_update_method.call_args[1]['obj_in']
            assert isinstance(update_call_args_obj_in, VideoUpdate)
            assert update_call_args_obj_in.status == new_status
            assert update_call_args_obj_in.error_message is None # Expect None
            assert update_call_args_obj_in.celery_task_id == celery_id
            assert update_call_args_obj_in.processed_frame_count == processed_frame_count_val
            
            assert isinstance(result, video_service.response_schema) 
            assert result.status == new_status
            assert result.error_message is None # Expect None
            assert result.celery_task_id == celery_id
            assert result.processed_frame_count == processed_frame_count_val

    async def test_update_video_metadata_and_status_video_not_found(
        self, video_service: VideoService
    ):
        mock_db = video_service.db
        execute_result_mock_get = MagicMock()
        execute_result_mock_get.scalars.return_value.first.return_value = None # Simulate video not found
        mock_db.execute = AsyncMock(return_value=execute_result_mock_get)
        
        video_id_for_test = uuid.uuid4() # Use a specific ID for the regex

        with patch.object(BaseService, 'update_async') as mock_super_update_method:
            with pytest.raises(NotFoundException, match=f"Video with id {video_id_for_test} not found for update \(prior to super\(\)\.update_async\)\."):
                await video_service.update_video_metadata_and_status(video_id=video_id_for_test, status=VideoStatus.ERROR)
            mock_super_update_method.assert_not_called() 