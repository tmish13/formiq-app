import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from uuid6 import uuid7
import os
from uuid import UUID # Added for type hinting if needed, and for Video model

from app.models.video import Video
from app.models.enums import VideoStatus, ExerciseType
# Assuming process_video_celery_task is directly importable
from app.tasks.video_tasks import process_video_celery_task 
# For asserting DB state
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.video_processing import VideoProcessResult # For VideoProcessingService mock
from app.core.config import Settings # For mocking get_app_settings

# Placeholder for database session fixture - this would typically come from conftest.py
# For now, we'll assume it's injected if available or handle session creation/cleanup manually if needed for a single test.

@pytest.fixture
async def test_video_in_db(db_session: AsyncSession) -> Video:
    """Creates a sample video object in the database for testing."""
    video = Video(
        id=uuid7(),
        user_id=uuid7(), # Example user_id
        filename="sample_video.mp4", # Added filename for completeness
        object_key="test_raw_videos/sample_video.mp4",
        status=VideoStatus.UPLOADED,
        exercise_type=ExerciseType.SQUAT,
        mime_type="video/mp4"  # Added mime_type
    )
    db_session.add(video)
    await db_session.commit()
    await db_session.refresh(video)
    return video

@pytest.mark.asyncio
@patch('app.tasks.video_tasks.get_app_settings')
@patch('app.tasks.video_tasks.StorageService')
@patch('app.tasks.video_tasks.VideoProcessingService')
@patch('app.tasks.video_tasks.detect_pose_celery_task.apply_async') # Direct patch for apply_async
@patch('app.tasks.video_tasks.os.path.exists') # Mock os.path.exists
@patch('app.tasks.video_tasks.os.makedirs')    # Mock os.makedirs
async def test_process_video_celery_task_successful_flow(
    mock_os_makedirs: MagicMock,
    mock_os_path_exists: MagicMock,
    mock_detect_pose_apply_async: MagicMock,
    MockVideoProcessingService: MagicMock, # Class mock
    MockStorageService: MagicMock,         # Class mock
    mock_get_app_settings: MagicMock,
    db_session: AsyncSession,
    test_video_in_db: Video,
):
    """
    Test the successful E2E flow of process_video_celery_task:
    - Fetches Video object.
    - Calls VideoProcessingService.process_video.
    - Calls VideoService methods to update status.
    - Enqueues detect_pose_celery_task.
    - Updates Video record in DB with results and final status.
    """
    video_id = test_video_in_db.id
    original_s3_path = f"s3://{test_video_in_db.s3_bucket}/{test_video_in_db.s3_key}"

    # ARRANGE
    # 1. Mock settings
    mock_settings = Settings(CELERY_SHARED_DATA_PATH="/tmp/celery_shared_test") # Example path
    mock_get_app_settings.return_value = mock_settings

    # 2. Mock os.path.exists and os.makedirs for shared data path
    mock_os_path_exists.return_value = False # Simulate directory doesn't exist initially
    mock_os_makedirs.return_value = None

    # 3. Mock StorageService instance and its download_file_bytes method
    mock_storage_service_instance = MockStorageService.return_value
    mock_storage_service_instance.download_file_bytes = AsyncMock(return_value=b"mock video content")

    # 4. Mock VideoProcessingService instance and its process_video method
    #    The task expects a dictionary result from process_video.
    mock_vps_instance = MockVideoProcessingService.return_value
    mock_processed_frame_s3_keys = [f"processed_frames/{video_id}/frame1.jpg", f"processed_frames/{video_id}/frame2.jpg"]
    mock_normalized_video_s3_key = f"normalized_videos/{video_id}/normalized.mp4"
    mock_frame_count = 2
    mock_video_duration = 5.5
    mock_fps = 30.0
    mock_video_dimensions = (1920, 1080) # width, height

    mock_process_video_dict_result = {
        "frame_paths": mock_processed_frame_s3_keys, # These are expected to be S3 keys by VideoService
        "normalized_video_path": mock_normalized_video_s3_key, # Expected to be an S3 key by VideoService
        "raw_video_path": "/tmp/celery_shared_test/some_raw_video.mp4",
        "processed_frame_count": mock_frame_count,
        "video_duration": mock_video_duration,
        "fps": mock_fps,
        "video_dimensions": mock_video_dimensions,
        "errors": None
    }
    mock_vps_instance.process_video = AsyncMock(return_value=mock_process_video_dict_result)

    # 5. `detect_pose_celery_task.apply_async` is already patched by decorator.

    # 6. Mock 'self' for the bound Celery task
    mock_celery_task_self = MagicMock()

    # ACT: Execute the Celery task directly.
    task_result = await process_video_celery_task(
        mock_celery_task_self, # Bound task 'self'
        video_id_str=str(video_id),
        original_video_path=original_s3_path, 
        exercise_type_value=test_video_in_db.exercise_type.value
    )

    # ASSERT
    # 0. Task result
    assert task_result["status"] == "success"
    assert task_result["video_id"] == str(video_id)

    # 1. Settings and OS path checks
    mock_get_app_settings.assert_called_once()
    expected_output_dir = os.path.join(mock_settings.CELERY_SHARED_DATA_PATH, "processed_frames", str(video_id))
    mock_os_path_exists.assert_called_once_with(expected_output_dir)
    mock_os_makedirs.assert_called_once_with(expected_output_dir, exist_ok=True)

    # 2. StorageService assertions
    MockStorageService.assert_called_once_with(settings=mock_settings)
    mock_storage_service_instance.download_file_bytes.assert_called_once_with(original_s3_path)

    # 3. VideoProcessingService assertions
    MockVideoProcessingService.assert_called_once_with(app_settings=mock_settings)
    mock_vps_instance.process_video.assert_called_once_with(
        video_data=b"mock video content",
        exercise_type=test_video_in_db.exercise_type,
        save_processed_frames=True,
        base_output_path=expected_output_dir
    )

    # 4. Database state assertions (VideoService calls are real, check their effect)
    await db_session.refresh(test_video_in_db) 
    
    assert test_video_in_db.status == VideoStatus.POSE_DETECTION_PENDING # Final status
    assert test_video_in_db.processed_object_key == mock_normalized_video_s3_key # This was added in a migration
    assert test_video_in_db.frame_s3_keys == mock_processed_frame_s3_keys # Corrected field name
    assert test_video_in_db.processed_frame_count == mock_frame_count
    assert test_video_in_db.duration == mock_video_duration
    assert test_video_in_db.fps == mock_fps
    assert test_video_in_db.resolution == f"{mock_video_dimensions[0]}x{mock_video_dimensions[1]}"
    assert test_video_in_db.processing_errors is None
    print("NOTE: DB assertions for frame_count, duration, fps, width, height need to be confirmed against actual Video model fields.")


    # 5. detect_pose_celery_task.apply_async assertions
    mock_detect_pose_apply_async.assert_called_once_with(
        args=[str(video_id), mock_processed_frame_s3_keys]
        # Add ,countdown=X if there's a specific delay used in the task
    )

    # TODO: Add test for VideoProcessingService failure (e.g., process_video raises error)
    # TODO: Add test for S3 download failure
    # TODO: Add test for local file not found (if original_video_path is local)
    # TODO: Add test for CELERY_SHARED_DATA_PATH not configured
    pass

    # Add more tests:
    # - Test case where VideoProcessingService.process_video raises an exception
    # - Test case where Video object is not found
    pass # Placeholder for more tests 

