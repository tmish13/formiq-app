import pytest
pytestmark = pytest.mark.integration

from unittest.mock import patch, MagicMock, AsyncMock
from uuid6 import uuid7
import os
from uuid import UUID, uuid4 # Ensure uuid4 is imported
from datetime import datetime # Added import
from celery.exceptions import Retry # Add this import

from sqlalchemy.ext.asyncio import async_sessionmaker # ADD THIS IMPORT
from app.models.video import Video
from app.models.enums import VideoStatus, ExerciseType
# Assuming process_video_celery_task is directly importable
from app.tasks.video_tasks import process_video_celery_task 
# For asserting DB state
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.video_processing import VideoProcessResult # For VideoProcessingService mock
from app.core.config import Settings # For mocking get_settings



# Helper for retry mock side_effect
# This is a generic helper. If a test needs to simulate Celery's Retry exception,
# it should configure its specific mock of self.retry to raise `celery.exceptions.Retry`.
def raise_exception_side_effect(exc: Exception, **kwargs):
    """Raises the provided exception. Kwargs are ignored unless exc is a class."""
    if isinstance(exc, type) and issubclass(exc, BaseException):
        raise exc(**kwargs if kwargs else {})
    elif isinstance(exc, BaseException):
        raise exc
    else:
        # Fallback, though exc should always be an exception instance or class
        raise RuntimeError(str(exc)) 

@pytest.fixture
async def test_video_in_db(db_session: AsyncSession) -> Video:
    """Creates a sample video object in the database for testing."""
    unique_suffix = uuid4().hex[:8] # Changed to uuid4()
    print(f"DEBUG: test_video_in_db generated unique_suffix: {unique_suffix}") # DEBUG
    video = Video(
        id=uuid7(),
        user_id=uuid7(), # Example user_id
        filename=f"sample_video_{unique_suffix}.mp4", 
        object_key=f"test_raw_videos/sample_video_{unique_suffix}.mp4", # Made unique
        status=VideoStatus.UPLOADED,
        exercise_type=ExerciseType.SQUAT,
        mime_type="video/mp4",  # Added mime_type
        created_at=datetime.now(), # Added
        updated_at=datetime.now()  # Added
    )
    db_session.add(video)
    await db_session.commit()
    await db_session.refresh(video)
    return video

