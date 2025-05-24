import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID
import os
import shutil

from backend.app.tasks.video_tasks import process_video_celery_task, get_app_settings
from backend.app.models.enums import VideoStatus, ExerciseType
from backend.app.core.config import Settings

# Mock settings early to avoid issues with global settings object
@pytest.fixture(autouse=True)
def mock_settings_early():
    # This fixture ensures that get_app_settings within the task module returns our mock
    # It's crucial for CELERY_SHARED_DATA_PATH
    mocked_settings = Settings(CELERY_SHARED_DATA_PATH="/tmp/celery_shared_test_data")
    with patch('backend.app.tasks.video_tasks.get_app_settings', return_value=mocked_settings):
        yield mocked_settings

@pytest.fixture
def patched_task_retry(mocker): # Using pytest-mock's mocker fixture
    # This fixture will mock the 'retry' method of the actual task object.
    # The side_effect will be raised when retry is called, allowing tests to catch it.
    # For tests that assert .assert_not_called(), this mock still works fine.
    return mocker.patch('backend.app.tasks.video_tasks.process_video_celery_task.retry',
                        side_effect=Exception("CeleryRetry"))

@pytest.fixture
def mock_celery_task_context(mock_settings_early):
    task = MagicMock()
    task.retry = MagicMock(side_effect=Exception("CeleryRetry")) # So we can assert it was called
    # Ensure CELERY_SHARED_DATA_PATH is set in the mocked settings
    task.app.conf = {'CELERY_SHARED_DATA_PATH': mock_settings_early.CELERY_SHARED_DATA_PATH}
    return task

@pytest.fixture
def mock_video_service():
    service = AsyncMock()
    service.set_video_status_from_task = AsyncMock()
    service.update_video_after_initial_processing = AsyncMock()
    return service

@pytest.fixture
def mock_storage_service():
    service = AsyncMock()
    service.download_file_bytes = AsyncMock(return_value=b"video_data")
    service.upload_file_from_path = AsyncMock()
    return service

@pytest.fixture
def mock_video_processing_service():
    service = AsyncMock()
    service.process_video = AsyncMock(return_value={
        "frame_paths": ["/tmp/frame1.jpg", "/tmp/frame2.jpg"],
        "normalized_video_path": "/tmp/normalized_video.mp4",
        "video_metadata": {
            "duration": 10.0,
            "fps": 30.0,
            "width": 1920,
            "height": 1080,
            "actual_frame_count": 300
        }
    })
    return service

@pytest.fixture
def mock_db_session():
    return AsyncMock() # Represents the async session from get_celery_db_session_context

@pytest.fixture
def mock_detect_pose_celery_task():
    mock_task = MagicMock()
    mock_task.apply_async = MagicMock()
    return mock_task

@pytest.fixture(autouse=True)
def setup_teardown_shared_data_dir(mock_settings_early):
    # Create the shared data directory before tests if it doesn't exist
    shared_path = mock_settings_early.CELERY_SHARED_DATA_PATH
    if not os.path.exists(shared_path):
        os.makedirs(shared_path, exist_ok=True)
    
    yield # Test runs here

    # Clean up the shared data directory after tests
    if os.path.exists(shared_path):
        shutil.rmtree(shared_path)