@pytest.mark.asyncio
@patch('app.tasks.video_tasks.get_app_settings')
@patch('app.tasks.video_tasks.StorageService')
@patch('app.tasks.video_tasks.VideoProcessingService')
@patch('app.tasks.video_tasks.detect_pose_celery_task.apply_async') # To assert it's NOT called
@patch('app.tasks.video_tasks.os.path.exists')
@patch('app.tasks.video_tasks.os.makedirs')
async def test_process_video_celery_task_vps_failure(
    mock_os_makedirs: MagicMock,
    mock_os_path_exists: MagicMock,
    mock_detect_pose_apply_async: MagicMock,
    MockVideoProcessingService: MagicMock,
    MockStorageService: MagicMock,
    mock_get_app_settings: MagicMock,
    db_session: AsyncSession,
    test_video_in_db: Video,
):
    video_id = test_video_in_db.id
    original_s3_path = f"s3://{test_video_in_db.s3_bucket}/{test_video_in_db.s3_key}"
    simulated_error_message = "Simulated video processing error from VPS"

    # ARRANGE
    mock_settings = Settings(CELERY_SHARED_DATA_PATH="/tmp/celery_shared_test_vps_fail")
    mock_get_app_settings.return_value = mock_settings

    mock_os_path_exists.return_value = False 
    mock_os_makedirs.return_value = None

    mock_storage_service_instance = MockStorageService.return_value
    mock_storage_service_instance.download_file_bytes = AsyncMock(return_value=b"mock video content")

    mock_vps_instance = MockVideoProcessingService.return_value
    mock_vps_instance.process_video = AsyncMock(side_effect=RuntimeError(simulated_error_message))

    # Mock 'self' for the bound Celery task and its retry method to prevent actual retries
    mock_celery_task_self = MagicMock()
    # When self.retry is called, we want it to just re-raise the exception 
    # so the test can assert the task's overall exception handling if desired,
    # or simply to stop the retry chain for this test unit.
    # For this test, we primarily care about DB state *before* retry logic fully unwinds.
    # The task code catches Exception, logs, updates status, then calls self.retry.
    # So the DB changes should happen before self.retry is an issue for this test.
    # We will assert the task_result which shows what it returned before raising for retry.
    mock_celery_task_self.retry = MagicMock(side_effect=lambda exc: exec("raise exc")) 

    # ACT
    # The task will catch the RuntimeError, log, update status, and then attempt to retry (which we mock).
    # We expect the task to return a dict indicating failure *before* re-raising for retry.
    # If task_always_eager is True, the retry might happen immediately and re-raise.
    # Let's catch the exception that would be raised by self.retry.
    with pytest.raises(RuntimeError, match=simulated_error_message):
        await process_video_celery_task(
            mock_celery_task_self,
            video_id_str=str(video_id),
            original_video_path=original_s3_path, 
            exercise_type_value=test_video_in_db.exercise_type.value
        )
    
    # Task result check is tricky if it re-raises. Let's verify DB state and mocks.
    # The task code updates DB *before* calling self.retry().

    # ASSERT
    # Check that essential setup mocks were called
    expected_output_dir = os.path.join(mock_settings.CELERY_SHARED_DATA_PATH, "processed_frames", str(video_id))
    mock_os_path_exists.assert_called_once_with(expected_output_dir)
    # mock_os_makedirs might not be called if error happens before its check in VPS, or it might.
    # For this test, process_video is mocked to fail, so dir creation inside VPS is not an issue.
    # The task itself creates it. So it should be called.
    mock_os_makedirs.assert_called_once_with(expected_output_dir, exist_ok=True) 

    mock_storage_service_instance.download_file_bytes.assert_called_once_with(original_s3_path)
    mock_vps_instance.process_video.assert_called_once() # Called, but raised an error

    # Database state assertions: VideoService calls are real
    await db_session.refresh(test_video_in_db)
    assert test_video_in_db.status == VideoStatus.PROCESSING_FAILED 
    assert isinstance(test_video_in_db.processing_errors, str) # As per task logic
    assert simulated_error_message in test_video_in_db.processing_errors

    # Crucially, the next task should NOT have been enqueued
    mock_detect_pose_apply_async.assert_not_called()
    pass 