@pytest.mark.asyncio
@patch('app.tasks.video_tasks.get_settings')
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
    mock_get_settings: MagicMock,
    db_session: AsyncSession,
    test_video_in_db: Video,
    test_async_session_factory: async_sessionmaker[AsyncSession], # INJECT FIXTURE
):
    """
    Scenario: A video is successfully processed by the Celery task without any errors.
    This test verifies the end-to-end happy path:
    1. Video metadata is fetched from the database.
    2. Shared directories are created if they don't exist.
    3. Video bytes are downloaded from S3 (mocked).
    4. VideoProcessingService processes the video (mocked success).
    5. Processed video and frames are uploaded to S3 (mocked).
    6. Video status and metadata (processed key, frame keys, duration, etc.) are updated in the DB.
    7. A subsequent pose detection task is enqueued.
    8. The task returns a success status.
    This ensures the primary functionality of the video processing pipeline for a valid video.
    """
    # ARRANGE
    # 1. Mock settings
    mock_settings = Settings(CELERY_SHARED_DATA_PATH="/tmp/celery_shared_test", AWS_BUCKET_NAME="test-bucket-formiq") # Changed here
    mock_get_settings.return_value = mock_settings

    video_id = test_video_in_db.id
    # Construct S3 path using settings and the object_key from the video model
    original_s3_path = f"s3://{mock_settings.S3_BUCKET}/{test_video_in_db.object_key}" # Changed here

    # 2. Mock os.path.exists and os.makedirs for shared data path
    mock_os_path_exists.return_value = False # Simulate directory doesn't exist initially
    mock_os_makedirs.return_value = None

    # 3. Mock StorageService instance and its download_file_bytes method
    mock_storage_service_instance = MockStorageService.return_value
    mock_storage_service_instance.download_file_bytes = AsyncMock(return_value=b"mock video content")
    mock_storage_service_instance.upload_file_from_path = AsyncMock(return_value="s3://mocked_normalized_path.mp4") # Task expects S3 key
    mock_storage_service_instance.upload_fileobj_to_s3 = AsyncMock(return_value="s3://mocked_frame_path.jpg")   # Task expects S3 key
    mock_storage_service_instance.get_public_url = AsyncMock(return_value="s3://mocked_public_url/processed.mp4") # ADDED

    # 4. Mock VideoProcessingService instance and its process_video method
    #    The task expects a dictionary result from process_video.
    mock_vps_instance = MockVideoProcessingService.return_value
    # Define what the mocked VideoProcessingService will return.
    # 'normalized_video_path' should be a filename, task will construct S3 key.
    # 'frame_paths' should be S3 keys, task will use them directly.
    mock_vps_returned_normalized_filename = "normalized.mp4" # Filename for VPS result
    mock_direct_s3_keys_for_frames = [f"processed_frames/{video_id}/frame1.jpg", f"processed_frames/{video_id}/frame2.jpg"] # S3 keys for frames
    
    # Metadata that VideoProcessingService is expected to return nested under "video_metadata"
    mock_vps_video_metadata = {
        "duration": 5.5,
        "fps": 30.0,
        "width": 1920,
        "height": 1080,
        "actual_frame_count": len(mock_direct_s3_keys_for_frames) 
    }

    mock_process_video_dict_result = {
        "frame_paths": mock_direct_s3_keys_for_frames, 
        "normalized_video_path": mock_vps_returned_normalized_filename, 
        "raw_video_path": "/tmp/celery_shared_test/some_raw_video.mp4",
        "video_metadata": mock_vps_video_metadata, # NESTED METADATA
        "errors": None
    }
    mock_vps_instance.process_video = AsyncMock(return_value=mock_process_video_dict_result)

    # 5. `detect_pose_celery_task.apply_async` is already patched by decorator.

    # 6. Mock 'self' for the bound Celery task
    # mock_celery_task_self = MagicMock() # REMOVED - Unused

    # ACT: Execute the Celery task directly.
    task_result = await process_video_celery_task.run(
        video_id_str=str(video_id),
        original_video_path=original_s3_path, 
        exercise_type_value=test_video_in_db.exercise_type
    )

    # ASSERT
    # 0. Task result
    assert task_result["status"] == "success"
    assert task_result["video_id"] == str(video_id)

    # 1. Settings and OS path checks
    mock_get_settings.assert_called_once()
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
    # await db_session.refresh(test_video_in_db) # REMOVED
    
    # assert test_video_in_db.status == VideoStatus.POSE_DETECTION_PENDING # Final status # REMOVED
    # assert test_video_in_db.processed_object_key == mock_normalized_video_s3_key # This was added in a migration # REMOVED
    # assert test_video_in_db.frame_s3_keys == mock_processed_frame_s3_keys # Corrected field name # REMOVED - (Note: mock_processed_frame_s3_keys was the old var name here)
    # assert test_video_in_db.processed_frame_count == mock_vps_video_metadata["actual_frame_count"] # REMOVED - (Note: mock_frame_count was old var)
    # assert test_video_in_db.duration == mock_vps_video_metadata["duration"] # REMOVED - (Note: mock_video_duration was old var)
    # assert test_video_in_db.fps == mock_vps_video_metadata["fps"] # REMOVED - (Note: mock_fps was old var)
    # assert test_video_in_db.resolution == f'{mock_vps_video_metadata["width"]}x{mock_vps_video_metadata["height"]}' # REMOVED - (Note: mock_video_dimensions was old var)
    # assert test_video_in_db.error_message is None # REMOVED - (Note: processing_errors was old var)
    # print("NOTE: DB assertions for frame_count, duration, fps, width, height need to be confirmed against actual Video model fields.") # REMOVED


    # 5. detect_pose_celery_task.apply_async assertions
    mock_detect_pose_apply_async.assert_called_once_with(
        args=[str(video_id), mock_direct_s3_keys_for_frames] # Use updated frame keys variable
        # Add ,countdown=X if there's a specific delay used in the task
    )

    # Re-fetch for latest state using the test-specific session factory
    async with test_async_session_factory() as new_db_session_for_assertion:
        video_from_db_after_task = await new_db_session_for_assertion.get(Video, video_id)
        assert video_from_db_after_task is not None, "Video not found in DB after task execution (successful flow)."
        assert video_from_db_after_task.status == VideoStatus.POSE_DETECTION_PENDING
        
        # Assert the S3 key constructed by the task for the normalized video.
        expected_processed_object_key = f"processed_videos/{video_id}/normalized_{mock_vps_returned_normalized_filename}"
        assert video_from_db_after_task.processed_object_key == expected_processed_object_key
        
        # Assert that the S3 keys for frames (directly from mock) are stored.
        assert video_from_db_after_task.frame_s3_keys == mock_direct_s3_keys_for_frames
        
        assert video_from_db_after_task.error_message is None
        
        # Assert metadata from the nested structure
        assert video_from_db_after_task.duration == mock_vps_video_metadata["duration"]
        assert video_from_db_after_task.fps == mock_vps_video_metadata["fps"]
        assert video_from_db_after_task.resolution == f'{mock_vps_video_metadata["width"]}x{mock_vps_video_metadata["height"]}'
        assert video_from_db_after_task.processed_frame_count == mock_vps_video_metadata["actual_frame_count"]

    # TODO: Add test for VideoProcessingService failure (e.g., process_video raises error)
    # TODO: Add test for S3 download failure
    # TODO: Add test for local file not found (if original_video_path is local)
    # TODO: Add test for CELERY_SHARED_DATA_PATH not configured
    pass # This pass is for the test function body

    # Add more tests:
    # - Test case where VideoProcessingService.process_video raises an exception
    # - Test case where Video object is not found
    # pass # Placeholder for more tests # REMOVED