@pytest.mark.asyncio
async def test_process_video_celery_task_success_s3_path(
    mock_celery_task_context,
    mock_video_service,
    mock_storage_service,
    mock_video_processing_service,
    mock_db_session,
    mock_detect_pose_celery_task,
    mock_settings_early # Ensure settings fixture is used
):
    video_id = uuid4()
    s3_video_path = f"s3://bucket/videos/{video_id}.mp4"
    exercise_type = ExerciseType.SQUAT

    # Mock the context manager for the DB session
    mock_get_celery_db_session_context = MagicMock()
    mock_get_celery_db_session_context.__aenter__.return_value = mock_db_session
    mock_get_celery_db_session_context.__aexit__.return_value = None
    
    # Create a dummy normalized video file that the task expects to exist after processing
    # and before uploading. Also dummy frame files.
    # The task will create video_id specific subdirectories
    video_output_dir = os.path.join(mock_settings_early.CELERY_SHARED_DATA_PATH, "processed_frames", str(video_id))
    os.makedirs(video_output_dir, exist_ok=True)
    
    normalized_video_local_path = "/tmp/normalized_video.mp4" # This path is from mock_video_processing_service
    with open(normalized_video_local_path, "wb") as f:
        f.write(b"dummy_normalized_video_content")
    
    frame1_local_path = "/tmp/frame1.jpg"
    frame2_local_path = "/tmp/frame2.jpg"
    with open(frame1_local_path, "wb") as f:
        f.write(b"dummy_frame1_content")
    with open(frame2_local_path, "wb") as f:
        f.write(b"dummy_frame2_content")


    with patch('backend.app.tasks.video_tasks.VideoService', return_value=mock_video_service) as mock_VideoService_class, \
         patch('backend.app.tasks.video_tasks.StorageService', return_value=mock_storage_service) as mock_StorageService_class, \
         patch('backend.app.tasks.video_tasks.VideoProcessingService', return_value=mock_video_processing_service) as mock_VideoProcessingService_class, \
         patch('backend.app.tasks.video_tasks.get_celery_db_session_context', return_value=mock_get_celery_db_session_context), \
         patch('backend.app.tasks.video_tasks.detect_pose_celery_task', mock_detect_pose_celery_task), \
         patch('backend.app.tasks.video_tasks.os.path.exists', MagicMock(side_effect=lambda x: True if x in [normalized_video_local_path, frame1_local_path, frame2_local_path, video_output_dir] else os.path.exists(x))), \
         patch('backend.app.tasks.video_tasks.shutil.rmtree', MagicMock()) as mock_rmtree:

        result = await process_video_celery_task.run(
            str(video_id),
            s3_video_path,
            exercise_type.value
        )

        assert result["status"] == "success"
        assert result["video_id"] == str(video_id)
        assert "processed_video_s3_key" in result
        assert "processed_frames_s3_keys" in result
        assert len(result["processed_frames_s3_keys"]) == 2

        mock_storage_service.download_file_bytes.assert_called_once_with(s3_video_path)
        mock_video_processing_service.process_video.assert_called_once()
        
        # Check S3 uploads
        # Expected: 1 normalized video, 2 frames
        assert mock_storage_service.upload_file_from_path.call_count == 3 
        mock_storage_service.upload_file_from_path.assert_any_call(
            local_file_path=normalized_video_local_path,
            object_key=f"processed_videos/{video_id}/normalized_{os.path.basename(normalized_video_local_path)}"
        )
        mock_storage_service.upload_file_from_path.assert_any_call(
            local_file_path=frame1_local_path,
            object_key=f"processed_frames/{video_id}/{os.path.basename(frame1_local_path)}"
        )

        # Check VideoService calls
        mock_video_service.set_video_status_from_task.assert_any_call(UUID(str(video_id)), new_status=VideoStatus.PROCESSING)
        mock_video_service.update_video_after_initial_processing.assert_called_once_with(
            video_id=UUID(str(video_id)),
            processed_object_key=f"processed_videos/{video_id}/normalized_{os.path.basename(normalized_video_local_path)}",
            frame_s3_keys=[
                f"processed_frames/{video_id}/{os.path.basename(frame1_local_path)}",
                f"processed_frames/{video_id}/{os.path.basename(frame2_local_path)}"
            ],
            status=VideoStatus.POSE_DETECTION_PENDING,
            duration=10.0,
            fps=30.0,
            resolution="1920x1080",
            processed_frame_count=300
        )

        # Check AI task enqueue
        mock_detect_pose_celery_task.apply_async.assert_called_once_with(
            args=[str(video_id), [
                f"processed_frames/{video_id}/{os.path.basename(frame1_local_path)}",
                f"processed_frames/{video_id}/{os.path.basename(frame2_local_path)}"
            ]]
        )
        mock_rmtree.assert_called_once() # Ensure cleanup

    # Cleanup dummy files created for the test
    if os.path.exists(normalized_video_local_path): os.remove(normalized_video_local_path)
    if os.path.exists(frame1_local_path): os.remove(frame1_local_path)
    if os.path.exists(frame2_local_path): os.remove(frame2_local_path)
    # The setup_teardown_shared_data_dir fixture handles the video_output_dir and its parent