@pytest.mark.asyncio
@patch('app.tasks.video_tasks.get_app_settings')
@patch('app.tasks.video_tasks.StorageService')
@patch('app.tasks.video_tasks.VideoProcessingService')
@patch('app.tasks.video_tasks.detect_pose_celery_task.apply_async') # To assert it's NOT called
@patch('app.tasks.video_tasks.os.path.exists') # May not be called if StorageService fails early
@patch('app.tasks.video_tasks.os.makedirs')    # May not be called
async def test_process_video_celery_task_s3_download_failure(
    mock_os_makedirs: MagicMock,
    mock_os_path_exists: MagicMock,
    mock_detect_pose_apply_async: MagicMock,
    MockVideoProcessingService: MagicMock,
    MockStorageService: MagicMock,
    mock_get_app_settings: MagicMock,
    db_session: AsyncSession,
    test_video_in_db: Video,
):
    video_id = test_video_in_db.id
    original_s3_path = f"s3://{test_video_in_db.s3_bucket}/{test_video_in_db.s3_key}"
    simulated_error_message = "Simulated S3 download error"

    # ARRANGE
    mock_settings = Settings(CELERY_SHARED_DATA_PATH="/tmp/celery_shared_s3_fail") # Different path for clarity
    mock_get_app_settings.return_value = mock_settings

    # StorageService.download_file_bytes raises an error
    mock_storage_service_instance = MockStorageService.return_value
    mock_storage_service_instance.download_file_bytes = AsyncMock(side_effect=RuntimeError(simulated_error_message))

    mock_vps_instance = MockVideoProcessingService.return_value # Get instance for assertion

    mock_celery_task_self = MagicMock()
    mock_celery_task_self.retry = MagicMock(side_effect=lambda exc: exec("raise exc"))

    # ACT & ASSERT for exception from task
    with pytest.raises(RuntimeError, match=simulated_error_message):
        await process_video_celery_task(
            mock_celery_task_self,
            video_id_str=str(video_id),
            original_video_path=original_s3_path, 
            exercise_type_value=test_video_in_db.exercise_type.value
        )

    # ASSERT MOCKS & DB
    MockStorageService.assert_called_once_with(settings=mock_settings)
    mock_storage_service_instance.download_file_bytes.assert_called_once_with(original_s3_path)
    
    # These should not have been called if download fails before they are used
    mock_os_path_exists.assert_not_called() # Or called if path check happens before download
                                            # Based on current task, path ops are after download if path isn't S3
                                            # but for S3 download, path ops (for output_dir) are after download.
                                            # For safety, let's assume it might be called if settings are accessed, but we can refine.
                                            # Actually, the output_dir logic is separate from input video_data fetching. So it will be called.
    expected_output_dir = os.path.join(mock_settings.CELERY_SHARED_DATA_PATH, "processed_frames", str(video_id))
    mock_os_path_exists.assert_called_once_with(expected_output_dir) # This check happens before VPS
    mock_os_makedirs.assert_called_once_with(expected_output_dir, exist_ok=True)

    MockVideoProcessingService.assert_not_called() # VPS class itself should not be instantiated if download fails
                                                   # Correction: VPS is instantiated. process_video is not called.
    MockVideoProcessingService.assert_called_once_with(app_settings=mock_settings)
    mock_vps_instance.process_video.assert_not_called()
    mock_detect_pose_apply_async.assert_not_called()

    await db_session.refresh(test_video_in_db)
    assert test_video_in_db.status == VideoStatus.PROCESSING_FAILED
    assert isinstance(test_video_in_db.processing_errors, str)
    assert simulated_error_message in test_video_in_db.processing_errors
    pass 