@pytest.mark.asyncio
@patch('app.tasks.video_tasks.get_settings')
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
    mock_get_settings: MagicMock,
    db_session: AsyncSession,
    test_video_in_db: Video,
    test_async_session_factory: async_sessionmaker[AsyncSession], # INJECT FIXTURE
):
    """
    Scenario: The VideoProcessingService (VPS) encounters an unrecoverable error
    while trying to process the video (e.g., ffmpeg error, corrupt video data).
    This test verifies that:
    1. The task attempts to process the video.
    2. The VPS failure is caught by the task.
    3. The task calls its 'retry' method, which is mocked here to simply re-raise the original error 
       (simulating that retries are exhausted or the error is non-transient for this specific test's purpose).
    4. The video's status in the database is updated to PROCESSING_FAILED.
    5. An error message is recorded in the video's error_message field.
    6. No pose detection task is enqueued.
    This ensures graceful handling of critical processing failures within an external service.
    """
    # ARRANGE
    mock_settings = Settings(CELERY_SHARED_DATA_PATH="/tmp/celery_shared_test_vps_fail", AWS_BUCKET_NAME="test-bucket-formiq")
    mock_get_settings.return_value = mock_settings

    video_id = test_video_in_db.id
    original_s3_path = f"s3://{mock_settings.S3_BUCKET}/{test_video_in_db.object_key}"
    simulated_error_message = "Simulated video processing error from VPS"

    mock_os_path_exists.return_value = False 
    mock_os_makedirs.return_value = None

    mock_storage_service_instance = MockStorageService.return_value
    mock_storage_service_instance.download_file_bytes = AsyncMock(return_value=b"mock video content")

    mock_vps_instance = MockVideoProcessingService.return_value
    mock_vps_instance.process_video = AsyncMock(side_effect=RuntimeError(simulated_error_message))

    # Patch the .retry attribute ON THE TASK OBJECT ITSELF for this test's scope.
    # The side_effect re-raises the original error to halt processing for this test.
    with patch.object(process_video_celery_task, 'retry', side_effect=raise_exception_side_effect) as mock_actual_task_retry:
        # ACT
        with pytest.raises(RuntimeError, match=simulated_error_message):
            await process_video_celery_task.run( # Use .run() for consistency
                video_id_str=str(video_id),
                original_video_path=original_s3_path, 
                exercise_type_value=test_video_in_db.exercise_type
            )

    # ASSERT
    MockStorageService.assert_called_once_with(settings=mock_settings)
    mock_storage_service_instance.download_file_bytes.assert_called_once_with(original_s3_path)
    
    expected_output_dir = os.path.join(mock_settings.CELERY_SHARED_DATA_PATH, "processed_frames", str(video_id))
    mock_os_path_exists.assert_called_once_with(expected_output_dir)
    mock_os_makedirs.assert_called_once_with(expected_output_dir, exist_ok=True) 

    MockVideoProcessingService.assert_called_once_with(app_settings=mock_settings)
    mock_vps_instance.process_video.assert_called_once_with(
        video_data=b"mock video content",
        exercise_type=test_video_in_db.exercise_type,
        save_processed_frames=True,
        base_output_path=expected_output_dir
    )
    mock_detect_pose_apply_async.assert_not_called()

    # Re-fetch the video object to ensure we have the latest state from the DB using the test-specific factory
    async with test_async_session_factory() as new_db_session_for_assertion:
        video_from_db_after_task = await new_db_session_for_assertion.get(Video, test_video_in_db.id)
        assert video_from_db_after_task is not None, "Video not found in DB after task execution (VPS failure)."
        assert video_from_db_after_task.status == VideoStatus.PROCESSING_FAILED
        assert video_from_db_after_task.error_message is not None
        assert simulated_error_message in video_from_db_after_task.error_message
    
    mock_actual_task_retry.assert_called_once() # Ensure retry was attempted (and failed, per mock setup)
    pass 

@pytest.mark.asyncio
@patch('app.tasks.video_tasks.get_settings')
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
    mock_get_settings: MagicMock,
    db_session: AsyncSession,
    test_video_in_db: Video,
    test_async_session_factory: async_sessionmaker[AsyncSession], # INJECT FIXTURE
):
    """
    Scenario: The task fails to download the original video from S3.
    This could be due to network issues, incorrect S3 path, or permissions problems.
    This test verifies that:
    1. The task attempts to download the video from S3.
    2. The S3 download failure (mocked) is caught.
    3. The task calls its 'retry' method, which is mocked to raise the original error.
    4. The video's status is updated to PROCESSING_FAILED in the database.
    5. An appropriate error message is stored in error_message.
    6. No further processing (VPS, pose detection) is attempted.
    This ensures robustness against failures in the initial data retrieval step.
    """
    # ARRANGE
    mock_settings = Settings(CELERY_SHARED_DATA_PATH="/tmp/celery_shared_s3_fail", AWS_BUCKET_NAME="test-bucket-formiq") # Changed here
    mock_get_settings.return_value = mock_settings

    video_id = test_video_in_db.id
    original_s3_path = f"s3://{mock_settings.S3_BUCKET}/{test_video_in_db.object_key}" # Changed here
    simulated_error_message = "Simulated S3 download error"

    # StorageService.download_file_bytes raises an error
    mock_storage_service_instance = MockStorageService.return_value
    mock_storage_service_instance.download_file_bytes = AsyncMock(side_effect=RuntimeError(simulated_error_message))

    mock_vps_instance = MockVideoProcessingService.return_value # Get instance for assertion

    # mock_celery_task_self = MagicMock() # REMOVED - Unused
    with patch.object(process_video_celery_task, 'retry', side_effect=raise_exception_side_effect) as mock_actual_task_retry:
        # ACT & ASSERT for exception from task
        with pytest.raises(RuntimeError, match=simulated_error_message):
            await process_video_celery_task( # THIS IS THE ORIGINAL ERROR LOCATION, .run() was not used here previously
                # mock_celery_task_self, # REMOVED
                str(video_id),
                original_s3_path,
                test_video_in_db.exercise_type
            )

    # ASSERT MOCKS & DB
    MockStorageService.assert_called_once_with(settings=mock_settings)
    mock_storage_service_instance.download_file_bytes.assert_called_once_with(original_s3_path)
    
    # These should not have been called if download fails before they are used
    mock_os_path_exists.assert_not_called() 
    mock_os_makedirs.assert_not_called()

    MockVideoProcessingService.assert_not_called() 
    mock_vps_instance.process_video.assert_not_called()

    # Assert database state using the test-specific session factory
    async with test_async_session_factory() as new_db_session_for_assertion:
        video_from_db_after_task = await new_db_session_for_assertion.get(Video, video_id)
        assert video_from_db_after_task is not None, "Video not found in DB after task execution (S3 download failure)."
        assert video_from_db_after_task.status == VideoStatus.PROCESSING_FAILED
        assert video_from_db_after_task.error_message is not None
        assert simulated_error_message in video_from_db_after_task.error_message
    pass 