@pytest.mark.asyncio
async def test_process_video_celery_task_success_local_path(
    mock_celery_task_context,
    mock_video_service,
    mock_storage_service, # Still needed for uploads
    mock_video_processing_service,
    mock_db_session,
    mock_detect_pose_celery_task,
    mock_settings_early
):
    video_id = uuid4()
    # Create a dummy local video file
    local_video_dir = os.path.join(mock_settings_early.CELERY_SHARED_DATA_PATH, "original_videos_test")
    os.makedirs(local_video_dir, exist_ok=True)
    local_video_path = os.path.join(local_video_dir, f"{video_id}.mp4")
    with open(local_video_path, "wb") as f:
        f.write(b"original_video_data")
    
    exercise_type = ExerciseType.SQUAT

    mock_get_celery_db_session_context = MagicMock()
    mock_get_celery_db_session_context.__aenter__.return_value = mock_db_session
    mock_get_celery_db_session_context.__aexit__.return_value = None

    video_output_dir = os.path.join(mock_settings_early.CELERY_SHARED_DATA_PATH, "processed_frames", str(video_id))
    # os.makedirs(video_output_dir, exist_ok=True) # Task creates this

    normalized_video_local_path = "/tmp/normalized_video.mp4"
    with open(normalized_video_local_path, "wb") as f: f.write(b"dummy")
    frame1_local_path = "/tmp/frame1.jpg"
    with open(frame1_local_path, "wb") as f: f.write(b"dummy")
    frame2_local_path = "/tmp/frame2.jpg"
    with open(frame2_local_path, "wb") as f: f.write(b"dummy")

    # Mock os.path.exists to specifically handle the local_video_path
    def mock_os_path_exists_side_effect(path_to_check):
        if path_to_check == local_video_path:
            return True
        if path_to_check in [normalized_video_local_path, frame1_local_path, frame2_local_path, video_output_dir]: # from mock_vps
             return True
        return os.path.exists(path_to_check) # default to real os.path.exists for other paths (like shared_dir)

    with patch('backend.app.tasks.video_tasks.VideoService', return_value=mock_video_service), \
         patch('backend.app.tasks.video_tasks.StorageService', return_value=mock_storage_service), \
         patch('backend.app.tasks.video_tasks.VideoProcessingService', return_value=mock_video_processing_service), \
         patch('backend.app.tasks.video_tasks.get_celery_db_session_context', return_value=mock_get_celery_db_session_context), \
         patch('backend.app.tasks.video_tasks.detect_pose_celery_task', mock_detect_pose_celery_task), \
         patch('backend.app.tasks.video_tasks.os.path.exists', side_effect=mock_os_path_exists_side_effect), \
         patch('backend.app.tasks.video_tasks.shutil.rmtree') as mock_rmtree:

        result = await process_video_celery_task.run(
            str(video_id),
            local_video_path,
            exercise_type.value
        )
        assert result["status"] == "success"
        mock_storage_service.download_file_bytes.assert_not_called() # Should read from local path
        mock_video_processing_service.process_video.assert_called_once()
        # Further assertions similar to s3_path test for uploads, DB updates, AI task enqueue
        mock_video_service.update_video_after_initial_processing.assert_called_once()
        mock_detect_pose_celery_task.apply_async.assert_called_once()
        mock_rmtree.assert_called_once()

    if os.path.exists(local_video_path): os.remove(local_video_path)
    if os.path.exists(local_video_dir): shutil.rmtree(local_video_dir)
    if os.path.exists(normalized_video_local_path): os.remove(normalized_video_local_path)
    if os.path.exists(frame1_local_path): os.remove(frame1_local_path)
    if os.path.exists(frame2_local_path): os.remove(frame2_local_path)