@pytest.mark.asyncio
@patch('app.tasks.video_tasks.get_app_settings')
@patch('app.tasks.video_tasks.StorageService')
@patch('app.tasks.video_tasks.VideoProcessingService')
@patch('app.tasks.video_tasks.detect_pose_celery_task.apply_async')
@patch('app.tasks.video_tasks.os.path.exists') 
@patch('app.tasks.video_tasks.os.makedirs')   
async def test_process_video_celery_task_local_file_not_found(
    mock_os_makedirs: MagicMock,
    mock_os_path_exists: MagicMock, # This is the main mock we control for local path
    mock_detect_pose_apply_async: MagicMock,
    MockVideoProcessingService: MagicMock,
    MockStorageService: MagicMock,
    mock_get_app_settings: MagicMock,
    db_session: AsyncSession,
    test_video_in_db: Video,
):
    video_id = test_video_in_db.id
    local_video_path = "/tmp/non_existent_local_video.mp4"
    expected_error_message = f"Original video not found at {local_video_path}" # Exact message from task

    # ARRANGE
    mock_settings = Settings(CELERY_SHARED_DATA_PATH="/tmp/celery_shared_local_fnf")
    mock_get_app_settings.return_value = mock_settings

    # For local path, task first checks os.path.exists for the *input* path
    # Then it checks for the *output* path (processed_frames_output_dir)
    def os_path_exists_side_effect(path_arg):
        if path_arg == local_video_path:
            return False # Simulate input local video file does not exist
        # For the output directory, let's assume it also doesn't exist initially to allow makedirs to be called
        elif path_arg == os.path.join(mock_settings.CELERY_SHARED_DATA_PATH, "processed_frames", str(video_id)):
            return False 
        return True # Default for any other unexpected path checks
    mock_os_path_exists.side_effect = os_path_exists_side_effect
    mock_os_makedirs.return_value = None # Allow this to be called for output_dir

    mock_storage_service_instance = MockStorageService.return_value
    mock_vps_instance = MockVideoProcessingService.return_value

    mock_celery_task_self = MagicMock()
    # The task catches FileNotFoundError and returns a dict, doesn't call self.retry by default for this.

    # ACT
    task_result = await process_video_celery_task(
        mock_celery_task_self,
        video_id_str=str(video_id),
        original_video_path=local_video_path, # Using local path
        exercise_type_value=test_video_in_db.exercise_type.value
    )

    # ASSERT: Task should return a failure dict for FileNotFoundError
    assert task_result["status"] == "failed"
    assert task_result["video_id"] == str(video_id)
    assert expected_error_message in task_result["error"]

    # MOCKS & DB
    # StorageService S3 download method should not be called for local paths
    mock_storage_service_instance.download_file_bytes.assert_not_called()

    # os.path.exists should have been called for the input local_video_path and output dir
    expected_output_dir = os.path.join(mock_settings.CELERY_SHARED_DATA_PATH, "processed_frames", str(video_id))
    mock_os_path_exists.assert_any_call(local_video_path)
    mock_os_path_exists.assert_any_call(expected_output_dir)
    mock_os_makedirs.assert_called_once_with(expected_output_dir, exist_ok=True)

    # VideoProcessingService and next task should not be called
    mock_vps_instance.process_video.assert_not_called()
    mock_detect_pose_apply_async.assert_not_called()

    await db_session.refresh(test_video_in_db)
    assert test_video_in_db.status == VideoStatus.PROCESSING_FAILED
    assert isinstance(test_video_in_db.processing_errors, str)
    assert expected_error_message in test_video_in_db.processing_errors
    pass