@pytest.mark.asyncio
@patch('app.tasks.video_tasks.get_settings')
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
    mock_get_settings: MagicMock,
    db_session: AsyncSession,
    test_video_in_db: Video,
    test_async_session_factory: async_sessionmaker[AsyncSession], # INJECT FIXTURE
):
    """
    Scenario: The task is configured to process a video from a local file path (e.g., after S3 download),
    but the file is unexpectedly missing at that path.
    This test verifies that:
    1. The task checks for the existence of the local file (mocked to simulate it being missing after download).
    2. A FileNotFoundError is raised internally by the task.
    3. The video's status is updated to PROCESSING_FAILED.
    4. An error message indicating the file not found is stored in error_message.
    5. No pose detection task is enqueued.
    This ensures correct error handling for local filesystem issues during processing.
    Note: This test assumes a two-step download then process flow where the local file check happens.
    If the task streams directly from S3 to VPS, this test might need adjustment or refer to a different error.
    For now, we assume `original_video_path` could be a local path that is then checked.
    Based on current task logic, it seems to download to a temporary local path first derived from CELERY_SHARED_DATA_PATH.
    This test will mock os.path.exists for that *temporary local path* to be False.
    """
    # ARRANGE
    mock_settings = Settings(CELERY_SHARED_DATA_PATH="/tmp/celery_shared_local_fail", AWS_BUCKET_NAME="test-bucket-formiq")
    mock_get_settings.return_value = mock_settings

    video_id_for_task = test_video_in_db.id 
    # This is the path that will be checked by os.path.exists inside the task *after* download (if it were S3)
    # Or, if original_video_path is already local, this is it.
    # The task internally constructs local_input_path = os.path.join(shared_path, video_id_str, os.path.basename(original_video_path_obj.path))
    # if original_video_path is an S3 path. Let's assume original_video_path IS the local path for this test.
    original_local_video_path = f"/tmp/celery_shared_local_fail/{video_id_for_task}/{test_video_in_db.filename}"
    expected_error_message_in_db = f"Original video not found at {original_local_video_path}" 
    # The task directly returns the str(fnf_error) which is just the message, not prefixed.
    expected_task_return_error = expected_error_message_in_db 

    def os_path_exists_side_effect(path_arg):
        if path_arg == original_local_video_path: # This is the critical check for the input file
            return False 
        # Allow output directory creation check to pass or fail depending on other mocks
        # For this test, the output dir check might not even be reached.
        elif path_arg == os.path.join(mock_settings.CELERY_SHARED_DATA_PATH, "processed_frames", str(video_id_for_task)):
            return False # Simulate output dir also doesn't exist, for os.makedirs to be called
        return True 
    mock_os_path_exists.side_effect = os_path_exists_side_effect
    mock_os_makedirs.return_value = None 

    # ACT: The task should catch FileNotFoundError and return a dict, not call self.retry by default.
    task_result = await process_video_celery_task.run(
        video_id_str=str(video_id_for_task), 
        original_video_path=original_local_video_path, # Pass the local path directly
        exercise_type_value=test_video_in_db.exercise_type
    )

    # ASSERT: Task should return a failure dict for FileNotFoundError
    assert task_result["status"] == "failed"
    assert task_result["video_id"] == str(video_id_for_task)
    assert expected_task_return_error == task_result["error"] # Check task's immediate return (exact match)

    # MOCKS & DB
    # StorageService.download_file_bytes should NOT be called if original_video_path is local and not found
    MockStorageService.return_value.download_file_bytes.assert_not_called()

    # os.path.exists should have been called for the input local_video_path
    mock_os_path_exists.assert_any_call(original_local_video_path)
    # os.makedirs for output_dir might be called if the shared_path check passes before file existence.
    # Based on current task structure, this is unlikely if local_input_path check fails first.
    # Let's assume it's not called if the input file doesn't exist.
    mock_os_makedirs.assert_not_called() 

    MockVideoProcessingService.return_value.process_video.assert_not_called()
    mock_detect_pose_apply_async.assert_not_called()

    # Assert Database state using the test-specific session factory
    async with test_async_session_factory() as new_db_session_for_assertion:
        video_from_db_after_task = await new_db_session_for_assertion.get(Video, video_id_for_task)
        assert video_from_db_after_task is not None, "Video not found in DB after task execution (local file not found)."
        assert video_from_db_after_task.status == VideoStatus.PROCESSING_FAILED
        assert video_from_db_after_task.error_message is not None 
        assert expected_error_message_in_db in video_from_db_after_task.error_message 
    pass