@pytest.mark.asyncio
async def test_process_video_local_file_not_found(
    mock_celery_task_context, mock_video_service, mock_storage_service, mock_db_session, mock_settings_early, patched_task_retry
):
    video_id = uuid4()
    non_existent_local_path = "/tmp/this_video_does_not_exist.mp4"
    exercise_type = ExerciseType.SQUAT

    mock_get_celery_db_session_context = MagicMock()
    mock_get_celery_db_session_context.__aenter__.return_value = mock_db_session
    mock_get_celery_db_session_context.__aexit__.return_value = None

    with patch('backend.app.tasks.video_tasks.VideoService', return_value=mock_video_service), \
         patch('backend.app.tasks.video_tasks.StorageService', return_value=mock_storage_service), \
         patch('backend.app.tasks.video_tasks.get_celery_db_session_context', return_value=mock_get_celery_db_session_context), \
         patch('backend.app.tasks.video_tasks.os.path.exists', return_value=False): # Mock os.path.exists to always be False for this test

        result = await process_video_celery_task.run(
            str(video_id),
            non_existent_local_path,
            exercise_type.value
        )
        assert result["status"] == "failed"
        assert "Original video not found" in result["error"]
        mock_video_service.set_video_status_from_task.assert_any_call(UUID(str(video_id)), new_status=VideoStatus.PROCESSING) # Initial status set
        mock_video_service.set_video_status_from_task.assert_any_call(
            UUID(str(video_id)),
            new_status=VideoStatus.PROCESSING_FAILED,
            error_msg=f"Original video not found at {non_existent_local_path}"
        )
        patched_task_retry.assert_not_called() # Should not retry FileNotFoundError by default in task logic

@pytest.mark.asyncio
async def test_process_video_processing_service_fails(
    mock_celery_task_context, mock_video_service, mock_storage_service, mock_video_processing_service, mock_db_session, mock_settings_early, patched_task_retry
):
    video_id = uuid4()
    mock_video_processing_service.process_video = AsyncMock(side_effect=Exception("VPS Failure"))

    mock_get_celery_db_session_context = MagicMock()
    mock_get_celery_db_session_context.__aenter__.return_value = mock_db_session
    mock_get_celery_db_session_context.__aexit__.return_value = None

    with patch('backend.app.tasks.video_tasks.VideoService', return_value=mock_video_service), \
         patch('backend.app.tasks.video_tasks.StorageService', return_value=mock_storage_service), \
         patch('backend.app.tasks.video_tasks.VideoProcessingService', return_value=mock_video_processing_service), \
         patch('backend.app.tasks.video_tasks.get_celery_db_session_context', return_value=mock_get_celery_db_session_context), \
         patch('backend.app.tasks.video_tasks.os.path.exists', return_value=True): # Assume shared paths exist

        # Expect the task to retry due to the generic exception
        with pytest.raises(Exception, match="CeleryRetry"): # Matches the side_effect of patched_task_retry
             await process_video_celery_task.run(
                str(video_id),
                "s3://dummy/path.mp4",
                ExerciseType.SQUAT.value
            )

        mock_video_service.set_video_status_from_task.assert_any_call(UUID(str(video_id)), new_status=VideoStatus.PROCESSING)
        mock_video_service.set_video_status_from_task.assert_any_call(
            UUID(str(video_id)),
            new_status=VideoStatus.PROCESSING_FAILED,
            error_msg="VPS Failure"
        )
        patched_task_retry.assert_called_once()