@pytest.mark.asyncio
@patch('app.tasks.video_tasks.get_app_settings')
@patch('app.tasks.video_tasks.StorageService')
@patch('app.tasks.video_tasks.VideoProcessingService')
@patch('app.tasks.video_tasks.detect_pose_celery_task.apply_async')
@patch('app.tasks.video_tasks.os.path.exists') 
@patch('app.tasks.video_tasks.os.makedirs')   
async def test_process_video_celery_task_missing_shared_path_config(
    mock_os_makedirs: MagicMock, # Will not be called if config check fails first
    mock_os_path_exists: MagicMock, # Will not be called
    mock_detect_pose_apply_async: MagicMock,
    MockVideoProcessingService: MagicMock,
    MockStorageService: MagicMock,
    mock_get_app_settings: MagicMock,
    db_session: AsyncSession,
    test_video_in_db: Video,
):
    video_id = test_video_in_db.id
    original_s3_path = f"s3://{test_video_in_db.s3_bucket}/{test_video_in_db.s3_key}"
    expected_error_message = "CELERY_SHARED_DATA_PATH not configured." # Exact message from task

    # ARRANGE
    # Mock settings to have an invalid/missing CELERY_SHARED_DATA_PATH
    mock_settings = Settings(CELERY_SHARED_DATA_PATH=None) # Or "" (empty string)
    mock_get_app_settings.return_value = mock_settings

    mock_storage_service_instance = MockStorageService.return_value
    # Assume download happens before the shared path check, so mock it successfully
    mock_storage_service_instance.download_file_bytes = AsyncMock(return_value=b"mock video content")
    
    mock_vps_instance = MockVideoProcessingService.return_value

    mock_celery_task_self = MagicMock()
    mock_celery_task_self.retry = MagicMock(side_effect=lambda exc: exec("raise exc"))

    # ACT & ASSERT for exception from task
    with pytest.raises(ValueError, match=expected_error_message):
        await process_video_celery_task(
            mock_celery_task_self,
            video_id_str=str(video_id),
            original_video_path=original_s3_path, 
            exercise_type_value=test_video_in_db.exercise_type.value
        )

    # ASSERT MOCKS & DB
    # StorageService download might still be called if it occurs before the config check
    # Based on task logic: download -> CELERY_SHARED_DATA_PATH check. So download is called.
    MockStorageService.assert_called_once_with(settings=mock_settings)
    mock_storage_service_instance.download_file_bytes.assert_called_once_with(original_s3_path)
    
    # These OS path operations related to the shared path should NOT be called if the path itself is invalid/missing.
    # The task raises ValueError *before* attempting to use it with os.path or os.makedirs.
    mock_os_path_exists.assert_not_called()
    mock_os_makedirs.assert_not_called()

    # VideoProcessingService and next task should not be called
    MockVideoProcessingService.assert_not_called() # Not even instantiated if config check fails
                                                   # Correction: VPS is instantiated just *before* process_video call, which is after shared_path check
                                                   # So if shared_path check fails, VPS is NOT instantiated.
    mock_vps_instance.process_video.assert_not_called()
    mock_detect_pose_apply_async.assert_not_called()

    await db_session.refresh(test_video_in_db)
    assert test_video_in_db.status == VideoStatus.PROCESSING_FAILED
    assert isinstance(test_video_in_db.processing_errors, str)
    assert expected_error_message in test_video_in_db.processing_errors
    pass