@pytest.mark.asyncio
@patch('app.tasks.video_tasks.get_settings')
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
    mock_get_settings: MagicMock,
    db_session: AsyncSession,
    test_video_in_db: Video,
    test_async_session_factory: async_sessionmaker[AsyncSession], # INJECT FIXTURE
):
    """
    Scenario: The Celery task is missing a critical configuration for CELERY_SHARED_DATA_PATH
    (e.g., it's an empty string or None).
    This path is required for temporary file storage during processing.
    This test verifies that:
    1. The task attempts to get settings and identifies the missing configuration.
    2. A ValueError (or similar configuration error) is raised by the task logic before major processing begins.
    3. The video's status is updated to PROCESSING_FAILED in the DB.
    4. An appropriate error message indicating the misconfiguration is stored in error_message.
    5. No S3 download, VPS processing, or pose detection is attempted.
    This ensures the task fails fast and clearly if essential configurations are missing.
    """
    # ARRANGE
    # Simulate CELERY_SHARED_DATA_PATH being an empty string
    mock_settings = Settings(CELERY_SHARED_DATA_PATH="", AWS_BUCKET_NAME="test-bucket-formiq")
    mock_get_settings.return_value = mock_settings

    video_id = test_video_in_db.id
    original_s3_path = f"s3://{mock_settings.S3_BUCKET}/{test_video_in_db.object_key}"
    expected_config_error_message = "CELERY_SHARED_DATA_PATH not configured." # Exact message from task's ValueError
    # This is the message that VideoService will construct and store in the DB
    expected_db_error_message = f"Configuration error: {expected_config_error_message}"
    # This is the message the task returns in its result dict["error"]
    expected_task_return_error_dict_message = f"Configuration error: {expected_config_error_message}"


    # Ensure StorageService.download_file_bytes is an AsyncMock for this test
    mock_storage_service_instance = MockStorageService.return_value
    mock_storage_service_instance.download_file_bytes = AsyncMock(return_value=b"mock video content for config fail test")

    # ACT: Call the task directly using .run()
    task_result = await process_video_celery_task.run(
            video_id_str=str(video_id),
            original_video_path=original_s3_path, 
        exercise_type_value=test_video_in_db.exercise_type
        )

    # ASSERT: Task should return a failure dict for this specific configuration error
    assert task_result["status"] == "failed"
    assert task_result["video_id"] == str(video_id)
    assert task_result["error"] == expected_task_return_error_dict_message

    # ASSERT MOCKS & DB
    # StorageService.download_file_bytes *IS* called before the CELERY_SHARED_DATA_PATH check in the current task logic.
    MockStorageService.assert_called_once_with(settings=mock_settings)
    MockStorageService.return_value.download_file_bytes.assert_called_once_with(original_s3_path)
    
    # These should not be called if the config check fails early (after download)
    mock_os_path_exists.assert_not_called()
    mock_os_makedirs.assert_not_called()

    MockVideoProcessingService.assert_not_called()
    mock_detect_pose_apply_async.assert_not_called()

    # Assert database state (error should be logged) using the test-specific session factory
    async with test_async_session_factory() as new_db_session_for_assertion:
        video_from_db_after_task = await new_db_session_for_assertion.get(Video, video_id)
        assert video_from_db_after_task is not None, "Video not found in DB after task execution (missing shared path)."
        assert video_from_db_after_task.status == VideoStatus.PROCESSING_FAILED
        assert video_from_db_after_task.error_message is not None 
        assert expected_db_error_message in video_from_db_after_task.error_message 