@pytest.mark.asyncio
async def test_process_video_s3_upload_normalized_fails(
    mock_celery_task_context, mock_video_service, mock_storage_service, mock_video_processing_service, mock_db_session, mock_settings_early, patched_task_retry
):
    video_id = uuid4()
    mock_storage_service.upload_file_from_path = AsyncMock(side_effect=[Exception("S3 Upload Norm Fail"), AsyncMock()]) # Fail first upload

    normalized_video_local_path = "/tmp/normalized_video.mp4"
    with open(normalized_video_local_path, "wb") as f: f.write(b"dummy")
    frame1_local_path = "/tmp/frame1.jpg" # Need this to exist for the processing step
    with open(frame1_local_path, "wb") as f: f.write(b"dummy")
    frame2_local_path = "/tmp/frame2.jpg"
    with open(frame2_local_path, "wb") as f: f.write(b"dummy")
    
    video_output_dir = os.path.join(mock_settings_early.CELERY_SHARED_DATA_PATH, "processed_frames", str(video_id))


    mock_get_celery_db_session_context = MagicMock()
    mock_get_celery_db_session_context.__aenter__.return_value = mock_db_session
    mock_get_celery_db_session_context.__aexit__.return_value = None

    with patch('backend.app.tasks.video_tasks.VideoService', return_value=mock_video_service), \
         patch('backend.app.tasks.video_tasks.StorageService', return_value=mock_storage_service), \
         patch('backend.app.tasks.video_tasks.VideoProcessingService', return_value=mock_video_processing_service), \
         patch('backend.app.tasks.video_tasks.get_celery_db_session_context', return_value=mock_get_celery_db_session_context), \
         patch('backend.app.tasks.video_tasks.os.path.exists', MagicMock(side_effect=lambda x: True if x in [normalized_video_local_path, frame1_local_path, frame2_local_path, video_output_dir] else os.path.exists(x))):

        with pytest.raises(Exception, match="CeleryRetry"):
            await process_video_celery_task.run(
                str(video_id),
                "s3://dummy/path.mp4",
                ExerciseType.SQUAT.value
            )
        
        mock_video_service.set_video_status_from_task.assert_any_call(
            UUID(str(video_id)),
            new_status=VideoStatus.PROCESSING_FAILED,
            error_msg="CeleryRetry"
        )
        # Check that retry was called with the original S3 upload exception
        assert patched_task_retry.call_args_list  # Ensure retry was called
        first_retry_call_args = patched_task_retry.call_args_list[0]
        assert 'exc' in first_retry_call_args.kwargs
        assert str(first_retry_call_args.kwargs['exc']) == "S3 Upload Norm Fail"

    if os.path.exists(normalized_video_local_path): os.remove(normalized_video_local_path)
    if os.path.exists(frame1_local_path): os.remove(frame1_local_path)
    if os.path.exists(frame2_local_path): os.remove(frame2_local_path)

@pytest.mark.asyncio
async def test_process_video_s3_upload_frame_fails(
    mock_celery_task_context, mock_video_service, mock_storage_service, mock_video_processing_service, mock_db_session, mock_settings_early, patched_task_retry
):
    video_id = uuid4()
    # Fail on second upload (first frame)
    mock_storage_service.upload_file_from_path = AsyncMock(side_effect=[
        AsyncMock(), # Normalized video upload success
        Exception("S3 Upload Frame Fail"), # First frame upload fail
        AsyncMock() # Subsequent calls (if any)
    ])

    normalized_video_local_path = "/tmp/normalized_video.mp4"
    with open(normalized_video_local_path, "wb") as f: f.write(b"dummy")
    frame1_local_path = "/tmp/frame1.jpg" 
    with open(frame1_local_path, "wb") as f: f.write(b"dummy")
    frame2_local_path = "/tmp/frame2.jpg"
    with open(frame2_local_path, "wb") as f: f.write(b"dummy")
    video_output_dir = os.path.join(mock_settings_early.CELERY_SHARED_DATA_PATH, "processed_frames", str(video_id))


    mock_get_celery_db_session_context = MagicMock()
    mock_get_celery_db_session_context.__aenter__.return_value = mock_db_session
    mock_get_celery_db_session_context.__aexit__.return_value = None

    with patch('backend.app.tasks.video_tasks.VideoService', return_value=mock_video_service), \
         patch('backend.app.tasks.video_tasks.StorageService', return_value=mock_storage_service), \
         patch('backend.app.tasks.video_tasks.VideoProcessingService', return_value=mock_video_processing_service), \
         patch('backend.app.tasks.video_tasks.get_celery_db_session_context', return_value=mock_get_celery_db_session_context), \
         patch('backend.app.tasks.video_tasks.os.path.exists', MagicMock(side_effect=lambda x: True if x in [normalized_video_local_path, frame1_local_path, frame2_local_path, video_output_dir] else os.path.exists(x))):

        with pytest.raises(Exception, match="CeleryRetry"):
            await process_video_celery_task.run(
                str(video_id),
                "s3://dummy/path.mp4",
                ExerciseType.SQUAT.value
            )
        
        mock_video_service.set_video_status_from_task.assert_any_call(
            UUID(str(video_id)),
            new_status=VideoStatus.PROCESSING_FAILED,
            error_msg="CeleryRetry"
        )
        # Check that retry was called with the original S3 upload exception
        assert patched_task_retry.call_args_list  # Ensure retry was called
        first_retry_call_args = patched_task_retry.call_args_list[0]
        assert 'exc' in first_retry_call_args.kwargs
        assert str(first_retry_call_args.kwargs['exc']) == "S3 Upload Frame Fail"

    if os.path.exists(normalized_video_local_path): os.remove(normalized_video_local_path)
    if os.path.exists(frame1_local_path): os.remove(frame1_local_path)
    if os.path.exists(frame2_local_path): os.remove(frame2_local_path)


