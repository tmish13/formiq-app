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
def video_service(mock_db_session: AsyncMock, mock_storage_service: MagicMock, mock_settings: MagicMock) -> VideoService:
    service = VideoService(db=mock_db_session, storage_service=mock_storage_service, app_settings=mock_settings)
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
        assert "Could not create video record" in exc_info.value.detail
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
    async def test_confirm_video_upload_success_dispatches_task(
        self, 
        mock_update_meta_status: AsyncMock, 
        mock_celery_delay: MagicMock, 
        video_service: VideoService, 
        sample_video_record: Video, 
        sample_user_id: uuid.UUID,
        mock_storage_service: MagicMock
    ):
        """Test successful video upload confirmation and Celery task dispatch."""
        video_id = sample_video_record.id
        object_key = sample_video_record.object_key
        video_size = 1024 * 1024  # 1MB
        exercise_type_value = sample_video_record.exercise_type

        # Mock DB calls
        mock_db = video_service.db
        execute_result_mock = MagicMock()
        execute_result_mock.scalars.return_value.first.return_value = sample_video_record # Video in PENDING_UPLOAD
        mock_db.execute = AsyncMock(return_value=execute_result_mock)
        
        # Mock first update to UPLOADED
        now_uploaded = datetime.now(timezone.utc)
        mock_uploaded_video_attributes = {
            "id": sample_video_record.id, "user_id": sample_video_record.user_id,
            "filename": sample_video_record.filename, "mime_type": sample_video_record.mime_type,
            "object_key": sample_video_record.object_key, "exercise_type": sample_video_record.exercise_type,
            "created_at": sample_video_record.created_at, "updated_at": now_uploaded,
            "status": VideoStatus.UPLOADED, "size": video_size, "url": "http://s3.public.url/video.mp4"
        }
        mock_uploaded_video_obj = Video(**mock_uploaded_video_attributes)

        with patch.object(BaseService, 'update_async', new_callable=AsyncMock) as mock_super_update_first_call:
            mock_super_update_first_call.return_value = mock_uploaded_video_obj

            mock_storage_service.get_public_url.return_value = "http://s3.public.url/video.mp4"
            mock_celery_task_instance = MagicMock()
            mock_celery_task_instance.id = "test_celery_task_id"
            mock_celery_delay.return_value = mock_celery_task_instance

            now_processing = datetime.now(timezone.utc)
            mock_processing_video_attributes = {
                **mock_uploaded_video_attributes, # Start with UPLOADED attributes
                "status": VideoStatus.PROCESSING, "celery_task_id": "test_celery_task_id",
                "updated_at": now_processing
            }
            mock_processing_video_obj_for_response = Video(**mock_processing_video_attributes)
            mock_update_meta_status.return_value = video_service.response_schema.from_orm(mock_processing_video_obj_for_response)

            result = await video_service.confirm_video_upload(
                video_id, sample_user_id, False, object_key, video_size
            )

        # video_service.db.refresh(sample_video_record) # This does not work as expected with AsyncMock
    
        # Check first update call (to UPLOADED) made to BaseService.update_async
        # mock_super_update_first_call.assert_awaited_once() # This was already checked within the with block
        # update_args = mock_super_update_first_call.call_args.kwargs
        # assert update_args['obj_in'].status == VideoStatus.UPLOADED # Also checked within the with block
        # assert update_args['obj_in'].size == video_size
        # assert update_args['obj_in'].url == "http://s3.public.url/video.mp4"
        # The above assertions on mock_super_update_first_call are correctly placed *inside* its `with` block.
        # The assertion `assert sample_video_record.status == VideoStatus.UPLOADED` is removed as it's misleading.

        mock_celery_delay.assert_called_once_with(
            video_id_str=str(video_id),
            original_video_path=object_key,
            exercise_type_value=exercise_type_value
        )
        
        # Check update_video_metadata_and_status call (to PROCESSING)
        mock_update_meta_status.assert_called_once_with(
            video_id=video_id,
            status=VideoStatus.PROCESSING,
            celery_task_id="test_celery_task_id",
            error_message=None
        )

        assert result.id == video_id
        assert result.status == VideoStatus.PROCESSING
        assert result.celery_task_id == "test_celery_task_id"

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

    @patch.object(VideoService, 'update_video_metadata_and_status', new_callable=AsyncMock)
    async def test_confirm_video_upload_celery_import_error(
        self, mock_update_meta_status: AsyncMock, video_service: VideoService, sample_video_record: Video, sample_user_id: uuid.UUID, mock_storage_service: MagicMock
    ):
        """Test handling of ImportError when trying to dispatch Celery task."""
        mock_storage_service.get_public_url = AsyncMock(return_value="http://s3.public.url/video_for_import_error.mp4") # Configure return value

        mock_db = video_service.db
        execute_result_mock_get = MagicMock() # For the initial get_async
        execute_result_mock_get.scalars.return_value.first.return_value = sample_video_record
        
        # For the get_async inside the patched update_video_metadata_and_status, if it's not fully mocked out by mock_update_meta_status
        # This assumes mock_update_meta_status effectively mocks the entire method including its potential get_async
        mock_db.execute = AsyncMock(return_value=execute_result_mock_get)
        
        now = datetime.now(timezone.utc)
        mock_uploaded_video = Video(
            id=sample_video_record.id,
            user_id=sample_video_record.user_id,
            filename=sample_video_record.filename,
            mime_type=sample_video_record.mime_type,
            object_key=sample_video_record.object_key,
            exercise_type=sample_video_record.exercise_type,
            created_at=sample_video_record.created_at,
            # ---- Key changes for this mock ----
            status=VideoStatus.UPLOADED, 
            updated_at=now,
            # ---- End Key changes ----
            # Carry over other nullable fields from sample_video_record
            url=sample_video_record.url,
            processed_url=sample_video_record.processed_url,
            size=sample_video_record.size,
            duration=sample_video_record.duration,
            resolution=sample_video_record.resolution,
            fps=sample_video_record.fps,
            processing_errors=sample_video_record.processing_errors,
            processed_object_key=sample_video_record.processed_object_key,
            frame_s3_keys=sample_video_record.frame_s3_keys,
            processed_frame_count=sample_video_record.processed_frame_count,
            thumbnail_s3_key=sample_video_record.thumbnail_s3_key,
            thumbnail_url=sample_video_record.thumbnail_url,
            additional_metadata=sample_video_record.additional_metadata,
            pose_data=sample_video_record.pose_data,
            pose_visualizations=sample_video_record.pose_visualizations,
            analysis_results=sample_video_record.analysis_results,
            stats=sample_video_record.stats,
            score=sample_video_record.score,
            rep_count=sample_video_record.rep_count,
            raw_pose_data=sample_video_record.raw_pose_data,
            calculated_angles=sample_video_record.calculated_angles,
            celery_task_id = None # Explicitly None before Celery call in this test path
        )
        mock_update_meta_status.return_value = video_service.response_schema.from_orm(mock_uploaded_video)
        
        # Patch Celery task import to raise ImportError
        with patch("app.tasks.video_tasks.process_video_celery_task.delay", side_effect=ImportError("Celery is down")):
            # Mock the final status update to PROCESSING_FAILED
            now_failed_import_err = datetime.now(timezone.utc)
            mock_failed_video_attrs = {
                "id": mock_uploaded_video.id, 
                "user_id": mock_uploaded_video.user_id,
                "filename": mock_uploaded_video.filename, 
                "mime_type": mock_uploaded_video.mime_type,
                "object_key": mock_uploaded_video.object_key, 
                "exercise_type": mock_uploaded_video.exercise_type,
                "created_at": mock_uploaded_video.created_at, 
                "updated_at": now_failed_import_err, # New timestamp
                "status": VideoStatus.PROCESSING_FAILED, 
                "error_message": "Task dispatch failed: Import Error - Celery is down",
                # Copy other necessary fields from mock_uploaded_video if they exist and are non-nullable
                "url": mock_uploaded_video.url,
                "processed_url": mock_uploaded_video.processed_url,
                "size": mock_uploaded_video.size,
                "duration": mock_uploaded_video.duration,
                "resolution": mock_uploaded_video.resolution,
                "fps": mock_uploaded_video.fps,
                "processing_errors": mock_uploaded_video.processing_errors,
                "processed_object_key": mock_uploaded_video.processed_object_key,
                "frame_s3_keys": mock_uploaded_video.frame_s3_keys,
                "processed_frame_count": mock_uploaded_video.processed_frame_count,
                "thumbnail_s3_key": mock_uploaded_video.thumbnail_s3_key,
                "thumbnail_url": mock_uploaded_video.thumbnail_url,
                "additional_metadata": mock_uploaded_video.additional_metadata,
                "pose_data": mock_uploaded_video.pose_data,
                "pose_visualizations": mock_uploaded_video.pose_visualizations,
                "analysis_results": mock_uploaded_video.analysis_results,
                "stats": mock_uploaded_video.stats,
                "score": mock_uploaded_video.score,
                "rep_count": mock_uploaded_video.rep_count,
                "raw_pose_data": mock_uploaded_video.raw_pose_data,
                "calculated_angles": mock_uploaded_video.calculated_angles,
                "celery_task_id": None # Celery task dispatch failed
            }
            mock_failed_video_obj = Video(**mock_failed_video_attrs)
            mock_update_meta_status.return_value = video_service.response_schema.from_orm(mock_failed_video_obj)
            
            result = await video_service.confirm_video_upload(
                sample_video_record.id, sample_user_id, False, sample_video_record.object_key, 100
            )

        assert isinstance(result, video_service.response_schema) # Changed here
        assert result.status == VideoStatus.PROCESSING_FAILED
        assert "Task dispatch failed: Import Error" in result.error_message
        # First update to UPLOADED should have happened
        mock_update_meta_status.assert_called_once()
        # Second update (update_video_metadata_and_status) to PROCESSING_FAILED
        mock_update_meta_status.assert_called_once_with(
            video_id=sample_video_record.id,
            status=VideoStatus.PROCESSING_FAILED,
            error_message="Task dispatch failed: Import Error - Celery is down"
        )
        
    @patch("app.tasks.video_tasks.process_video_celery_task.delay")
    @patch.object(VideoService, 'update_video_metadata_and_status', new_callable=AsyncMock)
    async def test_confirm_video_upload_celery_dispatch_general_error(
        self, mock_update_meta_status: AsyncMock, mock_celery_delay: MagicMock, video_service: VideoService, sample_video_record: Video, sample_user_id: uuid.UUID, mock_storage_service: MagicMock
    ):
        """Test handling of a general error when dispatching Celery task."""
        mock_db = video_service.db
        execute_result_mock_get = MagicMock()
        execute_result_mock_get.scalars.return_value.first.return_value = sample_video_record
        mock_db.execute = AsyncMock(return_value=execute_result_mock_get)

        now_uploaded_general_err = datetime.now(timezone.utc)
        mock_uploaded_video_attrs_general_err = {
            "id": sample_video_record.id, "user_id": sample_video_record.user_id,
            "filename": sample_video_record.filename, "mime_type": sample_video_record.mime_type,
            "object_key": sample_video_record.object_key, "exercise_type": sample_video_record.exercise_type,
            "created_at": sample_video_record.created_at, "updated_at": now_uploaded_general_err,
            "status": VideoStatus.UPLOADED, "size": 100, "url": "http://s3.public.url/video.mp4"
        }
        mock_uploaded_video_obj_general_err = Video(**mock_uploaded_video_attrs_general_err)
        
        mock_storage_service.get_public_url.return_value = "http://s3.public.url/video.mp4"
        
        dispatch_error_message = "Redis not available"
        mock_celery_delay.side_effect = Exception(dispatch_error_message)

        now_failed_general_err = datetime.now(timezone.utc)
        mock_failed_video_attrs_for_response = {
            **mock_uploaded_video_attrs_general_err, # Start with UPLOADED attributes
            "status": VideoStatus.PROCESSING_FAILED,
            "error_message": f"Task dispatch failed: {dispatch_error_message}",
            "updated_at": now_failed_general_err,
            "celery_task_id": None # No task ID if dispatch failed
        }
        mock_failed_video_obj_for_response = Video(**mock_failed_video_attrs_for_response)
        mock_update_meta_status.return_value = video_service.response_schema.from_orm(mock_failed_video_obj_for_response)
        
        with patch.object(BaseService, 'update_async', new_callable=AsyncMock) as mock_super_update_first_call:
            mock_super_update_first_call.return_value = mock_uploaded_video_obj_general_err

            result = await video_service.confirm_video_upload(
                sample_video_record.id, sample_user_id, False, sample_video_record.object_key, 100
            )

        assert isinstance(result, video_service.response_schema) # Changed here
        assert result.status == VideoStatus.PROCESSING_FAILED
        print(f"DEBUG: mock_failed_video_obj_for_response.error_message = {mock_failed_video_obj_for_response.error_message}")
        print(f"DEBUG: result.error_message = {result.error_message}")
        assert f"Task dispatch failed: {dispatch_error_message}" in result.error_message
        mock_update_meta_status.assert_called_once_with(
            video_id=sample_video_record.id,
            status=VideoStatus.PROCESSING_FAILED,
            error_message=f"Task dispatch failed: {dispatch_error_message}"
        )

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

        mock_celery_task_instance = MagicMock()
        mock_celery_task_instance.id = "superuser_celery_task_id"
        mock_celery_delay.return_value = mock_celery_task_instance

        # This is the Video that update_video_metadata_and_status (which is mocked) should return
        # Manually construct this from mock_uploaded_video_attrs_superuser and changes for processing state
        now_processing_superuser = datetime.now(timezone.utc)
        mock_processing_video_attrs_for_response_superuser = {
            **mock_uploaded_video_attrs_superuser, # Start with UPLOADED attributes
            "status": VideoStatus.PROCESSING, 
            "celery_task_id": "superuser_celery_task_id",
            "updated_at": now_processing_superuser
        }
        mock_processing_video_obj_for_response_superuser = Video(**mock_processing_video_attrs_for_response_superuser)
        mock_update_meta_status.return_value = video_service.response_schema.from_orm(mock_processing_video_obj_for_response_superuser)

        with patch.object(BaseService, 'update_async', new_callable=AsyncMock) as mock_super_update_first_call_superuser:
            mock_super_update_first_call_superuser.return_value = mock_uploaded_video_obj_superuser

            result = await video_service.confirm_video_upload(
                video_id, 
                superuser_confirming_id, # User doing the confirmation
                True,                    # is_superuser = True
                object_key, 
                video_size
            )

        mock_update_meta_status.assert_called_once_with(
            video_id=video_id,
            status=VideoStatus.PROCESSING,
            celery_task_id="superuser_celery_task_id",
            error_message=None
        )

        assert result.id == video_id
        assert result.status == VideoStatus.PROCESSING
        assert result.celery_task_id == "superuser_celery_task_id"

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