@pytest.mark.asyncio
@patch('app.tasks.video_tasks.get_settings')
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
    mock_get_settings: MagicMock,
    db_session: AsyncSession,
    test_video_in_db: Video,
    test_async_session_factory: async_sessionmaker[AsyncSession], # INJECT FIXTURE
):
    """
    Scenario: The VideoProcessingService (VPS) runs successfully but returns an incomplete result,
    for example, missing the 'normalized_video_path' or 'frame_paths' which are critical.
    This test verifies that:
    1. The task receives the incomplete result from VPS.
    2. The task identifies the missing critical data.
    3. The video's status is updated to VIDEO_PROCESSING_FAILED in the database.
    4. An error message indicating the nature of the incomplete data is stored in error_message.
    5. No pose detection task is enqueued.
    This ensures robustness against unexpected or malformed results from external services.
    """
    # ARRANGE
    mock_settings = Settings(CELERY_SHARED_DATA_PATH="/tmp/celery_shared_incomplete", AWS_BUCKET_NAME="test-bucket-formiq")
    mock_get_settings.return_value = mock_settings

    video_id = test_video_in_db.id
    original_s3_path = f"s3://{mock_settings.S3_BUCKET}/{test_video_in_db.object_key}"
    # This is the error message logged by the task and then set in the DB by VideoService
    expected_db_error_message = "Internal error: Missing frame paths or normalized video path after processing."
    # This is the exact error message returned in the task's result dict["error"]
    expected_task_return_error_dict_message = "Missing frame_paths or normalized_video_path"


    mock_os_path_exists.return_value = False # For output dir creation
    mock_os_makedirs.return_value = None

    mock_storage_service_instance = MockStorageService.return_value
    mock_storage_service_instance.download_file_bytes = AsyncMock(return_value=b"mock video content")
    # Mock S3 uploads as they might be called before the error is fully processed in the task
    mock_storage_service_instance.upload_file_from_path = AsyncMock(return_value="s3://mocked_normalized_incomplete.mp4")
    mock_storage_service_instance.upload_fileobj_to_s3 = AsyncMock(return_value="s3://mocked_frame_incomplete.jpg")

    mock_vps_instance = MockVideoProcessingService.return_value
    # Simulate VPS result missing 'frame_paths'
    mock_incomplete_process_video_result = {
        "normalized_video_path": f"normalized_videos/{video_id}/normalized.mp4", # Has normalized path
        # "frame_paths": ["some/path/frame1.jpg"], # INTENTIONALLY MISSING frame_paths
        "raw_video_path": "/tmp/celery_shared_incomplete/some_raw_video.mp4",
        "processed_frame_count": 0, "video_duration": 5.0, "fps": 30.0,
        "video_dimensions": (1280, 720), "errors": None
    }
    mock_vps_instance.process_video = AsyncMock(return_value=mock_incomplete_process_video_result)

    # ACT: Call .run() as the task handles this error internally and returns a dict
    task_result = await process_video_celery_task.run(
        video_id_str=str(video_id),
        original_video_path=original_s3_path, 
        exercise_type_value=test_video_in_db.exercise_type
    )

    # ASSERT: Task should return a specific failure dict for this case
    assert task_result["status"] == "failed"
    assert task_result["video_id"] == str(video_id)
    assert task_result["error"] == expected_task_return_error_dict_message

    # MOCKS & DB
    expected_output_dir = os.path.join(mock_settings.CELERY_SHARED_DATA_PATH, "processed_frames", str(video_id))
    mock_os_path_exists.assert_called_once_with(expected_output_dir)
    mock_os_makedirs.assert_called_once_with(expected_output_dir, exist_ok=True)
    mock_storage_service_instance.download_file_bytes.assert_called_once_with(original_s3_path)
    mock_vps_instance.process_video.assert_called_once() # Called, but returned incomplete data

    mock_detect_pose_apply_async.assert_not_called()

    # Re-fetch for latest DB state using the test-specific session factory
    async with test_async_session_factory() as new_db_session_for_assertion:
        video_from_db_after_task = await new_db_session_for_assertion.get(Video, video_id)
        assert video_from_db_after_task is not None, "Video not found in DB after task (VPS incomplete result)."
        assert video_from_db_after_task.status == VideoStatus.VIDEO_PROCESSING_FAILED 
        assert video_from_db_after_task.error_message is not None 
        assert expected_db_error_message in video_from_db_after_task.error_message 
    pass

@pytest.mark.asyncio
@patch('app.tasks.video_tasks.get_settings')
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
    mock_get_settings: MagicMock,
    db_session: AsyncSession
    # test_video_in_db: Video, # This fixture IS NOT used - REMOVE
):
    """Test process_video_celery_task when the video ID is not found in the database."""
    # ARRANGE
    non_existent_video_id = uuid7() # Use this
    original_s3_path = f"s3://some-bucket/some_key_for_non_existent.mp4" # Use a distinct path
    simulated_db_error_message = f"Video with ID {non_existent_video_id} not found in DB during status update." # Use this

    mock_settings = Settings(CELERY_SHARED_DATA_PATH="/tmp/celery_shared_video_nf", AWS_BUCKET_NAME="test-bucket-formiq")
    mock_get_settings.return_value = mock_settings
    
    with patch('app.tasks.video_tasks.VideoService') as MockVideoServiceForNotFound:
        mock_vs_instance_nf = MockVideoServiceForNotFound.return_value
        db_lookup_exception = Exception(simulated_db_error_message) 
        mock_vs_instance_nf.set_video_status_from_task = AsyncMock(side_effect=db_lookup_exception)

        with pytest.raises(Exception, match=simulated_db_error_message):
            await process_video_celery_task(
                # mock_celery_task_self, # REMOVED
                str(non_existent_video_id),
                original_s3_path,
                "SQUAT"
            )

    MockVideoServiceForNotFound.assert_called_once()
    mock_vs_instance_nf.set_video_status_from_task.assert_any_call(
        non_existent_video_id, # Use correct var 
        new_status=VideoStatus.PROCESSING
    )
    
    MockStorageService.return_value.download_file_bytes.assert_not_called()