@pytest.mark.asyncio
@patch('app.tasks.video_tasks.get_app_settings')
@patch('app.tasks.video_tasks.StorageService')
@patch('app.tasks.video_tasks.VideoProcessingService')
@patch('app.tasks.video_tasks.detect_pose_celery_task.apply_async')
@patch('app.tasks.video_tasks.os.path.exists')
@patch('app.tasks.video_tasks.os.makedirs')
async def test_process_video_celery_task_vps_incomplete_result(
    mock_os_makedirs: MagicMock,
    mock_os_path_exists: MagicMock,
    mock_detect_pose_apply_async: MagicMock,
    MockVideoProcessingService: MagicMock,
    MockStorageService: MagicMock,
    mock_get_app_settings: MagicMock,
    db_session: AsyncSession,
    test_video_in_db: Video,
):
    video_id = test_video_in_db.id
    original_s3_path = f"s3://{test_video_in_db.s3_bucket}/{test_video_in_db.s3_key}"
    # Error message from the task when result is incomplete
    expected_error_message = "Internal error: Missing frame paths or normalized video path after processing."

    # ARRANGE
    mock_settings = Settings(CELERY_SHARED_DATA_PATH="/tmp/celery_shared_incomplete")
    mock_get_app_settings.return_value = mock_settings

    mock_os_path_exists.return_value = False
    mock_os_makedirs.return_value = None

    mock_storage_service_instance = MockStorageService.return_value
    mock_storage_service_instance.download_file_bytes = AsyncMock(return_value=b"mock video content")

    mock_vps_instance = MockVideoProcessingService.return_value
    # Simulate VPS result missing 'frame_paths' (or could be 'normalized_video_path')
    mock_incomplete_process_video_result = {
        # "frame_paths": ["some/path/frame1.jpg"], # Intentionally missing or None
        "normalized_video_path": f"normalized_videos/{video_id}/normalized.mp4",
        "raw_video_path": "/tmp/celery_shared_incomplete/some_raw_video.mp4",
        "processed_frame_count": 0, # Or some value, doesn't matter much if paths are missing
        "video_duration": 5.0,
        "fps": 30.0,
        "video_dimensions": (1280, 720),
        "errors": None
    }
    mock_vps_instance.process_video = AsyncMock(return_value=mock_incomplete_process_video_result)

    mock_celery_task_self = MagicMock() # Not a bound task that retries for this path

    # ACT
    task_result = await process_video_celery_task(
        mock_celery_task_self, # self is passed for bound tasks, but not strictly needed if .retry isn't called
        video_id_str=str(video_id),
        original_video_path=original_s3_path, 
        exercise_type_value=test_video_in_db.exercise_type.value
    )

    # ASSERT: Task should return a specific failure dict for this case
    assert task_result["status"] == "failed"
    assert task_result["video_id"] == str(video_id)
    # The error in the returned dict is slightly different from the one logged to DB processing_errors
    assert "Missing frame_paths or normalized_video_path" in task_result["error"]

    # MOCKS & DB
    # Essential setup mocks should have been called
    expected_output_dir = os.path.join(mock_settings.CELERY_SHARED_DATA_PATH, "processed_frames", str(video_id))
    mock_os_path_exists.assert_called_once_with(expected_output_dir)
    mock_os_makedirs.assert_called_once_with(expected_output_dir, exist_ok=True)
    mock_storage_service_instance.download_file_bytes.assert_called_once_with(original_s3_path)
    mock_vps_instance.process_video.assert_called_once() # Called, but returned incomplete data

    # Next task should NOT have been enqueued
    mock_detect_pose_apply_async.assert_not_called()

    await db_session.refresh(test_video_in_db)
    assert test_video_in_db.status == VideoStatus.VIDEO_PROCESSING_FAILED # Specific status for this error
    assert isinstance(test_video_in_db.processing_errors, str)
    assert expected_error_message in test_video_in_db.processing_errors
    pass