@pytest.mark.asyncio
async def test_process_video_missing_celery_shared_path_config(
    mock_celery_task_context, mock_video_service, mock_storage_service, mock_db_session, patched_task_retry
):
    video_id = uuid4()
    # Create a settings instance where CELERY_SHARED_DATA_PATH is None or empty
    # misconfigured_settings = Settings(CELERY_SHARED_DATA_PATH=None) # This will cause Pydantic validation error

    mock_misconfigured_settings = MagicMock(spec=Settings)
    mock_misconfigured_settings.CELERY_SHARED_DATA_PATH = None
    # For any other settings attributes that might be accessed, ensure they have default or mock values if needed.
    # Example: mock_misconfigured_settings.S3_BUCKET_NAME = "test-bucket"
    # However, based on the task logic, only CELERY_SHARED_DATA_PATH seems critical for this specific error path.


    mock_get_celery_db_session_context = MagicMock()
    mock_get_celery_db_session_context.__aenter__.return_value = mock_db_session
    mock_get_celery_db_session_context.__aexit__.return_value = None

    with patch('backend.app.tasks.video_tasks.get_app_settings', return_value=mock_misconfigured_settings), \
         patch('backend.app.tasks.video_tasks.VideoService', return_value=mock_video_service), \
         patch('backend.app.tasks.video_tasks.StorageService', return_value=mock_storage_service), \
         patch('backend.app.tasks.video_tasks.get_celery_db_session_context', return_value=mock_get_celery_db_session_context):

        result = await process_video_celery_task.run(
            str(video_id),
            "s3://dummy/path.mp4", # Path doesn't matter as it should fail before this
            ExerciseType.SQUAT.value
        )
        assert result["status"] == "failed"
        assert "CELERY_SHARED_DATA_PATH not configured" in result["error"]
        mock_video_service.set_video_status_from_task.assert_any_call(
            UUID(str(video_id)),
            new_status=VideoStatus.PROCESSING_FAILED,
            error_msg="Configuration error: CELERY_SHARED_DATA_PATH not configured."
        )
        patched_task_retry.assert_not_called() # Configuration error should not retry