@pytest.mark.asyncio
@patch('app.tasks.video_tasks.get_settings')
@patch('app.tasks.video_tasks.StorageService')
@patch('app.tasks.video_tasks.VideoProcessingService')
@patch('app.tasks.video_tasks.detect_pose_celery_task.apply_async')
@patch('app.tasks.video_tasks.os.path.exists')
@patch('app.tasks.video_tasks.os.makedirs')
@patch.object(process_video_celery_task, 'retry') # This mocks process_video_celery_task.retry
async def test_process_video_celery_task_retry_and_succeed( 
    mock_celery_self_retry: MagicMock,          # Mock for task.retry()
    mock_os_makedirs: MagicMock,
    mock_os_path_exists: MagicMock,
    mock_detect_pose_apply_async: MagicMock,
    MockVideoProcessingService: MagicMock, 
    MockStorageService: MagicMock,
    mock_get_settings: MagicMock,
    db_session: AsyncSession,
    test_video_in_db: Video,
    test_async_session_factory: async_sessionmaker[AsyncSession], # INJECT FIXTURE
): 
    """
    Scenario: A video processing task encounters a temporary issue with an external
    service (VideoProcessingService) during its first execution attempt.
    The task is configured to retry on such failures.
    This test verifies that:
    1. The task correctly calls its 'retry' method when the transient error occurs.
    2. The 'retry' call signals a Celery Retry exception.
    3. Upon simulated re-execution by a Celery worker (i.e., calling the task again),
       the external service now succeeds.
    4. The task completes successfully on the subsequent attempt, updating the video's
       status and metadata in the database appropriately.
    This ensures the task's resilience to transient external failures.
    """
    # ARRANGE
    mock_settings = Settings(CELERY_SHARED_DATA_PATH="/tmp/celery_shared_retry_succeed", AWS_BUCKET_NAME="test-bucket-formiq")
    mock_get_settings.return_value = mock_settings

    video_id = test_video_in_db.id
    original_s3_path = f"s3://{mock_settings.S3_BUCKET}/{test_video_in_db.object_key}"
    transient_error_message = "Simulated transient VPS error during retry test"

    mock_os_path_exists.return_value = False # Shared path doesn't exist initially
    mock_os_makedirs.return_value = None

    mock_storage_service_instance = MockStorageService.return_value
    mock_storage_service_instance.download_file_bytes = AsyncMock(return_value=b"mock video content for retry")
    mock_storage_service_instance.upload_file_from_path = AsyncMock(return_value="s3://mocked_normalized_retry.mp4")
    mock_storage_service_instance.upload_fileobj_to_s3 = AsyncMock(return_value="s3://mocked_frame_retry.jpg")
    mock_storage_service_instance.get_public_url = AsyncMock(return_value="s3://mocked_public_url/processed_retry.mp4")

    mock_vps_instance = MockVideoProcessingService.return_value
    # Define what the VPS mock returns on its successful (second) call
    # 'normalized_video_path' should be a filename, task will construct S3 key.
    # 'frame_paths' should be S3 keys, task will use them directly.
    mock_vps_returned_filename_on_retry = "normalized_on_retry_from_vps.mp4" # RESTORED
    mock_s3_keys_frames_on_retry = [ # RESTORED
        f"processed_frames/{video_id}/frame_A_on_retry_from_vps.jpg",
        f"processed_frames/{video_id}/frame_B_on_retry_from_vps.png"
    ]
    # Metadata that VideoProcessingService is expected to return nested under "video_metadata" on success
    mock_vps_video_metadata_on_retry = {
        "duration": 1.0,
        "fps": 30.0,
        "width": 640,
        "height": 360,
        "actual_frame_count": len(mock_s3_keys_frames_on_retry) # RESTORED (uses correct var)
    }
    
    successful_vps_result = {
        "frame_paths": mock_s3_keys_frames_on_retry, # RESTORED
        "normalized_video_path": mock_vps_returned_filename_on_retry, # RESTORED
        "raw_video_path": f"/tmp/celery_shared_retry_succeed/{uuid4()}.mp4", 
        "video_metadata": mock_vps_video_metadata_on_retry, 
        "errors": None
    }

    # This state variable will be captured by the side_effect closure
    vps_call_count = 0
    async def vps_fail_then_succeed_side_effect(*args, **kwargs):
        nonlocal vps_call_count
        vps_call_count += 1
        if vps_call_count == 1:
            print(f"DEBUG: vps_fail_then_succeed_side_effect: Raising error on call {vps_call_count}")
            raise RuntimeError(transient_error_message)
        print(f"DEBUG: vps_fail_then_succeed_side_effect: Returning success on call {vps_call_count}")
        return successful_vps_result

    mock_vps_instance.process_video.side_effect = vps_fail_then_succeed_side_effect

    # Configure the mock for task.retry() to raise Celery's Retry exception
    # This is what the task itself calls (e.g., self.retry(exc=e, ...))
    # The actual signature of self.retry can take other args like countdown, max_retries, etc.
    # The task code calls it with `self.retry(exc=e)`. 
    # The decorator @app.task(..., default_retry_delay=60, max_retries=3) provides defaults.
    def actual_celery_retry_raiser(exc: Exception, **kwargs):
        print(f"DEBUG: actual_celery_retry_raiser called with exc: {exc}, kwargs: {kwargs}")
        # The mock should simulate the behavior of self.retry by raising the Retry exception.
        # It should pass through any arguments that self.retry would normally use.
        # If the task calls self.retry(exc=e), kwargs here will likely include what Celery provides (eta, etc.)
        # plus what the decorator defaults provide (countdown, max_retries if not overridden by self.retry call)
        raise Retry(exc=exc, **kwargs) # Pass through all kwargs

    mock_celery_self_retry.side_effect = actual_celery_retry_raiser

    # ACT & ASSERT - First Attempt (should trigger retry)
    print("DEBUG: First task call expecting Retry...")
    with pytest.raises(Retry) as excinfo:
        await process_video_celery_task(
            # When calling a task function directly that is decorated with @app.task(bind=True),
            # and that task's code calls self.retry(), the first argument to process_video_celery_task
            # should be the task instance (self). However, our @patch.object targets the
            # 'retry' attribute of the 'process_video_celery_task' *function object* itself.
            # Celery's Task.run() or direct invocation without bind=True context might behave differently.
            # For bound tasks, when you call `task.run()`, Celery supplies `self`.
            # If we call `process_video_celery_task()` directly, the `self` argument is the first one.
            # Let's assume the task signature is process_video_celery_task(self, video_id_str, ...)
            # So, we need to pass a mock for 'self' if the task is bound and uses 'self'.
            # The `process_video_celery_task` is indeed bind=True.
            # The @patch.object should correctly patch `process_video_celery_task.retry`.
            # The issue is that when `process_video_celery_task` is called directly (not via .run or .delay),
            # the `self` argument must be the *first* positional argument if it's to be used.
            # However, the Celery machinery sets up `self` when it executes the task.
            # The most straightforward way for an integration test is to call `task.run()`
            # if we need to test `self.retry` behavior accurately.
            # The error "TypeError: process_video_celery_task() got multiple values for argument 'video_id_str'"
            # from previous logs suggests direct call was passing mocks meant for `self` also as `video_id_str`.

            # Let's use .run() which correctly supplies `self` to the task.
            video_id_str=str(video_id),
            original_video_path=original_s3_path,
            exercise_type_value=test_video_in_db.exercise_type
        )
    
    # Assert that task.retry() was called, which raised Celery's Retry exception
    mock_celery_self_retry.assert_called_once()
    assert isinstance(excinfo.value.exc, RuntimeError), "The exception wrapped in Retry should be the original RuntimeError"
    assert str(excinfo.value.exc) == transient_error_message
    assert mock_vps_instance.process_video.call_count == 1 # VPS was called once and failed

    # ACT & ASSERT - Second Attempt (simulating Celery worker retry)
    print("DEBUG: Second task call expecting Success...")
    # Reset the retry mock for the second call if needed, though it shouldn't be hit again
    mock_celery_self_retry.reset_mock(side_effect=True) # Reset call history, keep side_effect if it were stateful

    task_result_on_retry = await process_video_celery_task.run( # Use .run() again
        video_id_str=str(video_id),
        original_video_path=original_s3_path,
        exercise_type_value=test_video_in_db.exercise_type
    )

    # Assertions for successful completion on retry
    assert task_result_on_retry["status"] == "success"
    assert task_result_on_retry["video_id"] == str(video_id)
    assert mock_vps_instance.process_video.call_count == 2 # VPS called again and succeeded
    mock_celery_self_retry.assert_not_called() # task.retry() should not be called on the successful attempt

    # Database assertions: Re-fetch the video to ensure changes are reflected using a new session
    async with test_async_session_factory() as new_db_session_for_assertion:
        video_from_db_after_retry = await new_db_session_for_assertion.get(Video, video_id)
        assert video_from_db_after_retry is not None, "Video not found in DB after retry and success."
        assert video_from_db_after_retry.status == VideoStatus.POSE_DETECTION_PENDING
        
        # Assert S3 key constructed by task for normalized video.
        expected_processed_object_key_on_retry = f"processed_videos/{video_id}/normalized_{mock_vps_returned_filename_on_retry}" # RESTORED
        assert video_from_db_after_retry.processed_object_key == expected_processed_object_key_on_retry # RESTORED
        # Assert that the S3 keys for frames (directly returned by VPS mock) are stored.
        assert video_from_db_after_retry.frame_s3_keys == mock_s3_keys_frames_on_retry # RESTORED
        
        assert video_from_db_after_retry.error_message is None 
        # Assert metadata from the nested structure
        assert video_from_db_after_retry.duration == mock_vps_video_metadata_on_retry["duration"]
        assert video_from_db_after_retry.fps == mock_vps_video_metadata_on_retry["fps"]
        assert video_from_db_after_retry.resolution == f'{mock_vps_video_metadata_on_retry["width"]}x{mock_vps_video_metadata_on_retry["height"]}'
        assert video_from_db_after_retry.processed_frame_count == mock_vps_video_metadata_on_retry["actual_frame_count"]


    mock_detect_pose_apply_async.assert_called_once_with(
        args=[str(video_id), mock_s3_keys_frames_on_retry] # RESTORED
        # Add other kwargs if your task uses them, e.g., queue, countdown
    )