@pytest.mark.asyncio
@patch('app.tasks.video_tasks.get_app_settings')
@patch('app.tasks.video_tasks.StorageService')
@patch('app.tasks.video_tasks.VideoProcessingService')
@patch('app.tasks.video_tasks.detect_pose_celery_task.apply_async')
@patch('app.tasks.video_tasks.os.path.exists')
@patch('app.tasks.video_tasks.os.makedirs')
async def test_process_video_celery_task_video_not_found(
    mock_os_makedirs: MagicMock, 
    mock_os_path_exists: MagicMock, 
    mock_detect_pose_apply_async: MagicMock,
    MockVideoProcessingService: MagicMock,
    MockStorageService: MagicMock,         
    mock_get_app_settings: MagicMock,
    db_session: AsyncSession, # db_session is used by the task via get_celery_db_session_context
    # test_video_in_db is NOT used here as we want to test a non-existent ID
):
    non_existent_video_id = uuid7()
    original_s3_path = f"s3://some-bucket/some_key.mp4" # Path doesn't matter much as DB call fails first
    simulated_db_error_message = f"Video with ID {non_existent_video_id} not found in DB during status update."

    # ARRANGE
    mock_settings = Settings(CELERY_SHARED_DATA_PATH="/tmp/celery_shared_video_nf")
    mock_get_app_settings.return_value = mock_settings

    # We need to mock VideoService instantiation or its method that fails.
    # The task instantiates VideoService: `video_service_instance = VideoService(...)`
    # Then calls `await video_service_instance.set_video_status_from_task(video_id, ...)`
    # Let's mock `set_video_status_from_task` on the VideoService class prototype used by the task.
    # This is a bit tricky because VideoService is instantiated inside the task.
    # A cleaner way might be to ensure the DB state causes the failure.
    # For this test, we'll assume that attempting to update a non-existent video via VideoService
    # will lead to an exception that the task's main try-except block catches.
    # The task will then log it and call self.retry. The actual exception might be from SQLAlchemy (e.g. NoResultFound transformed)
    # or a custom one from VideoService.
    # Let's assume VideoService.set_video_status_from_task itself raises an error if video not found.

    # To simulate VideoService failing to find the video, we can patch the VideoService
    # constructor or the specific method. Patching the method `set_video_status_from_task` is more direct.
    # However, VideoService is instantiated *inside* the task. 
    # The most robust way is to ensure the DB state causes the failure.
    # Since `non_existent_video_id` is not in `db_session`, the call within `set_video_status_from_task`
    # to fetch and update the video *should* fail naturally (e.g. raise NoResultFound or similar, which then gets caught).
    # The task code catches `Exception as e` and uses `str(e)` for the error message.
    
    # For the purpose of this test, we can let the DB interaction within VideoService naturally fail.
    # The specific error message might be generic like "No row was found for one()" from SQLAlchemy
    # if `set_video_status_from_task` uses something like `session.get_one()` or `query.one()`.
    # Let's expect a general Exception and that the task logs *something* related to the failure.
    # The task *itself* doesn't write to processing_errors for a video that it can't find to update.
    # It logs and retries. This test is about ensuring it handles such an early failure gracefully (i.e., doesn't crash without logging).

    mock_celery_task_self = MagicMock()
    # This will be the exception from the DB/VideoService layer if video is not found.
    # Let's simulate that the first DB interaction (set_video_status_from_task) fails.
    # We can achieve this by patching VideoService and making its method raise an error.
    
    with patch('app.tasks.video_tasks.VideoService') as MockVideoServiceForNotFound:
        mock_vs_instance_nf = MockVideoServiceForNotFound.return_value
        # Simulate the first call to set_video_status_from_task raising an error
        db_lookup_exception = Exception(simulated_db_error_message) # Generic exception for now
        mock_vs_instance_nf.set_video_status_from_task = AsyncMock(side_effect=db_lookup_exception)
        mock_celery_task_self.retry = MagicMock(side_effect=lambda exc: exec("raise exc"))

        # ACT & ASSERT for exception from task
        with pytest.raises(Exception, match=simulated_db_error_message):
            await process_video_celery_task.run( # Call .run() directly
                mock_celery_task_self, # self as first positional arg
                video_id_str=str(non_existent_video_id),
                original_video_path=original_s3_path,
                exercise_type_value=ExerciseType.SQUAT.value # Some valid exercise type
            )

    # ASSERT MOCKS 
    # VideoService was instantiated, and set_video_status_from_task was called
    MockVideoServiceForNotFound.assert_called_once()
    mock_vs_instance_nf.set_video_status_from_task.assert_called_once_with(
        UUID(str(non_existent_video_id)), # Ensure it's called with the UUID object
        new_status=VideoStatus.PROCESSING
    )
    
    # None of the subsequent operations should occur
    MockStorageService.return_value.download_file_bytes.assert_not_called()
    mock_os_path_exists.assert_not_called()
    mock_os_makedirs.assert_not_called()
    MockVideoProcessingService.return_value.process_video.assert_not_called()
    mock_detect_pose_apply_async.assert_not_called()
    pass