@pytest.mark.asyncio
async def test_process_video_processing_returns_no_paths(
    mock_celery_task_context,
    mock_video_service,
    mock_storage_service,
    mock_video_processing_service, # Mock this to return empty/None paths
    mock_db_session,
    mock_settings_early,
    patched_task_retry
):
    video_id = uuid4()
    mock_video_processing_service.process_video = AsyncMock(return_value={ # Missing paths
        "video_metadata": {"duration": 5.0}
    })

    mock_get_celery_db_session_context = MagicMock()
    mock_get_celery_db_session_context.__aenter__.return_value = mock_db_session
    mock_get_celery_db_session_context.__aexit__.return_value = None

    with patch('backend.app.tasks.video_tasks.VideoService', return_value=mock_video_service), \
         patch('backend.app.tasks.video_tasks.StorageService', return_value=mock_storage_service), \
         patch('backend.app.tasks.video_tasks.VideoProcessingService', return_value=mock_video_processing_service), \
         patch('backend.app.tasks.video_tasks.get_celery_db_session_context', return_value=mock_get_celery_db_session_context), \
         patch('backend.app.tasks.video_tasks.os.path.exists', return_value=True):

        result = await process_video_celery_task.run(
            str(video_id),
            "s3://dummy/path.mp4",
            ExerciseType.SQUAT.value
        )
        assert result["status"] == "failed"
        assert "Missing frame_paths or normalized_video_path" in result["error"]
        mock_video_service.set_video_status_from_task.assert_any_call(
            UUID(str(video_id)),
            VideoStatus.VIDEO_PROCESSING_FAILED,
            error_msg="Internal error: Missing frame paths or normalized video path after processing."
        )
        patched_task_retry.assert_not_called()


@pytest.mark.asyncio
async def test_process_video_cleanup_failure_still_succeeds(
    mock_celery_task_context,
    mock_video_service,
    mock_storage_service,
    mock_video_processing_service,
    mock_db_session,
    mock_detect_pose_celery_task,
    mock_settings_early
):
    video_id = uuid4()
    s3_video_path = f"s3://bucket/videos/{video_id}.mp4"
    exercise_type = ExerciseType.SQUAT

    mock_get_celery_db_session_context = MagicMock()
    mock_get_celery_db_session_context.__aenter__.return_value = mock_db_session
    mock_get_celery_db_session_context.__aexit__.return_value = None
    
    video_output_dir = os.path.join(mock_settings_early.CELERY_SHARED_DATA_PATH, "processed_frames", str(video_id))
    os.makedirs(video_output_dir, exist_ok=True)
    normalized_video_local_path = "/tmp/normalized_video.mp4"
    with open(normalized_video_local_path, "wb") as f: f.write(b"dummy")
    frame1_local_path = "/tmp/frame1.jpg"
    with open(frame1_local_path, "wb") as f: f.write(b"dummy")
    frame2_local_path = "/tmp/frame2.jpg"
    with open(frame2_local_path, "wb") as f: f.write(b"dummy")

    with patch('backend.app.tasks.video_tasks.VideoService', return_value=mock_video_service), \
         patch('backend.app.tasks.video_tasks.StorageService', return_value=mock_storage_service), \
         patch('backend.app.tasks.video_tasks.VideoProcessingService', return_value=mock_video_processing_service), \
         patch('backend.app.tasks.video_tasks.get_celery_db_session_context', return_value=mock_get_celery_db_session_context), \
         patch('backend.app.tasks.video_tasks.detect_pose_celery_task', mock_detect_pose_celery_task), \
         patch('backend.app.tasks.video_tasks.os.path.exists', MagicMock(side_effect=lambda x: True if x in [normalized_video_local_path, frame1_local_path, frame2_local_path, video_output_dir] else os.path.exists(x))), \
         patch('backend.app.tasks.video_tasks.shutil.rmtree', MagicMock(side_effect=OSError("Cleanup failed"))) as mock_rmtree: # Mock cleanup to fail

        result = await process_video_celery_task.run(
            str(video_id),
            s3_video_path,
            exercise_type.value
        )
        # Task should still be considered successful overall as cleanup is non-critical
        assert result["status"] == "success" 
        mock_rmtree.assert_called_once()
        # All other success assertions should hold (DB updates, AI task enqueue etc.)
        mock_video_service.update_video_after_initial_processing.assert_called_once()
        mock_detect_pose_celery_task.apply_async.assert_called_once()

    if os.path.exists(normalized_video_local_path): os.remove(normalized_video_local_path)
    if os.path.exists(frame1_local_path): os.remove(frame1_local_path)
    if os.path.exists(frame2_local_path): os.remove(frame2_local_path)
    # shutil.rmtree(video_output_dir, ignore_errors=True) # Ensure test cleanup of this dir if it wasn't removed by task

# This comment is to ensure the last line is the one above, removing any trailing tags. 