@pytest.mark.asyncio
@patch('app.tasks.video_tasks.get_app_settings')
@patch('app.tasks.video_tasks.StorageService')
@patch('app.tasks.video_tasks.VideoProcessingService')
@patch('app.tasks.video_tasks.detect_pose_celery_task.apply_async')
@patch('app.tasks.video_tasks.os.path.exists')
@patch('app.tasks.video_tasks.os.makedirs')
async def test_process_video_celery_task_retry_and_succeed( 
    mock_os_makedirs: MagicMock,
    mock_os_path_exists: MagicMock,
    mock_detect_pose_apply_async: MagicMock,
    MockVideoProcessingService: MagicMock, 
    MockStorageService: MagicMock,
    mock_get_app_settings: MagicMock,
    db_session: AsyncSession,
    test_video_in_db: Video,
): 
    """Test process_video_celery_task retries on a transient error and then succeeds."""
    video_id = test_video_in_db.id
    original_s3_path = f"s3://{test_video_in_db.s3_bucket}/{test_video_in_db.s3_key}"
    transient_error_message = "Simulated transient VPS error"

    # ARRANGE
    mock_settings = Settings(CELERY_SHARED_DATA_PATH="/tmp/celery_shared_retry")
    mock_get_app_settings.return_value = mock_settings

    mock_os_path_exists.return_value = True # Assume output dir exists for simplicity here
    mock_os_makedirs.return_value = None

    mock_storage_service_instance = MockStorageService.return_value
    mock_storage_service_instance.download_file_bytes = AsyncMock(return_value=b"mock video content retry")

    # Mock VideoProcessingService to fail once, then succeed
    mock_vps_instance = MockVideoProcessingService.return_value
    successful_vps_result = {
        "frame_paths": [f"processed_frames/{video_id}/retry_frame.jpg"],
        "normalized_video_path": f"normalized_videos/{video_id}/retry_normalized.mp4",
        "raw_video_path": "/tmp/celery_shared_retry/raw.mp4",
        "processed_frame_count": 1,
        "video_duration": 1.0,
        "fps": 30.0,
        "video_dimensions": (640, 360),
        "errors": None
    }
    mock_vps_instance.process_video.side_effect = [
        RuntimeError(transient_error_message), # First call: fail with transient error
        successful_vps_result                 # Second call (retry): succeed
    ]

    # Mock Celery task's 'self' and its retry method
    # We need to allow the first call to self.retry to proceed as Celery would,
    # then the task should be re-executed by the testing framework (e.g. if task_always_eager).
    # For unit/integration testing without full Celery worker, we simulate the retry call.
    mock_celery_task_self = MagicMock()
    
    # Store the exception that self.retry would be called with
    retry_exception_holder = {}
    def custom_retry_side_effect(exc, countdown=None, max_retries=None, **kwargs):
        retry_exception_holder['exc'] = exc
        # In a real Celery worker, this would re-queue the task.
        # For testing, we want the test to continue to the point where the task would be tried again.
        # If task_always_eager=True in Celery test config, it would re-run.
        # Here, we'll manually call the task logic again after checking the first retry attempt.
        # This is a common pattern for testing retries without a full worker.
        # We'll just raise the exception to signify the retry would happen.
        # The test then needs to call the task function again.
        raise exc # This simulates Celery re-raising or the retry mechanism.

    mock_celery_task_self.retry = MagicMock(side_effect=custom_retry_side_effect)
    mock_celery_task_self.request.retries = 0 # Simulate first attempt

    # ACT - First attempt (will fail and trigger retry)
    with pytest.raises(RuntimeError, match=transient_error_message):
        await process_video_celery_task(
            mock_celery_task_self,
            video_id_str=str(video_id),
            original_video_path=original_s3_path,
            exercise_type_value=test_video_in_db.exercise_type.value
        )
    
    # ASSERT - First attempt failed and retry was called
    mock_celery_task_self.retry.assert_called_once()
    assert isinstance(retry_exception_holder.get('exc'), RuntimeError)
    assert str(retry_exception_holder['exc']) == transient_error_message
    # Check DB status after first failure (should be PROCESSING_FAILED or similar, error logged)
    await db_session.refresh(test_video_in_db)
    assert test_video_in_db.status == VideoStatus.PROCESSING_FAILED
    assert transient_error_message in test_video_in_db.processing_errors

    # Simulate Celery re-running the task for the retry
    # Reset relevant mocks for the second call if necessary (e.g., call counts if asserting them per attempt)
    # mock_vps_instance.process_video.reset_mock() # Not needed due to side_effect list
    mock_celery_task_self.retry.reset_mock() # Reset retry mock for the second run
    mock_celery_task_self.request.retries = 1 # Simulate being in a retry attempt

    # ACT - Second attempt (should succeed)
    task_result_on_retry = await process_video_celery_task(
        mock_celery_task_self,
        video_id_str=str(video_id),
        original_video_path=original_s3_path,
        exercise_type_value=test_video_in_db.exercise_type.value
    )

    # ASSERT - Second attempt succeeded
    assert task_result_on_retry["status"] == "success"
    assert mock_vps_instance.process_video.call_count == 2 # Called once for fail, once for success
    mock_celery_task_self.retry.assert_not_called() # Retry should not be called on success

    await db_session.refresh(test_video_in_db)
    assert test_video_in_db.status == VideoStatus.POSE_DETECTION_PENDING
    assert test_video_in_db.processed_url == successful_vps_result["normalized_video_path"]
    assert test_video_in_db.processed_frame_paths == successful_vps_result["frame_paths"]
    assert test_video_in_db.processing_errors is None # Errors should be cleared on success

    mock_detect_pose_apply_async.assert_called_once_with(
        args=[str(video_id), successful_vps_result["frame_paths"]]
    )

@pytest.mark.integration
class TestProcessVideoCeleryTask:

    @pytest.fixture
    def mock_db_session(self):
        """Fixture for a mock database session."""
        return MagicMock()

    @pytest.fixture
    def mock_video_service(self):
        """Fixture for a mocked VideoService."""
        return MagicMock()

    @pytest.fixture
    def mock_video_processing_service(self):
        """Fixture for a mocked VideoProcessingService."""
        return MagicMock()

    # We'll need to set up a test database and interact with it for integration tests.
    # For now, focusing on the structure.

    def test_initial_setup_passing(self):
        """A simple test to confirm the test file and pytest are working."""
        assert True

# Tests for `process_video_celery_task` will be added here following the plan:
# - Test successful video processing flow
# - Test flow where VideoProcessingService.process_video raises an exception
# - Test Celery retry mechanisms (if applicable)